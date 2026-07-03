from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db import Base


class CorteDiario(Base):
    __tablename__ = "cortes_diarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, unique=True, nullable=False)
    total_ventas: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    total_gastos: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    ganancia_neta: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    num_pedidos: Mapped[int] = mapped_column(Integer, nullable=False)
    num_tickets: Mapped[int] = mapped_column(Integer, nullable=False)
    generado_en: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    id_usuario: Mapped[int] = mapped_column(ForeignKey("usuarios.id"), nullable=False)

    usuario: Mapped["Usuario"] = relationship()
    desglose_metodos: Mapped[list["CorteMetodoPago"]] = relationship(
        back_populates="corte", cascade="all, delete-orphan"
    )


class CorteMetodoPago(Base):
    __tablename__ = "corte_metodos_pago"

    id_corte: Mapped[int] = mapped_column(ForeignKey("cortes_diarios.id"), primary_key=True)
    id_metodo_pago: Mapped[int] = mapped_column(ForeignKey("metodos_pago.id"), primary_key=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    corte: Mapped["CorteDiario"] = relationship(back_populates="desglose_metodos")
    metodo: Mapped["MetodoPago"] = relationship()
