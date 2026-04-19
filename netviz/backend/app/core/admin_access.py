from ipaddress import ip_address
import secrets

from fastapi import Header, HTTPException, Request, status

from app.core.config import settings

ADMIN_TOKEN_HEADER = "X-NetViz-Admin-Token"


def _is_loopback_host(host: str | None) -> bool:
    if not host:
        return False

    try:
        return ip_address(host).is_loopback
    except ValueError:
        return host.lower() == "localhost"


async def require_admin_access(
    request: Request,
    admin_token: str | None = Header(default=None, alias=ADMIN_TOKEN_HEADER),
) -> None:
    client_host = request.client.host if request.client else None
    if _is_loopback_host(client_host):
        return

    configured_token = settings.admin_access_token
    if configured_token and admin_token:
        if secrets.compare_digest(admin_token, configured_token):
            return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Administrative settings are only available from loopback or with a valid admin token.",
    )
