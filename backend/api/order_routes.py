"""Order management API routes."""

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.services.order_service import OrderService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/orders", tags=["orders"])

order_service = OrderService()


class PlaceOrderRequest(BaseModel):
    ticker: str
    type: str = Field(
        ..., description="Order type: MARKET, LIMIT, SL, SL-M"
    )
    transaction_type: str = Field(
        ..., description="BUY or SELL"
    )
    quantity: int = Field(..., gt=0)
    price: float | None = Field(None, description="Required for LIMIT/SL orders")
    product_type: str = Field(
        "INTRADAY", description="INTRADAY, DELIVERY, or CARRYFORWARD"
    )
    exchange: str = "NSE"
    trigger_price: float | None = None


class PlaceOrderResponse(BaseModel):
    status: str
    order_id: str
    message: str


class ModifyOrderRequest(BaseModel):
    order_type: str | None = None
    quantity: int | None = None
    price: float | None = None
    trigger_price: float | None = None


class OrderDetail(BaseModel):
    order_id: str
    ticker: str
    exchange: str
    transaction_type: str
    order_type: str
    product_type: str
    quantity: int
    price: float | None = None
    status: str
    placed_at: str | None = None


class TradeDetail(BaseModel):
    order_id: str
    ticker: str
    transaction_type: str
    quantity: int
    price: float
    executed_at: str | None = None


class PositionDetail(BaseModel):
    ticker: str
    exchange: str
    quantity: int
    avg_price: float
    current_price: float
    pnl: float
    product_type: str | None = None


class HoldingDetail(BaseModel):
    ticker: str
    exchange: str
    quantity: int
    avg_price: float
    current_price: float
    pnl: float


@router.post("/place", response_model=PlaceOrderResponse)
async def place_order(request: PlaceOrderRequest):
    """Place a new order."""
    try:
        result = order_service.place_order(
            ticker=request.ticker,
            order_type=request.type,
            transaction_type=request.transaction_type,
            quantity=request.quantity,
            price=request.price or 0,
            product_type=request.product_type,
            exchange=request.exchange,
            trigger_price=request.trigger_price or 0,
        )
        return PlaceOrderResponse(
            status="success",
            order_id=str(result.get("orderid", result.get("order_id", ""))),
            message="Order placed successfully",
        )
    except Exception as e:
        logger.error("Order placement failed: %s", e)
        raise HTTPException(status_code=400, detail=f"Order placement failed: {e}")


@router.put("/{order_id}/modify")
async def modify_order(order_id: str, request: ModifyOrderRequest):
    """Modify an existing order."""
    try:
        modifications = request.model_dump(exclude_none=True)
        if not modifications:
            raise HTTPException(
                status_code=400, detail="No modification parameters provided"
            )
        result = order_service.modify_order(order_id=order_id, **modifications)
        return {"status": "success", "message": "Order modified", "data": result}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Order modification failed for %s: %s", order_id, e)
        raise HTTPException(status_code=400, detail=f"Order modification failed: {e}")


@router.delete("/{order_id}/cancel")
async def cancel_order(order_id: str):
    """Cancel an existing order."""
    try:
        result = order_service.cancel_order(order_id=order_id)
        return {"status": "success", "message": "Order cancelled", "data": result}
    except Exception as e:
        logger.error("Order cancellation failed for %s: %s", order_id, e)
        raise HTTPException(
            status_code=400, detail=f"Order cancellation failed: {e}"
        )


@router.get("/book", response_model=list[OrderDetail])
async def get_order_book():
    """Get the current order book."""
    try:
        orders = order_service.get_order_book()
        if not orders:
            return []
        return [
            OrderDetail(
                order_id=str(o.get("orderid", "")),
                ticker=o.get("tradingsymbol", ""),
                exchange=o.get("exchange", ""),
                transaction_type=o.get("transactiontype", ""),
                order_type=o.get("ordertype", ""),
                product_type=o.get("producttype", ""),
                quantity=int(o.get("quantity", 0)),
                price=float(o["price"]) if o.get("price") else None,
                status=o.get("status", ""),
                placed_at=o.get("ordertime"),
            )
            for o in orders
        ]
    except Exception as e:
        logger.error("Error fetching order book: %s", e)
        raise HTTPException(status_code=500, detail=f"Failed to fetch order book: {e}")


@router.get("/trades", response_model=list[TradeDetail])
async def get_trade_book():
    """Get the trade book."""
    try:
        trades = order_service.get_trade_book()
        if not trades:
            return []
        return [
            TradeDetail(
                order_id=str(t.get("orderid", "")),
                ticker=t.get("tradingsymbol", ""),
                transaction_type=t.get("transactiontype", ""),
                quantity=int(t.get("quantity", 0)),
                price=float(t.get("price", 0)),
                executed_at=t.get("filltime"),
            )
            for t in trades
        ]
    except Exception as e:
        logger.error("Error fetching trade book: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch trade book: {e}"
        )


@router.get("/positions", response_model=list[PositionDetail])
async def get_positions():
    """Get current positions."""
    try:
        positions = order_service.get_positions()
        if not positions:
            return []
        return [
            PositionDetail(
                ticker=p.get("tradingsymbol", ""),
                exchange=p.get("exchange", ""),
                quantity=int(p.get("netqty", 0)),
                avg_price=float(p.get("averageprice", 0)),
                current_price=float(p.get("ltp", 0)),
                pnl=float(p.get("pnl", 0)),
                product_type=p.get("producttype"),
            )
            for p in positions
        ]
    except Exception as e:
        logger.error("Error fetching positions: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch positions: {e}"
        )


@router.get("/holdings", response_model=list[HoldingDetail])
async def get_holdings():
    """Get holdings."""
    try:
        holdings = order_service.get_holdings()
        if not holdings:
            return []
        return [
            HoldingDetail(
                ticker=h.get("tradingsymbol", ""),
                exchange=h.get("exchange", ""),
                quantity=int(h.get("quantity", 0)),
                avg_price=float(h.get("averageprice", 0)),
                current_price=float(h.get("ltp", 0)),
                pnl=float(h.get("pnl", 0)),
            )
            for h in holdings
        ]
    except Exception as e:
        logger.error("Error fetching holdings: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to fetch holdings: {e}"
        )
