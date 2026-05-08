from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

@dataclass
class Holding:
    """
    Representa una compra individual de un activo.
    Una posición puede tener múltiples holdings (compras en diferentes fechas/precios).
    """
    qty: float
    price: float          # Precio de compra en moneda original (ARS o USD)
    date: datetime
    tc: Optional[float] = None  # Tasa de conversión al momento de la compra (para ARS->USD)

@dataclass
class Position:
    """
    Representa un activo único en el portfolio (ej: AL30, AAPL, BTC).
    Agrupa todos los holdings de ese ticker.
    """
    ticker: str
    asset_type: str       # 'ar', 'global', 'crypto'
    holdings: List[Holding] = field(default_factory=list)
    
    # Campos calculados dinámicamente (no se guardan en DB, se calculan al vuelo)
    _current_price: float = 0.0
    _change_pct: float = 0.0

    @property
    def total_qty(self) -> float:
        """Suma de todas las cantidades compradas."""
        return sum(h.qty for h in self.holdings)

    @property
    def avg_cost_original(self) -> float:
        """Precio promedio de compra ponderado por cantidad (en moneda original)."""
        if not self.holdings or self.total_qty == 0:
            return 0.0
        total_cost = sum(h.price * h.qty for h in self.holdings)
        return total_cost / self.total_qty

    @property
    def current_value_original(self) -> float:
        """Valor actual de la posición en su moneda original."""
        return self._current_price * self.total_qty

    def add_holding(self, qty: float, price: float, tc: Optional[float] = None):
        """Agrega una nueva compra a esta posición."""
        self.holdings.append(Holding(qty=qty, price=price, date=datetime.now(), tc=tc))

    def update_market_data(self, price: float, change_pct: float):
        """Actualiza el precio de mercado y la variación diaria desde la API."""
        self._current_price = price
        self._change_pct = change_pct

    @property
    def current_price(self) -> float:
        return self._current_price

    @property
    def change_pct(self) -> float:
        return self._change_pct