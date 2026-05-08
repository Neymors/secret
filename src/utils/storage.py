"""
Amygdalé — Utility: Local Storage
Maneja la persistencia de datos en archivos JSON locales.
Filosofía: Local-First (sin base de datos externa).
"""

import json
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class LocalStorage:
    """
    Gestor de almacenamiento local basado en archivos JSON.
    Crea automáticamente la carpeta 'data/' si no existe.
    """
    
    def __init__(self, base_path: str = "data"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        # Rutas de archivos
        self.positions_file = self.base_path / "positions.json"
        self.history_file = self.base_path / "history.json"

    def save_positions(self, positions_data: List[Dict[str, Any]]) -> bool:
        """Guarda la lista de posiciones en JSON."""
        try:
            with open(self.positions_file, 'w', encoding='utf-8') as f:
                json.dump(positions_data, f, indent=4, ensure_ascii=False)
            logger.info(f"💾 Posiciones guardadas ({len(positions_data)} activos)")
            return True
        except Exception as e:
            logger.error(f"❌ Error guardando posiciones: {e}")
            return False

    def load_positions(self) -> List[Dict[str, Any]]:
        """Carga las posiciones desde JSON. Devuelve lista vacía si no existe."""
        if not self.positions_file.exists():
            return []
        
        try:
            with open(self.positions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                logger.warning("Formato de posiciones inválido, reiniciando.")
                return []
        except Exception as e:
            logger.error(f"❌ Error cargando posiciones: {e}")
            return []

    def save_history(self, history_data: List[Dict[str, Any]]) -> bool:
        """Guarda el histórico diario en JSON."""
        try:
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"❌ Error guardando histórico: {e}")
            return False

    def load_history(self) -> List[Dict[str, Any]]:
        """Carga el histórico desde JSON. Devuelve lista vacía si no existe."""
        if not self.history_file.exists():
            return []
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return []
        except Exception as e:
            logger.error(f"❌ Error cargando histórico: {e}")
            return []

    def export_backup(self, positions: List[Dict], history: List[Dict]) -> Optional[str]:
        """Genera un string JSON completo para backup manual (Export)."""
        try:
            backup = {
                "version": "1.0",
                "positions": positions,
                "history": history
            }
            return json.dumps(backup, indent=4, ensure_ascii=False)
        except Exception as e:
            logger.error(f"❌ Error generando backup: {e}")
            return None

    def import_backup(self, json_content: str) -> bool:
        """Restaura posiciones e histórico desde un string JSON (Import)."""
        try:
            data = json.loads(json_content)
            
            if "positions" in data and isinstance(data["positions"], list):
                self.save_positions(data["positions"])
            
            if "history" in data and isinstance(data["history"], list):
                self.save_history(data["history"])
                
            logger.info("✅ Backup restaurado correctamente")
            return True
        except Exception as e:
            logger.error(f"❌ Error importando backup: {e}")
            return False