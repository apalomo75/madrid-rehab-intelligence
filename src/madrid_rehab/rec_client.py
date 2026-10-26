"""Consulta REC individual y explícita; sin persistencia, cookies ni reintentos."""

import os
import re
import socket
from http.client import HTTPException
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .administrative import key
from .rec import parse_rec

BASE_URL = "https://servpub.madrid.es/GITEP_WBFICHA/SGiteCons"
MAX_BYTES = 2_000_000
TIMEOUT = 15


class RecError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


def validate_ndp(ndp):
    if not isinstance(ndp, str) or not re.fullmatch(r"[0-9]{8}", ndp):
        raise RecError("invalid_ndp", "NDP inválido")
    return ndp


def official_url(ndp=None):
    return (
        BASE_URL
        if ndp is None
        else BASE_URL + "?" + urlencode(dict(opcion="6", origen="I", ndp=validate_ndp(ndp)))
    )


@dataclass(frozen=True)
class Policy:
    enabled: bool = False
    automation_evidence: str = ""
    reuse_evidence: str = ""
    public: bool = False

    @property
    def allowed(self):
        return bool(
            self.enabled and self.automation_evidence and self.reuse_evidence and not self.public
        )

    @classmethod
    def from_env(cls):
        return cls(
            os.environ.get("REC_LIVE_ENABLED", "false").lower() == "true"
            and os.environ.get("MADRID_REHAB_OFFLINE", "0") != "1",
            os.environ.get("REC_AUTOMATION_EVIDENCE", ""),
            os.environ.get("REC_REUSE_EVIDENCE", ""),
            os.environ.get("MADRID_REHAB_PUBLIC", "0") == "1",
        )


@dataclass(frozen=True)
class Response:
    content: bytes
    status: int = 200
    content_type: str = "text/html"
    encoding: str = "iso-8859-1"
    origin: str = "http"


class OfficialRedirects(HTTPRedirectHandler):
    max_redirections = 3
    max_repeats = 1

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlsplit(newurl)
        if (target.scheme, target.netloc, target.path) != (
            "https",
            "servpub.madrid.es",
            "/GITEP_WBFICHA/SGiteCons",
        ):
            raise RecError(
                "redirect", "Redirección fuera de la consulta oficial; revisión necesaria"
            )
        requested_ndp = parse_qs(urlsplit(req.full_url).query).get("ndp")
        returned_ndp = parse_qs(target.query).get("ndp")
        if returned_ndp and returned_ndp != requested_ndp:
            raise RecError("identity", "Redirección a otro NDP")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class HttpProvider:
    def __call__(self, ndp):
        request = Request(
            official_url(ndp), headers={"User-Agent": "MadridRehab-REC/1.0", "Accept": "text/html"}
        )
        try:
            with build_opener(ProxyHandler({}), OfficialRedirects()).open(
                request, timeout=TIMEOUT
            ) as r:
                content = r.read(MAX_BYTES + 1)
                if len(content) > MAX_BYTES:
                    raise RecError("incomplete", "Respuesta supera el tamaño máximo")
                length = r.headers.get("Content-Length")
                if length and len(content) != int(length):
                    raise RecError("incomplete", "Respuesta incompleta")
                return Response(
                    content,
                    r.status,
                    r.headers.get_content_type(),
                    r.headers.get_content_charset() or "iso-8859-1",
                )
        except HTTPError as exc:
            raise RecError("http", f"HTTP no satisfactorio: {exc.code}") from exc
        except (TimeoutError, socket.timeout) as exc:
            raise RecError("timeout", "Timeout al consultar REC") from exc
        except URLError as exc:
            code = (
                "timeout"
                if isinstance(exc.reason, (TimeoutError, socket.timeout))
                else "connection"
            )
            raise RecError(
                code,
                "REC temporalmente inaccesible"
                if code == "connection"
                else "Timeout al consultar REC",
            ) from exc
        except HTTPException as exc:
            raise RecError("incomplete", "Respuesta HTTP interrumpida") from exc
        except (OSError, ValueError) as exc:
            raise RecError(
                "connection", "REC temporalmente inaccesible o respuesta interrumpida"
            ) from exc


class LocalProvider:
    """Solo pruebas por inyección; nunca seleccionable desde la aplicación."""

    def __init__(self, path, ndp="11140360"):
        self.path, self.ndp = Path(path), validate_ndp(ndp)

    def __call__(self, ndp):
        if ndp != self.ndp:
            raise RecError("identity", "La captura local pertenece a otro NDP")
        return Response(self.path.read_bytes(), origin="local_historical")


def consult(ndp, address, *, policy=None, provider=None, parser=parse_rec):
    validate_ndp(ndp)
    policy = policy or Policy.from_env()
    if not policy.allowed:
        raise RecError("disabled", "Consulta integrada no habilitada")
    if not address:
        raise RecError("identity", "Dirección oficial no disponible para contrastar")
    response = (provider or HttpProvider())(ndp)
    if response.status != 200:
        raise RecError("http", f"HTTP no satisfactorio: {response.status}")
    if len(response.content) > MAX_BYTES:
        raise RecError("incomplete", "Respuesta supera el tamaño máximo")
    if response.content_type != "text/html":
        raise RecError("unexpected_html", "Respuesta no HTML")
    try:
        text = response.content.decode(response.encoding)
    except (UnicodeError, LookupError) as exc:
        raise RecError("unexpected_html", "Codificación HTML inesperada") from exc
    normalized = key(text)
    if any(t in normalized for t in ("SESION CADUCADA", "SESION EXPIRADA", "SESSION EXPIRED")):
        raise RecError("session", "Error de sesión REC")
    if "</html>" not in text.lower():
        raise RecError("incomplete", "HTML incompleto o mal formado")
    if "DATOS DEL ACCESO" not in normalized:
        if "<form" in text.lower():
            raise RecError("form", "Respuesta de formulario sin expediente")
        raise RecError("unexpected_html", "HTML inesperado")
    observed = datetime.now(timezone.utc).isoformat()
    try:
        result = parser(
            response.content,
            source_id=official_url(ndp),
            observed_at=observed,
            encoding=response.encoding,
        )
    except Exception as exc:
        raise RecError("parser", "Error de parser REC") from exc
    access = result.get("accesses", [{}])[0]
    if access.get("ndp") and access["ndp"] != ndp:
        raise RecError("identity", "Datos identificativos incompatibles: otro NDP")

    # Solo tolerar partículas de vía; nunca números, calificadores o calles diferentes.
    def address_key(value):
        return " ".join(
            t
            for t in re.findall(r"[A-Z0-9]+", key(value))
            if t not in {"DE", "DEL", "LA", "LAS", "LOS"}
        )

    if address_key(access.get("address_raw", "")) != address_key(address):
        raise RecError("identity", "Datos identificativos incompatibles: dirección distinta")
    for inspection in result.get("inspections", []):
        if not all(
            inspection.get(f)
            for f in (
                "case_reference",
                "inspection_type",
                "presentation_date_raw",
                "opinion_raw",
                "scope_raw",
                "status_raw",
            )
        ):
            raise RecError("incomplete", "Inspección incompleta; revisar ficha oficial")
    source = result.get("source_records", [{}])[0]
    if source.get("warnings"):
        raise RecError("parser", "Formato con campos sin interpretar; requiere revisión")
    if not any(
        "PRESENTADAS" in key(section) for section, _ in source.get("rows", [])
    ) and not result.get("inspections"):
        # La sección puede estar vacía sin filas: revisar el encabezado literal.
        if not re.search(r"I\.?T\.?E\.?.*I\.?E\.?E\.?.*PRESENTADAS", normalized):
            raise RecError("unexpected_html", "No se identifica la sección de inspecciones")
    # No conservar HTML ni filas originales en memoria de la interfaz.
    return dict(
        ndp=ndp,
        address=access.get("address_raw"),
        queried_at=observed,
        origin=response.origin,
        source_sha256=access.get("source_sha256"),
        identity_check="ndp_and_address" if access.get("ndp") else "address_only_ndp_from_request",
        inspections=result.get("inspections", []),
        events=result.get("events", []),
        relations=result.get("relations", []),
        state="success" if result.get("inspections") else "no_inspections",
    )
