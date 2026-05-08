import logging
from typing import Dict, Optional
from src.api.byma import get_bond_price
from src.api.yahoo import get_stock_price
from src.api.coingecko import get_crypto_price
from src.api.dolarapi import get_mep_rate
from src.utils.cache import Cache

logger = logging.getLogger(__name__)

class PriceService:
    """
    Servicio centralizado para obtener precios de mercado.
    Implementa caché en memoria para evitar saturar las APIs durante una sesión.
    """
    
    def __init__(self, cache_ttl_seconds: int = 300):
        self.cache = Cache(ttl_seconds=cache_ttl_seconds)
        self._mep_cache_key = "MEP_RATE"

    def get_mep_rate(self) -> float:
        """Obtiene la tasa MEP, usando caché si está disponible."""
        cached = self.cache.get(self._mep_cache_key)
        if cached is not None:
            return cached
        
        try:
            rate = get_mep_rate()
            if rate:
                self.cache.set(self._mep_cache_key, rate)
                return rate
        except Exception as e:
            logger.error(f"Error obteniendo MEP: {e}")
        
        # Fallback por defecto si falla todo
        return 1200.0

    def get_price(self, ticker: str, asset_type: str) -> Optional[Dict[str, float]]:
        """
        Obtiene el precio y variación diaria para un ticker específico.
        
        Args:
            ticker: Símbolo del activo (ej: AL30, AAPL, BTC).
            asset_type: 'ar', 'global', 'crypto'.
            
        Returns:
            Diccionario {'price': float, 'change': float} o None si falla.
        """
        cache_key = f"{ticker}_{asset_type}"
        
        # 1. Intentar caché primero
        cached_data = self.cache.get(cache_key)
        if cached_data:
            return cached_data

        # 2. Si no hay caché, llamar a la API correspondiente
        data = None
        try:
            if asset_type == 'ar':
                # Verificar si es bono o acción
                if ticker.upper() in ["AL30", "GD30", "AL35", "GD35", "AE38", "TX2U", "T2X5", "AO27", "AO30"]:
                    data = get_bond_price(ticker)
                else:
                    data = get_stock_price(ticker, is_argentine=True)
            
            elif asset_type == 'global':
                data = get_stock_price(ticker, is_argentine=False)
                
            elif asset_type == 'crypto':
                data = get_crypto_price(ticker)
                
        except Exception as e:
            logger.error(f"Error inesperado obteniendo precio para {ticker}: {e}")

        # 3. Guardar en caché si se obtuvo dato válido
        if data and 'price' in data:
            self.cache.set(cache_key, data)
            return data
            
        return None

    def get_prices_batch(self, positions: list) -> Dict[str, Dict[str, float]]:
        """
        Obtiene precios para una lista de posiciones.
        Útil para actualizar todo el portfolio de una vez.
        """
        results = {}
        for pos in positions:
            price_data = self.get_price(pos.ticker, pos.asset_type)
            if price_data:
                results[pos.ticker] = price_data
        return results