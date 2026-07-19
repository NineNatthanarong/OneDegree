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


def test_film_specializations_are_separate_tracks(client: TestClient) -> None:
    base = {
        "academic_year": "2569",
        "faculty_slug": "school-of-digital-media-and-cinematic-arts",
    }
    department_response = client.get("/api/v1/degree-plan", params=base)
    departments = department_response.json()["options"]["departments"]
    film = next(item for item in departments if item["name_th"] == "สาขาวิชาภาพยนตร์")

    track_response = client.get(
        "/api/v1/degree-plan",
        params={**base, "department_slug": film["slug"]},
    )
    tracks = track_response.json()["options"]["tracks"]
    assert len(tracks) == 11
    assert all(track["name"] != "default" for track in tracks)

    writing = next(
        track for track in tracks if track["name"] == "การผลิตภาพยนตร์กลุ่มการเขียนบท"
    )
    plan_response = client.get(
        "/api/v1/degree-plan",
        params={**base, "department_slug": film["slug"], "track_slug": writing["slug"]},
    )
    plan = plan_response.json()["options"]["plans"][0]
    response = client.get(
        "/api/v1/degree-plan",
        params={
            **base,
            "department_slug": film["slug"],
            "track_slug": writing["slug"],
            "plan_slug": plan["slug"],
        },
    )
    years = response.json()["degree_plan"]["cohorts"][0]["years"]
    year_3 = next(year for year in years if year["year"] == 3)
    year_4 = next(year for year in years if year["year"] == 4)
    semester_totals = [
        (len(semester["courses"]), semester["total_credits"])
        for semester in year_3["semesters"]
    ]
    assert semester_totals == [
        (6, 18),
        (7, 21),
    ]
    assert year_4["total_credits"] == 15


@pytest.mark.parametrize(
    ("academic_year", "department_name", "track_count"),
    [
        ("2564", "สาขาภาพยนตร์", 10),
        ("2565", "สาขาภาพยนตร์", 11),
        ("2566", "สาขาวิชาภาพยนตร์", 11),
        ("2567", "สาขาวิชาภาพยนตร์", 11),
        ("2568", "สาขาวิชาภาพยนตร์", 11),
        ("2569", "สาขาวิชาภาพยนตร์", 11),
    ],
)
def test_film_track_counts_across_supported_years(
    client: TestClient,
    academic_year: str,
    department_name: str,
    track_count: int,
) -> None:
    base = {
        "academic_year": academic_year,
        "faculty_slug": "school-of-digital-media-and-cinematic-arts",
    }
    department_response = client.get("/api/v1/degree-plan", params=base)
    film_departments = [
        department
        for department in department_response.json()["options"]["departments"]
        if "ภาพยนตร์" in department["name_th"]
    ]
    assert [department["name_th"] for department in film_departments] == [
        department_name
    ]

    track_response = client.get(
        "/api/v1/degree-plan",
        params={**base, "department_slug": film_departments[0]["slug"]},
    )
    tracks = track_response.json()["options"]["tracks"]
    assert len(tracks) == track_count
    assert all(track["name"] != "default" for track in tracks)


def test_degree_plan_route_invalid_faculty_returns_404(client: TestClient) -> None:
    response = client.get(
        "/api/v1/degree-plan",
        params={"academic_year": "2568", "faculty_slug": "not-found"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Faculty not found"
