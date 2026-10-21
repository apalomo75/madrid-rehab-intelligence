"""HTTP acotado con evidencia de errores y caché inmutable por URL."""

import hashlib
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


class DownloadError(RuntimeError):
    pass


class BudgetExceeded(DownloadError):
    pass


class Client:
    def __init__(self, root, config, opener=None):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.config = config
        self.opener = opener or urllib.request.urlopen
        self.requests = 0
        self.total_bytes = 0
        self.last_request = 0
        # Los topes no pueden elevarse desde la configuración sin cambiar código.
        if not 1 <= config["max_response_bytes"] <= 524288:
            raise ValueError("Tope por respuesta: 512 KiB")
        if not 1 <= config["max_total_bytes"] <= 5242880:
            raise ValueError("Tope por ejecución: 5 MiB; ampliarlo requiere aprobación")
        if not 1 <= config["max_requests"] <= 20:
            raise ValueError("Máximo 20 peticiones por ejecución")
        self.events = []

    def get(self, base, params=None):
        url = base + (("&" if "?" in base else "?") + urllib.parse.urlencode(params) if params else "")
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme != "https" or parsed.hostname not in {
            "datos.comunidad.madrid", "ovc.catastro.meh.es"
        }:
            raise ValueError("Solo se permiten los dos orígenes oficiales HTTPS configurados")
        key = hashlib.sha256(url.encode()).hexdigest()
        body_path = self.root / f"{key}.body"
        meta_path = self.root / f"{key}.json"
        if body_path.exists() and meta_path.exists():
            body = body_path.read_bytes()
            meta = json.loads(meta_path.read_text())
            if hashlib.sha256(body).hexdigest() != meta["sha256"]:
                raise DownloadError("Caché alterada")
            if len(body) > self.config["max_response_bytes"]:
                raise BudgetExceeded("Caché mayor que el límite actual")
            self.events.append({**meta, "cached": True})
            return body
        if self.requests >= self.config["max_requests"]:
            raise BudgetExceeded("Presupuesto de peticiones agotado")
        budget = min(self.config["max_response_bytes"], self.config["max_total_bytes"] - self.total_bytes)
        if budget <= 0:
            raise BudgetExceeded("Presupuesto de bytes agotado")
        time.sleep(max(0, self.config["interval_seconds"] - (time.monotonic() - self.last_request)))
        self.requests += 1
        self.last_request = time.monotonic()
        event = {
            "url": url, "captured_at": datetime.now(timezone.utc).isoformat(),
            "cached": False, "http_status": None, "bytes_read": 0,
        }
        try:
            request = urllib.request.Request(url, headers={
                "User-Agent": "MadridRehabIntelligence/0.1 limited-research-sample",
                "Accept-Encoding": "identity",
            })
            with self.opener(request, timeout=self.config["timeout_seconds"]) as response:
                final = urllib.parse.urlparse(response.geturl())
                if final.scheme != "https" or final.hostname != parsed.hostname:
                    raise DownloadError("Redirección fuera del origen permitido")
                event["http_status"] = response.status
                event["content_type"] = response.headers.get("Content-Type")
                length = response.headers.get("Content-Length")
                event["declared_bytes"] = int(length) if length else None
                if length and int(length) > budget:
                    raise BudgetExceeded(f"Respuesta anuncia {length} bytes; límite {budget}; cuerpo no leído")
                body = response.read(budget + 1)
                event["bytes_read"] = len(body)
                self.total_bytes += len(body)
                if len(body) > budget:
                    raise BudgetExceeded("Respuesta interrumpida al superar el límite; no se guarda")
                if response.status != 200:
                    raise DownloadError(f"HTTP inesperado: {response.status}")
            event["sha256"] = hashlib.sha256(body).hexdigest()
            body_path.write_bytes(body)
            meta_path.write_text(json.dumps(event, indent=2, ensure_ascii=False) + "\n")
            self.events.append(event)
            return body
        except (OSError, ValueError, DownloadError) as exc:
            if isinstance(exc, urllib.error.HTTPError):
                event["http_status"] = exc.code
            event["error_type"] = type(exc).__name__
            event["error"] = str(exc)
            self.events.append(event)
            raise DownloadError(str(exc)) from exc

    def manifest(self, path):
        Path(path).write_text(json.dumps({
            "requests": self.requests, "network_bytes": self.total_bytes,
            "events": self.events,
        }, indent=2, ensure_ascii=False) + "\n")
