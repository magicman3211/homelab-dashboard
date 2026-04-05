import asyncio
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.requests import Request
from fastapi.staticfiles import StaticFiles

from app.collectors.proxmox import get_proxmox_status
from app.collectors.pbs import get_pbs_status
from app.collectors.docker_collector import get_docker_status
from app.collectors.unifi import get_unifi_status
from app.config import settings

app = FastAPI(title="Homelab Dashboard")
app.mount("/static", StaticFiles(directory="app/static"), name="static")
templates = Jinja2Templates(directory="app/templates")
_executor = ThreadPoolExecutor(max_workers=6)


@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {
        "request": request,
        "refresh_interval": settings.refresh_interval,
    })


@app.get("/api/status")
async def status():
    loop = asyncio.get_event_loop()

    fns = [
        get_proxmox_status,
        get_pbs_status,
        get_docker_status,
        get_unifi_status,
    ]
    results = await asyncio.gather(
        *[loop.run_in_executor(_executor, fn) for fn in fns]
    )
    proxmox, pbs, docker, unifi = results

    attention = []

    if proxmox["available"]:
        for n in proxmox["nodes"]:
            if n["status"] != "online":
                attention.append({"severity": "error", "msg": f"Proxmox node {n['name']} is {n['status']}"})
            if n["cpu_pct"] > 85:
                attention.append({"severity": "warn", "msg": f"Proxmox {n['name']} CPU at {n['cpu_pct']}%"})
            if n["mem_pct"] > 90:
                attention.append({"severity": "warn", "msg": f"Proxmox {n['name']} memory at {n['mem_pct']}%"})
            if n["disk_pct"] > 85:
                attention.append({"severity": "warn", "msg": f"Proxmox {n['name']} disk at {n['disk_pct']}%"})
    elif proxmox.get("reason") and proxmox["reason"] != "not configured":
        attention.append({"severity": "error", "msg": f"Proxmox unreachable: {proxmox['reason']}"})

    if docker["available"]:
        for host in docker["hosts"]:
            if not host["available"]:
                attention.append({"severity": "error", "msg": f"Docker host '{host['name']}' unreachable: {host.get('reason', '')}"})
            else:
                for c in host["containers"]:
                    if not c["running"]:
                        attention.append({"severity": "warn", "msg": f"[{host['name']}] {c['name']} is {c['status']}"})
    elif docker.get("reason") and docker["reason"] != "not configured":
        attention.append({"severity": "error", "msg": f"Portainer unavailable: {docker['reason']}"})

    if unifi["available"]:
        offline = [d for d in unifi["devices"] if not d["online"]]
        for d in offline:
            attention.append({"severity": "warn", "msg": f"UniFi device {d['name']} is offline"})
    elif unifi.get("reason") and unifi["reason"] != "not configured":
        attention.append({"severity": "error", "msg": f"UniFi unreachable: {unifi['reason']}"})

    if pbs["available"]:
        for ds in pbs["datastores"]:
            if ds["used_pct"] > 90:
                attention.append({"severity": "error", "msg": f"PBS datastore '{ds['name']}' at {ds['used_pct']}% capacity"})
            elif ds["used_pct"] > 80:
                attention.append({"severity": "warn", "msg": f"PBS datastore '{ds['name']}' at {ds['used_pct']}% capacity"})
    elif pbs.get("reason") and pbs["reason"] != "not configured":
        attention.append({"severity": "error", "msg": f"PBS unreachable: {pbs['reason']}"})

    return {
        "proxmox": proxmox,
        "pbs": pbs,
        "docker": docker,
        "unifi": unifi,
        "attention": attention,
    }
