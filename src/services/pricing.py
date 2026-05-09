import requests
import yfinance as yf
from typing import List, Dict, Any, Optional
from datetime import datetime
from bs4 import BeautifulSoup

# Asegurate de que la importación de Position funcione con tu estructura
from src.models.portfolio import Position

class PriceService:
    """
    Servicio para obtener precios en tiempo real de activos argentinos, globales y criptomonedas.
    Incluye tasa MEP, caché simple y scraping para bonos argentinos.
    """

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Amygdalé/1.0 (Financial Portfolio Tracker)"
        })
        self.cache = {}  # caché simple {ticker: (price, timestamp)}
        self.cache_ttl = 60  # segundos

    def _get_from_cache(self, ticker: str) -> Optional[float]:
        """Obtiene precio de caché si no expiró."""
        if ticker in self.cache:
            price, timestamp = self.cache[ticker]
            if (datetime.now() - timestamp).total_seconds() < self.cache_ttl:
                return price
        return None

    def _set_cache(self, ticker: str, price: float):
        """Guarda precio en caché."""
        self.cache[ticker] = (price, datetime.now())

    # ---------- TASA MEP ----------
    def get_mep_rate(self) -> float:
        """
        Obtiene la cotización del dólar MEP (Bolsa) desde dolarapi.com.
        
        Returns:
            float: Tasa MEP. Si falla, retorna 1.0 como fallback.
        """
        try:
            url = "https://dolarapi.com/v1/dolares/bolsa"
            resp = self.session.get(url, timeout=8)
            if resp.status_code == 200:
                data = resp.json()
                mep = float(data.get("venta", 0))
                if mep > 0:
                    return mep
            # Fallback secundario
            url2 = "https://api.bluelytics.com.ar/v2/latest"
            resp2 = self.session.get(url2, timeout=5)
            if resp2.status_code == 200:
                data2 = resp2.json()
                mep2 = float(data2.get("blue", {}).get("value_sell", 0))
                if mep2 > 0:
                    return mep2
        except Exception as e:
            print(f"Error obteniendo MEP: {e}")
        return 1.0  # fallback seguro

    # ---------- BONOS ARGENTINOS (scraping PuenteNet) ----------
    def get_bond_price(self, ticker: str) -> Optional[float]:
        """
        Obtiene el precio de un bono argentino (AL30, GD30) en ARS mediante scraping.
        """
        try:
            bond_urls = {
                "AL30": "https://www.puentenet.com/cotizaciones/bonos/AL30",
                "GD30": "https://www.puentenet.com/cotizaciones/bonos/GD30"
            }
            url = bond_urls.get(ticker.upper())
            if not url:
                print(f"No hay URL mapeada para el bono {ticker}")
                return None

            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            resp = self.session.get(url, headers=headers, timeout=10)
            resp.raise_for_status()

            soup = BeautifulSoup(resp.text, 'html.parser')
            # Buscar el div que contiene el precio (puede cambiar)
            price_elem = soup.find('div', class_='price')
            if price_elem:
                price_text = price_elem.text.strip().replace('.', '').replace(',', '.')
                price = float(price_text)
                print(f"Precio obtenido para {ticker}: {price} ARS")
                return price
            else:
                print(f"No se encontró el elemento de precio para {ticker}")
                return None
        except Exception as e:
            print(f"Error obteniendo precio de bono {ticker}: {e}")
            return None

    # ---------- ACCIONES GLOBALES (yfinance) ----------
    def get_stock_price(self, ticker: str) -> Optional[float]:
        """Obtiene precio de acciones globales usando yfinance."""
        try:
            stock = yf.Ticker(ticker)
            price = stock.info.get('regularMarketPrice') or stock.info.get('currentPrice') or stock.info.get('previousClose')
            if price:
                print(f"Precio obtenido para {ticker}: {price} USD")
                return float(price)
            else:
                print(f"No se pudo obtener precio para {ticker} con yfinance")
                return None
        except Exception as e:
            print(f"Error obteniendo precio de acción {ticker}: {e}")
            return None

    # ---------- CRIPTOMONEDAS (CoinGecko) ----------
    def get_crypto_price(self, ticker: str) -> Optional[float]:
        """Obtiene precio de criptomoneda desde CoinGecko."""
        try:
            mapping = {
                "BTC": "bitcoin",
                "ETH": "ethereum",
                "USDT": "tether",
                "BNB": "binancecoin",
                "SOL": "solana",
                "ADA": "cardano",
                "DOGE": "dogecoin"
            }
            coin_id = mapping.get(ticker.upper())
            if not coin_id:
                print(f"No hay ID mapeado para la cripto {ticker}")
                return None

            url = f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
            resp = self.session.get(url, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            price = data.get(coin_id, {}).get("usd")
            if price:
                print(f"Precio obtenido para {ticker}: {price} USD")
                return float(price)
            else:
                print(f"No se encontró precio para {ticker} en CoinGecko")
                return None
        except Exception as e:
            print(f"Error obteniendo precio de cripto {ticker}: {e}")
            return None

    # ---------- PRECIO GENÉRICO SEGÚN TIPO ----------
    def get_price(self, ticker: str, asset_type: str) -> Optional[float]:
        """
        Obtiene el precio actual de un activo según su tipo.
        """
        cached = self._get_from_cache(ticker)
        if cached is not None:
            return cached

        price = None
        if asset_type == 'ar':
            price = self.get_bond_price(ticker)
        elif asset_type == 'global':
            price = self.get_stock_price(ticker)
        elif asset_type == 'crypto':
            price = self.get_crypto_price(ticker)
        
        if price is not None and price > 0:
            self._set_cache(ticker, price)
        return price

    def get_prices_batch(self, positions: List[Position]) -> Dict[str, float]:
        """
        Obtiene precios para una lista de posiciones.
        """
        prices = {}
        for pos in positions:
            ticker = pos.ticker
            asset_type = pos.asset_type
            price = self.get_price(ticker, asset_type)
            if price is not None:
                prices[ticker] = price
        return prices