# ROBOTS.md - AI Project Structure Guide

This file describes the current desktop version of Capstone Project Matcher for AI agents working in this repository.

## Project Purpose

Assign students to capstone projects by maximizing preference satisfaction while respecting per-project minimum and maximum seat limits.

The app is no longer a Flask web application. It is a Tkinter desktop program launched locally with Python.

## Entry Points

| File | Role |
|------|------|
| `app.py` | Small launcher that starts the desktop UI. |
| `front_end.py` | Main Tkinter application, layout, user actions, exports, and result rendering. |
| `optimizer.py` | Assignment engine with Linear Programming, Genetic Algorithm, and Brute Force strategies. |
| `parser_module.py` | CSV/TXT parsing and normalization for uploaded preference files. |

## Runtime Flow

1. `app.py` calls `front_end.main()`.
2. `CapstoneDesktopApp` builds the Tkinter interface.
3. The user loads a preference file through the file picker.
4. `parse_preferences()` converts the file into student and project data.
5. The UI gathers seat constraints and the selected algorithm.
6. `optimize_assignments()` runs in a worker thread.
7. The UI renders assignment tables, project groups, and summary statistics.
8. The user can export assignments or groups to CSV.

## Core Data Shapes

```python
{
    "name": str,
    "choices": [str, ...],
}
```

```python
{
    "Project Name": {"min": int, "max": int},
}
```

```python
{
    "assignments": {
        "Student Name": {"project": str, "rank": int | None}
    },
    "project_groups": {
        "Project Name": ["Student Name", ...]
    },
    "stats": {
        "total_students": int,
        "rank_counts": {"1": int, "2": int, ...},
        "unranked_count": int,
        "objective_value": float,
        "technique": str,
        "technique_label": str,
    },
}
```

## File Responsibilities

### `front_end.py`

- Builds the desktop layout
- Handles file browsing and parsing
- Validates min/max seat inputs
- Runs optimization off the main UI thread
- Displays assignments, groups, and rank distribution stats
- Exports assignments and grouped rosters

### `optimizer.py`

- Maps ranked preferences to numeric scores
- Supports three solving strategies:
  - `linear_programming`
  - `genetic_algorithm`
  - `brute_force`
- Returns either a structured result or an `{"error": ...}` payload

### `parser_module.py`

- Detects delimiter from the first few non-empty lines
- Finds the student-name column from common header names
- Pads short rows so missing trailing cells do not shift columns
- Deduplicates repeated student names by appending suffixes

## Important Constraints

- Every student must be assigned to exactly one project.
- A project may be unused if its minimum is `0`.
- Total maximum seats must be at least the number of students.
- Brute Force is intentionally limited in practice because it scales poorly.
- PuLP variable names must stay sanitized through `_safe()` in `optimizer.py`.

## Tests

| File | Coverage |
|------|----------|
| `tests/test_parser.py` | Delimiters, missing values, duplicate names, BOM handling |
| `tests/test_optimizer.py` | Feasibility, assignment correctness, ranking behavior, project grouping |

Run with:

```bash
pytest tests/
```

## Dependencies

```text
pulp>=2.7.0
```

Tkinter is provided by the Python standard library and does not need to be installed from `requirements.txt`.
