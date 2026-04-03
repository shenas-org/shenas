"""Tests for client authentication."""

from pathlib import Path

from fl_server.auth import ClientRegistry


class TestClientRegistry:
    def test_register_and_verify(self, tmp_path: Path) -> None:
        registry = ClientRegistry(token_file=tmp_path / "clients.json")
        token = registry.register("alice")

        assert registry.verify(token) == "alice"

    def test_invalid_token(self, tmp_path: Path) -> None:
        registry = ClientRegistry(token_file=tmp_path / "clients.json")
        registry.register("alice")

        assert registry.verify("bad-token") is None

    def test_revoke(self, tmp_path: Path) -> None:
        registry = ClientRegistry(token_file=tmp_path / "clients.json")
        token = registry.register("alice")

        assert registry.revoke("alice") is True
        assert registry.verify(token) is None

    def test_revoke_nonexistent(self, tmp_path: Path) -> None:
        registry = ClientRegistry(token_file=tmp_path / "clients.json")
        assert registry.revoke("nobody") is False

    def test_list_clients(self, tmp_path: Path) -> None:
        registry = ClientRegistry(token_file=tmp_path / "clients.json")
        registry.register("alice")
        registry.register("bob")

        assert sorted(registry.list_clients()) == ["alice", "bob"]

    def test_persistence(self, tmp_path: Path) -> None:
        token_file = tmp_path / "clients.json"
        registry = ClientRegistry(token_file=token_file)
        token = registry.register("alice")

        # Load from disk
        registry2 = ClientRegistry(token_file=token_file)
        assert registry2.verify(token) == "alice"
