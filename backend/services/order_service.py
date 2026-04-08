"""Order management service for Angel One SmartAPI."""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Dict, List, Optional

from backend.services.instrument_service import InstrumentService
from backend.services.smartapi_auth import SmartAPIAuth

logger = logging.getLogger(__name__)


class OrderType(str, Enum):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOPLOSS_LIMIT = "STOPLOSS_LIMIT"
    STOPLOSS_MARKET = "STOPLOSS_MARKET"


class TransactionType(str, Enum):
    BUY = "BUY"
    SELL = "SELL"


class ProductType(str, Enum):
    INTRADAY = "INTRADAY"
    DELIVERY = "DELIVERY"
    CARRYFORWARD = "CARRYFORWARD"
    MARGIN = "MARGIN"
    BO = "BO"


class Variety(str, Enum):
    NORMAL = "NORMAL"
    STOPLOSS = "STOPLOSS"
    AMO = "AMO"
    ROBO = "ROBO"


class OrderService:
    """Places, modifies, and tracks orders through Angel One SmartAPI."""

    def __init__(
        self,
        auth: Optional[SmartAPIAuth] = None,
        instrument_service: Optional[InstrumentService] = None,
    ) -> None:
        self._auth = auth or SmartAPIAuth()
        self._instruments = instrument_service or InstrumentService()

    # ── order placement ───────────────────────────────────────────────────

    def place_order(
        self,
        ticker: str,
        transaction_type: str,
        order_type: str = "MARKET",
        quantity: int = 1,
        price: float = 0,
        product_type: str = "INTRADAY",
        variety: str = "NORMAL",
        exchange: str = "NSE",
        trigger_price: float = 0,
    ) -> Dict[str, Any]:
        """Place an order via SmartAPI.

        Args:
            ticker: Trading symbol (e.g. "RELIANCE-EQ").
            transaction_type: "BUY" or "SELL".
            order_type: MARKET, LIMIT, STOPLOSS_LIMIT, STOPLOSS_MARKET.
            quantity: Number of shares / lots.
            price: Limit price (0 for MARKET orders).
            product_type: INTRADAY, DELIVERY, etc.
            variety: NORMAL, STOPLOSS, AMO, ROBO.
            exchange: Exchange segment.
            trigger_price: Trigger price for stop-loss orders.

        Returns:
            API response dict containing order ID.
        """
        token = self._resolve_token(ticker, exchange)
        session = self._auth.get_session()

        order_params = {
            "variety": variety,
            "tradingsymbol": ticker,
            "symboltoken": token,
            "transactiontype": transaction_type,
            "exchange": exchange,
            "ordertype": order_type,
            "producttype": product_type,
            "duration": "DAY",
            "price": str(price),
            "squareoff": "0",
            "stoploss": "0",
            "quantity": str(quantity),
            "triggerprice": str(trigger_price),
        }

        max_retries = 2
        for attempt in range(1, max_retries + 1):
            try:
                resp = session.placeOrder(order_params)
                logger.info(
                    "Order placed: %s %s %s qty=%d price=%.2f | response=%s",
                    transaction_type,
                    ticker,
                    order_type,
                    quantity,
                    price,
                    resp,
                )
                return {"status": "success", "order_id": resp}

            except Exception as exc:
                logger.error(
                    "placeOrder attempt %d/%d failed: %s", attempt, max_retries, exc
                )
                if attempt == max_retries:
                    raise
                session = self._auth.refresh_session()

        raise RuntimeError("Failed to place order")

    def place_stoploss_order(
        self,
        ticker: str,
        transaction_type: str,
        quantity: int,
        trigger_price: float,
        price: float,
        exchange: str = "NSE",
    ) -> Dict[str, Any]:
        """Convenience method to place a stop-loss limit order."""
        return self.place_order(
            ticker=ticker,
            transaction_type=transaction_type,
            order_type="STOPLOSS_LIMIT",
            quantity=quantity,
            price=price,
            trigger_price=trigger_price,
            product_type="INTRADAY",
            variety="STOPLOSS",
            exchange=exchange,
        )

    # ── order management ──────────────────────────────────────────────────

    def modify_order(
        self, order_id: str, params: Dict[str, Any], variety: str = "NORMAL"
    ) -> Dict[str, Any]:
        """Modify an existing order.

        Args:
            order_id: The order ID to modify.
            params: Dict of fields to update (e.g. price, quantity, trigger_price).
            variety: Order variety.

        Returns:
            API response dict.
        """
        session = self._auth.get_session()
        modify_params = {"variety": variety, "orderid": order_id, **params}

        try:
            resp = session.modifyOrder(modify_params)
            logger.info("Order %s modified: %s", order_id, resp)
            return {"status": "success", "order_id": resp}
        except Exception as exc:
            logger.error("modifyOrder failed for %s: %s", order_id, exc)
            raise

    def cancel_order(
        self, order_id: str, variety: str = "NORMAL"
    ) -> Dict[str, Any]:
        """Cancel an open order.

        Args:
            order_id: The order ID to cancel.
            variety: Order variety.

        Returns:
            API response dict.
        """
        session = self._auth.get_session()

        try:
            resp = session.cancelOrder(order_id, variety)
            logger.info("Order %s cancelled: %s", order_id, resp)
            return {"status": "success", "order_id": resp}
        except Exception as exc:
            logger.error("cancelOrder failed for %s: %s", order_id, exc)
            raise

    # ── order / trade queries ─────────────────────────────────────────────

    def get_order_book(self) -> List[Dict[str, Any]]:
        """Return the full order book for the current session."""
        session = self._auth.get_session()
        try:
            resp = session.orderBook()
            if resp and resp.get("status") and resp.get("data"):
                return resp["data"]
            return []
        except Exception as exc:
            logger.error("orderBook failed: %s", exc)
            raise

    def get_trade_book(self) -> List[Dict[str, Any]]:
        """Return the trade book for the current session."""
        session = self._auth.get_session()
        try:
            resp = session.tradeBook()
            if resp and resp.get("status") and resp.get("data"):
                return resp["data"]
            return []
        except Exception as exc:
            logger.error("tradeBook failed: %s", exc)
            raise

    def get_positions(self) -> List[Dict[str, Any]]:
        """Return current positions."""
        session = self._auth.get_session()
        try:
            resp = session.position()
            if resp and resp.get("status") and resp.get("data"):
                return resp["data"]
            return []
        except Exception as exc:
            logger.error("position failed: %s", exc)
            raise

    def get_holdings(self) -> List[Dict[str, Any]]:
        """Return portfolio holdings."""
        session = self._auth.get_session()
        try:
            resp = session.holding()
            if resp and resp.get("status") and resp.get("data"):
                return resp["data"]
            return []
        except Exception as exc:
            logger.error("holding failed: %s", exc)
            raise

    # ── internals ─────────────────────────────────────────────────────────

    def _resolve_token(self, ticker: str, exchange: str) -> str:
        token = self._instruments.token_lookup(ticker, exchange)
        if token is None:
            raise ValueError(
                f"Symbol token not found for ticker={ticker}, exchange={exchange}."
            )
        return token
