from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
import os
import base64
import json
from datetime import datetime, timezone
from pathlib import Path

KEYS_DIR = Path("keys")
PRIVATE_KEY_FILE = KEYS_DIR / "private.pem"
PUBLIC_KEY_FILE = KEYS_DIR / "public.pem"

def generate_and_save_keys():
    KEYS_DIR.mkdir(exist_ok=True)
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_key = private_key.public_key()

    with open(PRIVATE_KEY_FILE, "wb") as f:
        f.write(private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ))

    with open(PUBLIC_KEY_FILE, "wb") as f:
        f.write(public_key.public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        ))
    print("✅ Keys generated and saved in ./keys/")
    return private_key, public_key

def load_keys():
    if not PRIVATE_KEY_FILE.exists() or not PUBLIC_KEY_FILE.exists():
        return generate_and_save_keys()

    with open(PRIVATE_KEY_FILE, "rb") as f:
        private_key = serialization.load_pem_private_key(f.read(), password=None)

    with open(PUBLIC_KEY_FILE, "rb") as f:
        public_key = serialization.load_pem_public_key(f.read())

    return private_key, public_key

def encrypt_payment(public_key, sender: str, receiver: str, amount: float) -> dict:
    payload = {
        "sender": sender,
        "receiver": receiver,
        "amount": amount,
        "nonce": base64.b64encode(os.urandom(16)).decode(),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    plaintext = json.dumps(payload).encode()

    aes_key = AESGCM.generate_key(bit_length=256)
    aesgcm = AESGCM(aes_key)
    nonce = os.urandom(12)
    ciphertext = aesgcm.encrypt(nonce, plaintext, None)

    encrypted_key = public_key.encrypt(
        aes_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    return {
        "encrypted_key": base64.b64encode(encrypted_key).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "ciphertext": base64.b64encode(ciphertext).decode(),
        "packet_id": base64.b64encode(os.urandom(8)).decode()
    }

def decrypt_packet(private_key, packet: dict) -> dict:
    encrypted_key = base64.b64decode(packet["encrypted_key"])
    nonce = base64.b64decode(packet["nonce"])
    ciphertext = base64.b64decode(packet["ciphertext"])

    aes_key = private_key.decrypt(
        encrypted_key,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )
    )

    aesgcm = AESGCM(aes_key)
    plaintext = aesgcm.decrypt(nonce, ciphertext, None)
    return json.loads(plaintext.decode())