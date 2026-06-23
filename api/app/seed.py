from app.core.constants import EstatusCocinaNombre, EstatusMesaNombre, EstatusPedidoNombre, MetodoPagoNombre, RolNombre
from app.data.categorias import Categoria
from app.data.db import SessionLocal
from app.data.estatus_cocina import EstatusCocina
from app.data.estatus_mesas import EstatusMesa
from app.data.estatus_pedidos import EstatusPedido
from app.data.ingredientes import Ingrediente
from app.data.mesas import Mesa
from app.data.metodos_pago import MetodoPago
from app.data.productos import Producto
from app.data.recetas import Receta
from app.data.roles import Rol
from app.data.usuarios import Usuario
from app.security.auth import hash_password

ROLES = [RolNombre.MESERO, RolNombre.CAJERO, RolNombre.COCINERO, RolNombre.ADMINISTRADOR]
ESTATUS_MESAS = [EstatusMesaNombre.LIBRE, EstatusMesaNombre.OCUPADA, EstatusMesaNombre.RESERVADA]
ESTATUS_PEDIDOS = [
    EstatusPedidoNombre.PENDIENTE,
    EstatusPedidoNombre.EN_PREPARACION,
    EstatusPedidoNombre.LISTO,
    EstatusPedidoNombre.ENTREGADO,
    EstatusPedidoNombre.CANCELADO,
]
ESTATUS_COCINA = [
    EstatusCocinaNombre.PENDIENTE,
    EstatusCocinaNombre.EN_PREPARACION,
    EstatusCocinaNombre.LISTO,
]
METODOS_PAGO = [
    MetodoPagoNombre.EFECTIVO,
    MetodoPagoNombre.TARJETA_DEBITO,
    MetodoPagoNombre.TARJETA_CREDITO,
    MetodoPagoNombre.TRANSFERENCIA,
]


def _seed_catalogo(db, modelo, nombres: list[str]) -> None:
    for nombre in nombres:
        existe = db.query(modelo).filter(modelo.nombre == nombre).first()
        if not existe:
            db.add(modelo(nombre=nombre))
    db.commit()


def _get_or_create_categoria(db, nombre: str, descripcion: str | None = None) -> Categoria:
    categoria = db.query(Categoria).filter(Categoria.nombre == nombre).first()
    if not categoria:
        categoria = Categoria(nombre=nombre, descripcion=descripcion, activo=True)
        db.add(categoria)
        db.commit()
    return categoria


def _get_or_create_producto(db, nombre: str, precio_venta, id_categoria: int, descripcion: str | None = None) -> Producto:
    producto = db.query(Producto).filter(Producto.nombre == nombre).first()
    if not producto:
        producto = Producto(
            nombre=nombre,
            descripcion=descripcion,
            precio_venta=precio_venta,
            disponible=True,
            activo=True,
            id_categoria=id_categoria,
        )
        db.add(producto)
        db.commit()
    return producto


def _get_or_create_ingrediente(db, nombre: str, unidad: str, stock_actual, stock_minimo, costo_unitario) -> Ingrediente:
    ingrediente = db.query(Ingrediente).filter(Ingrediente.nombre == nombre).first()
    if not ingrediente:
        ingrediente = Ingrediente(
            nombre=nombre,
            unidad=unidad,
            stock_actual=stock_actual,
            stock_minimo=stock_minimo,
            costo_unitario=costo_unitario,
            activo=True,
        )
        db.add(ingrediente)
        db.commit()
    return ingrediente


def _get_or_create_receta(db, id_producto: int, id_ingrediente: int, cantidad_requerida) -> None:
    receta = (
        db.query(Receta)
        .filter(Receta.id_producto == id_producto, Receta.id_ingrediente == id_ingrediente)
        .first()
    )
    if not receta:
        db.add(Receta(id_producto=id_producto, id_ingrediente=id_ingrediente, cantidad_requerida=cantidad_requerida))
        db.commit()


def _seed_menu(db) -> None:
    ingredientes = {
        "Leche": _get_or_create_ingrediente(db, "Leche", "ml", 10000, 1500, 0.012),
        "Cafe molido": _get_or_create_ingrediente(db, "Café molido", "g", 5000, 800, 0.25),
        "Espresso shot": _get_or_create_ingrediente(db, "Espresso (shot)", "ml", 4000, 500, 0.40),
        "Chocolate": _get_or_create_ingrediente(db, "Jarabe de chocolate", "ml", 3000, 500, 0.15),
        "Vainilla": _get_or_create_ingrediente(db, "Jarabe de vainilla", "ml", 2000, 400, 0.15),
        "Caramelo": _get_or_create_ingrediente(db, "Jarabe de caramelo", "ml", 2000, 400, 0.15),
        "Te negro": _get_or_create_ingrediente(db, "Té negro (bolsa)", "u", 200, 30, 1.50),
        "Hielo": _get_or_create_ingrediente(db, "Hielo", "g", 20000, 3000, 0.002),
        "Harina": _get_or_create_ingrediente(db, "Harina", "g", 10000, 2000, 0.02),
        "Azucar": _get_or_create_ingrediente(db, "Azúcar", "g", 8000, 1500, 0.015),
        "Mantequilla": _get_or_create_ingrediente(db, "Mantequilla", "g", 4000, 800, 0.09),
        "Huevo": _get_or_create_ingrediente(db, "Huevo", "u", 200, 36, 3.00),
        "Chispas chocolate": _get_or_create_ingrediente(db, "Chispas de chocolate", "g", 3000, 500, 0.08),
        "Pan bimbo": _get_or_create_ingrediente(db, "Pan para sandwich", "u", 100, 20, 2.50),
        "Jamon": _get_or_create_ingrediente(db, "Jamón", "g", 3000, 500, 0.18),
        "Queso": _get_or_create_ingrediente(db, "Queso amarillo", "g", 3000, 500, 0.20),
    }

    cat_calientes = _get_or_create_categoria(db, "Bebidas calientes", "Café y té servidos calientes")
    cat_frias = _get_or_create_categoria(db, "Bebidas frías", "Café y té servidos fríos o con hielo")
    cat_reposteria = _get_or_create_categoria(db, "Repostería", "Panadería dulce de elaboración propia")
    cat_snacks = _get_or_create_categoria(db, "Snacks salados", "Sandwiches y bocadillos")

    productos_recetas = [
        # (nombre, precio, categoria, descripcion, [(ingrediente, cantidad), ...])
        ("Café Americano", 35.00, cat_calientes, "Café negro de filtro", [("Cafe molido", 18)]),
        ("Espresso", 30.00, cat_calientes, "Shot doble de espresso", [("Espresso shot", 30)]),
        ("Capuchino", 45.00, cat_calientes, "Espresso con leche vaporizada y espuma", [("Espresso shot", 30), ("Leche", 150)]),
        ("Latte Vainilla", 48.00, cat_calientes, "Café con leche y jarabe de vainilla", [("Espresso shot", 30), ("Leche", 180), ("Vainilla", 15)]),
        ("Mocha", 50.00, cat_calientes, "Café con chocolate y leche", [("Espresso shot", 30), ("Leche", 150), ("Chocolate", 20)]),
        ("Té Negro", 28.00, cat_calientes, "Infusión de té negro", [("Te negro", 1)]),
        ("Frappé de Caramelo", 55.00, cat_frias, "Café frío con hielo y caramelo", [("Espresso shot", 30), ("Leche", 120), ("Caramelo", 25), ("Hielo", 150)]),
        ("Iced Latte", 50.00, cat_frias, "Café con leche servido frío", [("Espresso shot", 30), ("Leche", 180), ("Hielo", 100)]),
        ("Té Helado", 32.00, cat_frias, "Té negro servido con hielo", [("Te negro", 1), ("Hielo", 150)]),
        ("Muffin de Chocolate", 38.00, cat_reposteria, "Pieza individual horneada en casa", [("Harina", 60), ("Azucar", 35), ("Mantequilla", 25), ("Huevo", 1), ("Chispas chocolate", 20)]),
        ("Pan de Vainilla", 32.00, cat_reposteria, "Rebanada de pan dulce", [("Harina", 50), ("Azucar", 25), ("Mantequilla", 20), ("Huevo", 1), ("Vainilla", 5)]),
        ("Galleta con Chispas", 25.00, cat_reposteria, "Galleta artesanal", [("Harina", 30), ("Azucar", 20), ("Mantequilla", 15), ("Chispas chocolate", 15)]),
        ("Sandwich de Jamón y Queso", 55.00, cat_snacks, "Pan blanco, jamón y queso amarillo", [("Pan bimbo", 2), ("Jamon", 60), ("Queso", 40)]),
    ]

    for nombre, precio, categoria, descripcion, receta in productos_recetas:
        producto = _get_or_create_producto(db, nombre, precio, categoria.id, descripcion)
        for nombre_ingrediente, cantidad in receta:
            ingrediente = ingredientes[nombre_ingrediente]
            _get_or_create_receta(db, producto.id, ingrediente.id, cantidad)


def run() -> None:
    db = SessionLocal()
    try:
        _seed_catalogo(db, Rol, ROLES)
        _seed_catalogo(db, EstatusMesa, ESTATUS_MESAS)
        _seed_catalogo(db, EstatusPedido, ESTATUS_PEDIDOS)
        _seed_catalogo(db, EstatusCocina, ESTATUS_COCINA)
        _seed_catalogo(db, MetodoPago, METODOS_PAGO)

        estatus_libre = db.query(EstatusMesa).filter(EstatusMesa.nombre == EstatusMesaNombre.LIBRE).first()
        if db.query(Mesa).count() == 0:
            for numero in range(1, 9):
                db.add(Mesa(numero_mesa=numero, capacidad=4, id_estatus=estatus_libre.id))
            db.commit()

        _seed_menu(db)

        rol_admin = db.query(Rol).filter(Rol.nombre == RolNombre.ADMINISTRADOR).first()
        admin = db.query(Usuario).filter(Usuario.correo_electronico == "admin@coffeecode.com").first()
        if not admin:
            db.add(
                Usuario(
                    nombre="Admin",
                    apellido_paterno="Coffee",
                    apellido_materno="Code",
                    correo_electronico="admin@coffeecode.com",
                    password_hash=hash_password("Admin123!"),
                    id_rol=rol_admin.id,
                )
            )
            db.commit()

        rol_mesero = db.query(Rol).filter(Rol.nombre == RolNombre.MESERO).first()
        mesero = db.query(Usuario).filter(Usuario.correo_electronico == "mesero@coffeecode.com").first()
        if not mesero:
            db.add(
                Usuario(
                    nombre="Juan",
                    apellido_paterno="Perez",
                    correo_electronico="mesero@coffeecode.com",
                    password_hash=hash_password("Mesero123!"),
                    id_rol=rol_mesero.id,
                )
            )
            db.commit()

        rol_cajero = db.query(Rol).filter(Rol.nombre == RolNombre.CAJERO).first()
        cajero = db.query(Usuario).filter(Usuario.correo_electronico == "cajero@coffeecode.com").first()
        if not cajero:
            db.add(
                Usuario(
                    nombre="Maria",
                    apellido_paterno="Lopez",
                    correo_electronico="cajero@coffeecode.com",
                    password_hash=hash_password("Cajero123!"),
                    id_rol=rol_cajero.id,
                )
            )
            db.commit()

        rol_cocinero = db.query(Rol).filter(Rol.nombre == RolNombre.COCINERO).first()
        cocinero = db.query(Usuario).filter(Usuario.correo_electronico == "cocinero@coffeecode.com").first()
        if not cocinero:
            db.add(
                Usuario(
                    nombre="Carlos",
                    apellido_paterno="Ramirez",
                    correo_electronico="cocinero@coffeecode.com",
                    password_hash=hash_password("Cocinero123!"),
                    id_rol=rol_cocinero.id,
                )
            )
            db.commit()

        print("Seed completado: catálogos, mesas y usuarios de prueba listos.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
