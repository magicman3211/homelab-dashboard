import os
import time
from app.config import settings


def get_backup_status() -> dict:
    paths = [p.strip() for p in settings.backup_paths.split(",") if p.strip()]
    if not paths:
        return {"available": False, "reason": "no paths configured", "backups": []}

    max_age_s = settings.backup_max_age_hours * 3600
    now = time.time()
    backups = []

    for path in paths:
        if not os.path.exists(path):
            backups.append(
                {
                    "path": path,
                    "found": False,
                    "fresh": False,
                    "age_hours": None,
                    "newest_file": None,
                }
            )
            continue

        # Find the newest file under this path (non-recursive)
        newest_mtime = None
        newest_name = None
        try:
            for entry in os.scandir(path):
                if entry.is_file(follow_symlinks=False):
                    mtime = entry.stat().st_mtime
                    if newest_mtime is None or mtime > newest_mtime:
                        newest_mtime = mtime
                        newest_name = entry.name
        except PermissionError:
            pass

        if newest_mtime is None:
            backups.append(
                {
                    "path": path,
                    "found": True,
                    "fresh": False,
                    "age_hours": None,
                    "newest_file": None,
                }
            )
        else:
            age_s = now - newest_mtime
            age_h = round(age_s / 3600, 1)
            backups.append(
                {
                    "path": path,
                    "found": True,
                    "fresh": age_s <= max_age_s,
                    "age_hours": age_h,
                    "newest_file": newest_name,
                }
            )

    return {"available": True, "backups": backups, "max_age_hours": settings.backup_max_age_hours}
