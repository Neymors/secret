import requests
import logging

# Configuración de logging
logger = logging.getLogger(__name__)

BASE_URL = "https://open.bymadata.com.ar/van-api/robo/prices"

# Mapeo de Tickers comunes a Símbolos BYMA
BOND_MAP = {
    "AL30": "AL30",
    "GD30": "GD30",
    "AL35": "AL35",
    "GD35": "GD35",
    "AE38": "AE38",
    "GD38": "GD38",
    "TX2U": "TX2U",
    "T2X5": "T2X5",
    "AO27": "AO27", # Bonar 2027
    "AO30": "AO30", # Bonar 2030
}

def get_bond_price(ticker: str) -> dict | None:
    """
    Obtiene el precio y variación diaria de un bono argentino vía BYMA.
    
    Args:
        ticker: El símbolo del bono (ej: AL30, GD30).
        
    Returns:
        Diccionario con 'price' (float) y 'change' (float en %) o None si falla.
    """
    symbol = BOND_MAP.get(ticker.upper())
    
    if not symbol:
        logger.warning(f"Ticker {ticker} no mapeado en BYMA.")
        return None

    try:
        params = {"symbol": symbol}
        response = requests.get(BASE_URL, params=params, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        # La API devuelve una lista, buscamos el símbolo exacto
        if isinstance(data, list):
            quote = next((item for item in data if item["symbol"] == symbol), None)
        else:
            quote = data
            
        if quote and "last" in quote:
            return {
                "price": float(quote["last"]),
                "change": float(quote.get("varPct", 0)), # Variación porcentual
                "source": "BYMA"
            }
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error consultando BYMA para {ticker}: {e}")
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Error procesando respuesta BYMA para {ticker}: {e}")
        
    return None