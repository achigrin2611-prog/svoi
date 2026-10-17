from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
import base64

# Генерируем ключи
private_key = ec.generate_private_key(ec.SECP256R1())
public_key = private_key.public_key()

# Приватный ключ (Base64 URL-safe)
private_pem = private_key.private_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PrivateFormat.PKCS8,
    encryption_algorithm=serialization.NoEncryption()
)
private_b64 = base64.urlsafe_b64encode(private_pem).decode('utf-8').rstrip('=')

# Публичный ключ (Base64 URL-safe)
public_pem = public_key.public_bytes(
    encoding=serialization.Encoding.X962,
    format=serialization.PublicFormat.UncompressedPoint
)
public_b64 = base64.urlsafe_b64encode(public_pem).decode('utf-8').rstrip('=')

print("PUBLIC_KEY:", public_b64)
print("PRIVATE_KEY:", private_b64)