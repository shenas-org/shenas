from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock

from shenas_sources.core.table import AggregateTable, EventTable, SnapshotTable
from shenas_sources.duolingo.tables import (
    Achievements,
    Courses,
    DailyXp,
    Friends,
    League,
    UserProfile,
)


class TestDailyXp:
    def test_yields_summaries_with_epoch_dates(self) -> None:
        client = MagicMock()
        client.get_xp_summaries.return_value = [
            {"date": 1774656000, "gainedXp": 150, "numSessions": 3, "totalSessionTime": 900},
            {"date": 1774742400, "gainedXp": 80, "numSessions": 2, "totalSessionTime": 600},
        ]

        results = list(DailyXp.extract(client, start_date="2026-03-25"))
        assert len(results) == 2
        assert results[0]["date"] == date(2026, 3, 28)
        assert results[0]["xp_gained"] == 150
        assert results[1]["num_sessions"] == 2

    def test_handles_none_values(self) -> None:
        client = MagicMock()
        client.get_xp_summaries.return_value = [
            {"date": 1774656000, "gainedXp": None, "numSessions": None, "totalSessionTime": None},
        ]

        results = list(DailyXp.extract(client, start_date="2026-03-25"))
        assert len(results) == 1
        assert results[0]["xp_gained"] == 0
        assert results[0]["num_sessions"] == 0

    def test_skips_entries_without_date(self) -> None:
        client = MagicMock()
        client.get_xp_summaries.return_value = [
            {"gainedXp": 50},
            {"date": 1774656000, "gainedXp": 80},
        ]

        results = list(DailyXp.extract(client, start_date="2026-03-25"))
        assert len(results) == 1


class TestCourses:
    def test_yields_courses(self) -> None:
        client = MagicMock()
        client.get_courses.return_value = [
            {"language": "German", "language_code": "de", "from_language": "en", "xp": 5000, "crowns": 50, "level": 12},
        ]

        results = list(Courses.extract(client))
        assert len(results) == 1
        assert results[0]["language"] == "German"


class TestUserProfile:
    def test_yields_profile(self) -> None:
        client = MagicMock()
        client.get_user.return_value = {
            "username": "testuser",
            "name": "Test",
            "streak": 42,
            "totalXp": 50000,
            "creationDate": 1600000000,
            "learningLanguage": "de",
            "fromLanguage": "en",
            "xpGoal": 30,
            "hasPlus": True,
            "streakData": {
                "currentStreak": {"length": 42, "startDate": "2026-02-15"},
                "longestStreak": {"length": 120},
                "streakFreezesUsed": 3,
            },
        }
        client.get_following.return_value = [{"userId": 1}, {"userId": 2}]
        client.get_followers.return_value = [{"userId": 3}]

        results = list(UserProfile.extract(client))
        assert len(results) == 1
        row = results[0]
        assert row["username"] == "testuser"
        assert row["display_name_"] == "Test"
        assert row["streak"] == 42
        assert row["longest_streak"] == 120
        assert row["streak_start"] == "2026-02-15"
        assert row["streak_freezes_used"] == 3
        assert row["daily_goal_xp"] == 30
        assert row["has_super"] is True
        assert row["following_count"] == 2
        assert row["followers_count"] == 1


class TestAchievements:
    def test_yields_unlocked(self) -> None:
        client = MagicMock()
        client.get_achievements.return_value = [
            {"name": "WILDFIRE", "tier": 3, "title": "Wildfire", "count": 100, "unlockTimestamp": 1700000000},
            {"name": "SAGE", "tier": 1, "title": "Sage", "count": 5},
        ]

        rows = list(Achievements.extract(client))
        assert len(rows) == 2
        assert rows[0]["achievement_name"] == "WILDFIRE"
        assert rows[0]["tier"] == 3
        assert rows[0]["count"] == 100
        assert rows[0]["unlocked_at"] is not None
        assert rows[1]["unlocked_at"] is None


class TestLeague:
    def test_yields_league_with_user_rank(self) -> None:
        client = MagicMock()
        client.user_id = 999
        client.get_league.return_value = {
            "cohort": {
                "cohortId": "abc-123",
                "tier": 4,
                "cohortEndDate": 1800000000,
                "rankings": [
                    {"user_id": 111, "score": 500},
                    {"user_id": 999, "score": 350},
                    {"user_id": 222, "score": 200},
                ],
            }
        }

        rows = list(League.extract(client))
        assert len(rows) == 1
        row = rows[0]
        assert row["cohort_id"] == "abc-123"
        assert row["league_tier"] == 4
        assert row["league_name"] == "Ruby"
        assert row["rank"] == 2
        assert row["weekly_xp"] == 350
        assert row["cohort_size"] == 3

    def test_no_data_yields_nothing(self) -> None:
        client = MagicMock()
        client.user_id = 999
        client.get_league.return_value = None
        assert list(League.extract(client)) == []


class TestFriends:
    def test_yields_following_with_mutual_flag(self) -> None:
        client = MagicMock()
        client.get_following.return_value = [
            {"userId": 1, "username": "alice", "displayName": "Alice", "totalXp": 1000, "streak": 5},
            {"userId": 2, "username": "bob", "displayName": "Bob", "totalXp": 800, "streak": 10},
        ]
        client.get_followers.return_value = [
            {"userId": 1, "username": "alice"},
        ]

        rows = list(Friends.extract(client))
        assert len(rows) == 2
        alice = next(r for r in rows if r["user_id"] == 1)
        bob = next(r for r in rows if r["user_id"] == 2)
        assert alice["is_follower"] is True
        assert bob["is_follower"] is False
        assert alice["display_name_"] == "Alice"


class TestKindsAndDispositions:
    def test_daily_xp_is_aggregate(self) -> None:
        assert issubclass(DailyXp, AggregateTable)
        assert DailyXp.time_at == "date"

    def test_achievements_is_event(self) -> None:
        assert issubclass(Achievements, EventTable)
        assert Achievements.time_at == "unlocked_at"

    def test_friends_is_snapshot_scd2(self) -> None:
        assert issubclass(Friends, SnapshotTable)
        assert Friends.write_disposition() == {"disposition": "merge", "strategy": "scd2"}
