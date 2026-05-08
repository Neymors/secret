import time
from typing import Any, Optional

class Cache:
    """
    Caché simple en memoria con TTL (Time To Live).
    Ideal para evitar llamadas repetidas a APIs externas durante la misma sesión.
    """
    
    def __init__(self, ttl_seconds: int = 300):
        self.ttl = ttl_seconds
        self._cache = {}

    def set(self, key: str, value: Any):
        """Guarda un valor con la marca de tiempo actual."""
        self._cache[key] = {
            'value': value,
            'timestamp': time.time()
        }

    def get(self, key: str) -> Optional[Any]:
        """
        Recupera un valor si existe y no ha expirado.
        Devuelve None si no existe o expiró.
        """
        if key not in self._cache:
            return None
        
        entry = self._cache[key]
        now = time.time()
        
        # Si expiró, borrarlo y devolver None
        if now - entry['timestamp'] > self.ttl:
            del self._cache[key]
            return None
            
        return entry['value']

    def clear(self):
        """Limpia toda la caché."""
        self._cache.clear()