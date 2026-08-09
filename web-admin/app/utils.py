from datetime import date, datetime


def parsear_fecha(valor: str | None, default: date) -> date:
    if not valor:
        return default
    return datetime.strptime(valor, "%Y-%m-%d").date()


def parsear_fechas_detalle(filas: list[dict], campo: str) -> None:
    for fila in filas:
        fila[campo] = datetime.fromisoformat(fila[campo])
