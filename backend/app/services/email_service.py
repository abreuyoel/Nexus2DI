"""Envío de correo del módulo de Ventas (confirmación de pedido al cliente,
alerta de pedido grande al supervisor, etc.). SMTP simple vía smtplib
(stdlib) -- sin proveedor externo nuevo que integrar bajo presión de tiempo.

Si SMTP_HOST no está configurado, enviar() es un no-op que solo loguea --
así el flujo de pedidos NUNCA se bloquea porque falte config de correo
(mismo criterio que send_push_notification con VAPID_PRIVATE_KEY vacío)."""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from app.core.config import settings

logger = logging.getLogger("app")


def enviar(destinatario: str, asunto: str, cuerpo_html: str) -> bool:
    if not destinatario:
        return False
    if not settings.SMTP_HOST:
        logger.info(f"[Email] SMTP no configurado -- se omite envío a {destinatario}: {asunto}")
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"] = settings.SMTP_FROM
        msg["To"] = destinatario
        msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
            server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.SMTP_FROM, [destinatario], msg.as_string())
        return True
    except Exception as e:
        # Best-effort: un fallo de correo nunca debe tumbar el registro de un
        # pedido -- el pedido ya se guardó en BD antes de llegar acá.
        logger.warning(f"[Email] Fallo enviando a {destinatario}: {e!r}")
        return False


def html_confirmacion_pedido(numero_pedido: str, cliente: str, total: float, lineas: list[dict]) -> str:
    filas = "".join(
        f"<tr><td style='padding:4px 8px'>{l['nombre_producto']}</td>"
        f"<td style='padding:4px 8px;text-align:center'>{l['cantidad']}</td>"
        f"<td style='padding:4px 8px;text-align:right'>${l['precio_unitario']:.2f}</td></tr>"
        for l in lineas
    )
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:520px">
      <h2 style="color:#0D2137">Pedido {numero_pedido}</h2>
      <p>Hola <b>{cliente}</b>, confirmamos la recepción de tu pedido.</p>
      <table style="width:100%;border-collapse:collapse;margin:12px 0">
        <thead><tr style="background:#f0f4f8">
          <th style="text-align:left;padding:4px 8px">Producto</th>
          <th style="padding:4px 8px">Cant.</th>
          <th style="text-align:right;padding:4px 8px">Precio</th>
        </tr></thead>
        <tbody>{filas}</tbody>
      </table>
      <p style="font-size:18px"><b>Total: ${total:.2f}</b></p>
      <p style="color:#546E7A;font-size:12px">Nexus2Di -- este correo se generó automáticamente.</p>
    </div>
    """


def html_alerta_pedido_grande(numero_pedido: str, vendedor: str, cliente: str, total: float) -> str:
    return f"""
    <div style="font-family:Arial,sans-serif;max-width:520px">
      <h2 style="color:#E65100">Pedido grande registrado</h2>
      <p><b>{vendedor}</b> registró el pedido <b>{numero_pedido}</b> para <b>{cliente}</b> por
      <b>${total:.2f}</b>, por encima del umbral configurado.</p>
    </div>
    """
