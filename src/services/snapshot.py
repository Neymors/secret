import json
import logging
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class SnapshotService:
    """
    Servicio para gestionar el histórico diario del portfolio.
    Guarda snapshots en JSON localmente para alimentar el gráfico de líneas.
    """
    
    def __init__(self, storage_path: str = "data/history.json", max_days: int = 365):
        self.storage_path = Path(storage_path)
        self.max_days = max_days
        
        # Asegurar que el directorio existe
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Cargar histórico existente o iniciar vacío
        self.history = self._load_history()

    def _load_history(self) -> List[Dict[str, Any]]:
        """Carga el histórico desde el archivo JSON."""
        if not self.storage_path.exists():
            return []
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                # Validar estructura básica
                if isinstance(data, list):
                    return data
                logger.warning("Formato de histórico inválido, reiniciando.")
                return []
        except Exception as e:
            logger.error(f"Error cargando histórico: {e}")
            return []

    def _save_history(self):
        """Guarda el histórico actual en el archivo JSON."""
        try:
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(self.history, f, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"Error guardando histórico: {e}")

    def save_snapshot(self, total_usd: float, mep_rate: Optional[float] = None) -> bool:
        """
        Guarda un snapshot del día si no existe ya uno para hoy.
        
        Args:
            total_usd: Valor total del portfolio en USD.
            mep_rate: Tasa MEP actual (usada para calcular el benchmark).
            
        Returns:
            True si se guardó un nuevo snapshot, False si ya existía o hubo error.
        """
        today_str = date.today().isoformat() # YYYY-MM-DD
        
        # Verificar si ya hay snapshot para hoy
        if self.history and self.history[-1].get('date') == today_str:
            logger.info(f"Snapshot para {today_str} ya existe. Omitiendo.")
            return False
        
        if total_usd <= 0:
            logger.warning("Valor total <= 0, no se guarda snapshot.")
            return False

        # Calcular Benchmark (Proxy: Variación del MEP vs Default 1200)
        # Si no hay MEP, asumimos 0% de cambio para el benchmark
        default_mep = 1200.0
        current_mep = mep_rate if mep_rate else default_mep
        
        bench_change_pct = ((current_mep - default_mep) / default_mep) * 100 if default_mep != 0 else 0
        
        # El benchmark es el valor del portfolio ajustado por la variación del MEP
        # Esto simula cómo habría performado el dinero si hubiera estado en efectivo/MEP
        benchmark_value = total_usd * (1 + bench_change_pct / 100)

        snapshot = {
            "date": today_str,
            "totalUSD": round(total_usd, 2),
            "benchmark": round(benchmark_value, 2),
            "mepRate": round(current_mep, 2)
        }

        self.history.append(snapshot)
        
        # Mantener solo los últimos N días
        if len(self.history) > self.max_days:
            self.history = self.history[-self.max_days:]
            
        self._save_history()
        logger.info(f"📸 Snapshot guardado: {today_str} | Total: ${total_usd:,.2f}")
        return True

    def get_history(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Obtiene el histórico de los últimos N días.
        
        Args:
            days: Cantidad de días a recuperar (ej: 30 para 1M, 365 para 1Y).
            
        Returns:
            Lista de diccionarios con los snapshots.
        """
        if not self.history:
            return []
        
        # Filtrar por fecha si es necesario, aunque al estar ordenados cronológicamente
        # podemos tomar los últimos N directamente.
        return self.history[-days:] if len(self.history) >= days else self.history

    def clear_history(self):
        """Borra todo el histórico (útil para testing o reseteo)."""
        self.history = []
        self._save_history()
        logger.info("🗑️ Histórico borrado.")