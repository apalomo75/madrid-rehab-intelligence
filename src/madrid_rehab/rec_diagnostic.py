"""One public landing-page GET; never submits a record query or enumerates NDPs."""

import argparse
import hashlib
import json
import socket
import ssl
import urllib.error
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from http.cookiejar import CookieJar
from pathlib import Path

URL = "https://servpub.madrid.es/GITEP_WBFICHA/SGiteCons"


class Forms(HTMLParser):
    def __init__(self):
        super().__init__()
        self.forms = []
        self.scripts = 0

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "form":
            self.forms.append(
                {
                    "method": attrs.get("method", "GET").upper(),
                    "action": attrs.get("action", ""),
                    "fields": [],
                }
            )
        elif tag in {"input", "select", "textarea"} and self.forms:
            # Preserve names/types only, not hidden values/session tokens.
            self.forms[-1]["fields"].append(
                {"name": attrs.get("name"), "type": attrs.get("type", tag)}
            )
        elif tag == "script":
            self.scripts += 1


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def classify(exc):
    reason = getattr(exc, "reason", exc)
    if isinstance(reason, socket.gaierror):
        return "dns_failure"
    if isinstance(reason, ssl.SSLError):
        return "tls_failure"
    if isinstance(exc, urllib.error.HTTPError):
        return "redirect_stopped" if 300 <= exc.code < 400 else "http_error"
    return "connection_failure"


def query_allowed(
    *, public_information, automation_permission, authenticated=False, challenge=False
):
    """An individual manual observation is never proof of automated-query permission."""
    return public_information and automation_permission and not authenticated and not challenge


def diagnose(output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    output.chmod(0o700)
    cookies = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies), NoRedirect())
    report = {
        "url": URL,
        "method": "GET",
        "parameters": {},
        "observed_at": datetime.now(timezone.utc).isoformat(),
        "record_queries": 0,
        "batch_authorized": False,
    }
    try:
        request = urllib.request.Request(
            URL,
            headers={
                "User-Agent": "MadridRehabResearch/15 (single public landing-page diagnostic)"
            },
        )
        with opener.open(request, timeout=20) as response:
            raw = response.read(2_000_001)
            if len(raw) > 2_000_000:
                raise ValueError("Response limit exceeded")
            encoding = response.headers.get_content_charset() or "iso-8859-1"
            parser = Forms()
            parser.feed(raw.decode(encoding, errors="replace"))
            (output / "landing.html").write_bytes(raw)
            (output / "landing.html").chmod(0o600)
            report.update(
                status="landing_received",
                http_status=response.status,
                final_url=response.url,
                encoding=encoding,
                sha256=hashlib.sha256(raw).hexdigest(),
                forms=parser.forms,
                scripts=parser.scripts,
                cookie_names=sorted({c.name for c in cookies}),
                session_requirement="not_tested",
                ndp_pattern="not_tested",
                reuse="unverified",
            )
    except (OSError, urllib.error.URLError, ValueError) as exc:
        report.update(
            status=classify(exc),
            error=str(exc),
            http_status=getattr(exc, "code", None),
            ndp_pattern="not_tested",
        )
    (output / "manifest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    report = diagnose(args.output_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["status"] == "landing_received" else 2


if __name__ == "__main__":
    raise SystemExit(main())
