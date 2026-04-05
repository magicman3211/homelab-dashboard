import requests
import urllib3
from app.config import settings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_unifi_status() -> dict:
    if not settings.unifi_host:
        return {"available": False, "reason": "not configured", "devices": []}

    base = f"https://{settings.unifi_host}"
    verify = settings.unifi_verify_ssl
    session = requests.Session()

    try:
        # Try UDM login first, fall back to classic controller
        udm = False
        resp = session.post(
            f"{base}/api/auth/login",
            json={"username": settings.unifi_username, "password": settings.unifi_password},
            verify=verify,
            timeout=10,
        )
        if resp.status_code == 200:
            udm = True
        else:
            resp = session.post(
                f"{base}/api/login",
                json={"username": settings.unifi_username, "password": settings.unifi_password},
                verify=verify,
                timeout=10,
            )
            resp.raise_for_status()

        # Fetch devices
        devices_path = (
            f"/proxy/network/api/s/{settings.unifi_site}/stat/device"
            if udm
            else f"/api/s/{settings.unifi_site}/stat/device"
        )
        resp = session.get(
            f"{base}{devices_path}",
            verify=verify,
            timeout=10,
        )
        resp.raise_for_status()
        raw = resp.json().get("data", [])

        devices = []
        for d in raw:
            devices.append(
                {
                    "name": d.get("name") or d.get("hostname") or d.get("mac", "unknown"),
                    "model": d.get("model", ""),
                    "type": d.get("type", ""),
                    "state": d.get("state", 0),
                    "online": d.get("state", 0) == 1,
                    "ip": d.get("ip", ""),
                    "uptime_s": d.get("uptime", 0),
                }
            )

        devices.sort(key=lambda x: (not x["online"], x["name"]))
        return {"available": True, "devices": devices}

    except Exception as exc:
        return {"available": False, "reason": str(exc), "devices": []}

    finally:
        try:
            logout_path = "/api/auth/logout" if udm else "/api/logout"
            session.post(f"{base}{logout_path}", verify=verify, timeout=5)
        except Exception:
            pass
