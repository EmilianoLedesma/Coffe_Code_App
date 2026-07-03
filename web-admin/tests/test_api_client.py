import pytest
import responses

from app.api_client import (
    ApiError,
    descargar_reporte,
    listar_productos,
    login,
    obtener_reporte_financiero,
    obtener_reporte_inventario,
)

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


@responses.activate
def test_obtener_reporte_financiero():
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes/financiero",
        json={"total_ventas": "550.00", "ranking_margen": []},
        status=200,
    )

    resultado = obtener_reporte_financiero(BASE_URL, "token", "2026-06-01", "2026-06-30")

    assert resultado["total_ventas"] == "550.00"


@responses.activate
def test_obtener_reporte_inventario():
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes/inventario",
        json={"riesgo": []},
        status=200,
    )

    resultado = obtener_reporte_inventario(BASE_URL, "token")

    assert resultado == {"riesgo": []}


@responses.activate
def test_descargar_reporte_devuelve_response_crudo():
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes/financiero/pdf",
        body=b"%PDF-contenido-simulado",
        status=200,
        content_type="application/pdf",
    )

    respuesta = descargar_reporte(BASE_URL, "token", "financiero", "pdf", {"desde": "2026-06-01"})

    assert respuesta.status_code == 200
    assert respuesta.content == b"%PDF-contenido-simulado"


@responses.activate
def test_descargar_reporte_lanza_apierror_en_4xx():
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes/inventario/xlsx",
        json={"detail": "No autorizado"},
        status=403,
    )

    with pytest.raises(ApiError) as exc_info:
        descargar_reporte(BASE_URL, "token", "inventario", "xlsx")

    assert exc_info.value.status_code == 403
