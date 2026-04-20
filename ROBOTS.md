# ROBOTS.md — AI Project Structure Guide

This file describes the structure of the Capstone Project Matcher for AI agents working on this codebase.

---

## Project Purpose

Assign students to capstone projects by solving an Integer Linear Program that maximizes total preference satisfaction subject to per-project capacity constraints.

---

## Entry Points

| File | Role |
|------|------|
| `app.py` | Flask application. Start here. Defines all HTTP routes. |
| `optimizer.py` | Core ILP logic. Edit this to change the assignment algorithm. |
| `parser_module.py` | File parsing. Edit this to support new input formats. |

---

## API Routes (`app.py`)

| Method | Route | Input | Output |
|--------|-------|-------|--------|
| GET | `/` | — | Renders `templates/index.html` |
| POST | `/upload` | `multipart/form-data` — file field `file` (.csv or .txt) | `{students, projects}` JSON |
| POST | `/optimize` | `{students, constraints}` JSON | `{assignments, project_groups, stats}` JSON |
| POST | `/download` | `{assignments}` JSON | CSV file download |

---

## Data Shapes

```python
# Student (from /upload response and sent to /optimize)
{
  "name": str,
  "choices": [str, ...]   # ordered list, index 0 = top choice
}

# Constraints (sent to /optimize)
{
  "Project Name": { "min": int, "max": int },
  ...
}

# Assignment result (from /optimize)
{
  "assignments": {
    "Student Name": { "project": str, "rank": int | None }
  },
  "project_groups": {
    "Project Name": ["Student Name", ...]
  },
  "stats": {
    "total_students": int,
    "rank_counts": { "1": int, "2": int, ... },
    "unranked_count": int,
    "objective_value": float
  }
}
```

---

## Optimization Model (`optimizer.py`)

- **Type**: Binary Integer Linear Program
- **Solver**: PuLP with CBC (open-source, no license required)
- **Variables**: `x[student][project] ∈ {0, 1}`
- **Objective**: Maximize `Σ score(student, project) × x[student][project]`
  - Score = `(num_choices - rank_index)` if ranked, else `0`
- **Constraints**:
  1. Each student assigned to exactly one project
  2. Each project receives between `min` and `max` students

---

## Frontend (`templates/index.html`, `static/`)

Single-page app with three sequential sections controlled by `static/js/main.js`:

1. **Upload** (`#section-upload`) — drag-and-drop file upload, calls `POST /upload`
2. **Configure** (`#section-configure`) — editable project min/max table, calls `POST /optimize`
3. **Results** (`#section-results`) — stat cards, Chart.js doughnut, assignment table, group cards

State is held in the `state` object in `main.js`. No server-side session is used.

---

## Tests (`tests/`)

| File | Coverage |
|------|----------|
| `test_parser.py` | CSV/TXT parsing: delimiters, missing fields, duplicate names, BOM |
| `test_optimizer.py` | Assignment correctness, capacity bounds, infeasibility, stats |

Run with: `pytest tests/`

---

## Dependencies

```
flask>=3.0.0   # Web server
pulp>=2.7.0    # ILP solver (bundles CBC binary)
```

Frontend dependencies are loaded via CDN (Bootstrap 5, Font Awesome 6, Chart.js 4, Inter font). No npm or build step required.

---

## Do Not Modify

- `static/css/style.css` step indicator classes (`.step`, `.step-circle`, `.step.active`, `.step.done`) are tightly coupled to `main.js`'s `setStep()` function.
- PuLP variable/constraint names must remain sanitized via `_safe()` in `optimizer.py` — PuLP rejects names with spaces or special characters.
