import pytest
import responses

from app.api_client import ApiError, listar_productos, login

BASE_URL = "http://testserver"


@responses.activate
def test_login_devuelve_token_y_rol():
    responses.add(
        responses.POST,
        f"{BASE_URL}/auth/login",
        json={"access_token": "abc123", "rol": "Administrador"},
        status=200,
    )

    resultado = login(BASE_URL, "admin@coffeecode.com", "Admin123!")

    assert resultado == {"access_token": "abc123", "rol": "Administrador"}


@responses.activate
def test_login_credenciales_invalidas_lanza_apierror():
    responses.add(
        responses.POST,
        f"{BASE_URL}/auth/login",
        json={"detail": "Correo o contraseña incorrectos"},
        status=401,
    )

    with pytest.raises(ApiError) as excinfo:
        login(BASE_URL, "malo@coffeecode.com", "mal")

    assert excinfo.value.status_code == 401
    assert "incorrectos" in excinfo.value.detail


@responses.activate
def test_listar_productos_envia_bearer_token():
    responses.add(
        responses.GET,
        f"{BASE_URL}/productos",
        json=[{"id": 1, "nombre": "Latte"}],
        status=200,
    )

    resultado = listar_productos(BASE_URL, "token-de-prueba")

    assert resultado == [{"id": 1, "nombre": "Latte"}]
    assert responses.calls[0].request.headers["Authorization"] == "Bearer token-de-prueba"
