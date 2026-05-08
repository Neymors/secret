"""
Amygdalé API Clients Package
Centraliza los clientes para obtener precios de diferentes fuentes.
"""

# Importamos las funciones principales de cada módulo para exponerlas aquí
# Esto permite hacer: from src.api import get_bond_price, get_stock_price, etc.

try:
    from .byma import get_bond_price
    from .yahoo import get_stock_price
    from .coingecko import get_crypto_price
    from .dolarapi import get_mep_rate
except ImportError:
    # Si algún módulo falla al importar (ej. dependencias faltantes),
    # definimos placeholders para evitar que toda la app se rompa al inicio.
    def get_bond_price(*args, **kwargs): return None
    def get_stock_price(*args, **kwargs): return None
    def get_crypto_price(*args, **kwargs): return None
    def get_mep_rate(*args, **kwargs): return None

__all__ = [
    'get_bond_price',
    'get_stock_price',
    'get_crypto_price',
    'get_mep_rate'
]