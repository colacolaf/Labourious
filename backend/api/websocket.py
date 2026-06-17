from fastapi import APIRouter, WebSocket

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/connect")
async def websocket_connect(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_json({"type": "connected", "message": "WebSocket stub — Phase 2"})
    await websocket.close()
