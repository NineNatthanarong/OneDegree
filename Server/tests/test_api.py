from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.database import get_engine, get_session_factory
from app.db.seed import load_dataset


@pytest.fixture(scope="session")
def client(tmp_path_factory: pytest.TempPathFactory) -> TestClient:
    workspace_root = Path(__file__).resolve().parents[1]
    database_path = tmp_path_factory.mktemp("db") / "degreeplan-test.db"

    previous_database_url = os.environ.get("DATABASE_URL")
    previous_seed_data_path = os.environ.get("SEED_DATA_PATH")

    os.environ["DATABASE_URL"] = f"sqlite:///{database_path}"
    os.environ["SEED_DATA_PATH"] = str(workspace_root / "curriculum_database.json")

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    load_dataset.cache_clear()

    from app.main import create_app

    with TestClient(create_app()) as api_client:
        yield api_client

    if previous_database_url is None:
        os.environ.pop("DATABASE_URL", None)
    else:
        os.environ["DATABASE_URL"] = previous_database_url

    if previous_seed_data_path is None:
        os.environ.pop("SEED_DATA_PATH", None)
    else:
        os.environ["SEED_DATA_PATH"] = previous_seed_data_path

    get_settings.cache_clear()
    get_engine.cache_clear()
    get_session_factory.cache_clear()
    load_dataset.cache_clear()


def test_healthcheck(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_degree_plan_route_returns_years_first(client: TestClient) -> None:
    response = client.get("/api/v1/degree-plan")
    assert response.status_code == 200
    payload = response.json()

    assert payload["next_query_field"] == "academic_year"
    assert payload["options"]["academic_years"]
    assert payload["degree_plan"] is None


def test_degree_plan_route_returns_faculties_for_year(client: TestClient) -> None:
    response = client.get("/api/v1/degree-plan", params={"academic_year": "2568"})
    assert response.status_code == 200
    payload = response.json()

    assert payload["next_query_field"] == "faculty_slug"
    assert payload["selected"]["academic_year"] == "2568"
    assert payload["options"]["faculties"]


def test_degree_plan_route_returns_departments_for_faculty(client: TestClient) -> None:
    response = client.get(
        "/api/v1/degree-plan",
        params={"academic_year": "2568", "faculty_slug": "school-of-accounting"},
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["next_query_field"] == "department_slug"
    assert payload["options"]["departments"]


def test_degree_plan_route_returns_final_degree_plan(client: TestClient) -> None:
    department_response = client.get(
        "/api/v1/degree-plan",
        params={"academic_year": "2568", "faculty_slug": "school-of-accounting"},
    )
    department_slug = department_response.json()["options"]["departments"][0]["slug"]

    track_response = client.get(
        "/api/v1/degree-plan",
        params={
            "academic_year": "2568",
            "faculty_slug": "school-of-accounting",
            "department_slug": department_slug,
        },
    )
    track_slug = track_response.json()["options"]["tracks"][0]["slug"]

    plan_response = client.get(
        "/api/v1/degree-plan",
        params={
            "academic_year": "2568",
            "faculty_slug": "school-of-accounting",
            "department_slug": department_slug,
            "track_slug": track_slug,
        },
    )
    plan_slug = plan_response.json()["options"]["plans"][0]["slug"]

    response = client.get(
        "/api/v1/degree-plan",
        params={
            "academic_year": "2568",
            "faculty_slug": "school-of-accounting",
            "department_slug": department_slug,
            "track_slug": track_slug,
            "plan_slug": plan_slug,
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["next_query_field"] is None
    assert payload["degree_plan"] is not None
    assert payload["degree_plan"]["academic_year"] == "2568"
    assert payload["degree_plan"]["faculty"]["slug"] == "school-of-accounting"
    assert payload["degree_plan"]["department"]["slug"] == department_slug
    assert payload["degree_plan"]["track"]["slug"] == track_slug
    assert payload["degree_plan"]["plan"]["slug"] == plan_slug
    assert payload["degree_plan"]["cohorts"]
    assert payload["degree_plan"]["cohorts"][0]["years"]


def test_degree_plan_route_requires_ordered_query(client: TestClient) -> None:
    response = client.get("/api/v1/degree-plan", params={"faculty_slug": "school-of-accounting"})
    assert response.status_code == 400
    assert response.json()["detail"] == "academic_year is required before faculty_slug"


def test_degree_plan_route_invalid_faculty_returns_404(client: TestClient) -> None:
    response = client.get(
        "/api/v1/degree-plan",
        params={"academic_year": "2568", "faculty_slug": "not-found"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Faculty not found"
