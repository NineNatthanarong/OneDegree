# Degree Plan Curriculum API

Read-only backend API and database layer for the `curriculum_database.json` dataset.

## What this includes

- **FastAPI** backend with auto-generated docs at `/docs`
- **SQLAlchemy** data model for academic years, faculties, departments, tracks, plans, cohorts, and courses
- **PostgreSQL** database in Docker Compose
- **Automatic seed/import** from `curriculum_database.json` on startup
- **One-command deploy** with Docker

## Architecture

The JSON file is imported into a relational schema optimized for read access:

- `academic_years`
- `faculties`
- `departments`
- `tracks`
- `plan_types`
- `cohorts`
- `course_catalog_entries`
- `semester_courses`

This supports a simple degree-plan-first flow through one main API route.

## API routes

Base URL: `http://localhost:1223/api/v1`

### System

- `GET /health`
- `GET /metadata`

### Main degree plan route

- `GET /degree-plan`

Query params:

- `academic_year`
- `faculty_slug`
- `department_slug`
- `track_slug`
- `plan_slug`

Use the same route repeatedly:

1. `GET /api/v1/degree-plan`
   - returns available academic years
2. `GET /api/v1/degree-plan?academic_year=2568`
   - returns faculties for that year
3. `GET /api/v1/degree-plan?academic_year=2568&faculty_slug=school-of-accounting`
   - returns departments
4. `GET /api/v1/degree-plan?academic_year=2568&faculty_slug=school-of-accounting&department_slug=hlaksuutrbaychiibanthit`
   - returns tracks
5. `GET /api/v1/degree-plan?academic_year=2568&faculty_slug=school-of-accounting&department_slug=hlaksuutrbaychiibanthit&track_slug=default`
   - returns plans
6. `GET /api/v1/degree-plan?academic_year=2568&faculty_slug=school-of-accounting&department_slug=hlaksuutrbaychiibanthit&track_slug=default&plan_slug=pkti`
   - returns the final degree plan

Response fields:

- `selected` — current query values
- `next_query_field` — what query field the frontend should ask for next
- `options` — current valid options from backend
- `degree_plan` — filled only when all required query params are provided

### Degree plan response

The final `degree_plan` object returns:

- selected academic year
- selected faculty
- selected department
- selected track
- selected plan
- all cohort variants inside that plan
- each cohort's study years, semesters, and courses

Why cohorts are included:

- the source JSON sometimes has multiple cohort versions under the same plan
- many are standard 4-year plans
- some transfer/extended plans have 1, 2, 3, or 5 study years in the source data
- returning cohorts preserves the real data instead of guessing one version

## One-command deploy

Use either command:

```bash
make deploy
```

or directly:

```bash
docker compose up --build -d
```

After startup:

- API: [http://localhost:1223](http://localhost:1223)
- Swagger docs: [http://localhost:1223/docs](http://localhost:1223/docs)
- PostgreSQL: `localhost:1224`

## Local test

```bash
pip install -r requirements-dev.txt
pytest -q
```

## Notes

- The API is intentionally **read-only**
- No authentication is included, per your request
- On startup, the importer checks the JSON file checksum and only re-imports if the source file changed
- The main business API is now **one route**: `/api/v1/degree-plan`
