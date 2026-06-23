from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CategoriaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str


class ProductoCreate(BaseModel):
    nombre: str = Field(min_length=2, max_length=150)
    descripcion: str | None = None
    precio_venta: Decimal = Field(gt=0)
    disponible: bool = True
    activo: bool = True
    id_categoria: int


class ProductoUpdate(BaseModel):
    nombre: str | None = Field(default=None, min_length=2, max_length=150)
    descripcion: str | None = None
    precio_venta: Decimal | None = Field(default=None, gt=0)
    disponible: bool | None = None
    activo: bool | None = None
    id_categoria: int | None = None


class ProductoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nombre: str
    descripcion: str | None
    precio_venta: Decimal
    disponible: bool
    activo: bool
    categoria: CategoriaOut


class RecetaCreate(BaseModel):
    producto_id: int
    ingrediente_id: int
    cantidad: Decimal = Field(gt=0)


class IngredienteResumenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    unidad: str


class RecetaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id_producto: int
    id_ingrediente: int
    cantidad_requerida: Decimal
    ingrediente: IngredienteResumenOut
