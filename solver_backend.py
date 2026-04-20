from __future__ import annotations

from typing import Any


def assign_students(students: list[Any], capstones: list[Any], technique: str) -> dict[str, Any]:
    """
    Replace this stub with the real solver implementation.

    Expected inputs:
    - students: objects with `.name` and `.preferences`
    - capstones: objects with `.name`, `.minimum`, and `.maximum`
    - technique: one of:
        - "brute_force"
        - "linear_programming"
        - "genetic_algorithm"

    Expected return shape:
    {
        "technique": technique,
        "used_demo_solver": False,
        "summary": {
            "students": <int>,
            "projects": <int>,
            "top_choice_matches": <int>,
        },
        "assignments": [
            {"student": "Avery Brooks", "project": "AI Tutor", "matched_rank": 1},
        ],
        "capstone_summary": [
            {"project": "AI Tutor", "assigned": 3, "minimum": 2, "maximum": 4, "status": "OK"},
        ],
    }
    """

    raise NotImplementedError(
        "Implement assign_students(...) in solver_backend.py to connect the real backend solver."
    )
