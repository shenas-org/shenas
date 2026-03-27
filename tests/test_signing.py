from pathlib import Path

import pytest

from registry.signing import (
    generate_keypair,
    load_private_key,
    load_public_key,
    sign_file,
    verify_bytes,
    verify_file,
    write_signature,
)


@pytest.fixture()
def keypair(tmp_path: Path) -> tuple[Path, Path]:
    return generate_keypair(tmp_path / "keys")


@pytest.fixture()
def sample_file(tmp_path: Path) -> Path:
    f = tmp_path / "test.whl"
    f.write_bytes(b"fake wheel content for signing test")
    return f


class TestKeypair:
    def test_generates_files(self, keypair: tuple[Path, Path]) -> None:
        priv, pub = keypair
        assert priv.exists()
        assert pub.exists()

    def test_private_key_permissions(self, keypair: tuple[Path, Path]) -> None:
        priv, _ = keypair
        assert oct(priv.stat().st_mode)[-3:] == "600"

    def test_pem_format(self, keypair: tuple[Path, Path]) -> None:
        priv, pub = keypair
        assert b"PRIVATE KEY" in priv.read_bytes()
        assert b"PUBLIC KEY" in pub.read_bytes()

    def test_load_private_key(self, keypair: tuple[Path, Path]) -> None:
        priv, _ = keypair
        key = load_private_key(priv)
        assert key is not None

    def test_load_public_key(self, keypair: tuple[Path, Path]) -> None:
        _, pub = keypair
        key = load_public_key(pub)
        assert key is not None

    def test_idempotent_keygen(self, tmp_path: Path) -> None:
        dir1 = tmp_path / "keys"
        generate_keypair(dir1)
        generate_keypair(dir1)
        assert (dir1 / "shenas.key").exists()


class TestSignAndVerify:
    def test_sign_file_returns_base64(self, keypair: tuple[Path, Path], sample_file: Path) -> None:
        priv, _ = keypair
        key = load_private_key(priv)
        sig = sign_file(key, sample_file)
        assert isinstance(sig, str)
        assert len(sig) > 0

    def test_write_signature_creates_sig_file(self, keypair: tuple[Path, Path], sample_file: Path) -> None:
        priv, _ = keypair
        key = load_private_key(priv)
        sig_path = write_signature(key, sample_file)
        assert sig_path.exists()
        assert sig_path.name == "test.whl.sig"

    def test_verify_file_valid(self, keypair: tuple[Path, Path], sample_file: Path) -> None:
        priv, pub = keypair
        priv_key = load_private_key(priv)
        pub_key = load_public_key(pub)
        sig = sign_file(priv_key, sample_file)
        assert verify_file(pub_key, sample_file, sig) is True

    def test_verify_file_tampered(self, keypair: tuple[Path, Path], sample_file: Path) -> None:
        priv, pub = keypair
        priv_key = load_private_key(priv)
        pub_key = load_public_key(pub)
        sig = sign_file(priv_key, sample_file)
        sample_file.write_bytes(b"tampered content")
        assert verify_file(pub_key, sample_file, sig) is False

    def test_verify_file_wrong_sig(self, keypair: tuple[Path, Path], sample_file: Path) -> None:
        _, pub = keypair
        pub_key = load_public_key(pub)
        assert verify_file(pub_key, sample_file, "badsig==") is False

    def test_verify_bytes_valid(self, keypair: tuple[Path, Path]) -> None:
        priv, pub = keypair
        priv_key = load_private_key(priv)
        pub_key = load_public_key(pub)
        import base64

        data = b"test data"
        sig = base64.b64encode(priv_key.sign(data)).decode()
        assert verify_bytes(pub_key, data, sig) is True

    def test_verify_bytes_invalid(self, keypair: tuple[Path, Path]) -> None:
        _, pub = keypair
        pub_key = load_public_key(pub)
        assert verify_bytes(pub_key, b"data", "badsig==") is False

    def test_different_keypair_fails(self, tmp_path: Path, sample_file: Path) -> None:
        _, pub1 = generate_keypair(tmp_path / "keys1")
        priv2, _ = generate_keypair(tmp_path / "keys2")
        sig = sign_file(load_private_key(priv2), sample_file)
        assert verify_file(load_public_key(pub1), sample_file, sig) is False
