from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.data.db import Base


class MetodoPago(Base):
    __tablename__ = "metodos_pago"

    id: Mapped[int] = mapped_column(primary_key=True)
    nombre: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    pagos: Mapped[list["Pago"]] = relationship(back_populates="metodo")
