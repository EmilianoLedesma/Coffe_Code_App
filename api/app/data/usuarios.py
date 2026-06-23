from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido_paterno: Mapped[str] = mapped_column(String(100), nullable=False)
    apellido_materno: Mapped[str | None] = mapped_column(String(100), nullable=True)
    correo_electronico: Mapped[str] = mapped_column(String(150), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    fecha_creacion: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    id_rol: Mapped[int] = mapped_column(ForeignKey("roles.id"), nullable=False)

    rol: Mapped["Rol"] = relationship(back_populates="usuarios")
    pedidos: Mapped[list["Pedido"]] = relationship(back_populates="usuario")
    tickets: Mapped[list["Ticket"]] = relationship(back_populates="usuario")
    gastos: Mapped[list["Gasto"]] = relationship(back_populates="usuario")
