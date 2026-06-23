import os

import psycopg2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.core.constants import (
    EstatusCocinaNombre,
    EstatusMesaNombre,
    EstatusPedidoNombre,
    MetodoPagoNombre,
    RolNombre,
)
from app.data.db import Base, get_db
from app.data.estatus_cocina import EstatusCocina
from app.data.estatus_mesas import EstatusMesa
from app.data.estatus_pedidos import EstatusPedido
from app.data.mesas import Mesa
from app.data.metodos_pago import MetodoPago
from app.data.roles import Rol
from app.data.usuarios import Usuario
from app.main import app
from app.security.auth import hash_password

TEST_DB_NAME = "coffee_code_test"
ADMIN_DATABASE_URL = os.environ.get(
    "TEST_ADMIN_DATABASE_URL",
    "postgresql+psycopg2://coffee_user:coffee_pass@localhost:5434/postgres",
)
TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    f"postgresql+psycopg2://coffee_user:coffee_pass@localhost:5434/{TEST_DB_NAME}",
)


def _crear_db_de_test_si_no_existe() -> None:
    conn = psycopg2.connect(ADMIN_DATABASE_URL.replace("postgresql+psycopg2://", "postgresql://"))
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (TEST_DB_NAME,))
            if not cur.fetchone():
                cur.execute(f'CREATE DATABASE "{TEST_DB_NAME}"')
    finally:
        conn.close()


@pytest.fixture(scope="session")
def engine():
    _crear_db_de_test_si_no_existe()
    eng = create_engine(TEST_DATABASE_URL)
    Base.metadata.create_all(eng)
    yield eng
    eng.dispose()


@pytest.fixture()
def db_session(engine):
    connection = engine.connect()
    transaction = connection.begin()
    SessionLocalTest = sessionmaker(bind=connection)
    session = SessionLocalTest()

    nested = connection.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def _restart_savepoint(sess, trans):
        nonlocal nested
        if not nested.is_active:
            nested = connection.begin_nested()

    yield session

    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture()
def client(db_session):
    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture()
def catalogos(db_session):
    """Inserta el catalogo minimo (roles, estatus, metodos de pago) que la
    mayoria de los servicios de negocio asumen que ya existe."""
    roles = {
        nombre: Rol(nombre=nombre)
        for nombre in [
            RolNombre.MESERO,
            RolNombre.CAJERO,
            RolNombre.COCINERO,
            RolNombre.ADMINISTRADOR,
        ]
    }
    db_session.add_all(roles.values())

    estatus_mesas = {
        nombre: EstatusMesa(nombre=nombre)
        for nombre in [
            EstatusMesaNombre.LIBRE,
            EstatusMesaNombre.OCUPADA,
            EstatusMesaNombre.RESERVADA,
        ]
    }
    db_session.add_all(estatus_mesas.values())

    estatus_pedidos = {
        nombre: EstatusPedido(nombre=nombre)
        for nombre in [
            EstatusPedidoNombre.PENDIENTE,
            EstatusPedidoNombre.EN_PREPARACION,
            EstatusPedidoNombre.LISTO,
            EstatusPedidoNombre.ENTREGADO,
            EstatusPedidoNombre.CANCELADO,
        ]
    }
    db_session.add_all(estatus_pedidos.values())

    estatus_cocina = {
        nombre: EstatusCocina(nombre=nombre)
        for nombre in [
            EstatusCocinaNombre.PENDIENTE,
            EstatusCocinaNombre.EN_PREPARACION,
            EstatusCocinaNombre.LISTO,
        ]
    }
    db_session.add_all(estatus_cocina.values())

    metodos_pago = {
        nombre: MetodoPago(nombre=nombre)
        for nombre in [
            MetodoPagoNombre.EFECTIVO,
            MetodoPagoNombre.TARJETA_DEBITO,
            MetodoPagoNombre.TARJETA_CREDITO,
            MetodoPagoNombre.TRANSFERENCIA,
        ]
    }
    db_session.add_all(metodos_pago.values())

    db_session.flush()

    return {
        "roles": roles,
        "estatus_mesas": estatus_mesas,
        "estatus_pedidos": estatus_pedidos,
        "estatus_cocina": estatus_cocina,
        "metodos_pago": metodos_pago,
    }


@pytest.fixture()
def mesa_libre(db_session, catalogos):
    mesa = Mesa(numero_mesa=1, capacidad=4, id_estatus=catalogos["estatus_mesas"][EstatusMesaNombre.LIBRE].id)
    db_session.add(mesa)
    db_session.flush()
    return mesa


@pytest.fixture()
def usuario_mesero(db_session, catalogos):
    usuario = Usuario(
        nombre="Test",
        apellido_paterno="Mesero",
        correo_electronico="test.mesero@coffeecode.com",
        password_hash=hash_password("Test1234!"),
        id_rol=catalogos["roles"][RolNombre.MESERO].id,
    )
    db_session.add(usuario)
    db_session.flush()
    return usuario
