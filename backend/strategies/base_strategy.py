from __future__ import annotations

from abc import ABC, abstractmethod
import pandas as pd
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import logging


class Signal(Enum):
    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


@dataclass
class TradeSignal:
    signal: Signal
    ticker: str
    price: float
    stop_loss: Optional[float] = None
    target: Optional[float] = None
    strategy_name: str = ""
    reason: str = ""
    quantity: int = 0


class BaseStrategy(ABC):
    def __init__(self, name: str, params: dict):
        self.name = name
        self.params = params
        self.logger = logging.getLogger(f"strategy.{name}")

    @abstractmethod
    def generate_signal(self, df: pd.DataFrame, ticker: str) -> TradeSignal:
        pass

    @abstractmethod
    def get_default_params(self) -> dict:
        pass

    def update_params(self, params: dict):
        self.params.update(params)
