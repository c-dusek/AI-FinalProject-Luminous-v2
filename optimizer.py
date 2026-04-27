"""Optimization strategies for assigning students to projects."""

import random
import re

import pulp


SUPPORTED_TECHNIQUES = {
    "linear_programming": "Linear Programming",
    "brute_force": "Brute Force",
    "genetic_algorithm": "Genetic Algorithm",
}

_BRUTE_FORCE_STUDENT_LIMIT = 80


def _safe(name: str) -> str:
    """Sanitize a string for use as a PuLP variable/constraint name."""
    return re.sub(r"[^a-zA-Z0-9]", "_", name)


def _build_scores(students: list, all_projects: list, n_choices: int) -> dict:
    """Convert ranked choices into a score table shared by each solver."""
    scores: dict = {}
    for student in students:
        sname = student["name"]
        scores[sname] = {}
        for proj in all_projects:
            if proj in student["choices"]:
                rank_idx = student["choices"].index(proj)
                scores[sname][proj] = n_choices - rank_idx
            else:
                scores[sname][proj] = 0
    return scores


def _build_result(students: list, assignment_list: list, all_projects: list, scores: dict, technique: str) -> dict:
    """Build the result structure consumed by the UI and CSV exports."""
    assignments: dict = {}
    for student, proj in zip(students, assignment_list):
        sname = student["name"]
        rank = student["choices"].index(proj) + 1 if proj in student["choices"] else None
        assignments[sname] = {"project": proj, "rank": rank}

    project_groups: dict = {}
    for proj in all_projects:
        members = sorted(name for name, a in assignments.items() if a["project"] == proj)
        if members:
            project_groups[proj] = members

    rank_counts: dict = {}
    unranked_count = 0
    for info in assignments.values():
        r = info["rank"]
        if r is not None:
            rank_counts[str(r)] = rank_counts.get(str(r), 0) + 1
        else:
            unranked_count += 1

    total_score = sum(scores[s["name"]][p] for s, p in zip(students, assignment_list))
    stats = {
        "total_students": len(students),
        "rank_counts": rank_counts,
        "unranked_count": unranked_count,
        "objective_value": total_score,
        "technique": technique,
        "technique_label": SUPPORTED_TECHNIQUES[technique],
    }
    return {"assignments": assignments, "project_groups": project_groups, "stats": stats}


def _project_count_is_valid(count: int, limits: dict, total_students: int) -> bool:
    """A project is valid if it is closed or it satisfies its min/max limits."""
    min_cap = max(0, limits.get("min", 0))
    max_cap = limits.get("max", total_students)
    return count == 0 or min_cap <= count <= max_cap


def _solve_brute_force(students: list, constraints: dict, scores: dict, all_projects: list) -> dict:
    """Enumerate assignments with backtracking for very small class sizes."""
    if len(students) > _BRUTE_FORCE_STUDENT_LIMIT:
        return {
            "error": (
                f"Brute Force is limited to {_BRUTE_FORCE_STUDENT_LIMIT} students "
                f"({len(students)} loaded). Use Linear Programming or Genetic Algorithm for larger inputs."
            )
        }

    best: dict = {"score": -1, "assignment": None}

    def backtrack(idx: int, current: list, counts: dict) -> None:
        if idx == len(students):
            # Validate the final seat counts here so projects are allowed to stay
            # completely unused when their minimum is zero.
            for proj, limits in constraints.items():
                if not _project_count_is_valid(counts.get(proj, 0), limits, len(students)):
                    return
            score = sum(scores[students[i]["name"]][current[i]] for i in range(len(students)))
            if score > best["score"]:
                best["score"] = score
                best["assignment"] = current[:]
            return

        sname = students[idx]["name"]
        remaining = len(students) - idx - 1  # students left after this one
        for proj in all_projects:
            cur = counts.get(proj, 0)
            max_cap = constraints[proj].get("max", len(students))
            if cur >= max_cap:
                continue
            # Prune: if adding this student would make it impossible for a
            # project with a min constraint to ever reach its minimum,
            # skip this branch early.
            min_cap = constraints[proj].get("min", 0)
            if min_cap > 0 and cur + 1 < min_cap and remaining < min_cap - cur - 1:
                continue
            current.append(proj)
            counts[proj] = cur + 1
            backtrack(idx + 1, current, counts)
            current.pop()
            counts[proj] -= 1

    backtrack(0, [], {})

    if best["assignment"] is None:
        return {
            "error": (
                "No feasible solution found. The project min/max capacities "
                "cannot accommodate all students."
            )
        }

    return _build_result(students, best["assignment"], all_projects, scores, "brute_force")


def _solve_genetic(
    students: list,
    constraints: dict,
    scores: dict,
    all_projects: list,
    generations: int = 300,
    pop_size: int = 150,
) -> dict:
    """Search for a good feasible assignment using an evolutionary heuristic."""
    n = len(students)
    proj_idx = {p: i for i, p in enumerate(all_projects)}

    def fitness(chrom: list) -> float:
        # Heavy penalties push the search toward feasible seat counts while
        # still rewarding assignments that satisfy higher-ranked preferences.
        counts = [0] * len(all_projects)
        score = 0.0
        for i, s in enumerate(students):
            p = chrom[i]
            counts[proj_idx[p]] += 1
            score += scores[s["name"]][p]
        penalty = 0.0
        for j, proj in enumerate(all_projects):
            min_c = constraints[proj].get("min", 0)
            max_c = constraints[proj].get("max", n)
            if 0 < counts[j] < min_c:
                penalty += (min_c - counts[j]) * 1000
            if counts[j] > max_c:
                penalty += (counts[j] - max_c) * 1000
        return score - penalty

    def random_chrom() -> list:
        return [random.choice(all_projects) for _ in range(n)]

    def crossover(a: list, b: list) -> list:
        pt = random.randint(1, n - 1)
        return a[:pt] + b[pt:]

    def mutate(chrom: list, rate: float = 0.05) -> list:
        return [random.choice(all_projects) if random.random() < rate else g for g in chrom]

    def tournament(pop: list, fits: list, k: int = 4) -> list:
        candidates = random.sample(range(len(pop)), k)
        return pop[max(candidates, key=lambda i: fits[i])]

    def greedy_chrom() -> list:
        # Seed part of the population with preference-aware candidates so the
        # search does not start entirely from random assignments.
        chrom = []
        counts = {p: 0 for p in all_projects}
        for s in students:
            for choice in s["choices"] + [p for p in all_projects if p not in s["choices"]]:
                if counts[choice] < constraints[choice].get("max", n):
                    chrom.append(choice)
                    counts[choice] += 1
                    break
        return chrom

    n_greedy = max(1, pop_size // 5)
    population = [greedy_chrom() for _ in range(n_greedy)] + [random_chrom() for _ in range(pop_size - n_greedy)]

    for _ in range(generations):
        fits = [fitness(c) for c in population]
        sorted_idx = sorted(range(len(population)), key=lambda i: fits[i], reverse=True)
        new_pop = [population[i][:] for i in sorted_idx[:2]]
        while len(new_pop) < pop_size:
            child = crossover(tournament(population, fits), tournament(population, fits))
            new_pop.append(mutate(child))
        population = new_pop

    fits = [fitness(c) for c in population]
    best = population[max(range(len(population)), key=lambda i: fits[i])]

    counts = {proj: 0 for proj in all_projects}
    for proj in best:
        counts[proj] += 1
    for proj, limits in constraints.items():
        if not _project_count_is_valid(counts[proj], limits, n):
            return {
                "error": (
                    "Genetic Algorithm could not find a feasible solution satisfying all seat constraints. "
                    "Try relaxing the minimum/maximum seat limits."
                )
            }

    return _build_result(students, best, all_projects, scores, "genetic_algorithm")


def optimize_assignments(students: list, constraints: dict, technique: str = "linear_programming") -> dict:
    """
    Assign each student to exactly one capstone project to maximize total preference score.

    Scoring:
        Rank 1 (top choice) → N points  (N = max choices any student submitted)
        Rank 2              → N-1 points
        ...
        Rank N              → 1 point
        Unranked project    → 0 points

    Args:
        students    : list of {"name": str, "choices": [str, ...]}  (ordered preference)
        constraints : {"Project Name": {"min": int, "max": int}, ...}
        technique   : "linear_programming" | "brute_force" | "genetic_algorithm"

    Returns:
        dict with keys: assignments, project_groups, stats
        or dict with key: error (on infeasibility)
    """
    if technique not in SUPPORTED_TECHNIQUES:
        supported = ", ".join(SUPPORTED_TECHNIQUES.values())
        return {
            "error": (
                f"The backend currently supports: {supported}. "
                f"Requested technique '{technique}' is not available."
            )
        }

    all_projects = list(constraints.keys())
    n_choices = max((len(s["choices"]) for s in students), default=6)
    scores = _build_scores(students, all_projects, n_choices)

    # Fast pre-check: total max must accommodate every student.
    total_max = sum(c.get("max", len(students)) for c in constraints.values())
    if total_max < len(students):
        return {
            "error": (
                f"Total maximum seats across all projects ({total_max}) is less than "
                f"the number of students ({len(students)}). "
                "Raise the maximum seat counts before running."
            )
        }

    if technique == "brute_force":
        return _solve_brute_force(students, constraints, scores, all_projects)

    if technique == "genetic_algorithm":
        return _solve_genetic(students, constraints, scores, all_projects)

    # Linear Programming is the default because it finds an exact optimum for
    # the score model while remaining fast for typical class sizes.
    prob = pulp.LpProblem("Capstone_Matching", pulp.LpMaximize)

    x: dict = {}
    for i, student in enumerate(students):
        sname = student["name"]
        x[sname] = {}
        for proj in all_projects:
            x[sname][proj] = pulp.LpVariable(f"x_{i}_{_safe(proj)}", cat="Binary")

    prob += pulp.lpSum(
        scores[s["name"]][p] * x[s["name"]][p]
        for s in students
        for p in all_projects
    )

    for i, student in enumerate(students):
        sname = student["name"]
        prob += pulp.lpSum(x[sname][p] for p in all_projects) == 1, f"one_project_{i}"

    for proj in all_projects:
        min_cap = max(0, constraints[proj].get("min", 0))
        max_cap = constraints[proj].get("max", len(students))
        proj_load = pulp.lpSum(x[s["name"]][proj] for s in students)
        # This binary "open" switch lets the solver either leave a project empty
        # or enforce both bounds when the project is used.
        is_open = pulp.LpVariable(f"open_{_safe(proj)}", cat="Binary")
        prob += proj_load >= min_cap * is_open, f"min_{_safe(proj)}"
        prob += proj_load <= max_cap * is_open, f"max_{_safe(proj)}"

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    if prob.status != 1:
        if prob.status == -1:
            return {
                "error": (
                    "No feasible solution found. The project min/max capacities "
                    "cannot accommodate all students. Try lowering minimum seats "
                    "or raising maximum seats."
                )
            }
        return {"error": f"Solver returned status: {pulp.LpStatus[prob.status]}"}

    # Collapse the decision matrix back to one assigned project per student.
    assignment_list: list = []
    for student in students:
        sname = student["name"]
        for proj in all_projects:
            val = pulp.value(x[sname][proj])
            if val is not None and val > 0.5:
                assignment_list.append(proj)
                break

    result = _build_result(students, assignment_list, all_projects, scores, "linear_programming")
    result["stats"]["objective_value"] = round(pulp.value(prob.objective), 2)
    return result
