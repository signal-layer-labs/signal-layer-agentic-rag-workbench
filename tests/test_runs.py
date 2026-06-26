from collections.abc import Sequence
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.models import AgentRun
from app.main import app
from app.services.run_service import RunService, get_run_service


class InMemoryAgentRunRepository:
    def __init__(self) -> None:
        self.runs: dict[UUID, AgentRun] = {}

    def create(self, business_question: str, summary: str) -> AgentRun:
        run = AgentRun(
            id=uuid4(),
            business_question=business_question,
            status="created",
            summary=summary,
        )
        self.runs[run.id] = run
        return run

    def get_by_id(self, run_id: UUID) -> AgentRun | None:
        return self.runs.get(run_id)

    def list_recent(self, limit: int = 20) -> Sequence[AgentRun]:
        return list(self.runs.values())[-limit:]


@pytest.fixture
def client() -> TestClient:
    repository = InMemoryAgentRunRepository()
    app.dependency_overrides[get_run_service] = lambda: RunService(repository)
    test_client = TestClient(app)
    yield test_client
    app.dependency_overrides.clear()


def test_create_and_get_run(client: TestClient) -> None:
    business_question = (
        "Analyze last quarter sales and summarize risks and opportunities."
    )

    create_response = client.post(
        "/runs",
        json={"business_question": business_question},
    )

    assert create_response.status_code == 201
    created_run = create_response.json()
    assert created_run["status"] == "created"
    assert created_run["business_question"] == business_question
    assert created_run["summary"] == (
        "Mock run created. Agent execution will be added in a later phase."
    )
    UUID(created_run["run_id"])

    get_response = client.get(f"/runs/{created_run['run_id']}")

    assert get_response.status_code == 200
    assert get_response.json() == created_run


def test_get_missing_run(client: TestClient) -> None:
    response = client.get(f"/runs/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {
        "error": {
            "code": "not_found",
            "message": "Agent run not found.",
            "retryable": False,
            "details": {},
        }
    }
