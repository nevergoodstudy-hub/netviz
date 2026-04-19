from ipaddress import ip_address
import secrets
from typing import Mapping

from fastapi import Header, HTTPException, Request, WebSocket, status

from app.core.config import settings

ADMIN_TOKEN_HEADER = "X-NetViz-Admin-Token"


def _is_loopback_host(host: str | None) -> bool:
    if not host:
        return False

    try:
        return ip_address(host).is_loopback
    except ValueError:
        return host.lower() == "localhost"


def _has_proxy_forwarding_headers(headers: Mapping[str, str]) -> bool:
    return bool(headers.get("x-forwarded-for") or headers.get("forwarded"))


def _authorize_admin_access(
    client_host: str | None,
    headers: Mapping[str, str],
    admin_token: str | None,
) -> None:
    if _is_loopback_host(client_host) and not _has_proxy_forwarding_headers(headers):
        return

    configured_token = settings.admin_access_token
    if configured_token and admin_token:
        if secrets.compare_digest(admin_token, configured_token):
            return

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Administrative access is only available from direct loopback requests or with a valid admin token.",
    )


async def require_admin_access(
    request: Request,
    admin_token: str | None = Header(default=None, alias=ADMIN_TOKEN_HEADER),
) -> None:
    client_host = request.client.host if request.client else None
    _authorize_admin_access(client_host, request.headers, admin_token)


def websocket_has_admin_access(websocket: WebSocket) -> bool:
    client_host = websocket.client.host if websocket.client else None
    admin_token = websocket.headers.get(ADMIN_TOKEN_HEADER.lower())

    try:
        _authorize_admin_access(client_host, websocket.headers, admin_token)
        return True
    except HTTPException:
        return False
