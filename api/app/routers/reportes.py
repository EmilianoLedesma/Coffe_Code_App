from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.constants import RolNombre
from app.data.db import get_db
from app.models.reportes import (
    ReporteFinancieroOut,
    ReporteInventarioOut,
    ReportePedidosOut,
    ReporteProductosOut,
)
from app.security.auth import require_rol
from app.services.reportes import (
    construir_reporte_financiero,
    construir_reporte_inventario,
    construir_reporte_pedidos,
    construir_reporte_productos,
)
from app.services.reportes_export import (
    generar_pdf_financiero,
    generar_pdf_inventario,
    generar_pdf_pedidos,
    generar_pdf_productos,
    generar_xlsx_financiero,
    generar_xlsx_inventario,
    generar_xlsx_pedidos,
    generar_xlsx_productos,
)

router = APIRouter(prefix="/api/reportes", tags=["reportes"])

_solo_admin = require_rol(RolNombre.ADMINISTRADOR)


def _rango_por_defecto(desde: datetime | None, hasta: datetime | None) -> tuple[datetime, datetime]:
    hasta = hasta or datetime.now(timezone.utc)
    if hasta.time() == datetime.min.time():
        # `hasta` llegó como fecha pelada (ej. "2026-08-08"), que FastAPI
        # parsea a medianoche — sin este ajuste, las ventas del propio día
        # `hasta` quedan excluidas silenciosamente del reporte.
        hasta = hasta.replace(hour=23, minute=59, second=59, microsecond=999999)
    desde = desde or (hasta - timedelta(days=30))
    return desde, hasta


@router.get("/financiero", response_model=ReporteFinancieroOut)
def financiero(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    categoria_id: int | None = None,
    usuario_id: int | None = None,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> dict:
    desde, hasta = _rango_por_defecto(desde, hasta)
    return construir_reporte_financiero(db, desde, hasta, categoria_id=categoria_id, usuario_id=usuario_id)


@router.get("/inventario", response_model=ReporteInventarioOut)
def inventario(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> dict:
    return construir_reporte_inventario(db, desde, hasta)


@router.get("/financiero/pdf")
def financiero_pdf(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    categoria_id: int | None = None,
    usuario_id: int | None = None,
    secciones: list[str] | None = Query(None),
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> StreamingResponse:
    desde, hasta = _rango_por_defecto(desde, hasta)
    datos = construir_reporte_financiero(db, desde, hasta, categoria_id=categoria_id, usuario_id=usuario_id)
    buffer = generar_pdf_financiero(datos, set(secciones) if secciones else None)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=reporte_financiero.pdf"},
    )


@router.get("/financiero/xlsx")
def financiero_xlsx(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    categoria_id: int | None = None,
    usuario_id: int | None = None,
    secciones: list[str] | None = Query(None),
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> StreamingResponse:
    desde, hasta = _rango_por_defecto(desde, hasta)
    datos = construir_reporte_financiero(db, desde, hasta, categoria_id=categoria_id, usuario_id=usuario_id)
    buffer = generar_xlsx_financiero(datos, set(secciones) if secciones else None)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reporte_financiero.xlsx"},
    )


@router.get("/inventario/pdf")
def inventario_pdf(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    secciones: list[str] | None = Query(None),
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> StreamingResponse:
    datos = construir_reporte_inventario(db, desde, hasta)
    buffer = generar_pdf_inventario(datos, set(secciones) if secciones else None)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=reporte_inventario.pdf"},
    )


@router.get("/inventario/xlsx")
def inventario_xlsx(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    secciones: list[str] | None = Query(None),
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> StreamingResponse:
    datos = construir_reporte_inventario(db, desde, hasta)
    buffer = generar_xlsx_inventario(datos, set(secciones) if secciones else None)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reporte_inventario.xlsx"},
    )


@router.get("/productos", response_model=ReporteProductosOut)
def productos(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> dict:
    desde, hasta = _rango_por_defecto(desde, hasta)
    return construir_reporte_productos(db, desde, hasta)


@router.get("/productos/pdf")
def productos_pdf(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> StreamingResponse:
    desde, hasta = _rango_por_defecto(desde, hasta)
    datos = construir_reporte_productos(db, desde, hasta)
    buffer = generar_pdf_productos(datos)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=reporte_productos.pdf"},
    )


@router.get("/productos/xlsx")
def productos_xlsx(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> StreamingResponse:
    desde, hasta = _rango_por_defecto(desde, hasta)
    datos = construir_reporte_productos(db, desde, hasta)
    buffer = generar_xlsx_productos(datos)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reporte_productos.xlsx"},
    )


@router.get("/pedidos", response_model=ReportePedidosOut)
def pedidos(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> dict:
    desde, hasta = _rango_por_defecto(desde, hasta)
    return construir_reporte_pedidos(db, desde, hasta)


@router.get("/pedidos/pdf")
def pedidos_pdf(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> StreamingResponse:
    desde, hasta = _rango_por_defecto(desde, hasta)
    datos = construir_reporte_pedidos(db, desde, hasta)
    buffer = generar_pdf_pedidos(datos)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=reporte_pedidos.pdf"},
    )


@router.get("/pedidos/xlsx")
def pedidos_xlsx(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> StreamingResponse:
    desde, hasta = _rango_por_defecto(desde, hasta)
    datos = construir_reporte_pedidos(db, desde, hasta)
    buffer = generar_xlsx_pedidos(datos)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reporte_pedidos.xlsx"},
    )
