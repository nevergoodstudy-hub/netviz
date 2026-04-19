"""Helpers for validating AI provider base URLs."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import SplitResult, urlsplit, urlunsplit


OFFICIAL_PROVIDER_BASE_URLS = {
    "openai": "https://api.openai.com/v1",
    "deepseek": "https://api.deepseek.com",
    "ollama": "http://localhost:11434",
}


def default_provider_base_url(provider: str) -> str:
    try:
        return OFFICIAL_PROVIDER_BASE_URLS[provider]
    except KeyError as exc:
        raise ValueError(f"Unsupported provider for base URL normalization: {provider}") from exc


def normalize_ai_base_url(
    provider: str,
    base_url: str | None,
    *,
    allow_unsafe_cloud_urls: bool = False,
) -> str:
    """Normalize and validate provider base URLs before use."""
    if provider == "ollama":
        return _normalize_ollama_base_url(base_url)
    if provider in {"openai", "deepseek"}:
        return _normalize_cloud_base_url(
            provider,
            base_url,
            allow_unsafe_cloud_urls=allow_unsafe_cloud_urls,
        )
    raise ValueError(f"Unsupported provider for base URL normalization: {provider}")


def _normalize_cloud_base_url(
    provider: str,
    base_url: str | None,
    *,
    allow_unsafe_cloud_urls: bool,
) -> str:
    default_url = default_provider_base_url(provider)
    candidate = (base_url or default_url).strip()
    if not candidate:
        candidate = default_url

    parsed = _parse_https_url(candidate)
    hostname = _normalized_hostname(parsed)
    default_parts = urlsplit(default_url)
    default_host = _normalized_hostname(default_parts)

    if hostname == default_host:
        normalized_path = parsed.path.rstrip("/") or default_parts.path
        if normalized_path != default_parts.path and not allow_unsafe_cloud_urls:
            raise ValueError(
                f"{provider} base URL must use the official path {default_parts.path or '/'}."
            )
        return _rebuild_url(parsed, path=normalized_path)

    if not allow_unsafe_cloud_urls:
        raise ValueError(
            f"{provider} base URL must use the official host {default_host}. "
            "Set ALLOW_UNSAFE_AI_BASE_URLS=true only if you knowingly need a custom public HTTPS endpoint."
        )

    if _host_is_private_like(hostname):
        raise ValueError(
            f"{provider} base URL must not target loopback, private, link-local, or reserved hosts."
        )

    return _rebuild_url(parsed, path=parsed.path.rstrip("/"))


def _normalize_ollama_base_url(base_url: str | None) -> str:
    candidate = (base_url or default_provider_base_url("ollama")).strip()
    if not candidate:
        candidate = default_provider_base_url("ollama")

    parsed = urlsplit(candidate)
    if parsed.scheme not in {"http", "https"}:
        raise ValueError("Ollama base URL must use http or https.")
    if not parsed.hostname:
        raise ValueError("Ollama base URL must include a hostname.")
    return _rebuild_url(parsed, path=parsed.path.rstrip("/"))


def _parse_https_url(value: str) -> SplitResult:
    parsed = urlsplit(value)
    if parsed.scheme != "https":
        raise ValueError("Cloud AI provider base URLs must use https.")
    if not parsed.hostname:
        raise ValueError("Cloud AI provider base URLs must include a hostname.")
    return parsed


def _normalized_hostname(parsed: SplitResult) -> str:
    hostname = parsed.hostname
    if hostname is None:
        raise ValueError("Base URL must include a hostname.")
    return hostname.rstrip(".").lower()


def _rebuild_url(parsed: SplitResult, *, path: str) -> str:
    normalized_path = path or ""
    if normalized_path and not normalized_path.startswith("/"):
        normalized_path = f"/{normalized_path}"
    return urlunsplit((parsed.scheme, parsed.netloc, normalized_path, "", ""))


def _host_is_private_like(hostname: str) -> bool:
    if hostname == "localhost":
        return True

    try:
        return _ip_is_private_like(ipaddress.ip_address(hostname))
    except ValueError:
        pass

    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror:
        return False

    for _, _, _, _, sockaddr in infos:
        raw_ip = sockaddr[0]
        try:
            resolved = ipaddress.ip_address(raw_ip)
        except ValueError:
            continue
        if _ip_is_private_like(resolved):
            return True
    return False


def _ip_is_private_like(address: ipaddress._BaseAddress) -> bool:
    return any(
        (
            address.is_private,
            address.is_loopback,
            address.is_link_local,
            address.is_reserved,
            address.is_multicast,
            address.is_unspecified,
        )
    )
