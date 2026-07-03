import pytest
import responses

from app.blueprints.reportes import bp as reportes_bp

BASE_URL = "http://testserver"


@pytest.fixture()
def client(app):
    if "reportes" not in app.blueprints:
        app.register_blueprint(reportes_bp)
    return app.test_client()


def _login_como_admin(client):
    with client.session_transaction() as sess:
        sess["token"] = "token-admin"
        sess["rol"] = "Administrador"
        sess["correo"] = "admin@coffeecode.com"


@responses.activate
def test_exportar_financiero_pdf_retransmite_bytes(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes/financiero/pdf",
        body=b"%PDF-contenido",
        status=200,
        content_type="application/pdf",
    )

    respuesta = client.get("/reportes/financiero/exportar.pdf?desde=2026-06-01&hasta=2026-06-30")

    assert respuesta.status_code == 200
    assert respuesta.content_type == "application/pdf"
    assert respuesta.data == b"%PDF-contenido"


@responses.activate
def test_exportar_inventario_xlsx_retransmite_bytes(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/api/reportes/inventario/xlsx",
        body=b"PK-contenido-zip",
        status=200,
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

    respuesta = client.get("/reportes/inventario/exportar.xlsx")

    assert respuesta.status_code == 200
    assert respuesta.data == b"PK-contenido-zip"


def test_exportar_formato_invalido_da_404(client):
    _login_como_admin(client)
    respuesta = client.get("/reportes/financiero/exportar.docx")
    assert respuesta.status_code == 404


@responses.activate
def test_exportar_sin_sesion_redirige_a_login(client):
    respuesta = client.get("/reportes/financiero/exportar.pdf", follow_redirects=False)
    assert respuesta.status_code == 302
    assert "/login" in respuesta.headers["Location"]
