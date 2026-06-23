from decimal import Decimal

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Numeric, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db import Base


class DetallePedido(Base):
    __tablename__ = "detalle_pedidos"
    __table_args__ = (CheckConstraint("cantidad >= 1", name="ck_detalle_pedidos_cantidad_min"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    cantidad: Mapped[int] = mapped_column(Integer, nullable=False)
    especificaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    id_producto: Mapped[int] = mapped_column(ForeignKey("productos.id"), nullable=False)
    id_pedido: Mapped[int] = mapped_column(ForeignKey("pedidos.id"), nullable=False)
    id_estatus: Mapped[int] = mapped_column(ForeignKey("estatus_cocina.id"), nullable=False)

    producto: Mapped["Producto"] = relationship(back_populates="detalle_pedidos")
    pedido: Mapped["Pedido"] = relationship(back_populates="detalle")
    estatus: Mapped["EstatusCocina"] = relationship(back_populates="detalle_pedidos")
