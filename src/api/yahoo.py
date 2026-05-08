import requests
import logging

logger = logging.getLogger(__name__)

BASE_URL = "https://query1.finance.yahoo.com/v8/finance/chart"

def get_stock_price(ticker: str, is_argentine: bool = False) -> dict | None:
    """
    Obtiene el precio y variación diaria de una acción vía Yahoo Finance.
    
    Args:
        ticker: Símbolo del activo (ej: AAPL, YPF).
        is_argentine: Si es True, agrega el sufijo '.BA' automáticamente.
        
    Returns:
        Diccionario con 'price' (float) y 'change' (float en %) o None si falla.
    """
    # Si es argentino, Yahoo requiere el sufijo .BA
    symbol = f"{ticker}.BA" if is_argentine else ticker
    
    try:
        params = {
            "symbol": symbol,
            "interval": "1d",
            "range": "2d" # Necesitamos el cierre de ayer para calcular el cambio %
        }
        
        response = requests.get(BASE_URL, params=params, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        result = data.get("chart", {}).get("result", [])
        
        if not result:
            logger.warning(f"No se encontraron datos para {symbol} en Yahoo.")
            return None
            
        meta = result[0].get("meta", {})
        current_price = meta.get("regularMarketPrice")
        previous_close = meta.get("chartPreviousClose")
        
        if current_price and previous_close:
            change_pct = ((current_price - previous_close) / previous_close) * 100
            return {
                "price": float(current_price),
                "change": float(change_pct),
                "source": "Yahoo"
            }
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error consultando Yahoo para {symbol}: {e}")
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Error procesando respuesta Yahoo para {symbol}: {e}")
        
    return None