import pytest
from unittest.mock import AsyncMock
from backend.api.websocket import ConnectionManager, manager, set_approval_handler


@pytest.fixture
def conn_manager():
    """Create a fresh ConnectionManager for testing."""
    return ConnectionManager()


@pytest.mark.asyncio
async def test_broadcast_sends_to_all(conn_manager):
    """Test that broadcast sends data to all active connections."""
    # Create mock WebSockets
    ws1 = AsyncMock()
    ws2 = AsyncMock()

    # Add to manager
    conn_manager.active.add(ws1)
    conn_manager.active.add(ws2)

    # Broadcast data
    test_data = {"type": "test", "message": "hello"}
    await conn_manager.broadcast(test_data)

    # Assert both WebSockets received the data
    ws1.send_json.assert_called_once_with(test_data)
    ws2.send_json.assert_called_once_with(test_data)


@pytest.mark.asyncio
async def test_broadcast_removes_dead(conn_manager):
    """Test that broadcast removes dead connections after failed send."""
    # Create mock WebSockets
    ws_good = AsyncMock()
    ws_dead = AsyncMock()
    ws_dead.send_json.side_effect = Exception("Connection closed")

    # Add to manager
    conn_manager.active.add(ws_good)
    conn_manager.active.add(ws_dead)

    # Broadcast data
    test_data = {"type": "test", "message": "hello"}
    await conn_manager.broadcast(test_data)

    # Assert good connection sent data
    ws_good.send_json.assert_called_once_with(test_data)
    # Assert dead connection was removed
    assert ws_dead not in conn_manager.active
    assert ws_good in conn_manager.active


@pytest.mark.asyncio
async def test_disconnect_removes(conn_manager):
    """Test that disconnect removes a WebSocket from active set."""
    ws = AsyncMock()
    conn_manager.active.add(ws)

    assert ws in conn_manager.active

    conn_manager.disconnect(ws)

    assert ws not in conn_manager.active


def test_set_approval_handler():
    """Test that set_approval_handler sets the callback."""
    async def test_handler(data):
        pass

    set_approval_handler(test_handler)
    from backend.api import websocket
    assert websocket._approval_handler == test_handler


@pytest.mark.asyncio
async def test_reject_trade_routes_to_handler():
    """reject_trade inbound message calls approval handler with approved=False."""
    from backend.api.websocket import _handle_inbound, set_approval_handler
    calls = []
    async def handler(data):
        calls.append(data)
    set_approval_handler(handler)
    await _handle_inbound({"type": "reject_trade", "trade_id": "abc"})
    assert len(calls) == 1
    assert calls[0]["type"] == "reject_trade"
