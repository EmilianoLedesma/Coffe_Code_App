from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class IngredienteCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=150)
    unidad: str = Field(min_length=1, max_length=20)
    stock_actual: Decimal = Field(default=Decimal("0"), ge=0)
    stock_minimo: Decimal = Field(ge=0)
    costo_unitario: Decimal = Field(gt=0)
    activo: bool = True


class IngredienteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    unidad: str
    stock_actual: Decimal
    stock_minimo: Decimal
    costo_unitario: Decimal
    activo: bool


class ActualizarStock(BaseModel):
    cantidad: Decimal = Field(description="Delta a aplicar al stock actual; puede ser negativo")
