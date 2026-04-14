"""Freedom House source tables.

- ``FreedomScores`` -- annual freedom ratings per country with full
  sub-indicator breakdown (25 questions across 7 subcategories).
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, ClassVar

from app.table import Field
from shenas_sources.core.table import AggregateTable

if TYPE_CHECKING:
    from collections.abc import Iterator

    from shenas_sources.freedomhouse.client import FreedomHouseClient


class FreedomScores(AggregateTable):
    """Annual freedom ratings per country from Freedom House."""

    class _Meta:
        name = "freedom_scores"
        display_name = "Freedom Scores"
        description = (
            "Annual Freedom in the World ratings: political rights (1-7), "
            "civil liberties (1-7), aggregate score (0-100), 7 subcategory scores, "
            "and 25 individual question scores (0-4 each)."
        )
        pk = ("country", "edition")

    time_at: ClassVar[str] = "edition"

    country: Annotated[str, Field(db_type="VARCHAR", description="Country or territory name", display_name="Country")] = ""
    is_territory: Annotated[
        bool, Field(db_type="BOOLEAN", description="Territory (vs sovereign country)", display_name="Territory")
    ] = False
    edition: Annotated[int, Field(db_type="INTEGER", description="Report edition year", display_name="Edition")] = 0
    status: Annotated[
        str,
        Field(
            db_type="VARCHAR",
            description="Freedom status: Free, Partly Free, or Not Free",
            display_name="Status",
        ),
    ] = ""
    political_rights: Annotated[
        int | None,
        Field(
            db_type="INTEGER",
            description="Political Rights rating (1=most free, 7=least free)",
            display_name="PR Rating",
            value_range=(1, 7),
        ),
    ] = None
    civil_liberties: Annotated[
        int | None,
        Field(
            db_type="INTEGER",
            description="Civil Liberties rating (1=most free, 7=least free)",
            display_name="CL Rating",
            value_range=(1, 7),
        ),
    ] = None
    total: Annotated[
        int | None,
        Field(
            db_type="INTEGER",
            description="Aggregate freedom score (0=least free, 100=most free)",
            display_name="Total Score",
            value_range=(0, 100),
        ),
    ] = None
    # Subcategory scores
    sub_a: Annotated[
        int | None,
        Field(db_type="INTEGER", description="Electoral Process (max 12)", display_name="A: Electoral", value_range=(0, 12)),
    ] = None
    sub_b: Annotated[
        int | None,
        Field(
            db_type="INTEGER",
            description="Political Pluralism and Participation (max 16)",
            display_name="B: Pluralism",
            value_range=(0, 16),
        ),
    ] = None
    sub_c: Annotated[
        int | None,
        Field(
            db_type="INTEGER",
            description="Functioning of Government (max 12)",
            display_name="C: Government",
            value_range=(0, 12),
        ),
    ] = None
    sub_d: Annotated[
        int | None,
        Field(
            db_type="INTEGER",
            description="Freedom of Expression and Belief (max 16)",
            display_name="D: Expression",
            value_range=(0, 16),
        ),
    ] = None
    sub_e: Annotated[
        int | None,
        Field(
            db_type="INTEGER",
            description="Associational and Organizational Rights (max 12)",
            display_name="E: Association",
            value_range=(0, 12),
        ),
    ] = None
    sub_f: Annotated[
        int | None,
        Field(db_type="INTEGER", description="Rule of Law (max 16)", display_name="F: Rule of Law", value_range=(0, 16)),
    ] = None
    sub_g: Annotated[
        int | None,
        Field(
            db_type="INTEGER",
            description="Personal Autonomy and Individual Rights (max 16)",
            display_name="G: Autonomy",
            value_range=(0, 16),
        ),
    ] = None
    # Individual question scores (A1-A3, B1-B4, C1-C3, D1-D4, E1-E3, F1-F4, G1-G4)
    q_a1: Annotated[int | None, Field(db_type="INTEGER", description="A1 score (0-4)", display_name="A1")] = None
    q_a2: Annotated[int | None, Field(db_type="INTEGER", description="A2 score (0-4)", display_name="A2")] = None
    q_a3: Annotated[int | None, Field(db_type="INTEGER", description="A3 score (0-4)", display_name="A3")] = None
    q_b1: Annotated[int | None, Field(db_type="INTEGER", description="B1 score (0-4)", display_name="B1")] = None
    q_b2: Annotated[int | None, Field(db_type="INTEGER", description="B2 score (0-4)", display_name="B2")] = None
    q_b3: Annotated[int | None, Field(db_type="INTEGER", description="B3 score (0-4)", display_name="B3")] = None
    q_b4: Annotated[int | None, Field(db_type="INTEGER", description="B4 score (0-4)", display_name="B4")] = None
    q_c1: Annotated[int | None, Field(db_type="INTEGER", description="C1 score (0-4)", display_name="C1")] = None
    q_c2: Annotated[int | None, Field(db_type="INTEGER", description="C2 score (0-4)", display_name="C2")] = None
    q_c3: Annotated[int | None, Field(db_type="INTEGER", description="C3 score (0-4)", display_name="C3")] = None
    q_d1: Annotated[int | None, Field(db_type="INTEGER", description="D1 score (0-4)", display_name="D1")] = None
    q_d2: Annotated[int | None, Field(db_type="INTEGER", description="D2 score (0-4)", display_name="D2")] = None
    q_d3: Annotated[int | None, Field(db_type="INTEGER", description="D3 score (0-4)", display_name="D3")] = None
    q_d4: Annotated[int | None, Field(db_type="INTEGER", description="D4 score (0-4)", display_name="D4")] = None
    q_e1: Annotated[int | None, Field(db_type="INTEGER", description="E1 score (0-4)", display_name="E1")] = None
    q_e2: Annotated[int | None, Field(db_type="INTEGER", description="E2 score (0-4)", display_name="E2")] = None
    q_e3: Annotated[int | None, Field(db_type="INTEGER", description="E3 score (0-4)", display_name="E3")] = None
    q_f1: Annotated[int | None, Field(db_type="INTEGER", description="F1 score (0-4)", display_name="F1")] = None
    q_f2: Annotated[int | None, Field(db_type="INTEGER", description="F2 score (0-4)", display_name="F2")] = None
    q_f3: Annotated[int | None, Field(db_type="INTEGER", description="F3 score (0-4)", display_name="F3")] = None
    q_f4: Annotated[int | None, Field(db_type="INTEGER", description="F4 score (0-4)", display_name="F4")] = None
    q_g1: Annotated[int | None, Field(db_type="INTEGER", description="G1 score (0-4)", display_name="G1")] = None
    q_g2: Annotated[int | None, Field(db_type="INTEGER", description="G2 score (0-4)", display_name="G2")] = None
    q_g3: Annotated[int | None, Field(db_type="INTEGER", description="G3 score (0-4)", display_name="G3")] = None
    q_g4: Annotated[int | None, Field(db_type="INTEGER", description="G4 score (0-4)", display_name="G4")] = None

    @classmethod
    def extract(cls, client: FreedomHouseClient, **_: Any) -> Iterator[dict[str, Any]]:
        yield from client.get_freedom_scores()


TABLES = (FreedomScores,)
