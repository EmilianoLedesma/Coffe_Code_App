from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db import Base


class EstatusCocina(Base):
    __tablename__ = "estatus_cocina"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    detalle_pedidos: Mapped[list["DetallePedido"]] = relationship(back_populates="estatus")
