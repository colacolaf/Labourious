import pytest
from unittest.mock import patch, AsyncMock, MagicMock


def test_get_connector_alpaca_live_uses_live_base():
    """get_connector with paper=False creates AlpacaConnector pointing to live URL."""
    from backend.brokers.manager import get_connector
    vault = MagicMock()
    vault.get.side_effect = lambda k: "test_key" if "key" in k else "test_secret"

    connector = get_connector("alpaca", vault, paper=False)
    assert "paper-api" not in connector._base
    assert "api.alpaca.markets" in connector._base


def test_get_connector_alpaca_paper_uses_paper_base():
    """get_connector with paper=True (default) creates AlpacaConnector pointing to paper URL."""
    from backend.brokers.manager import get_connector
    vault = MagicMock()
    vault.get.side_effect = lambda k: "test_key" if "key" in k else "test_secret"

    connector = get_connector("alpaca", vault)  # default paper=True
    assert "paper-api.alpaca.markets" in connector._base


def test_get_connector_kraken_returns_kraken_connector():
    """get_connector('kraken') returns a BrokerConnector."""
    from backend.brokers.manager import get_connector
    from backend.brokers.base import BrokerConnector
    vault = MagicMock()
    vault.get.side_effect = lambda k: "test_key"

    connector = get_connector("kraken", vault)
    assert isinstance(connector, BrokerConnector)
