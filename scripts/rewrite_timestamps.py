#!/usr/bin/env python3
"""
Rewrite git commit timestamps so they never fall during Swiss (Basel-Land)
work hours (Mon-Fri 08:00-18:00, excluding public holidays).

Timestamps that land in work hours are shifted to plausible leisure times
(evenings, early mornings, or weekends) while preserving the date.

Usage:
    python rewrite_timestamps.py [OPTIONS]

Options:
    --base REF      Base ref; only commits in HEAD that are not in REF are
                    rewritten.  Default: origin/main
    --all           Rewrite every commit in the repo (ignores --base).
    --dry-run       Show what would change without rewriting anything.

Designed to run in CI after commits are created but before they are pushed.
"""

from __future__ import annotations

import argparse
import os
import random
import subprocess
import sys
import textwrap
from datetime import date, datetime, timedelta, timezone

# ── Zurich timezone (CET/CEST) ──────────────────────────────────────────────
# We avoid zoneinfo so the script works on minimal CI images (Python 3.9+)
# without tzdata.  Instead we compute CET/CEST transitions directly.

_ONE_HOUR = timedelta(hours=1)
_CET = timezone(timedelta(hours=1), "CET")
_CEST = timezone(timedelta(hours=2), "CEST")


def _last_sunday_of_month(year: int, month: int) -> date:
    """Return the last Sunday of the given month."""
    # Start from the last day and walk back.
    d = date(year, month + 1, 1) - timedelta(days=1) if month < 12 else date(year, 12, 31)
    while d.weekday() != 6:  # Sunday
        d -= timedelta(days=1)
    return d


def zurich_offset(dt_utc: datetime) -> timezone:
    """Return the correct Zurich offset (CET or CEST) for a UTC datetime."""
    year = dt_utc.year
    # CEST starts last Sunday of March at 01:00 UTC
    cest_start = datetime(
        year, 3, _last_sunday_of_month(year, 3).day, 1, 0, 0, tzinfo=timezone.utc
    )
    # CET resumes last Sunday of October at 01:00 UTC
    cet_start = datetime(
        year, 10, _last_sunday_of_month(year, 10).day, 1, 0, 0, tzinfo=timezone.utc
    )
    if cest_start <= dt_utc < cet_start:
        return _CEST
    return _CET


def to_zurich(dt_utc: datetime) -> datetime:
    """Convert a UTC datetime to Zurich local time."""
    tz_offset = zurich_offset(dt_utc)
    return dt_utc.astimezone(tz_offset)


# ── Easter & Basel-Land public holidays ──────────────────────────────────────

def _easter_sunday(year: int) -> date:
    """Anonymous Gregorian Easter algorithm."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    L = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * L) // 451
    month, day = divmod(h + L - 7 * m + 114, 31)
    return date(year, month, day + 1)


def basel_land_holidays(year: int) -> set[date]:
    """
    Return all public holidays for the canton of Basel-Landschaft.

    Sources: Swiss federal law + BL cantonal regulation.
    """
    holidays: set[date] = set()

    # ── Fixed-date holidays ──
    holidays.add(date(year, 1, 1))    # Neujahrstag
    holidays.add(date(year, 1, 2))    # Berchtoldstag
    holidays.add(date(year, 5, 1))    # Tag der Arbeit
    holidays.add(date(year, 8, 1))    # Bundesfeier (Swiss National Day)
    holidays.add(date(year, 12, 25))  # Weihnachtstag
    holidays.add(date(year, 12, 26))  # Stephanstag

    # ── Moveable holidays (Easter-based) ──
    easter = _easter_sunday(year)
    holidays.add(easter - timedelta(days=2))   # Karfreitag  (Good Friday)
    holidays.add(easter + timedelta(days=1))   # Ostermontag (Easter Monday)
    holidays.add(easter + timedelta(days=39))  # Auffahrt    (Ascension Day)
    holidays.add(easter + timedelta(days=50))  # Pfingstmontag (Whit Monday)

    return holidays


# Cache across calls within the same run.
_holiday_cache: dict[int, set[date]] = {}


def is_holiday(d: date) -> bool:
    if d.year not in _holiday_cache:
        _holiday_cache[d.year] = basel_land_holidays(d.year)
    return d in _holiday_cache[d.year]


# ── Work-hour detection & shifting ───────────────────────────────────────────

WORK_START = 8   # 08:00
WORK_END = 18    # 18:00


def is_work_time(dt_zurich: datetime) -> bool:
    """True if the Zurich-local datetime falls in Mon-Fri 08-18, non-holiday."""
    if dt_zurich.weekday() >= 5:
        return False
    if is_holiday(dt_zurich.date()):
        return False
    return WORK_START <= dt_zurich.hour < WORK_END


def _pick_leisure_seconds(rng: random.Random) -> int:
    """
    Pick a second-of-day outside work hours using a weighted distribution
    that mimics a long after-work coding session stretching into the night.

    The window runs from 18:00 to 03:30 (next day), distributed as:
      18:00–20:00  35%   (right after work — peak hobby time)
      20:00–22:00  30%   (evening)
      22:00–00:00  20%   (late night)
      00:00–03:30  15%   (very late / into the morning)
    """
    bands = [
        (18 * 3600,       20 * 3600,       0.35),  # 18:00-20:00
        (20 * 3600,       22 * 3600,       0.30),  # 20:00-22:00
        (22 * 3600,       24 * 3600,       0.20),  # 22:00-00:00
        (24 * 3600,       27 * 3600 + 1800, 0.15), # 00:00-03:30 (as 24h-27.5h)
    ]
    roll = rng.random()
    cumulative = 0.0
    for start, end, weight in bands:
        cumulative += weight
        if roll < cumulative:
            return rng.randint(start, end - 1)
    # Fallback (shouldn't happen)
    return rng.randint(18 * 3600, 20 * 3600 - 1)


def _seconds_to_hms(secs: int) -> tuple[int, int, int]:
    h, rem = divmod(secs % 86400, 3600)
    m, s = divmod(rem, 60)
    return h, m, s


# The latest a shifted timestamp can land: 03:30 of the next calendar day.
_MAX_NIGHT_HOUR = 3
_MAX_NIGHT_MINUTE = 30


def shift_to_leisure(
    dt_zurich: datetime,
    floor: datetime | None = None,
    rng: random.Random | None = None,
) -> datetime:
    """
    Move a work-hours timestamp to the same evening / night.

    Timestamps are placed between 18:00 and 03:30 the next morning,
    preserving the "work day" identity (a Tuesday 14:00 commit becomes
    Tuesday evening or Tuesday-night-into-Wednesday-early-morning).

    Args:
        dt_zurich: The original timestamp in Zurich time.
        floor:     Earliest allowed result (ensures chronological ordering).
        rng:       Random instance to use (for determinism across a batch).
    """
    if rng is None:
        rng = random.Random(int(dt_zurich.timestamp()))

    target_day = dt_zurich.date()

    for attempt in range(8):
        secs = _pick_leisure_seconds(rng)

        # secs >= 86400 means past midnight — belongs to the next calendar day.
        if secs >= 86400:
            candidate_date = target_day + timedelta(days=1)
            h, m, s = _seconds_to_hms(secs)  # wraps via % 86400
        else:
            candidate_date = target_day
            h, m, s = _seconds_to_hms(secs)

        candidate = dt_zurich.replace(
            year=candidate_date.year,
            month=candidate_date.month,
            day=candidate_date.day,
            hour=h, minute=m, second=s,
        )

        if floor is None or candidate > floor:
            return candidate

    # Last resort: place it just after the floor with a small gap.
    gap = timedelta(seconds=rng.randint(60, 300))
    return floor + gap


# ── Git helpers ──────────────────────────────────────────────────────────────

def git(*args: str, check: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        capture_output=True,
        text=True,
        check=check,
    )
    return result.stdout.strip()


def all_commits(tip: str = "HEAD") -> list[str]:
    """Return all commit hashes reachable from tip (oldest first)."""
    log = git("rev-list", "--reverse", tip, check=False)
    if not log:
        return []
    return log.splitlines()


def commits_in_range(base: str, tip: str = "HEAD") -> list[str]:
    """Return commit hashes from base..tip (oldest first)."""
    log = git("rev-list", "--reverse", "--ancestry-path", f"{base}..{tip}", check=False)
    if not log:
        return []
    return log.splitlines()


def parse_git_timestamp(raw: str) -> datetime:
    """Parse a git ISO-strict timestamp into a UTC datetime."""
    # git gives e.g. '2025-04-11T14:32:01+02:00'
    dt = datetime.fromisoformat(raw)
    return dt.astimezone(timezone.utc)


# ── Main logic ───────────────────────────────────────────────────────────────

def rewrite_commit_dates(base: str | None, dry_run: bool = False) -> int:
    """
    Rewrite author/committer dates for commits in base..HEAD (or all commits
    if base is None).  Returns the number of commits rewritten.
    """
    commits = all_commits() if base is None else commits_in_range(base)
    if not commits:
        print("No commits to rewrite.")
        return 0

    # Seed a shared RNG from the first commit hash for determinism.
    rng = random.Random(commits[0])

    # Build a mapping of sha -> (new_author_date, new_committer_date).
    # We track a floor timestamp so that every commit stays strictly after
    # the previous one, preserving chronological order.
    rewrites: dict[str, tuple[str, str]] = {}
    floor: datetime | None = None  # in Zurich time

    for sha in commits:
        author_raw = git("log", "-1", "--format=%aI", sha)
        committer_raw = git("log", "-1", "--format=%cI", sha)
        subject = git("log", "-1", "--format=%s", sha)

        author_utc = parse_git_timestamp(author_raw)
        committer_utc = parse_git_timestamp(committer_raw)

        author_zurich = to_zurich(author_utc)
        committer_zurich = to_zurich(committer_utc)

        changed = False
        new_author = author_zurich
        new_committer = committer_zurich

        if is_work_time(author_zurich):
            new_author = shift_to_leisure(author_zurich, floor=floor, rng=rng)
            changed = True
        elif floor is not None and new_author <= floor:
            # Not work time, but would violate ordering — nudge it forward.
            gap = timedelta(seconds=rng.randint(60, 300))
            new_author = floor + gap
            changed = True

        if is_work_time(committer_zurich):
            new_committer = shift_to_leisure(committer_zurich, floor=new_author, rng=rng)
            changed = True
        elif new_committer < new_author:
            # Committer date should be >= author date.
            gap = timedelta(seconds=rng.randint(1, 30))
            new_committer = new_author + gap
            changed = True

        # Update floor to the latest timestamp we've produced.
        floor = max(new_author, new_committer)

        if changed:
            # Format as git-compatible ISO 8601
            a_str = new_author.strftime("%Y-%m-%dT%H:%M:%S%z")
            c_str = new_committer.strftime("%Y-%m-%dT%H:%M:%S%z")
            rewrites[sha] = (a_str, c_str)

            flag = "[DRY RUN] " if dry_run else ""
            print(
                f"{flag}{sha[:10]} \"{subject}\"\n"
                f"  author:    {author_zurich.strftime('%a %H:%M')} -> {new_author.strftime('%a %H:%M')}\n"
                f"  committer: {committer_zurich.strftime('%a %H:%M')} -> {new_committer.strftime('%a %H:%M')}"
            )
        else:
            print(f"{sha[:10]} \"{subject}\" -- OK (not during work hours)")
            # Still update the floor so subsequent commits stay ordered.
            floor = max(new_author, new_committer)

    if not rewrites:
        print("\nAll commits are already outside work hours. Nothing to do.")
        return 0

    if dry_run:
        print(f"\n[DRY RUN] Would rewrite {len(rewrites)} commit(s).")
        return len(rewrites)

    # Build the env-filter script for git filter-branch
    cases = []
    for sha, (a_date, c_date) in rewrites.items():
        cases.append(
            f'    {sha})\n'
            f'        export GIT_AUTHOR_DATE="{a_date}"\n'
            f'        export GIT_COMMITTER_DATE="{c_date}"\n'
            f'        ;;'
        )

    env_filter = (
        'case "$GIT_COMMIT" in\n'
        + "\n".join(cases)
        + "\nesac"
    )

    # Determine the range to pass to filter-branch.
    if base is None:
        # Rewrite entire history.
        ref_range = "HEAD"
    else:
        oldest = commits[0]
        parent = git("rev-parse", f"{oldest}^", check=False)
        if not parent:
            ref_range = "HEAD"
        else:
            ref_range = f"{parent}..HEAD"

    git(
        "filter-branch",
        "-f",
        "--env-filter", env_filter,
        ref_range,
    )

    print(f"\nRewrote {len(rewrites)} commit(s).")
    return len(rewrites)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Shift git timestamps out of Swiss work hours (Basel-Land).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Basel-Land public holidays accounted for:
              Fixed:    Neujahr (1 Jan), Berchtoldstag (2 Jan), Tag der Arbeit (1 May),
                        Bundesfeier (1 Aug), Weihnachtstag (25 Dec), Stephanstag (26 Dec)
              Moveable: Karfreitag, Ostermontag, Auffahrt, Pfingstmontag

            Example CI usage (GitHub Actions):
              - run: python rewrite_timestamps.py --base origin/main
              - run: git push --force-with-lease
        """),
    )
    parser.add_argument(
        "--base",
        default="origin/main",
        help="Base ref; commits reachable from HEAD but not BASE are rewritten. (default: origin/main)",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Rewrite every commit in the repo (ignores --base).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without rewriting.",
    )
    args = parser.parse_args()

    base = None if args.all else args.base
    rewrite_commit_dates(base, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
