from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db import Base


class EstatusMesa(Base):
    __tablename__ = "estatus_mesas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    mesas: Mapped[list["Mesa"]] = relationship(back_populates="estatus")
