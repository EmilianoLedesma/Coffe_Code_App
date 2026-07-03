import requests

_TIMEOUT = 5


class ApiError(Exception):
    def __init__(self, status_code: int | None, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def _headers(token: str | None) -> dict:
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _request(method: str, base_url: str, path: str, token: str | None = None, **kwargs):
    try:
        respuesta = requests.request(
            method, f"{base_url}{path}", headers=_headers(token), timeout=_TIMEOUT, **kwargs
        )
    except requests.RequestException as exc:
        raise ApiError(None, f"No se pudo conectar con la API: {exc}") from exc

    if respuesta.status_code >= 400:
        try:
            detalle = respuesta.json().get("detail", respuesta.text)
        except ValueError:
            detalle = respuesta.text
        raise ApiError(respuesta.status_code, detalle)

    if respuesta.status_code == 204 or not respuesta.content:
        return None
    return respuesta.json()


def login(base_url: str, correo: str, password: str) -> dict:
    return _request(
        "POST",
        base_url,
        "/auth/login",
        json={"correo_electronico": correo, "password": password},
    )


def listar_usuarios(base_url: str, token: str) -> list[dict]:
    return _request("GET", base_url, "/api/usuarios", token=token)


def crear_usuario(base_url: str, token: str, payload: dict) -> dict:
    return _request("POST", base_url, "/api/usuarios", token=token, json=payload)


def actualizar_usuario(base_url: str, token: str, usuario_id: int, payload: dict) -> dict:
    return _request("PUT", base_url, f"/api/usuarios/{usuario_id}", token=token, json=payload)


def listar_categorias(base_url: str, token: str) -> list[dict]:
    return _request("GET", base_url, "/categorias", token=token)


def listar_productos(base_url: str, token: str) -> list[dict]:
    return _request("GET", base_url, "/productos", token=token)


def crear_producto(base_url: str, token: str, payload: dict) -> dict:
    return _request("POST", base_url, "/productos", token=token, json=payload)


def actualizar_producto(base_url: str, token: str, producto_id: int, payload: dict) -> dict:
    return _request("PUT", base_url, f"/productos/{producto_id}", token=token, json=payload)


def eliminar_producto(base_url: str, token: str, producto_id: int) -> None:
    return _request("DELETE", base_url, f"/productos/{producto_id}", token=token)


def listar_ingredientes(base_url: str, token: str) -> list[dict]:
    return _request("GET", base_url, "/ingredientes", token=token)


def crear_ingrediente(base_url: str, token: str, payload: dict) -> dict:
    return _request("POST", base_url, "/ingredientes", token=token, json=payload)


def ajustar_stock_ingrediente(base_url: str, token: str, ingrediente_id: int, cantidad: str) -> dict:
    return _request(
        "PUT",
        base_url,
        f"/ingredientes/{ingrediente_id}/stock",
        token=token,
        json={"cantidad": cantidad},
    )


def listar_receta_producto(base_url: str, token: str, producto_id: int) -> list[dict]:
    return _request(
        "GET", base_url, "/producto_ingrediente", token=token, params={"producto_id": producto_id}
    )


def crear_receta(base_url: str, token: str, payload: dict) -> dict:
    return _request("POST", base_url, "/producto_ingrediente", token=token, json=payload)


def eliminar_receta(base_url: str, token: str, producto_id: int, ingrediente_id: int) -> None:
    return _request(
        "DELETE", base_url, f"/producto_ingrediente/{producto_id}/{ingrediente_id}", token=token
    )


def obtener_reporte_admin(base_url: str, token: str, desde: str, hasta: str) -> dict:
    return _request(
        "GET", base_url, "/api/reportes", token=token, params={"desde": desde, "hasta": hasta}
    )


def generar_corte_diario(base_url: str, token: str, fecha: str | None = None) -> dict:
    params = {"fecha": fecha} if fecha else {}
    return _request("POST", base_url, "/api/cortes-diarios", token=token, params=params)


def listar_cortes_diarios(base_url: str, token: str, desde: str, hasta: str) -> list[dict]:
    return _request(
        "GET", base_url, "/api/cortes-diarios", token=token, params={"desde": desde, "hasta": hasta}
    )
