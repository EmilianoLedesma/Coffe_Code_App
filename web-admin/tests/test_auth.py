import responses

BASE_URL = "http://testserver"


def test_login_page_carga(client):
    respuesta = client.get("/login")
    assert respuesta.status_code == 200
    assert b"Coffee Code" in respuesta.data


@responses.activate
def test_login_exitoso_como_administrador_redirige_al_dashboard(client):
    responses.add(
        responses.POST,
        f"{BASE_URL}/auth/login",
        json={"access_token": "token-admin", "rol": "Administrador"},
        status=200,
    )

    respuesta = client.post(
        "/login",
        data={"correo": "admin@coffeecode.com", "password": "Admin123!"},
        follow_redirects=False,
    )

    assert respuesta.status_code == 302
    with client.session_transaction() as sess:
        assert sess["token"] == "token-admin"
        assert sess["rol"] == "Administrador"


@responses.activate
def test_login_con_rol_no_admin_es_rechazado(client):
    responses.add(
        responses.POST,
        f"{BASE_URL}/auth/login",
        json={"access_token": "token-mesero", "rol": "Mesero"},
        status=200,
    )

    respuesta = client.post(
        "/login",
        data={"correo": "mesero@coffeecode.com", "password": "Mesero123!"},
    )

    assert respuesta.status_code == 200
    assert "Administrador" in respuesta.get_data(as_text=True)
    with client.session_transaction() as sess:
        assert "token" not in sess


def test_ruta_protegida_sin_sesion_redirige_a_login(client):
    respuesta = client.get("/", follow_redirects=False)
    assert respuesta.status_code == 302
    assert "/login" in respuesta.headers["Location"]


def test_logout_limpia_la_sesion(client):
    with client.session_transaction() as sess:
        sess["token"] = "algun-token"
        sess["rol"] = "Administrador"

    respuesta = client.get("/logout", follow_redirects=False)

    assert respuesta.status_code == 302
    with client.session_transaction() as sess:
        assert "token" not in sess
