"""Ed25519 signing and verification for shenas packages."""

import base64
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)
from cryptography.hazmat.primitives.serialization import (
    Encoding,
    NoEncryption,
    PrivateFormat,
    PublicFormat,
)


def generate_keypair(key_dir: Path) -> tuple[Path, Path]:
    """Generate an Ed25519 keypair and write to key_dir."""
    key_dir.mkdir(parents=True, exist_ok=True)
    private_key = Ed25519PrivateKey.generate()

    priv_path = key_dir / "shenas.key"
    pub_path = key_dir / "shenas.pub"

    priv_path.write_bytes(
        private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    )
    priv_path.chmod(0o600)

    pub_path.write_bytes(
        private_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    )

    return priv_path, pub_path


def load_private_key(path: Path) -> Ed25519PrivateKey:
    from cryptography.hazmat.primitives.serialization import load_pem_private_key

    return load_pem_private_key(path.read_bytes(), password=None)


def load_public_key(path: Path) -> Ed25519PublicKey:
    from cryptography.hazmat.primitives.serialization import load_pem_public_key

    key = load_pem_public_key(path.read_bytes())
    if not isinstance(key, Ed25519PublicKey):
        raise TypeError(f"Expected Ed25519 public key, got {type(key)}")
    return key


def sign_file(private_key: Ed25519PrivateKey, file_path: Path) -> str:
    """Sign a file and return the base64-encoded signature."""
    data = file_path.read_bytes()
    sig = private_key.sign(data)
    return base64.b64encode(sig).decode()


def write_signature(private_key: Ed25519PrivateKey, file_path: Path) -> Path:
    """Sign a file and write the .sig file next to it."""
    sig_b64 = sign_file(private_key, file_path)
    sig_path = file_path.with_suffix(file_path.suffix + ".sig")
    sig_path.write_text(sig_b64)
    return sig_path


def verify_file(public_key: Ed25519PublicKey, file_path: Path, sig_b64: str) -> bool:
    """Verify a file against a base64-encoded signature."""
    data = file_path.read_bytes()
    sig = base64.b64decode(sig_b64)
    try:
        public_key.verify(sig, data)
        return True
    except Exception:
        return False


def verify_bytes(public_key: Ed25519PublicKey, data: bytes, sig_b64: str) -> bool:
    """Verify raw bytes against a base64-encoded signature."""
    sig = base64.b64decode(sig_b64)
    try:
        public_key.verify(sig, data)
        return True
    except Exception:
        return False
