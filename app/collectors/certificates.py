import ssl
import socket
from datetime import datetime, timezone
from app.config import settings


def _check_cert(host: str, port: int) -> dict:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE  # we want expiry even for self-signed certs

    try:
        with socket.create_connection((host, port), timeout=8) as sock:
            with ctx.wrap_socket(sock, server_hostname=host) as ssock:
                cert = ssock.getpeercert()

        not_after = cert.get("notAfter", "")
        expiry = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z").replace(tzinfo=timezone.utc)
        days_left = (expiry - datetime.now(timezone.utc)).days

        subject = dict(x[0] for x in cert.get("subject", []))
        cn = subject.get("commonName", host)

        return {
            "host": host,
            "port": port,
            "cn": cn,
            "expiry": expiry.strftime("%Y-%m-%d"),
            "days_left": days_left,
            "ok": days_left > settings.cert_warn_days,
            "error": None,
        }
    except Exception as exc:
        return {
            "host": host,
            "port": port,
            "cn": host,
            "expiry": None,
            "days_left": None,
            "ok": False,
            "error": str(exc),
        }


def get_cert_status() -> dict:
    raw = [h.strip() for h in settings.cert_hosts.split(",") if h.strip()]
    if not raw:
        return {"available": False, "reason": "no hosts configured", "certs": []}

    certs = []
    for entry in raw:
        if ":" in entry:
            host, port_str = entry.rsplit(":", 1)
            port = int(port_str)
        else:
            host, port = entry, 443
        certs.append(_check_cert(host, port))

    certs.sort(key=lambda x: (x["days_left"] is None, x["days_left"] or 9999))
    return {"available": True, "certs": certs, "warn_days": settings.cert_warn_days}
