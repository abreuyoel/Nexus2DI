from fastapi import Request


def get_client_ip(request: Request) -> str:
    """IP real del cliente detrás de Cloudflare Tunnel + nginx.

    Cloudflare preserva la IP original del visitante en CF-Connecting-IP;
    dentro del clúster, request.client.host solo vería la IP del pod de
    nginx (el reverse proxy), no la del usuario.
    """
    cf_ip = request.headers.get("CF-Connecting-IP")
    if cf_ip:
        return cf_ip
    xff = request.headers.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"
