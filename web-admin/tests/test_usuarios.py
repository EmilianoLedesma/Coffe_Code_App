import responses

BASE_URL = "http://testserver"


def _login_como_admin(client):
    with client.session_transaction() as sess:
        sess["token"] = "token-admin"
        sess["rol"] = "Administrador"
        sess["correo"] = "admin@coffeecode.com"


@responses.activate
def test_listar_usuarios_muestra_tabla(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/roles",
        json=[
            {"id": 1, "nombre": "Mesero"},
            {"id": 2, "nombre": "Cajero"},
            {"id": 3, "nombre": "Cocinero"},
            {"id": 4, "nombre": "Administrador"},
        ],
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/usuarios",
        json=[
            {
                "id": 1,
                "nombre": "Ana",
                "apellido_paterno": "Ruiz",
                "apellido_materno": None,
                "correo_electronico": "ana@coffeecode.com",
                "activo": True,
                "fecha_creacion": "2026-01-01T00:00:00",
                "rol": {"id": 4, "nombre": "Administrador"},
            }
        ],
        status=200,
    )

    respuesta = client.get("/usuarios")

    assert respuesta.status_code == 200
    assert b"ana@coffeecode.com" in respuesta.data


@responses.activate
def test_listar_usuarios_usa_roles_de_la_api(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/roles",
        json=[
            {"id": 1, "nombre": "Mesero"},
            {"id": 2, "nombre": "Cajero"},
            {"id": 3, "nombre": "Cocinero"},
            {"id": 4, "nombre": "Administrador"},
        ],
        status=200,
    )
    responses.add(responses.GET, f"{BASE_URL}/api/usuarios", json=[], status=200)

    respuesta = client.get("/usuarios")

    assert respuesta.status_code == 200
    assert responses.calls[0].request.url.endswith("/api/roles")


@responses.activate
def test_crear_usuario_reenvia_payload_a_la_api(client):
    _login_como_admin(client)
    responses.add(
        responses.POST,
        f"{BASE_URL}/api/usuarios",
        json={"id": 2},
        status=201,
    )

    respuesta = client.post(
        "/usuarios/nuevo",
        data={
            "nombre": "Luis",
            "apellido_paterno": "Perez",
            "apellido_materno": "",
            "correo_electronico": "luis@coffeecode.com",
            "password": "Password123",
            "id_rol": "1",
        },
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    enviado = responses.calls[-1].request
    assert enviado.headers["Authorization"] == "Bearer token-admin"


def test_usuarios_sin_sesion_redirige_a_login(client):
    respuesta = client.get("/usuarios", follow_redirects=False)
    assert respuesta.status_code == 302
    assert "/login" in respuesta.headers["Location"]


@responses.activate
def test_editar_usuario_envia_password_si_se_captura(client):
    _login_como_admin(client)
    responses.add(
        responses.PUT,
        f"{BASE_URL}/api/usuarios/1",
        json={"id": 1, "nombre": "Ana"},
        status=200,
    )

    respuesta = client.post(
        "/usuarios/1/editar",
        data={
            "nombre": "Ana",
            "apellido_paterno": "Ruiz",
            "apellido_materno": "",
            "correo_electronico": "ana@coffeecode.com",
            "id_rol": "1",
            "password": "NuevaClave123!",
        },
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    import json

    cuerpo_enviado = json.loads(responses.calls[-1].request.body)
    assert cuerpo_enviado["password"] == "NuevaClave123!"


@responses.activate
def test_editar_usuario_sin_password_no_la_envia(client):
    _login_como_admin(client)
    responses.add(
        responses.PUT,
        f"{BASE_URL}/api/usuarios/1",
        json={"id": 1, "nombre": "Ana"},
        status=200,
    )

    respuesta = client.post(
        "/usuarios/1/editar",
        data={
            "nombre": "Ana",
            "apellido_paterno": "Ruiz",
            "apellido_materno": "",
            "correo_electronico": "ana@coffeecode.com",
            "id_rol": "1",
            "password": "",
        },
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    import json

    cuerpo_enviado = json.loads(responses.calls[-1].request.body)
    assert "password" not in cuerpo_enviado
