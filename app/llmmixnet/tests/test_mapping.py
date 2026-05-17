"""Tests for MappingStore: DuckDB schema, encrypt/decrypt, TTL, HMAC bin."""

from __future__ import annotations

from app.llmmixnet.mapping import MappingStore, _derive_hmac_key, _derive_map_key, hmac_bin_merchant


class TestKeyDerivation:
    def test_derive_map_key_deterministic(self, root_key_k1, device_salt):
        key_a = _derive_map_key(root_key_k1, device_salt)
        key_b = _derive_map_key(root_key_k1, device_salt)
        assert key_a == key_b

    def test_derive_hmac_key_differs_from_map_key(self, root_key_k1, device_salt):
        map_key = _derive_map_key(root_key_k1, device_salt)
        hmac_key = _derive_hmac_key(root_key_k1, device_salt)
        assert map_key != hmac_key

    def test_different_salts_yield_different_keys(self, root_key_k1):
        key_a = _derive_map_key(root_key_k1, b"\x01" * 32)
        key_b = _derive_map_key(root_key_k1, b"\x02" * 32)
        assert key_a != key_b

    def test_map_key_is_32_bytes(self, root_key_k1, device_salt):
        key = _derive_map_key(root_key_k1, device_salt)
        assert len(key) == 32


class TestHmacBin:
    def test_merchant_bin_deterministic(self):
        key = b"\x03" * 32
        bin_a = hmac_bin_merchant(key, "Starbucks")
        bin_b = hmac_bin_merchant(key, "Starbucks")
        assert bin_a == bin_b

    def test_different_merchants_usually_differ(self):
        key = b"\x03" * 32
        bin_starbucks = hmac_bin_merchant(key, "Starbucks")
        bin_mcdonalds = hmac_bin_merchant(key, "McDonalds")
        assert bin_starbucks != bin_mcdonalds

    def test_bin_format(self):
        key = b"\x03" * 32
        token = hmac_bin_merchant(key, "Starbucks")
        assert token.startswith("MERCHANT_BIN_0x")
        hex_part = token[len("MERCHANT_BIN_0x") :]
        assert len(hex_part) == 4
        int(hex_part, 16)

    def test_different_keys_yield_different_bins(self):
        token_a = hmac_bin_merchant(b"\x01" * 32, "Starbucks")
        token_b = hmac_bin_merchant(b"\x02" * 32, "Starbucks")
        assert token_a != token_b


class TestMappingStore:
    def test_schema_created(self, mapping_store, con):
        tables = con.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'llmmixnet'").fetchall()
        names = {row[0] for row in tables}
        assert "mappings" in names
        assert "sessions" in names
        assert "audit_log" in names

    def test_create_session_returns_id(self, mapping_store):
        session_id = mapping_store.create_session()
        assert len(session_id) == 36

    def test_store_and_retrieve_round_trip(self, mapping_store):
        session_id = mapping_store.create_session()
        mapping_id = "test-mapping-1"
        mapping_store.store_mapping(
            session_id=session_id,
            mapping_id=mapping_id,
            placeholder="<PERSON_0>",
            entity_text="Alice Smith",
            entity_type="PERSON",
        )
        result = mapping_store.retrieve_entity(mapping_id, "<PERSON_0>")
        assert result == "Alice Smith"

    def test_retrieve_nonexistent_returns_none(self, mapping_store):
        mapping_store.create_session()
        result = mapping_store.retrieve_entity("no-such-mapping", "<PERSON_0>")
        assert result is None

    def test_multiple_entities_same_mapping(self, mapping_store):
        session_id = mapping_store.create_session()
        mapping_id = "test-mapping-multi"
        pairs = [
            ("<PERSON_0>", "Alice"),
            ("<PERSON_1>", "Bob"),
            ("<EMAIL_ADDRESS_0>", "alice@example.com"),
        ]
        for placeholder, entity_text in pairs:
            mapping_store.store_mapping(
                session_id=session_id,
                mapping_id=mapping_id,
                placeholder=placeholder,
                entity_text=entity_text,
                entity_type=placeholder.split("_")[0].strip("<"),
            )
        for placeholder, expected in pairs:
            assert mapping_store.retrieve_entity(mapping_id, placeholder) == expected

    def test_list_placeholders(self, mapping_store):
        session_id = mapping_store.create_session()
        mapping_id = "test-list"
        mapping_store.store_mapping(session_id, mapping_id, "<PERSON_0>", "Alice", "PERSON")
        mapping_store.store_mapping(session_id, mapping_id, "<PERSON_1>", "Bob", "PERSON")
        placeholders = mapping_store.list_placeholders(mapping_id)
        assert set(placeholders.keys()) == {"<PERSON_0>", "<PERSON_1>"}

    def test_different_sessions_isolated(self, mapping_store):
        session_a = mapping_store.create_session()
        session_b = mapping_store.create_session()
        mapping_store.store_mapping(session_a, "map-a", "<PERSON_0>", "Alice", "PERSON")
        mapping_store.store_mapping(session_b, "map-b", "<PERSON_0>", "Bob", "PERSON")
        assert mapping_store.retrieve_entity("map-a", "<PERSON_0>") == "Alice"
        assert mapping_store.retrieve_entity("map-b", "<PERSON_0>") == "Bob"

    def test_persistent_session_amber_audit(self, mapping_store, con):
        session_id = mapping_store.create_session(persistent_mode=True)
        assert mapping_store.is_persistent(session_id)
        rows = con.execute(
            "SELECT event_type FROM llmmixnet.audit_log WHERE session_id = ?",
            [session_id],
        ).fetchall()
        assert any(row[0] == "persistent_mode_enabled" for row in rows)

    def test_non_persistent_session(self, mapping_store):
        session_id = mapping_store.create_session(persistent_mode=False)
        assert not mapping_store.is_persistent(session_id)

    def test_evict_expired_removes_rows(self, con, root_key_k1, device_salt):
        store = MappingStore.from_root_key(con, root_key_k1, device_salt)
        session_id = store.create_session()
        mapping_id = "exp-test"
        store.store_mapping(session_id, mapping_id, "<PERSON_0>", "Alice", "PERSON")
        con.execute(
            "UPDATE llmmixnet.mappings SET expires_at = '2000-01-01' WHERE mapping_id = ?",
            [mapping_id],
        )
        count = store.evict_expired()
        assert count == 1
        assert store.retrieve_entity(mapping_id, "<PERSON_0>") is None

    def test_hmac_bin_via_store(self, mapping_store):
        token = mapping_store.hmac_bin("Whole Foods")
        assert token.startswith("MERCHANT_BIN_0x")

    def test_encryption_produces_different_ciphertexts(self, mapping_store):
        session_id = mapping_store.create_session()
        mapping_id = "enc-test"
        mapping_store.store_mapping(session_id, mapping_id, "<PERSON_0>", "Alice", "PERSON")
        mapping_store.store_mapping(session_id, mapping_id + "2", "<PERSON_0>", "Alice", "PERSON")
        rows = mapping_store._con.execute("SELECT mapping_blob FROM llmmixnet.mappings").fetchall()
        blobs = [row[0] for row in rows]
        assert blobs[0] != blobs[1]
