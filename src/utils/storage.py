import json
import os
from typing import List, Dict, Any

class LocalStorage:
    """
    Maneja el guardado y carga de datos en el sistema de archivos local.
    """

    def __init__(self, data_dir: str = "data"):
        """
        Inicializa el almacenamiento local.
        
        Args:
            data_dir: Directorio donde se guardarán los archivos JSON.
        """
        self.data_dir = data_dir
        self.positions_file = os.path.join(data_dir, "positions.json")
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        """Crea el directorio de datos si no existe."""
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def save_positions(self, positions: List[Dict[str, Any]]) -> bool:
        """
        Guarda la lista de posiciones en un archivo JSON.
        
        Args:
            positions: Lista de diccionarios con los datos de cada posición.
        
        Returns:
            True si se guardó correctamente, False en caso contrario.
        """
        try:
            with open(self.positions_file, 'w', encoding='utf-8') as f:
                json.dump(positions, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error al guardar posiciones: {e}")
            return False

    def load_positions(self) -> List[Dict[str, Any]]:
        """
        Carga las posiciones desde el archivo JSON.
        
        Returns:
            Lista de diccionarios con las posiciones. Si el archivo no existe o
            está corrupto, retorna una lista vacía.
        """
        if not os.path.exists(self.positions_file):
            return []

        try:
            with open(self.positions_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                else:
                    print("El archivo positions.json no contiene una lista.")
                    return []
        except json.JSONDecodeError as e:
            print(f"Error decodificando JSON: {e}")
            return []
        except Exception as e:
            print(f"Error inesperado al cargar posiciones: {e}")
            return []