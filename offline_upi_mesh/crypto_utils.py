"""
Compact hybrid encryption for offline payment packets.

Why this changed: the old format (RSA-2048 wrapped key + JSON + base64 twice)
produced ~880 characters, which makes a very dense QR code that webcams
cannot read. This version uses X25519 (ECIES-style) so the whole packet is
only ~140 bytes -> a small, easily scannable QR.

Wire format:  "UM1:" + base64url( 0x01 | ephemeral_pub(32) | nonce(12) | AES-GCM ciphertext+tag )
"""
import base64
import json
import os
import re
import time
from pathlib import Path

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric.x25519 import (
    X25519PrivateKey,
    X25519PublicKey,
)
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

PREFIX = "UM1:"
VERSION = b"\x01"
KEYS_DIR = Path("keys")
PRIVATE_KEY_FILE = KEYS_DIR / "x25519_private.pem"
PUBLIC_KEY_FILE = KEYS_DIR / "x25519_public.pem"

PACKET_RE = re.compile(r"UM1:[A-Za-z0-9_\-]+")


def generate_and_save_keys():
    KEYS_DIR.mkdir(exist_ok=True)
    private_key = X25519PrivateKey.generate()
    PRIVATE_KEY_FILE.write_bytes(private_key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))
    PUBLIC_KEY_FILE.write_bytes(private_key.public_key().public_bytes(
        serialization.Encoding.PEM,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    ))
    print("Keys generated and saved in ./keys/")
    return private_key, private_key.public_key()


def load_keys():
    if not PRIVATE_KEY_FILE.exists() or not PUBLIC_KEY_FILE.exists():
        return generate_and_save_keys()
    private_key = serialization.load_pem_private_key(PRIVATE_KEY_FILE.read_bytes(), password=None)
    public_key = serialization.load_pem_public_key(PUBLIC_KEY_FILE.read_bytes())
    return private_key, public_key


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _derive_key(shared_secret: bytes, eph_pub: bytes) -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(), length=32, salt=eph_pub, info=b"upi-mesh-v1"
    ).derive(shared_secret)


def encrypt_payment(public_key, sender: str, receiver: str, amount: float) -> str:
    """Returns the packet as a compact string: 'UM1:<base64url>'."""
    payload = {
        "s": sender,
        "r": receiver,
        "a": amount,
        "t": int(time.time()),
        "n": os.urandom(6).hex(),   # makes every packet unique
    }
    plaintext = json.dumps(payload, separators=(",", ":")).encode()

    eph_priv = X25519PrivateKey.generate()
    eph_pub = eph_priv.public_key().public_bytes(
        serialization.Encoding.Raw, serialization.PublicFormat.Raw
    )
    key = _derive_key(eph_priv.exchange(public_key), eph_pub)
    nonce = os.urandom(12)
    ciphertext = AESGCM(key).encrypt(nonce, plaintext, eph_pub)  # eph_pub bound as AAD
    return PREFIX + _b64e(VERSION + eph_pub + nonce + ciphertext)


def extract_packet(text: str) -> str:
    """Pull a packet string out of whatever was scanned/pasted (JSON-wrapped,
    quoted, with stray whitespace / non-breaking spaces, etc.)."""
    m = PACKET_RE.search(text.replace("\u00a0", " "))
    if not m:
        raise ValueError("No UPI-Mesh packet found (expected text starting with 'UM1:')")
    return m.group(0)


def decrypt_packet(private_key, packet: str) -> dict:
    raw = _b64d(extract_packet(packet)[len(PREFIX):])
    if len(raw) < 1 + 32 + 12 + 16 or raw[:1] != VERSION:
        raise ValueError("Malformed packet")
    eph_pub, nonce, ciphertext = raw[1:33], raw[33:45], raw[45:]
    shared = private_key.exchange(X25519PublicKey.from_public_bytes(eph_pub))
    key = _derive_key(shared, eph_pub)
    plaintext = AESGCM(key).decrypt(nonce, ciphertext, eph_pub)
    p = json.loads(plaintext.decode())
    return {"sender": p["s"], "receiver": p["r"], "amount": float(p["a"]),
            "timestamp": p["t"]}
