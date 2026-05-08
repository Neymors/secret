import requests
import logging

logger = logging.getLogger(__name__)

BASE_URL = "https://dolarapi.com/v1/dolares/bolsa"

def get_mep_rate() -> float | None:
    """
    Obtiene la tasa de venta del Dólar MEP (Bolsa).
    
    Returns:
        Float con la tasa de venta o None si falla.
    """
    try:
        response = requests.get(BASE_URL, timeout=5)
        response.raise_for_status()
        
        data = response.json()
        
        # La API devuelve un objeto con varios campos, nos interesa 'venta'
        if "venta" in data:
            return float(data["venta"])
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error consultando DolarApi (MEP): {e}")
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Error procesando respuesta DolarApi: {e}")
        
    # Fallback a un valor por defecto si falla la API (opcional)
    return 1200.0 