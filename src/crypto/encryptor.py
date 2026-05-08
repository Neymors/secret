import os
import json
import base64
import logging
from typing import Any, Optional

# Librería estándar de criptografía en Python
try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.backends import default_backend
except ImportError:
    raise ImportError("Please install 'cryptography' package: pip install cryptography")

logger = logging.getLogger(__name__)

class Encryptor:
    """
    Gestor de cifrado AES-GCM con derivación de clave PBKDF2.
    Equivalente Python de la Web Crypto API usada en la versión JS.
    """
    
    def __init__(self, salt_file_path: str = "data/.salt"):
        self.salt_file = salt_file_path
        self.salt = self._load_or_create_salt()
        # Iteraciones altas para resistir fuerza bruta (similar a 200k en JS)
        self.iterations = 200_000 

    def _load_or_create_salt(self) -> bytes:
        """Carga un salt persistente o crea uno nuevo si no existe."""
        if os.path.exists(self.salt_file):
            with open(self.salt_file, 'rb') as f:
                return f.read()
        
        # Crear nuevo salt de 16 bytes
        new_salt = os.urandom(16)
        os.makedirs(os.path.dirname(self.salt_file), exist_ok=True)
        with open(self.salt_file, 'wb') as f:
            f.write(new_salt)
        
        logger.info("🔑 Nuevo salt generado y guardado.")
        return new_salt

    def _derive_key(self, passphrase: str) -> bytes:
        """
        Deriva una clave de 256 bits desde la passphrase usando PBKDF2-HMAC-SHA256.
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32, # 256 bits
            salt=self.salt,
            iterations=self.iterations,
            backend=default_backend()
        )
        return kdf.derive(passphrase.encode('utf-8'))

    def encrypt_data(self, data: Any, passphrase: str) -> str:
        """
        Cifra un objeto Python (dict/list) y devuelve un string Base64.
        Formato: IV (12 bytes) + Ciphertext + Tag (16 bytes implícito en GCM)
        """
        try:
            key = self._derive_key(passphrase)
            aesgcm = AESGCM(key)
            
            # IV aleatorio de 12 bytes (estándar para GCM)
            iv = os.urandom(12)
            
            # Serializar datos a JSON bytes
            plaintext = json.dumps(data, ensure_ascii=False).encode('utf-8')
            
            # Cifrar
            ciphertext = aesgcm.encrypt(iv, plaintext, None)
            
            # Empaquetar: IV + Ciphertext
            packed = iv + ciphertext
            
            # Codificar a Base64 para almacenamiento fácil en JSON
            return base64.b64encode(packed).decode('utf-8')
            
        except Exception as e:
            logger.error(f"❌ Error al cifrar datos: {e}")
            raise

    def decrypt_data(self, encrypted_b64: str, passphrase: str) -> Any:
        """
        Descifra un string Base64 y devuelve el objeto Python original.
        """
        try:
            key = self._derive_key(passphrase)
            aesgcm = AESGCM(key)
            
            # Decodificar Base64
            packed = base64.b64decode(encrypted_b64)
            
            # Extraer IV (primeros 12 bytes) y Ciphertext (resto)
            iv = packed[:12]
            ciphertext = packed[12:]
            
            # Descifrar
            plaintext = aesgcm.decrypt(iv, ciphertext, None)
            
            # Deserializar JSON
            return json.loads(plaintext.decode('utf-8'))
            
        except Exception as e:
            # Si falla, suele ser contraseña incorrecta o datos corruptos
            logger.warning(f"⚠️ Fallo al descifrar: Contraseña incorrecta o datos dañados.")
            raise ValueError("Invalid passphrase or corrupted data")

    def is_encrypted(self, file_path: str) -> bool:
        """Verifica si un archivo JSON parece estar cifrado (empieza con '{' o '[' vs string largo)."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                first_char = f.read(1)
                # Si empieza con '{' o '[', es JSON plano. Si es otro char, probablemente Base64.
                return first_char not in ['{', '[']
        except FileNotFoundError:
            return False