from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db import Base


class Pedido(Base):
    __tablename__ = "pedidos"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    total: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    id_mesa: Mapped[int] = mapped_column(ForeignKey("mesas.id"), nullable=False)
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)
    id_estatus: Mapped[int] = mapped_column(ForeignKey("estatus_pedidos.id"), nullable=False)

    mesa: Mapped["Mesa"] = relationship(back_populates="pedidos")
    usuario: Mapped["Usuario"] = relationship(back_populates="pedidos")
    estatus: Mapped["EstatusPedido"] = relationship(back_populates="pedidos")
    detalle: Mapped[list["DetallePedido"]] = relationship(
        back_populates="pedido", cascade="all, delete-orphan"
    )
    ticket: Mapped["Ticket"] = relationship(back_populates="pedido", uselist=False)
