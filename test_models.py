from src.crypto.encryptor import Encryptor

# 1. Iniciar encryptor
crypto = Encryptor(salt_file_path="data/test_salt")

# 2. Datos de prueba
my_portfolio = {
    "positions": [
        {"ticker": "AL30", "qty": 10, "ppc": 5000},
        {"ticker": "BTC", "qty": 0.01, "ppc": 60000}
    ],
    "secret_note": "Este dato está protegido."
}

password = "mi_clave_secreta_123"

# 3. Cifrar
print("🔒 Cifrando...")
encrypted_str = crypto.encrypt_data(my_portfolio, password)
print(f"Longitud cifrado: {len(encrypted_str)} chars")
print(f"Muestra: {encrypted_str[:50]}...")

# 4. Descifrar
print("\n🔓 Descifrando...")
try:
    decrypted_data = crypto.decrypt_data(encrypted_str, password)
    print(f"Ticker recuperado: {decrypted_data['positions'][0]['ticker']}")
    print(f"Nota secreta: {decrypted_data['secret_note']}")
    print("✅ Éxito: Los datos coinciden.")
except ValueError:
    print("❌ Error: Contraseña incorrecta.")

# 5. Probar contraseña incorrecta
print("\n🕵️ Probando contraseña incorrecta...")
try:
    crypto.decrypt_data(encrypted_str, "clave_incorrecta")
except ValueError:
    print("✅ Correcto: Se rechazó la contraseña incorrecta.")