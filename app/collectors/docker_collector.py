import requests
from app.config import settings


def get_docker_status() -> dict:
    if not settings.portainer_url or not settings.portainer_api_key:
        return {"available": False, "reason": "not configured", "hosts": []}

    base = settings.portainer_url.rstrip("/")
    headers = {"X-API-Key": settings.portainer_api_key}

    try:

        # Get all endpoints
        resp = requests.get(f"{base}/api/endpoints", headers=headers, timeout=5)
        resp.raise_for_status()
        endpoints = resp.json()

        hosts = []
        for ep in endpoints:
            ep_id = ep["Id"]
            ep_name = ep["Name"]
            ep_status = ep.get("Status", 1)  # 1=up, 2=down

            if ep_status != 1:
                hosts.append({
                    "id": ep_id,
                    "name": ep_name,
                    "available": False,
                    "reason": "endpoint down",
                    "containers": [],
                })
                continue

            try:
                resp = requests.get(
                    f"{base}/api/endpoints/{ep_id}/docker/containers/json",
                    headers=headers,
                    params={"all": "true"},
                    timeout=5,
                )
                resp.raise_for_status()
                raw = resp.json()

                containers = []
                for c in raw:
                    name = c.get("Names", ["unknown"])[0].lstrip("/")
                    image = c.get("Image", "")
                    state = c.get("State", "unknown")
                    containers.append({
                        "name": name,
                        "image": image,
                        "status": state,
                        "running": state == "running",
                    })
                containers.sort(key=lambda x: (not x["running"], x["name"]))

                hosts.append({
                    "id": ep_id,
                    "name": ep_name,
                    "available": True,
                    "containers": containers,
                })
            except Exception as exc:
                hosts.append({
                    "id": ep_id,
                    "name": ep_name,
                    "available": False,
                    "reason": str(exc),
                    "containers": [],
                })

        return {"available": True, "hosts": hosts}

    except Exception as exc:
        return {"available": False, "reason": str(exc), "hosts": []}
