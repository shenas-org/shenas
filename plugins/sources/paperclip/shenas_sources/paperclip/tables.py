"""Paperclip source tables (Phase 1).

- ``PaperclipCompanies`` -- identity columns for the authenticated company (DimensionTable / SCD2).
- ``PaperclipAgents``    -- agents belonging to the company (DimensionTable / SCD2).
- ``PaperclipProjects``  -- projects within the company (DimensionTable / SCD2).
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Annotated, Any

from app.table import Field
from shenas_sources.core.table import DimensionTable, SourceTable

if TYPE_CHECKING:
    from collections.abc import Iterator

    from shenas_sources.paperclip.client import PaperclipClient


def _to_iso(value: Any) -> str | None:
    """Coerce a Paperclip timestamp to ISO-8601, or None if missing."""
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (int, float)) and value > 0:
        seconds = value / 1000.0 if value > 1_000_000_000_000 else float(value)
        return datetime.fromtimestamp(seconds, tz=UTC).isoformat()
    return str(value) or None


def _company_id_from_client(client: PaperclipClient) -> str:
    """Return the companyId of the authenticated agent."""
    me = client.get_me()
    return str(me.get("companyId") or me.get("company_id") or "")


class PaperclipCompanies(DimensionTable):
    """Registered Paperclip company. SCD2 tracks identity-level changes."""

    class _Meta:
        name = "paperclip_companies"
        display_name = "Companies"
        description = "Paperclip company identity data."
        pk = ("company_id",)

    company_id: Annotated[str, Field(db_type="VARCHAR", description="Company UUID", display_name="Company ID")]
    name: Annotated[str | None, Field(db_type="VARCHAR", description="Company name", display_name="Name")] = None
    description: Annotated[
        str | None, Field(db_type="VARCHAR", description="Company description", display_name="Description")
    ] = None
    status: Annotated[str | None, Field(db_type="VARCHAR", description="Company status", display_name="Status")] = None
    issue_prefix: Annotated[
        str | None, Field(db_type="VARCHAR", description="Issue identifier prefix (e.g. SHE)", display_name="Issue Prefix")
    ] = None
    brand_color: Annotated[
        str | None, Field(db_type="VARCHAR", description="Brand color hex code", display_name="Brand Color")
    ] = None
    logo_url: Annotated[str | None, Field(db_type="VARCHAR", description="Logo URL", display_name="Logo URL")] = None
    budget_monthly_cents: Annotated[
        int | None, Field(db_type="INTEGER", description="Monthly budget in cents", display_name="Monthly Budget (¢)")
    ] = None

    @classmethod
    def extract(cls, client: PaperclipClient, **_: Any) -> Iterator[dict[str, Any]]:
        company_id = _company_id_from_client(client)
        if not company_id:
            return
        row = client.get_company(company_id)
        yield {
            "company_id": company_id,
            "name": row.get("name"),
            "description": row.get("description"),
            "status": row.get("status"),
            "issue_prefix": row.get("issuePrefix") or row.get("issue_prefix"),
            "brand_color": row.get("brandColor") or row.get("brand_color"),
            "logo_url": row.get("logoUrl") or row.get("logo_url"),
            "budget_monthly_cents": (
                int(v) if (v := row.get("budgetMonthlyCents") or row.get("budget_monthly_cents")) is not None else None
            ),
        }


class PaperclipAgents(DimensionTable):
    """Agents belonging to the authenticated company. SCD2 tracks role and status changes."""

    class _Meta:
        name = "paperclip_agents"
        display_name = "Agents"
        description = "Agents registered in the Paperclip company."
        pk = ("agent_id",)

    agent_id: Annotated[str, Field(db_type="VARCHAR", description="Agent UUID", display_name="Agent ID")]
    company_id: Annotated[
        str | None, Field(db_type="VARCHAR", description="Parent company UUID", display_name="Company ID")
    ] = None
    name: Annotated[str | None, Field(db_type="VARCHAR", description="Agent name", display_name="Name")] = None
    title: Annotated[str | None, Field(db_type="VARCHAR", description="Agent title", display_name="Title")] = None
    role: Annotated[str | None, Field(db_type="VARCHAR", description="Agent role", display_name="Role")] = None
    icon: Annotated[str | None, Field(db_type="VARCHAR", description="Agent icon identifier", display_name="Icon")] = None
    status: Annotated[str | None, Field(db_type="VARCHAR", description="Agent status", display_name="Status")] = None
    reports_to: Annotated[
        str | None, Field(db_type="VARCHAR", description="UUID of the supervising agent", display_name="Reports To")
    ] = None
    capabilities: Annotated[
        str | None, Field(db_type="VARCHAR", description="Comma-separated capability list", display_name="Capabilities")
    ] = None
    adapter_type: Annotated[
        str | None, Field(db_type="VARCHAR", description="Adapter type (e.g. claude)", display_name="Adapter Type")
    ] = None
    budget_monthly_cents: Annotated[
        int | None, Field(db_type="INTEGER", description="Monthly budget in cents", display_name="Monthly Budget (¢)")
    ] = None
    url_key: Annotated[str | None, Field(db_type="VARCHAR", description="URL-safe agent key", display_name="URL Key")] = None
    last_heartbeat_at: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="Timestamp of last heartbeat", display_name="Last Heartbeat")
    ] = None

    @classmethod
    def extract(cls, client: PaperclipClient, **_: Any) -> Iterator[dict[str, Any]]:
        company_id = _company_id_from_client(client)
        if not company_id:
            return
        for agent in client.get_agents(company_id):
            caps = agent.get("capabilities")
            if isinstance(caps, list):
                caps = ",".join(str(c) for c in caps)
            yield {
                "agent_id": str(agent.get("id") or agent.get("agent_id") or ""),
                "company_id": company_id,
                "name": agent.get("name"),
                "title": agent.get("title"),
                "role": agent.get("role"),
                "icon": agent.get("icon"),
                "status": agent.get("status"),
                "reports_to": agent.get("reportsTo") or agent.get("reports_to"),
                "capabilities": caps,
                "adapter_type": agent.get("adapterType") or agent.get("adapter_type"),
                "budget_monthly_cents": (
                    int(v) if (v := agent.get("budgetMonthlyCents") or agent.get("budget_monthly_cents")) is not None else None
                ),
                "url_key": agent.get("urlKey") or agent.get("url_key"),
                "last_heartbeat_at": _to_iso(agent.get("lastHeartbeatAt") or agent.get("last_heartbeat_at")),
            }


class PaperclipProjects(DimensionTable):
    """Projects within the authenticated company. SCD2 tracks status and lead changes."""

    class _Meta:
        name = "paperclip_projects"
        display_name = "Projects"
        description = "Projects registered in the Paperclip company."
        pk = ("project_id",)

    project_id: Annotated[str, Field(db_type="VARCHAR", description="Project UUID", display_name="Project ID")]
    company_id: Annotated[
        str | None, Field(db_type="VARCHAR", description="Parent company UUID", display_name="Company ID")
    ] = None
    name: Annotated[str | None, Field(db_type="VARCHAR", description="Project name", display_name="Name")] = None
    status: Annotated[str | None, Field(db_type="VARCHAR", description="Project status", display_name="Status")] = None
    lead_agent_id: Annotated[
        str | None, Field(db_type="VARCHAR", description="UUID of the lead agent", display_name="Lead Agent ID")
    ] = None
    target_date: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="Target completion date", display_name="Target Date")
    ] = None
    color: Annotated[str | None, Field(db_type="VARCHAR", description="Project color hex", display_name="Color")] = None
    archived_at: Annotated[
        str | None, Field(db_type="TIMESTAMP", description="Timestamp when archived, if any", display_name="Archived At")
    ] = None
    url_key: Annotated[str | None, Field(db_type="VARCHAR", description="URL-safe project key", display_name="URL Key")] = None

    @classmethod
    def extract(cls, client: PaperclipClient, **_: Any) -> Iterator[dict[str, Any]]:
        company_id = _company_id_from_client(client)
        if not company_id:
            return
        for project in client.get_projects(company_id):
            yield {
                "project_id": str(project.get("id") or project.get("project_id") or ""),
                "company_id": company_id,
                "name": project.get("name"),
                "status": project.get("status"),
                "lead_agent_id": project.get("leadAgentId") or project.get("lead_agent_id"),
                "target_date": _to_iso(project.get("targetDate") or project.get("target_date")),
                "color": project.get("color"),
                "archived_at": _to_iso(project.get("archivedAt") or project.get("archived_at")),
                "url_key": project.get("urlKey") or project.get("url_key"),
            }


TABLES: tuple[type[SourceTable], ...] = (PaperclipCompanies, PaperclipAgents, PaperclipProjects)
