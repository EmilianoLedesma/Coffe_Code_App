from decimal import Decimal

from sqlalchemy import Boolean, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db import Base


class Ingrediente(Base):
    __tablename__ = "ingredientes"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(150), nullable=False)
    unidad: Mapped[str] = mapped_column(String(20), nullable=False)
    stock_actual: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0, nullable=False)
    stock_minimo: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    costo_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    recetas: Mapped[list["Receta"]] = relationship(back_populates="ingrediente")
