import io

from reportlab.lib.units import mm
from reportlab.pdfgen import canvas

from app.data.pedidos import Pedido
from app.data.tickets import Ticket

_ANCHO = 80 * mm
_MARGEN = 6 * mm
_LINEA = 5 * mm
_ALTO_FIJO = 70 * mm


def generar_pdf_ticket(ticket: Ticket, pedido: Pedido | None) -> io.BytesIO:
    items = list(pedido.detalle) if pedido else []
    alto = _ALTO_FIJO + len(items) * _LINEA

    buffer = io.BytesIO()
    lienzo = canvas.Canvas(buffer, pagesize=(_ANCHO, alto))
    cursor = [alto - _MARGEN - _LINEA]

    def centrado(texto: str, fuente: str = "Helvetica", tamano: int = 8) -> None:
        lienzo.setFont(fuente, tamano)
        lienzo.drawCentredString(_ANCHO / 2, cursor[0], texto)
        cursor[0] -= _LINEA

    def fila(izquierda: str, derecha: str, fuente: str = "Helvetica", tamano: int = 8) -> None:
        lienzo.setFont(fuente, tamano)
        lienzo.drawString(_MARGEN, cursor[0], izquierda)
        lienzo.drawRightString(_ANCHO - _MARGEN, cursor[0], derecha)
        cursor[0] -= _LINEA

    def separador() -> None:
        cursor[0] += _LINEA / 2
        lienzo.setDash([2, 2])
        lienzo.line(_MARGEN, cursor[0], _ANCHO - _MARGEN, cursor[0])
        lienzo.setDash([])
        cursor[0] -= _LINEA

    numero_mesa = pedido.mesa.numero_mesa if pedido and pedido.mesa else ticket.id_mesa
    centrado("COFFEE CODE", "Helvetica-Bold", 11)
    centrado(f"Folio #{ticket.id} - Mesa {numero_mesa}", tamano=7)
    centrado(ticket.fecha_emision.strftime("%d/%m/%Y %H:%M"), tamano=7)

    separador()
    for item in items:
        importe = item.cantidad * item.precio_unitario
        fila(f"{item.cantidad}x {item.producto.nombre}"[:28], f"${importe:,.2f}")

    separador()
    fila("Subtotal", f"${ticket.subtotal:,.2f}")
    fila("IVA", f"${ticket.iva:,.2f}")
    fila("TOTAL", f"${ticket.total:,.2f}", "Helvetica-Bold", 10)

    separador()
    if ticket.pago:
        fila("Metodo", ticket.pago.metodo.nombre)
        fila("Recibido", f"${ticket.pago.monto_recibido:,.2f}")
        fila("Cambio", f"${ticket.pago.cambio:,.2f}")
    else:
        centrado("Pendiente de pago", "Helvetica-Bold", 8)

    lienzo.showPage()
    lienzo.save()
    buffer.seek(0)
    return buffer
