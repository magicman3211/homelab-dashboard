from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Proxmox (comma-separated for multiple hosts)
    proxmox_host: str = ""
    proxmox_user: str = "root@pam"
    proxmox_password: str = ""
    proxmox_verify_ssl: bool = False

    @property
    def proxmox_hosts(self) -> list[str]:
        return [h.strip() for h in self.proxmox_host.split(",") if h.strip()]

    @property
    def proxmox_users(self) -> list[str]:
        users = [u.strip() for u in self.proxmox_user.split(",") if u.strip()]
        hosts = self.proxmox_hosts
        if len(users) < len(hosts):
            users += [users[-1]] * (len(hosts) - len(users))
        return users

    @property
    def proxmox_passwords(self) -> list[str]:
        passwords = [p.strip() for p in self.proxmox_password.split(",") if p.strip()]
        hosts = self.proxmox_hosts
        if len(passwords) < len(hosts):
            passwords += [passwords[-1]] * (len(hosts) - len(passwords))
        return passwords

    # UniFi
    unifi_host: str = ""
    unifi_username: str = ""
    unifi_password: str = ""
    unifi_site: str = "default"
    unifi_verify_ssl: bool = False

    # Proxmox Backup Server
    pbs_host: str = ""
    pbs_port: int = 8007
    pbs_username: str = "root@pam"
    pbs_password: str = ""
    pbs_verify_ssl: bool = False

    # Portainer
    portainer_url: str = ""
    portainer_api_key: str = ""

    # UI

    # UI
    refresh_interval: int = 60

    class Config:
        env_file = ".env"


settings = Settings()
