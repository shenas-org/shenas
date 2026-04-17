"""Integration tests for app.llm -- backends, cache, model store."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

import pytest

if TYPE_CHECKING:
    import duckdb

from app.llm.backends import Backend, LlamaCppBackend, ShenasProxyBackend
from app.llm.cache import LlmCache
from app.llm.models import DEFAULT_MODEL, Model, ModelStore, _AbsoluteModel

# -- Model / ModelStore ---------------------------------------------------


class TestModel:
    def test_default_model_has_url(self) -> None:
        assert DEFAULT_MODEL.url is not None
        assert DEFAULT_MODEL.filename.endswith(".gguf")

    def test_path_is_under_store_dir(self) -> None:
        m = Model(filename="test.gguf")
        assert m.path == ModelStore.dir() / "test.gguf"

    def test_exists_false_for_missing(self) -> None:
        m = Model(filename="nonexistent.gguf")
        assert m.exists is False

    def test_size_bytes_zero_for_missing(self) -> None:
        m = Model(filename="nonexistent.gguf")
        assert m.size_bytes == 0


class TestModelStore:
    def test_dir_returns_data_models_in_dev(self) -> None:
        assert ModelStore.dir() == Path("data") / "models"

    def test_dir_returns_home_in_bundle(self) -> None:
        with patch("app.llm.models.sys") as mock_sys:
            mock_sys._MEIPASS = "/tmp/bundle"
            assert ModelStore.dir() == Path.home() / ".shenas" / "models"

    def test_list_models_empty_when_no_dir(self, tmp_path: Path) -> None:
        with patch.object(ModelStore, "dir", return_value=tmp_path / "missing"):
            assert ModelStore.list_models() == []

    def test_list_models_finds_gguf_files(self, tmp_path: Path) -> None:
        (tmp_path / "a.gguf").touch()
        (tmp_path / "b.gguf").touch()
        (tmp_path / "c.txt").touch()
        with patch.object(ModelStore, "dir", return_value=tmp_path):
            models = ModelStore.list_models()
        assert len(models) == 2
        assert {m.filename for m in models} == {"a.gguf", "b.gguf"}

    def test_resolve_none_returns_default(self) -> None:
        assert ModelStore.resolve(None) is DEFAULT_MODEL

    def test_resolve_filename(self) -> None:
        m = ModelStore.resolve("custom.gguf")
        assert m.filename == "custom.gguf"
        assert m.path == ModelStore.dir() / "custom.gguf"

    def test_resolve_absolute_path(self) -> None:
        m = ModelStore.resolve("/opt/models/big.gguf")
        assert isinstance(m, _AbsoluteModel)
        assert m.path == Path("/opt/models/big.gguf")
        assert m.filename == "big.gguf"

    def test_remove_deletes_file(self, tmp_path: Path) -> None:
        f = tmp_path / "delete-me.gguf"
        f.touch()
        with patch.object(ModelStore, "dir", return_value=tmp_path):
            ModelStore.remove("delete-me.gguf")
        assert not f.exists()

    def test_download_no_url_raises(self) -> None:
        m = Model(filename="no-url.gguf")
        with pytest.raises(RuntimeError, match="no URL configured"):
            ModelStore.download(m)


# -- LlmCache ------------------------------------------------------------


class TestLlmCache:
    def test_creates_table(self, db_con: duckdb.DuckDBPyConnection) -> None:
        cache = LlmCache()
        tables = db_con.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'shenas_system'"
        ).fetchall()
        assert ("llm_cache",) in tables
        _ = cache

    def test_put_and_get(self, db_con: duckdb.DuckDBPyConnection) -> None:
        cache = LlmCache()
        cache.put(text="hello", prompt_hash="p1", model="test-model", result="greeting")
        assert cache.get(text="hello", prompt_hash="p1", model="test-model") == "greeting"

    def test_get_miss_returns_none(self, db_con: duckdb.DuckDBPyConnection) -> None:
        cache = LlmCache()
        assert cache.get(text="missing", prompt_hash="p1", model="m") is None

    def test_model_isolation(self, db_con: duckdb.DuckDBPyConnection) -> None:
        """Different models get different cache entries for the same text."""
        cache = LlmCache()
        cache.put(text="hello", prompt_hash="p1", model="model-a", result="result-a")
        cache.put(text="hello", prompt_hash="p1", model="model-b", result="result-b")
        assert cache.get(text="hello", prompt_hash="p1", model="model-a") == "result-a"
        assert cache.get(text="hello", prompt_hash="p1", model="model-b") == "result-b"

    def test_prompt_isolation(self, db_con: duckdb.DuckDBPyConnection) -> None:
        """Different prompts get different cache entries for the same text."""
        cache = LlmCache()
        cache.put(text="hello", prompt_hash="prompt-1", model="m", result="r1")
        cache.put(text="hello", prompt_hash="prompt-2", model="m", result="r2")
        assert cache.get(text="hello", prompt_hash="prompt-1", model="m") == "r1"
        assert cache.get(text="hello", prompt_hash="prompt-2", model="m") == "r2"

    def test_put_overwrites(self, db_con: duckdb.DuckDBPyConnection) -> None:
        cache = LlmCache()
        cache.put(text="hello", prompt_hash="p1", model="m", result="old")
        cache.put(text="hello", prompt_hash="p1", model="m", result="new")
        assert cache.get(text="hello", prompt_hash="p1", model="m") == "new"

    def test_hash16_deterministic(self) -> None:
        assert LlmCache.hash16("test") == LlmCache.hash16("test")
        assert LlmCache.hash16("a") != LlmCache.hash16("b")
        assert len(LlmCache.hash16("test")) == 16

    def test_join_sql(self, db_con: duckdb.DuckDBPyConnection) -> None:
        cache = LlmCache()
        db_con.execute("CREATE SCHEMA IF NOT EXISTS test_schema")
        db_con.execute("CREATE TABLE IF NOT EXISTS test_schema.src (name VARCHAR)")
        db_con.execute("DELETE FROM test_schema.src")
        db_con.execute("INSERT INTO test_schema.src VALUES ('hello'), ('world')")
        cache.put(text="hello", prompt_hash="p1", model="m", result="greeting")

        sql, params = cache.join_sql(
            source="test_schema.src",
            text_col="name",
            prompt_hash="p1",
            model="m",
            output_col="category",
        )
        rows = db_con.execute(sql, params).fetchall()
        assert len(rows) == 2
        results = {r[0]: r[1] for r in rows}
        assert results["hello"] == "greeting"
        assert results["world"] is None


# -- Backend factory ------------------------------------------------------


class TestBackendFactory:
    def test_unknown_backend_raises(self) -> None:
        with pytest.raises(RuntimeError, match="unknown llm backend"):
            Backend.from_config({"backend": "invalid"})

    def test_local_without_model_raises(self) -> None:
        with (
            patch.object(ModelStore, "resolve", return_value=Model(filename="missing.gguf")),
            pytest.raises(RuntimeError, match=r"Model not found|llama-cpp-python"),
        ):
            Backend.from_config({"backend": "local"})

    def test_proxy_without_token_raises(self) -> None:
        with (
            patch("app.local_users.LocalUser.get_remote_token", return_value=None),
            pytest.raises(RuntimeError, match=r"shenas\.net account"),
        ):
            Backend.from_config({"backend": "proxy"})

    def test_proxy_with_token_creates_backend(self) -> None:
        with patch("app.local_users.LocalUser.get_remote_token", return_value="tok-123"):
            backend = Backend.from_config({"backend": "proxy"})
        assert isinstance(backend, ShenasProxyBackend)
        assert "shenas-net@" in backend.name

    def test_local_default_resolves_default_model(self) -> None:
        """from_config with no model_path resolves to DEFAULT_MODEL."""
        model = ModelStore.resolve(None)
        assert model is DEFAULT_MODEL


# -- LlamaCppBackend (requires model on disk) -----------------------------


@pytest.fixture
def llama_backend() -> LlamaCppBackend | None:
    """Return a LlamaCppBackend if a model is available, else skip."""
    try:
        return LlamaCppBackend.get(DEFAULT_MODEL)
    except RuntimeError:
        pytest.skip("No local model available -- run `shenasctl model download`")
        return None  # unreachable but makes ty happy


class TestLlamaCppBackend:
    def test_singleton(self, llama_backend: LlamaCppBackend) -> None:
        second = LlamaCppBackend.get(DEFAULT_MODEL)
        assert second is llama_backend

    def test_name_is_filename(self, llama_backend: LlamaCppBackend) -> None:
        assert llama_backend.name == DEFAULT_MODEL.filename

    def test_categorize_returns_string(self, llama_backend: LlamaCppBackend) -> None:
        result = llama_backend.categorize(
            "Morning jog",
            prompt="Categorize into one word: Morning jog. Valid categories: Run, Bike, Swim.",
        )
        assert isinstance(result, str)
        assert len(result) > 0

    def test_categorize_picks_valid_category(self, llama_backend: LlamaCppBackend) -> None:
        result = llama_backend.categorize(
            "Bought groceries at the store",
            prompt="Reply with exactly one word from this list: Food, Transport, Shopping."
            " Text: Bought groceries at the store",
        )
        assert result is not None
        first_word = result.strip().split()[0].strip(".*")
        assert first_word in {"Food", "Transport", "Shopping"}


# -- End-to-end: backend + cache -----------------------------------------


class TestEndToEnd:
    def test_categorize_and_cache_round_trip(self, llama_backend: LlamaCppBackend, db_con: duckdb.DuckDBPyConnection) -> None:
        cache = LlmCache()
        prompt = "Reply with one word: Run or Walk. Text: sprinting fast"
        prompt_hash = LlmCache.hash16(prompt)
        text = "sprinting fast"

        # Miss
        assert cache.get(text=text, prompt_hash=prompt_hash, model=llama_backend.name) is None

        # Categorize
        result = llama_backend.categorize(text, prompt=prompt)
        assert result is not None

        # Store
        cache.put(text=text, prompt_hash=prompt_hash, model=llama_backend.name, result=result)

        # Hit
        cached = cache.get(text=text, prompt_hash=prompt_hash, model=llama_backend.name)
        assert cached == result

    def test_different_model_does_not_hit_cache(
        self, llama_backend: LlamaCppBackend, db_con: duckdb.DuckDBPyConnection
    ) -> None:
        cache = LlmCache()
        prompt_hash = LlmCache.hash16("test prompt")
        cache.put(text="hello", prompt_hash=prompt_hash, model=llama_backend.name, result="cached")

        # Same text, different model -> miss
        assert cache.get(text="hello", prompt_hash=prompt_hash, model="other-model") is None
