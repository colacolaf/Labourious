from backend.brokers.base import BrokerConnector
from backend.brokers.alpaca import AlpacaConnector
from backend.brokers.binance import BinanceConnector


def get_connector(broker: str, vault) -> BrokerConnector:
    """Return a broker connector, pulling credentials from vault."""
    broker = broker.lower()
    if broker == "alpaca":
        return AlpacaConnector(
            api_key=vault.get("alpaca_api_key"),
            secret=vault.get("alpaca_secret"),
            paper=True,
        )
    if broker == "binance":
        return BinanceConnector(
            api_key=vault.get("binance_api_key"),
            secret=vault.get("binance_secret"),
        )
    raise ValueError(f"Unsupported broker: {broker}")
