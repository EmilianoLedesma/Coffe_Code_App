import io
from datetime import datetime

from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

_HOUSE = colors.HexColor("#1E3932")
_ACCENT = colors.HexColor("#00754A")
_LIGHT = colors.HexColor("#F2F0EB")
_GREY = colors.HexColor("#6B7280")

_ESTILO_TABLA = TableStyle(
    [
        ("BACKGROUND", (0, 0), (-1, 0), _HOUSE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [_LIGHT, colors.white]),
        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#CCCCCC")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
)

_RELLENO_ENCABEZADO = PatternFill(start_color="1E3932", end_color="1E3932", fill_type="solid")
_FUENTE_ENCABEZADO = Font(color="FFFFFF", bold=True)


def _documento_base(buffer: io.BytesIO) -> SimpleDocTemplate:
    return SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )


def _estilos_parrafo():
    base = getSampleStyleSheet()
    h1 = ParagraphStyle("h1", parent=base["Heading1"], textColor=_ACCENT, fontSize=18, spaceAfter=4)
    h2 = ParagraphStyle("h2", parent=base["Heading2"], textColor=_HOUSE, fontSize=11, spaceBefore=10, spaceAfter=4)
    sub = ParagraphStyle("sub", parent=base["Normal"], textColor=_GREY, fontSize=9, spaceAfter=8)
    ftr = ParagraphStyle("ftr", parent=base["Normal"], textColor=colors.grey, fontSize=8)
    return h1, h2, sub, ftr


def _tabla(filas: list[list[str]]) -> Table:
    tabla = Table(filas, hAlign="LEFT")
    tabla.setStyle(_ESTILO_TABLA)
    return tabla


def generar_pdf_financiero(datos: dict) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = _documento_base(buffer)
    h1, h2, sub, ftr = _estilos_parrafo()

    story = [Paragraph("Coffee Code — Reporte Financiero", h1)]
    story.append(
        Paragraph(f"Periodo: {datos['desde'].strftime('%d/%m/%Y')} — {datos['hasta'].strftime('%d/%m/%Y')}", sub)
    )
    story.append(
        _tabla(
            [
                ["Ventas", "Gastos", "Ganancia neta", "Margen %"],
                [
                    f"${datos['total_ventas']:,.2f}",
                    f"${datos['total_gastos']:,.2f}",
                    f"${datos['ganancia_neta']:,.2f}",
                    f"{datos['margen_pct']}%",
                ],
            ]
        )
    )

    if datos["ranking_margen"]:
        story.append(Paragraph("Rendimiento de producto", h2))
        story.append(
            _tabla(
                [["Producto", "Ingresos", "Costo estimado", "Margen", "Margen %"]]
                + [
                    [
                        fila["nombre"],
                        f"${fila['ingresos']:,.2f}",
                        f"${fila['costo_total']:,.2f}",
                        f"${fila['margen']:,.2f}",
                        f"{fila['margen_pct']}%",
                    ]
                    for fila in datos["ranking_margen"]
                ]
            )
        )

    if datos["ventas_por_categoria"]:
        story.append(Paragraph("Ventas por categoría", h2))
        story.append(
            _tabla(
                [["Categoría", "Total"]]
                + [[fila["nombre"], f"${fila['total']:,.2f}"] for fila in datos["ventas_por_categoria"]]
            )
        )

    if datos["ventas_por_usuario"]:
        story.append(Paragraph("Ventas por mesero/cajero", h2))
        story.append(
            _tabla(
                [["Usuario", "Total"]]
                + [[fila["nombre"], f"${fila['total']:,.2f}"] for fila in datos["ventas_por_usuario"]]
            )
        )

    if datos["ventas_por_metodo_pago"]:
        story.append(Paragraph("Ventas por método de pago", h2))
        story.append(
            _tabla(
                [["Método de pago", "Total"]]
                + [[fila["metodo_pago"], f"${fila['total']:,.2f}"] for fila in datos["ventas_por_metodo_pago"]]
            )
        )

    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph(f"Generado por Coffee Code API · {datetime.now().strftime('%d/%m/%Y %H:%M')}", ftr))
    doc.build(story)
    buffer.seek(0)
    return buffer


def generar_pdf_inventario(datos: dict) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = _documento_base(buffer)
    h1, h2, sub, ftr = _estilos_parrafo()

    story = [Paragraph("Coffee Code — Reporte de Inventario", h1)]
    story.append(Paragraph(f"Generado: {datetime.now().strftime('%d/%m/%Y %H:%M')}", sub))

    if datos["riesgo"]:
        story.append(Paragraph("Riesgo de inventario", h2))
        story.append(
            _tabla(
                [["Ingrediente", "Falta", "Costo de reposición", "Productos afectados"]]
                + [
                    [
                        fila["nombre"],
                        f"{fila['falta']} {fila['unidad']}",
                        f"${fila['costo_reposicion']:,.2f}",
                        ", ".join(fila["productos_afectados"]),
                    ]
                    for fila in datos["riesgo"]
                ]
            )
        )
    else:
        story.append(Paragraph("Sin ingredientes bajo el stock mínimo.", sub))

    if datos["ranking_consumo"]:
        story.append(Paragraph("Ranking de consumo de ingredientes", h2))
        story.append(
            _tabla(
                [["Ingrediente", "Cantidad consumida"]]
                + [
                    [fila["nombre"], f"{fila['cantidad_consumida']} {fila['unidad']}"]
                    for fila in datos["ranking_consumo"]
                ]
            )
        )

    story.append(Spacer(1, 0.8 * cm))
    story.append(Paragraph(f"Generado por Coffee Code API · {datetime.now().strftime('%d/%m/%Y %H:%M')}", ftr))
    doc.build(story)
    buffer.seek(0)
    return buffer


def generar_xlsx_financiero(datos: dict) -> io.BytesIO:
    libro = Workbook()
    hoja_resumen = libro.active
    hoja_resumen.title = "Resumen financiero"
    hoja_resumen.append(["Métrica", "Valor"])
    for celda in hoja_resumen[1]:
        celda.fill = _RELLENO_ENCABEZADO
        celda.font = _FUENTE_ENCABEZADO
    hoja_resumen.append(["Ventas", float(datos["total_ventas"])])
    hoja_resumen.append(["Gastos", float(datos["total_gastos"])])
    hoja_resumen.append(["Ganancia neta", float(datos["ganancia_neta"])])
    hoja_resumen.append(["Margen %", float(datos["margen_pct"])])

    hoja_ranking = libro.create_sheet("Rendimiento de producto")
    hoja_ranking.append(["Producto", "Ingresos", "Costo estimado", "Margen", "Margen %"])
    for celda in hoja_ranking[1]:
        celda.fill = _RELLENO_ENCABEZADO
        celda.font = _FUENTE_ENCABEZADO
    for fila in datos["ranking_margen"]:
        hoja_ranking.append(
            [
                fila["nombre"],
                float(fila["ingresos"]),
                float(fila["costo_total"]),
                float(fila["margen"]),
                float(fila["margen_pct"]),
            ]
        )

    hoja_categoria = libro.create_sheet("Ventas por categoría")
    hoja_categoria.append(["Categoría", "Total"])
    for celda in hoja_categoria[1]:
        celda.fill = _RELLENO_ENCABEZADO
        celda.font = _FUENTE_ENCABEZADO
    for fila in datos["ventas_por_categoria"]:
        hoja_categoria.append([fila["nombre"], float(fila["total"])])

    hoja_usuario = libro.create_sheet("Ventas por usuario")
    hoja_usuario.append(["Usuario", "Total"])
    for celda in hoja_usuario[1]:
        celda.fill = _RELLENO_ENCABEZADO
        celda.font = _FUENTE_ENCABEZADO
    for fila in datos["ventas_por_usuario"]:
        hoja_usuario.append([fila["nombre"], float(fila["total"])])

    hoja_metodo_pago = libro.create_sheet("Ventas por método de pago")
    hoja_metodo_pago.append(["Método de pago", "Total"])
    for celda in hoja_metodo_pago[1]:
        celda.fill = _RELLENO_ENCABEZADO
        celda.font = _FUENTE_ENCABEZADO
    for fila in datos["ventas_por_metodo_pago"]:
        hoja_metodo_pago.append([fila["metodo_pago"], float(fila["total"])])

    buffer = io.BytesIO()
    libro.save(buffer)
    buffer.seek(0)
    return buffer


def generar_xlsx_inventario(datos: dict) -> io.BytesIO:
    libro = Workbook()
    hoja = libro.active
    hoja.title = "Riesgo de inventario"
    hoja.append(["Ingrediente", "Falta", "Unidad", "Costo de reposición", "Productos afectados"])
    for celda in hoja[1]:
        celda.fill = _RELLENO_ENCABEZADO
        celda.font = _FUENTE_ENCABEZADO
    for fila in datos["riesgo"]:
        hoja.append(
            [
                fila["nombre"],
                float(fila["falta"]),
                fila["unidad"],
                float(fila["costo_reposicion"]),
                ", ".join(fila["productos_afectados"]),
            ]
        )

    hoja_consumo = libro.create_sheet("Ranking de consumo")
    hoja_consumo.append(["Ingrediente", "Unidad", "Cantidad consumida"])
    for celda in hoja_consumo[1]:
        celda.fill = _RELLENO_ENCABEZADO
        celda.font = _FUENTE_ENCABEZADO
    for fila in datos["ranking_consumo"]:
        hoja_consumo.append([fila["nombre"], fila["unidad"], float(fila["cantidad_consumida"])])

    buffer = io.BytesIO()
    libro.save(buffer)
    buffer.seek(0)
    return buffer
