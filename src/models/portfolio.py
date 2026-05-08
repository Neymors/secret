import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from .position import Position, Holding

class Portfolio:
    """
    Gestiona la colección de posiciones y realiza los cálculos financieros globales.
    Maneja la conversión de ARS a USD usando la tasa MEP proporcionada.
    """
    
    def __init__(self, mep_rate: float = 1200.0):
        self.positions: List[Position] = []
        self.mep_rate = mep_rate
        self.history: List[Dict[str, Any]] = [] # Para guardar snapshots diarios

    def add_position(self, ticker: str, asset_type: str, qty: float, ppc: float, tc: Optional[float] = None):
        """
        Agrega o actualiza una posición en el portfolio.
        
        Args:
            ticker: Símbolo del activo.
            asset_type: 'ar', 'global', 'crypto'.
            qty: Cantidad comprada.
            ppc: Precio promedio de compra (o precio de esta compra específica).
            tc: Tasa de conversión usada al momento de la compra (si es ARS).
        """
        # Buscar si ya existe
        existing_pos = next((p for p in self.positions if p.ticker == ticker), None)
        
        # Si no tiene TC y es AR, usamos el MEP actual como referencia histórica aproximada
        # Nota: En una app real, deberías guardar el MEP histórico exacto del día de la compra.
        if tc is None and asset_type == 'ar':
            tc = self.mep_rate

        if existing_pos:
            existing_pos.add_holding(qty, ppc, tc)
        else:
            new_pos = Position(ticker=ticker, asset_type=asset_type)
            new_pos.add_holding(qty, ppc, tc)
            self.positions.append(new_pos)

    def remove_position(self, ticker: str):
        """Elimina una posición completa por su ticker."""
        self.positions = [p for p in self.positions if p.ticker != ticker]

    def update_prices(self, prices_dict: Dict[str, Dict[str, float]]):
        """
        Actualiza los precios de mercado de todas las posiciones.
        
        Args:
            prices_dict: Diccionario { 'TICKER': {'price': float, 'change': float} }
        """
        for pos in self.positions:
            if pos.ticker in prices_dict:
                data = prices_dict[pos.ticker]
                pos.update_market_data(data['price'], data['change'])

    # ───────── CÁLCULOS FINANCIEROS ─────────

    @property
    def total_value_usd(self) -> float:
        """Calcula el valor total del portfolio convertido a USD."""
        total = 0.0
        for pos in self.positions:
            if pos.asset_type == 'ar':
                # Convertir ARS a USD usando MEP
                total += (pos.current_value_original / self.mep_rate)
            else:
                # Ya está en USD (Global/Crypto)
                total += pos.current_value_original
        return total

    @property
    def total_cost_usd(self) -> float:
        """Calcula el costo total original convertido a USD."""
        total = 0.0
        for pos in self.positions:
            for h in pos.holdings:
                cost_usd = (h.price * h.qty) / (h.tc if h.tc else self.mep_rate) if pos.asset_type == 'ar' else (h.price * h.qty)
                total += cost_usd
        return total

    @property
    def total_pnl_usd(self) -> float:
        """Ganancia/Pérdida total en USD."""
        return self.total_value_usd - self.total_cost_usd

    @property
    def total_pnl_pct(self) -> float:
        """Porcentaje de ganancia/pérdida total."""
        if self.total_cost_usd == 0:
            return 0.0
        return (self.total_pnl_usd / self.total_cost_usd) * 100

    @property
    def best_performer_today(self) -> Optional[Position]:
        """Devuelve la posición con mayor variación positiva hoy."""
        if not self.positions:
            return None
        # Filtramos solo los que tienen datos de cambio
        active_positions = [p for p in self.positions if p.change_pct != 0]
        if not active_positions:
            return None
        return max(active_positions, key=lambda p: p.change_pct)

    # ───────── PERSISTENCIA (JSON) ─────────

    def to_dict(self) -> Dict[str, Any]:
        """Serializa el portfolio a un diccionario para guardar en JSON."""
        return {
            "mep_rate": self.mep_rate,
            "positions": [
                {
                    "ticker": p.ticker,
                    "asset_type": p.asset_type,
                    "holdings": [
                        {
                            "qty": h.qty,
                            "price": h.price,
                            "date": h.date.isoformat(),
                            "tc": h.tc
                        } for h in p.holdings
                    ]
                } for p in self.positions
            ],
            "history": self.history
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Portfolio':
        """Crea una instancia de Portfolio desde un diccionario (cargado de JSON)."""
        portfolio = cls(mep_rate=data.get("mep_rate", 1200.0))
        
        for pos_data in data.get("positions", []):
            pos = Position(ticker=pos_data["ticker"], asset_type=pos_data["asset_type"])
            for h_data in pos_data.get("holdings", []):
                holding = Holding(
                    qty=h_data["qty"],
                    price=h_data["price"],
                    date=datetime.fromisoformat(h_data["date"]),
                    tc=h_data.get("tc")
                )
                pos.holdings.append(holding)
            portfolio.positions.append(pos)
            
        portfolio.history = data.get("history", [])
        return portfolio

    def save_to_json(self, filepath: str):
        """Guarda el estado actual en un archivo JSON."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=4, ensure_ascii=False)

    @classmethod
    def load_from_json(cls, filepath: str) -> 'Portfolio':
        """Carga el estado desde un archivo JSON."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return cls.from_dict(data)
        except FileNotFoundError:
            return cls() # Devuelve un portfolio vacío si no existe el archivo