"""Notification service -- Telegram and email alerts."""

from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Any, Dict, Optional

import httpx

from backend.core.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """Send trade alerts and risk notifications via Telegram and email."""

    def __init__(self) -> None:
        self._telegram_url: Optional[str] = None
        if settings.TELEGRAM_BOT_TOKEN:
            self._telegram_url = (
                f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            )

    # ── Telegram ──────────────────────────────────────────────────────────

    def send_telegram(self, message: str) -> bool:
        """Send a message to the configured Telegram chat.

        Returns:
            True if sent successfully, False otherwise.
        """
        if not self._telegram_url or not settings.TELEGRAM_CHAT_ID:
            logger.warning("Telegram not configured -- skipping message.")
            return False

        payload = {
            "chat_id": settings.TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "HTML",
        }

        try:
            with httpx.Client(timeout=10.0) as client:
                resp = client.post(self._telegram_url, json=payload)
                resp.raise_for_status()
            logger.info("Telegram message sent successfully.")
            return True
        except Exception as exc:
            logger.error("Failed to send Telegram message: %s", exc)
            return False

    # ── Email ─────────────────────────────────────────────────────────────

    def send_email(self, subject: str, body: str, to_email: str) -> bool:
        """Send an email via SMTP.

        Returns:
            True if sent successfully, False otherwise.
        """
        if not all([settings.EMAIL_HOST, settings.EMAIL_PORT, settings.EMAIL_USER, settings.EMAIL_PASSWORD]):
            logger.warning("Email not configured -- skipping.")
            return False

        msg = MIMEMultipart()
        msg["From"] = settings.EMAIL_USER  # type: ignore[assignment]
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        try:
            with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:  # type: ignore[arg-type]
                server.starttls()
                server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)  # type: ignore[arg-type]
                server.send_message(msg)
            logger.info("Email sent to %s: %s", to_email, subject)
            return True
        except Exception as exc:
            logger.error("Failed to send email: %s", exc)
            return False

    # ── high-level notifications ──────────────────────────────────────────

    def notify_trade(self, trade_details: Dict[str, Any]) -> None:
        """Format and send a trade notification via all channels.

        Args:
            trade_details: Dict with keys like ticker, action, quantity, price, etc.
        """
        ticker = trade_details.get("ticker", "N/A")
        action = trade_details.get("action", "N/A")
        qty = trade_details.get("quantity", "N/A")
        price = trade_details.get("price", "N/A")
        order_id = trade_details.get("order_id", "N/A")

        message = (
            f"<b>Trade Executed</b>\n"
            f"Ticker: {ticker}\n"
            f"Action: {action}\n"
            f"Qty: {qty}\n"
            f"Price: {price}\n"
            f"Order ID: {order_id}"
        )

        self.send_telegram(message)
        if settings.EMAIL_USER:
            self.send_email(
                subject=f"Trade Alert: {action} {ticker}",
                body=message,
                to_email=settings.EMAIL_USER,
            )

    def notify_signal(self, strategy: str, ticker: str, signal_type: str) -> None:
        """Send a trading signal notification.

        Args:
            strategy: Name of the strategy generating the signal.
            ticker: Instrument symbol.
            signal_type: e.g. "BUY", "SELL", "EXIT".
        """
        message = (
            f"<b>Signal Alert</b>\n"
            f"Strategy: {strategy}\n"
            f"Ticker: {ticker}\n"
            f"Signal: {signal_type}"
        )

        self.send_telegram(message)
        if settings.EMAIL_USER:
            self.send_email(
                subject=f"Signal: {signal_type} {ticker} ({strategy})",
                body=message,
                to_email=settings.EMAIL_USER,
            )

    def notify_risk_alert(self, alert_type: str, details: str) -> None:
        """Send a risk management alert.

        Args:
            alert_type: Category (e.g. "DRAWDOWN", "LOSS_LIMIT", "TRADE_LIMIT").
            details: Human-readable explanation.
        """
        message = (
            f"<b>Risk Alert</b>\n"
            f"Type: {alert_type}\n"
            f"Details: {details}"
        )

        self.send_telegram(message)
        if settings.EMAIL_USER:
            self.send_email(
                subject=f"Risk Alert: {alert_type}",
                body=message,
                to_email=settings.EMAIL_USER,
            )
