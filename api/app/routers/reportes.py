from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.constants import RolNombre
from app.data.db import get_db
from app.models.reportes import ReporteFinancieroOut, ReporteInventarioOut
from app.security.auth import require_rol
from app.services.reportes import construir_reporte_financiero, construir_reporte_inventario
from app.services.reportes_export import (
    generar_pdf_financiero,
    generar_pdf_inventario,
    generar_xlsx_financiero,
    generar_xlsx_inventario,
)

router = APIRouter(prefix="/api/reportes", tags=["reportes"])

_solo_admin = require_rol(RolNombre.ADMINISTRADOR)


def _rango_por_defecto(desde: datetime | None, hasta: datetime | None) -> tuple[datetime, datetime]:
    hasta = hasta or datetime.now(timezone.utc)
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
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> StreamingResponse:
    desde, hasta = _rango_por_defecto(desde, hasta)
    datos = construir_reporte_financiero(db, desde, hasta, categoria_id=categoria_id, usuario_id=usuario_id)
    buffer = generar_pdf_financiero(datos)
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
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> StreamingResponse:
    desde, hasta = _rango_por_defecto(desde, hasta)
    datos = construir_reporte_financiero(db, desde, hasta, categoria_id=categoria_id, usuario_id=usuario_id)
    buffer = generar_xlsx_financiero(datos)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reporte_financiero.xlsx"},
    )


@router.get("/inventario/pdf")
def inventario_pdf(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> StreamingResponse:
    datos = construir_reporte_inventario(db, desde, hasta)
    buffer = generar_pdf_inventario(datos)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=reporte_inventario.pdf"},
    )


@router.get("/inventario/xlsx")
def inventario_xlsx(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    db: Session = Depends(get_db),
    _=Depends(_solo_admin),
) -> StreamingResponse:
    datos = construir_reporte_inventario(db, desde, hasta)
    buffer = generar_xlsx_inventario(datos)
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=reporte_inventario.xlsx"},
    )
