"""FastAPI application entry point for the algo trading platform."""

from __future__ import annotations

import json
import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from backend.api.auth_routes import router as auth_router
from backend.api.backtest_routes import router as backtest_router
from backend.api.dashboard_routes import router as dashboard_router
from backend.api.market_routes import router as market_router
from backend.api.order_routes import router as order_router
from backend.api.strategy_routes import router as strategy_router
from backend.core.database import init_db
from backend.services.instrument_service import InstrumentService
from backend.services.websocket_service import WebSocketService
from backend.strategies.strategy_engine import StrategyEngine

logger = logging.getLogger(__name__)

instrument_service = InstrumentService()
strategy_engine = StrategyEngine()
ws_service = WebSocketService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle events."""
    # ── Startup ──────────────────────────────────────────────────────────
    logger.info("Initializing database...")
    await init_db()

    logger.info("Loading instrument master data...")
    try:
        count = instrument_service.load_instruments()
        logger.info("Loaded %d instruments.", count)
    except Exception:
        logger.warning("Failed to load instruments at startup.", exc_info=True)

    logger.info("Loading strategies...")
    try:
        strategies = strategy_engine.load_strategies()
        logger.info(
            "Loaded %d strategies.", len(strategies)
        )
    except Exception:
        logger.warning("Failed to load strategies at startup.", exc_info=True)

    logger.info("Application startup complete.")
    yield

    # ── Shutdown ─────────────────────────────────────────────────────────
    logger.info("Application shutting down...")
    try:
        await ws_manager.disconnect_all()
    except Exception:
        logger.warning("Error during WebSocket cleanup.", exc_info=True)
    logger.info("Shutdown complete.")


app = FastAPI(
    title="Algo Trading Platform",
    description="Automated trading system with Angel One SmartAPI integration",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS middleware ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include routers ─────────────────────────────────────────────────────
app.include_router(auth_router)
app.include_router(market_router)
app.include_router(order_router)
app.include_router(strategy_router)
app.include_router(dashboard_router)
app.include_router(backtest_router)


# ── WebSocket connection manager ────────────────────────────────────────
class ConnectionManager:
    """Manages active WebSocket connections for live data streaming."""

    def __init__(self) -> None:
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(
            "WebSocket client connected. Active connections: %d",
            len(self.active_connections),
        )

    def disconnect(self, websocket: WebSocket) -> None:
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        logger.info(
            "WebSocket client disconnected. Active connections: %d",
            len(self.active_connections),
        )

    async def disconnect_all(self) -> None:
        for conn in self.active_connections:
            try:
                await conn.close()
            except Exception:
                pass
        self.active_connections.clear()

    async def broadcast(self, message: dict) -> None:
        """Send a message to all connected clients."""
        disconnected: list[WebSocket] = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for conn in disconnected:
            self.disconnect(conn)

    async def send_personal(self, websocket: WebSocket, message: dict) -> None:
        """Send a message to a specific client."""
        try:
            await websocket.send_json(message)
        except Exception:
            self.disconnect(websocket)


ws_manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for live data streaming to the frontend."""
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type", "")

                if msg_type == "subscribe":
                    # Client wants to subscribe to a ticker's live data
                    ticker = message.get("ticker", "")
                    await ws_manager.send_personal(
                        websocket,
                        {
                            "type": "subscribed",
                            "ticker": ticker,
                            "message": f"Subscribed to {ticker}",
                        },
                    )
                elif msg_type == "unsubscribe":
                    ticker = message.get("ticker", "")
                    await ws_manager.send_personal(
                        websocket,
                        {
                            "type": "unsubscribed",
                            "ticker": ticker,
                            "message": f"Unsubscribed from {ticker}",
                        },
                    )
                elif msg_type == "ping":
                    await ws_manager.send_personal(
                        websocket, {"type": "pong"}
                    )
                else:
                    await ws_manager.send_personal(
                        websocket,
                        {"type": "error", "message": f"Unknown message type: {msg_type}"},
                    )
            except json.JSONDecodeError:
                await ws_manager.send_personal(
                    websocket, {"type": "error", "message": "Invalid JSON"}
                )
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)


# ── Health check ────────────────────────────────────────────────────────
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "algo-trading-platform",
        "version": "1.0.0",
    }


# ── Serve frontend static files ────────────────────────────────────────
frontend_build = Path(__file__).resolve().parent.parent / "frontend" / "build"
if frontend_build.is_dir():
    app.mount("/", StaticFiles(directory=str(frontend_build), html=True), name="frontend")
    logger.info("Serving frontend from %s", frontend_build)
