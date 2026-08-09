import responses

BASE_URL = "http://testserver"


def _login_como_admin(client):
    with client.session_transaction() as sess:
        sess["token"] = "token-admin"
        sess["rol"] = "Administrador"
        sess["correo"] = "admin@coffeecode.com"


@responses.activate
def test_listado_muestra_badges_de_pagado_y_pendiente(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/tickets",
        json=[
            {
                "id": 1,
                "subtotal": "100.00",
                "iva": "16.00",
                "total": "116.00",
                "fecha_emision": "2026-08-09T12:30:00",
                "id_pedido": 7,
                "id_mesa": 3,
                "id_usuario": 2,
                "pago": {
                    "id": 1,
                    "monto_recibido": "200.00",
                    "cambio": "84.00",
                    "metodo": {"id": 1, "nombre": "Efectivo"},
                },
            },
            {
                "id": 2,
                "subtotal": "50.00",
                "iva": "8.00",
                "total": "58.00",
                "fecha_emision": "2026-08-09T13:00:00",
                "id_pedido": 8,
                "id_mesa": 3,
                "id_usuario": 2,
                "pago": None,
            },
        ],
        status=200,
    )
    responses.add(
        responses.GET,
        f"{BASE_URL}/mesas",
        json=[{"id": 3, "numero_mesa": 12, "capacidad": 4}],
        status=200,
    )

    respuesta = client.get("/tickets")
    html = respuesta.data.decode()

    assert respuesta.status_code == 200
    assert "badge-success" in html and "Pagado" in html
    assert "badge-warning" in html and "Pendiente" in html
    assert ">12<" in html  # numero_mesa resuelto, no id_mesa


@responses.activate
def test_filtro_pendientes_pide_pagado_false(client):
    _login_como_admin(client)
    responses.add(responses.GET, f"{BASE_URL}/tickets", json=[], status=200)
    responses.add(responses.GET, f"{BASE_URL}/mesas", json=[], status=200)

    respuesta = client.get("/tickets?pagado=no")

    assert respuesta.status_code == 200
    assert "pagado=false" in responses.calls[0].request.url


@responses.activate
def test_preview_retransmite_pdf_sin_forzar_descarga(client):
    _login_como_admin(client)
    responses.add(
        responses.GET,
        f"{BASE_URL}/tickets/5/pdf",
        body=b"%PDF-ticket",
        status=200,
        content_type="application/pdf",
    )

    respuesta = client.get("/tickets/5/preview")

    assert respuesta.status_code == 200
    assert respuesta.content_type == "application/pdf"
    assert respuesta.data == b"%PDF-ticket"
    assert "Content-Disposition" not in respuesta.headers


def test_tickets_sin_sesion_redirige_a_login(client):
    respuesta = client.get("/tickets", follow_redirects=False)
    assert respuesta.status_code == 302
    assert "/login" in respuesta.headers["Location"]
