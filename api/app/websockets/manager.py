import asyncio
from collections import defaultdict

from fastapi import WebSocket

CANALES_VALIDOS = {"mesero", "cocina", "caja"}


class ConnectionManager:
    """Gestiona conexiones WebSocket agrupadas por canal (rol) y permite
    emitir eventos desde código síncrono (los routers de pedidos/caja corren
    en threadpool) hacia el loop de asyncio donde viven los sockets."""

    def __init__(self) -> None:
        self._conexiones: dict[str, list[WebSocket]] = defaultdict(list)
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    async def conectar(self, canal: str, websocket: WebSocket) -> None:
        await websocket.accept()
        self._conexiones[canal].append(websocket)

    def desconectar(self, canal: str, websocket: WebSocket) -> None:
        conexiones = self._conexiones.get(canal, [])
        if websocket in conexiones:
            conexiones.remove(websocket)

    async def _enviar_a_canal(self, canal: str, mensaje: dict) -> None:
        for websocket in list(self._conexiones.get(canal, [])):
            try:
                await websocket.send_json(mensaje)
            except Exception:
                self.desconectar(canal, websocket)

    def emitir(self, canal: str, mensaje: dict) -> None:
        """Thread-safe: se puede llamar desde rutas síncronas (threadpool)."""
        if self._loop is None:
            return
        asyncio.run_coroutine_threadsafe(self._enviar_a_canal(canal, mensaje), self._loop)


manager = ConnectionManager()
