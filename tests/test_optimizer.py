import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from optimizer import optimize_assignments


PROJECTS = {
    'Alpha': {'min': 1, 'max': 5},
    'Beta':  {'min': 1, 'max': 5},
    'Gamma': {'min': 0, 'max': 5},
}

STUDENTS = [
    {'name': 'Alice', 'choices': ['Alpha', 'Beta', 'Gamma']},
    {'name': 'Bob',   'choices': ['Beta',  'Alpha', 'Gamma']},
    {'name': 'Carol', 'choices': ['Alpha', 'Gamma', 'Beta']},
    {'name': 'Dave',  'choices': ['Beta',  'Gamma', 'Alpha']},
]


def test_all_students_assigned():
    result = optimize_assignments(STUDENTS, PROJECTS)
    assert 'error' not in result
    assert len(result['assignments']) == len(STUDENTS)


def test_each_student_one_project():
    result = optimize_assignments(STUDENTS, PROJECTS)
    for name, info in result['assignments'].items():
        assert info['project'] in PROJECTS


def test_capacity_respected():
    result = optimize_assignments(STUDENTS, PROJECTS)
    for proj, members in result['project_groups'].items():
        assert len(members) <= PROJECTS[proj]['max']
        assert len(members) >= PROJECTS[proj]['min']


def test_prefers_top_choice():
    students = [{'name': 'Only', 'choices': ['Alpha', 'Beta', 'Gamma']}]
    projects = {'Alpha': {'min': 0, 'max': 5}, 'Beta': {'min': 0, 'max': 5}, 'Gamma': {'min': 0, 'max': 5}}
    result = optimize_assignments(students, projects)
    assert result['assignments']['Only']['project'] == 'Alpha'
    assert result['assignments']['Only']['rank'] == 1


def test_stats_populated():
    result = optimize_assignments(STUDENTS, PROJECTS)
    stats = result['stats']
    assert stats['total_students'] == len(STUDENTS)
    assert isinstance(stats['rank_counts'], dict)


def test_infeasible_returns_error():
    # 5 students, but Beta min=4 AND Gamma min=4 → need 8 seats minimum, only 5 students
    students = [{'name': f'S{i}', 'choices': ['Alpha']} for i in range(5)]
    projects = {'Alpha': {'min': 0, 'max': 5}, 'Beta': {'min': 4, 'max': 5}, 'Gamma': {'min': 4, 'max': 5}}
    result = optimize_assignments(students, projects)
    assert 'error' in result


def test_unranked_assignment_when_needed():
    students = [{'name': 'Alice', 'choices': ['Alpha']}, {'name': 'Bob', 'choices': ['Alpha']}]
    projects = {'Alpha': {'min': 0, 'max': 1}, 'Beta': {'min': 1, 'max': 5}}
    result = optimize_assignments(students, projects)
    assert 'error' not in result
    ranks = [info['rank'] for info in result['assignments'].values()]
    assert None in ranks or 1 in ranks


def test_single_student_single_project():
    students = [{'name': 'Solo', 'choices': ['Alpha']}]
    projects = {'Alpha': {'min': 1, 'max': 3}}
    result = optimize_assignments(students, projects)
    assert result['assignments']['Solo']['project'] == 'Alpha'
    assert result['assignments']['Solo']['rank'] == 1


def test_project_groups_match_assignments():
    result = optimize_assignments(STUDENTS, PROJECTS)
    all_in_groups = [m for members in result['project_groups'].values() for m in members]
    assert sorted(all_in_groups) == sorted(result['assignments'].keys())
