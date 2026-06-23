import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers.admin import router as admin_router
from app.routers.auth import router as auth_router
from app.routers.caja import router as caja_router
from app.routers.ingredientes import router as ingredientes_router
from app.routers.mesas import router as mesas_router
from app.routers.pedidos import router as pedidos_router
from app.routers.productos import router as productos_router
from app.routers.recetas import router as recetas_router
from app.routers.websockets import router as websockets_router
from app.websockets.manager import manager


@asynccontextmanager
async def lifespan(app: FastAPI):
    manager.set_loop(asyncio.get_running_loop())
    yield


app = FastAPI(title="Coffee Code API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(mesas_router)
app.include_router(pedidos_router)
app.include_router(caja_router)
app.include_router(productos_router)
app.include_router(ingredientes_router)
app.include_router(recetas_router)
app.include_router(admin_router)
app.include_router(websockets_router)


@app.get("/health", tags=["health"])
def health() -> dict:
    return {"status": "ok"}
