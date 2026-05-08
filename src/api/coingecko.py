import requests
import logging

logger = logging.getLogger(__name__)

BASE_URL = "https://api.coingecko.com/api/v3/simple/price"

# Mapeo básico de Tickers comunes a IDs de CoinGecko
CRYPTO_MAP = {
    "BTC": "bitcoin",
    "ETH": "ethereum",
    "SOL": "solana",
    "USDT": "tether",
    "BNB": "binancecoin",
    "ADA": "cardano",
    "DOT": "polkadot",
    "MATIC": "matic-network",
    "XRP": "ripple"
}

def get_crypto_price(ticker: str) -> dict | None:
    """
    Obtiene el precio en USD y variación 24h de una criptomoneda.
    
    Args:
        ticker: Símbolo de la cripto (ej: BTC, ETH).
        
    Returns:
        Diccionario con 'price' (float) y 'change' (float en %) o None si falla.
    """
    coin_id = CRYPTO_MAP.get(ticker.upper())
    
    if not coin_id:
        # Si no está en el mapa, intentamos usar el ticker en minúsculas como ID
        # Nota: Esto puede fallar si el ID no coincide exactamente con el ticker
        coin_id = ticker.lower()
        logger.info(f"Ticker {ticker} no mapeado, intentando ID directo: {coin_id}")

    try:
        params = {
            "ids": coin_id,
            "vs_currencies": "usd",
            "include_24hr_change": "true"
        }
        
        response = requests.get(BASE_URL, params=params, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        if coin_id in data:
            coin_data = data[coin_id]
            price = coin_data.get("usd")
            change = coin_data.get("usd_24h_change")
            
            if price is not None:
                return {
                    "price": float(price),
                    "change": float(change) if change is not None else 0.0,
                    "source": "CoinGecko"
                }
                
    except requests.exceptions.RequestException as e:
        logger.error(f"Error consultando CoinGecko para {ticker}: {e}")
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Error procesando respuesta CoinGecko para {ticker}: {e}")
        
    return None