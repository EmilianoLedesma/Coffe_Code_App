from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db import Base


class Pago(Base):
    __tablename__ = "pagos"

    id: Mapped[int] = mapped_column(primary_key=True)
    monto_recibido: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    cambio: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    id_ticket: Mapped[int] = mapped_column(ForeignKey("tickets.id"), unique=True, nullable=False)
    id_metodo: Mapped[int] = mapped_column(ForeignKey("metodos_pago.id"), nullable=False)

    ticket: Mapped["Ticket"] = relationship(back_populates="pago")
    metodo: Mapped["MetodoPago"] = relationship(back_populates="pagos")
