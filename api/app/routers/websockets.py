from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status

from app.core.constants import RolNombre
from app.security.auth import decode_access_token
from app.websockets.manager import CANALES_VALIDOS, manager

router = APIRouter(tags=["websockets"])

_ROL_POR_CANAL = {
    "mesero": RolNombre.MESERO,
    "cocina": RolNombre.COCINERO,
    "caja": RolNombre.CAJERO,
}


@router.websocket("/ws/{canal}")
async def websocket_endpoint(websocket: WebSocket, canal: str, token: str) -> None:
    if canal not in CANALES_VALIDOS:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Canal inválido")
        return

    try:
        payload = decode_access_token(token)
    except Exception:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Token inválido o expirado")
        return

    rol = payload.get("rol")
    rol_esperado = _ROL_POR_CANAL[canal]
    if rol != rol_esperado and rol != RolNombre.ADMINISTRADOR:
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Rol no autorizado para este canal")
        return

    await manager.conectar(canal, websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.desconectar(canal, websocket)
