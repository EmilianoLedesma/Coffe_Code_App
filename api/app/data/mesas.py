from sqlalchemy import Boolean, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db import Base


class Mesa(Base):
    __tablename__ = "mesas"

    id: Mapped[int] = mapped_column(primary_key=True)
    numero_mesa: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    capacidad: Mapped[int] = mapped_column(Integer, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    id_estatus: Mapped[int] = mapped_column(ForeignKey("estatus_mesas.id"), nullable=False)

    estatus: Mapped["EstatusMesa"] = relationship(back_populates="mesas")
    pedidos: Mapped[list["Pedido"]] = relationship(back_populates="mesa")
