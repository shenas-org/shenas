from unittest.mock import MagicMock

from shenas_sources.paperclip.tables import PaperclipAgents, PaperclipCompanies, PaperclipProjects


def _make_client(
    *,
    company_id: str = "co-001",
    company: dict | None = None,
    agents: list[dict] | None = None,
    projects: list[dict] | None = None,
) -> MagicMock:
    client = MagicMock()
    client.get_me.return_value = {"companyId": company_id}
    client.get_company.return_value = company or {}
    client.get_agents.return_value = agents or []
    client.get_projects.return_value = projects or []
    return client


SAMPLE_COMPANY = {
    "name": "Shenas",
    "description": "Local-first QS platform",
    "status": "active",
    "issuePrefix": "SHE",
    "brandColor": "#ff5500",
    "logoUrl": "https://example.com/logo.svg",
    "budgetMonthlyCents": 5000,
}

SAMPLE_AGENT = {
    "id": "agent-001",
    "name": "Coder",
    "title": "Platform Engineer",
    "role": "engineer",
    "icon": "code",
    "status": "running",
    "reportsTo": "cto-001",
    "capabilities": ["python", "rust"],
    "adapterType": "claude",
    "budgetMonthlyCents": 1000,
    "urlKey": "coder",
    "lastHeartbeatAt": "2026-05-11T10:00:00Z",
}

SAMPLE_PROJECT = {
    "id": "proj-001",
    "name": "Onboarding",
    "status": "active",
    "leadAgentId": "agent-001",
    "targetDate": "2026-12-31T00:00:00Z",
    "color": "#3399ff",
    "archivedAt": None,
    "urlKey": "onboarding",
}


class TestPaperclipCompanies:
    def test_extract_yields_company(self) -> None:
        client = _make_client(company_id="co-001", company=SAMPLE_COMPANY)
        rows = list(PaperclipCompanies.extract(client))
        assert len(rows) == 1
        row = rows[0]
        assert row["company_id"] == "co-001"
        assert row["name"] == "Shenas"
        assert row["issue_prefix"] == "SHE"
        assert row["budget_monthly_cents"] == 5000
        assert row["brand_color"] == "#ff5500"

    def test_extract_empty_company_id(self) -> None:
        client = _make_client(company_id="")
        assert list(PaperclipCompanies.extract(client)) == []

    def test_extract_null_optional_fields(self) -> None:
        client = _make_client(company_id="co-002", company={"name": "Minimal"})
        rows = list(PaperclipCompanies.extract(client))
        assert rows[0]["description"] is None
        assert rows[0]["budget_monthly_cents"] is None


class TestPaperclipAgents:
    def test_extract_yields_agent(self) -> None:
        client = _make_client(company_id="co-001", agents=[SAMPLE_AGENT])
        rows = list(PaperclipAgents.extract(client))
        assert len(rows) == 1
        row = rows[0]
        assert row["agent_id"] == "agent-001"
        assert row["name"] == "Coder"
        assert row["adapter_type"] == "claude"
        assert row["budget_monthly_cents"] == 1000
        assert row["url_key"] == "coder"
        assert row["last_heartbeat_at"] == "2026-05-11T10:00:00Z"
        assert row["capabilities"] == "python,rust"
        assert row["reports_to"] == "cto-001"

    def test_extract_empty_agents(self) -> None:
        client = _make_client(company_id="co-001", agents=[])
        assert list(PaperclipAgents.extract(client)) == []

    def test_extract_capabilities_string_passthrough(self) -> None:
        agent = {**SAMPLE_AGENT, "capabilities": "python,rust"}
        client = _make_client(company_id="co-001", agents=[agent])
        rows = list(PaperclipAgents.extract(client))
        assert rows[0]["capabilities"] == "python,rust"


class TestPaperclipProjects:
    def test_extract_yields_project(self) -> None:
        client = _make_client(company_id="co-001", projects=[SAMPLE_PROJECT])
        rows = list(PaperclipProjects.extract(client))
        assert len(rows) == 1
        row = rows[0]
        assert row["project_id"] == "proj-001"
        assert row["name"] == "Onboarding"
        assert row["status"] == "active"
        assert row["lead_agent_id"] == "agent-001"
        assert row["target_date"] == "2026-12-31T00:00:00Z"
        assert row["archived_at"] is None
        assert row["url_key"] == "onboarding"

    def test_extract_empty_projects(self) -> None:
        client = _make_client(company_id="co-001", projects=[])
        assert list(PaperclipProjects.extract(client)) == []
