from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter(prefix="/ws", tags=["websocket"])


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.active: set[WebSocket] = set()

    async def connect(self, ws: WebSocket):
        """Accept a WebSocket connection and add to active set."""
        await ws.accept()
        self.active.add(ws)

    def disconnect(self, ws: WebSocket):
        """Remove a WebSocket from active set."""
        self.active.discard(ws)

    async def broadcast(self, data: dict):
        """Broadcast data to all active connections; remove dead connections silently."""
        dead = set()
        for ws in self.active:
            try:
                await ws.send_json(data)
            except Exception:
                dead.add(ws)
        self.active -= dead


# Module-level singleton — imported by orchestrator and risk_agent
manager = ConnectionManager()

# Module-level callback for trade approval — set by orchestrator at startup
_approval_handler = None


def set_approval_handler(fn):
    """Set the approval handler callback."""
    global _approval_handler
    _approval_handler = fn


async def _handle_inbound(data: dict):
    """Route inbound WS messages."""
    msg_type = data.get("type")
    if msg_type in ("approve_trade", "reject_trade"):
        if _approval_handler:
            await _approval_handler(data)


@router.websocket("/connect")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time trading updates and trade approvals."""
    await manager.connect(websocket)
    try:
        await websocket.send_json({"type": "connected"})
        while True:
            data = await websocket.receive_json()
            await _handle_inbound(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)


@router.websocket("")
async def websocket_root(websocket: WebSocket):
    """WS endpoint at /ws (spec-compliant path)."""
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            await _handle_inbound(data)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
