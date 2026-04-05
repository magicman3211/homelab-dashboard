import requests
import urllib3
from app.config import settings

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def get_pbs_status() -> dict:
    if not settings.pbs_host:
        return {"available": False, "reason": "not configured", "datastores": []}

    base = f"https://{settings.pbs_host}:{settings.pbs_port}"
    headers = {}

    try:
        # Authenticate
        resp = requests.post(
            f"{base}/api2/json/access/ticket",
            data={"username": settings.pbs_username, "password": settings.pbs_password},
            verify=settings.pbs_verify_ssl,
            timeout=10,
        )
        resp.raise_for_status()
        ticket_data = resp.json()["data"]
        ticket = ticket_data["ticket"]
        token = ticket_data["CSRFPreventionToken"]
        headers = {
            "Cookie": f"PBSAuthCookie={ticket}",
            "CSRFPreventionToken": token,
        }

        # Fetch datastore list
        resp = requests.get(
            f"{base}/api2/json/admin/datastore",
            headers=headers,
            verify=settings.pbs_verify_ssl,
            timeout=10,
        )
        resp.raise_for_status()
        raw_stores = resp.json().get("data", [])

        datastores = []
        for ds in raw_stores:
            name = ds.get("store", "unknown")

            # Fetch per-datastore status (includes disk usage)
            total, used, avail = 0, 0, 0
            try:
                sr = requests.get(
                    f"{base}/api2/json/admin/datastore/{name}/status",
                    headers=headers,
                    verify=settings.pbs_verify_ssl,
                    timeout=10,
                )
                if sr.ok:
                    sd = sr.json().get("data", {})
                    total = sd.get("total", 0)
                    used = sd.get("used", 0)
                    avail = sd.get("avail", 0)
            except Exception:
                pass

            used_pct = round(used / total * 100, 1) if total else 0

            # Fetch snapshot count
            snap_count = 0
            try:
                sr = requests.get(
                    f"{base}/api2/json/admin/datastore/{name}/snapshots",
                    headers=headers,
                    verify=settings.pbs_verify_ssl,
                    timeout=10,
                )
                if sr.ok:
                    snap_count = len(sr.json().get("data", []))
            except Exception:
                pass

            datastores.append({
                "name": name,
                "total_gb": round(total / 1024**3, 1) if total else 0,
                "used_gb": round(used / 1024**3, 1) if used else 0,
                "avail_gb": round(avail / 1024**3, 1) if avail else 0,
                "used_pct": used_pct,
                "snapshots": snap_count,
            })

        return {"available": True, "host": settings.pbs_host, "datastores": datastores}

    except Exception as exc:
        return {"available": False, "reason": str(exc), "datastores": []}
