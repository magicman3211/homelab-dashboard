from app.config import settings


def get_proxmox_status() -> dict:
    if not settings.proxmox_host:
        return {"available": False, "reason": "not configured", "nodes": []}

    from proxmoxer import ProxmoxAPI

    all_nodes = []
    errors = []

    for host, user, password in zip(
        settings.proxmox_hosts, settings.proxmox_users, settings.proxmox_passwords
    ):
        try:
            px = ProxmoxAPI(
                host,
                user=user,
                password=password,
                verify_ssl=settings.proxmox_verify_ssl,
                timeout=10,
            )
            for node in px.nodes.get():
                name = node["node"]
                mem_total = node.get("maxmem", 1)
                disk_total = node.get("maxdisk", 1)
                all_nodes.append(
                    {
                        "name": name,
                        "host": host,
                        "status": node.get("status", "unknown"),
                        "cpu_pct": round(node.get("cpu", 0) * 100, 1),
                        "mem_pct": round(node.get("mem", 0) / mem_total * 100, 1),
                        "disk_pct": round(node.get("disk", 0) / disk_total * 100, 1),
                        "uptime_s": node.get("uptime", 0),
                    }
                )
        except Exception as exc:
            errors.append(f"{host}: {exc}")

    if not all_nodes and errors:
        return {"available": False, "reason": "; ".join(errors), "nodes": []}

    return {"available": True, "nodes": all_nodes, "errors": errors}
