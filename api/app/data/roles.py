from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db import Base


class Rol(Base):
    __tablename__ = "roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    descripcion: Mapped[str | None] = mapped_column(String(255), nullable=True)

    usuarios: Mapped[list["Usuario"]] = relationship(back_populates="rol")
