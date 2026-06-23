from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db import Base


class Receta(Base):
    __tablename__ = "recetas"

    id_producto: Mapped[int] = mapped_column(ForeignKey("productos.id"), primary_key=True)
    id_ingrediente: Mapped[int] = mapped_column(ForeignKey("ingredientes.id"), primary_key=True)
    cantidad_requerida: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    producto: Mapped["Producto"] = relationship(back_populates="recetas")
    ingrediente: Mapped["Ingrediente"] = relationship(back_populates="recetas")
