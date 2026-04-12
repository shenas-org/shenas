"""Tests for app.mesh.relay_sync -- push/pull/full-cycle relay transport."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from app.mesh import relay_sync


class TestPushToPeer:
    def test_no_token_returns_false(self) -> None:
        with patch("app.local_users.LocalUser.get_remote_token", return_value=None):
            assert relay_sync.push_to_peer("https://srv", "peer-1", [{"a": 1}]) is False

    def test_success(self) -> None:
        mock_resp = MagicMock(status_code=200)
        with (
            patch("app.local_users.LocalUser.get_remote_token", return_value="tok"),
            patch("httpx.post", return_value=mock_resp) as mock_post,
        ):
            assert relay_sync.push_to_peer("https://srv", "peer-1", [{"a": 1}]) is True
        mock_post.assert_called_once()
        body = mock_post.call_args.kwargs["json"]
        assert json.loads(body["payload"]) == [{"a": 1}]

    def test_non_200(self) -> None:
        mock_resp = MagicMock(status_code=500, text="boom")
        with (
            patch("app.local_users.LocalUser.get_remote_token", return_value="tok"),
            patch("httpx.post", return_value=mock_resp),
        ):
            assert relay_sync.push_to_peer("https://srv", "peer-1", []) is False

    def test_network_error(self) -> None:
        with (
            patch("app.local_users.LocalUser.get_remote_token", return_value="tok"),
            patch("httpx.post", side_effect=RuntimeError("boom")),
        ):
            assert relay_sync.push_to_peer("https://srv", "peer-1", []) is False


class TestPullFromRelay:
    def test_returns_empty_when_unauthenticated(self) -> None:
        with (
            patch("app.local_users.LocalUser.get_remote_token", return_value=None),
            patch("app.mesh.relay_sync._get_device_id", return_value="dev"),
        ):
            assert relay_sync.pull_from_relay("https://srv") == []

    def test_success(self) -> None:
        mock_resp = MagicMock(status_code=200, json=lambda: [{"payload": "[]"}])
        with (
            patch("app.local_users.LocalUser.get_remote_token", return_value="tok"),
            patch("app.mesh.relay_sync._get_device_id", return_value="dev"),
            patch("httpx.get", return_value=mock_resp),
        ):
            messages = relay_sync.pull_from_relay("https://srv")
        assert messages == [{"payload": "[]"}]

    def test_network_error(self) -> None:
        with (
            patch("app.local_users.LocalUser.get_remote_token", return_value="tok"),
            patch("app.mesh.relay_sync._get_device_id", return_value="dev"),
            patch("httpx.get", side_effect=RuntimeError("boom")),
        ):
            assert relay_sync.pull_from_relay("https://srv") == []


class TestApplyRemoteEvents:
    def test_skips_events_from_self(self, patch_db: None) -> None:
        from app.mesh import sync_log

        sync_log.ensure_sync_tables()
        local_id = sync_log._get_device_id()
        events = [
            {"device_id": local_id, "table_schema": "metrics", "table_name": "t", "operation": "INSERT"},
            {"device_id": "other", "table_schema": "metrics", "table_name": "t", "operation": "INSERT", "row_key": "r1"},
        ]
        count = relay_sync.apply_remote_events(json.dumps(events))
        assert count == 1

    def test_appends_events_from_peers(self, patch_db: None) -> None:
        from app.mesh import sync_log

        sync_log.ensure_sync_tables()
        events = [
            {
                "device_id": "peer-1",
                "table_schema": "metrics",
                "table_name": "tbl",
                "operation": "INSERT",
                "row_key": "r1",
                "payload": "{}",
            }
        ]
        count = relay_sync.apply_remote_events(json.dumps(events))
        assert count == 1


class TestSyncWithPeers:
    def test_no_credentials(self) -> None:
        with (
            patch("app.local_users.LocalUser.get_remote_token", return_value=None),
            patch("app.mesh.relay_sync._get_device_id", return_value=None),
        ):
            assert relay_sync.sync_with_peers("https://srv") == {"pushed": 0, "pulled": 0}

    def test_full_cycle(self, patch_db: None) -> None:
        from app.mesh import sync_log

        sync_log.ensure_sync_tables()
        sync_log.append_event("metrics", "tbl", "INSERT", row_key="r1")

        peers_resp = MagicMock(status_code=200, json=lambda: [{"id": "self"}, {"id": "peer-1"}])
        empty_pull = MagicMock(status_code=200, json=list)
        push_resp = MagicMock(status_code=200)

        with (
            patch("app.local_users.LocalUser.get_remote_token", return_value="tok"),
            patch("app.mesh.relay_sync._get_device_id", return_value="self"),
            patch("httpx.get", return_value=peers_resp),
            patch("httpx.post", return_value=push_resp),
            patch("app.mesh.relay_sync.pull_from_relay", return_value=[]),
        ):
            result = relay_sync.sync_with_peers("https://srv")
        assert result["pushed"] >= 1
        assert result["pulled"] == 0
        _ = empty_pull  # silence unused

    def test_peer_discovery_failure(self, patch_db: None) -> None:
        with (
            patch("app.local_users.LocalUser.get_remote_token", return_value="tok"),
            patch("app.mesh.relay_sync._get_device_id", return_value="self"),
            patch("httpx.get", side_effect=RuntimeError("boom")),
            patch("app.mesh.relay_sync.pull_from_relay", return_value=[]),
        ):
            result = relay_sync.sync_with_peers("https://srv")
        assert result == {"pushed": 0, "pulled": 0}


class TestGetTokenAndDeviceId:
    def test_get_remote_token_no_user(self, patch_db: None) -> None:
        from app.local_users import LocalUser

        assert LocalUser.get_remote_token() is None

    def test_get_device_id_missing_row(self, patch_db: None) -> None:
        # No identity row yet -- should return None.
        assert relay_sync._get_device_id() is None
