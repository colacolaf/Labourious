from backend.brokers.base import BrokerConnector
from backend.brokers.alpaca import AlpacaConnector
from backend.brokers.binance import BinanceConnector


def get_connector(broker: str, vault, paper: bool = True) -> BrokerConnector:
    """Return a broker connector. paper=True (default) is safe for all non-production use."""
    broker = broker.lower()
    if broker == "alpaca":
        return AlpacaConnector(
            api_key=vault.get("alpaca_api_key"),
            secret=vault.get("alpaca_secret"),
            paper=paper,
        )
    if broker == "binance":
        return BinanceConnector(
            api_key=vault.get("binance_api_key"),
            secret=vault.get("binance_secret"),
        )
    if broker == "kraken":
        from backend.brokers.kraken import KrakenConnector
        return KrakenConnector(
            api_key=vault.get("kraken_api_key"),
            secret=vault.get("kraken_api_secret"),
            paper=paper,
        )
    # Generic ccxt fallback for any other exchange
    from backend.brokers.ccxt_generic import CcxtConnector
    return CcxtConnector(
        exchange_id=broker,
        api_key=vault.get(f"{broker}_api_key"),
        secret=vault.get(f"{broker}_secret"),
    )


def list_brokers() -> list[str]:
    """Return natively supported broker names."""
    return ["alpaca", "binance", "kraken"]
