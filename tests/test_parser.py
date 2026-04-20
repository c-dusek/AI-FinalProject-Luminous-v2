import pytest
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from parser_module import parse_preferences


BASIC_CSV = """Name,Choice1,Choice2,Choice3
Alice,Alpha,Beta,Gamma
Bob,Beta,Alpha,Delta
"""

TAB_CSV = "Name\tChoice1\tChoice2\nCarol\tGamma\tAlpha\n"

SEMICOLON_CSV = "Name;Choice1;Choice2\nDave;Delta;Alpha\n"

MISSING_CHOICES = """Name,Choice1,Choice2,Choice3
Eve,Alpha,,
"""

STUDENT_HEADER_CSV = """Student,Choice1,Choice2
Frank,Alpha,Beta
"""


def test_basic_csv():
    students, projects = parse_preferences(BASIC_CSV)
    assert len(students) == 2
    assert students[0]['name'] == 'Alice'
    assert students[0]['choices'] == ['Alpha', 'Beta', 'Gamma']
    assert 'Alpha' in projects and 'Beta' in projects and 'Delta' in projects


def test_tab_delimiter():
    students, projects = parse_preferences(TAB_CSV)
    assert len(students) == 1
    assert students[0]['name'] == 'Carol'
    assert students[0]['choices'] == ['Gamma', 'Alpha']


def test_semicolon_delimiter():
    students, projects = parse_preferences(SEMICOLON_CSV)
    assert len(students) == 1
    assert students[0]['choices'] == ['Delta', 'Alpha']


def test_missing_choices_skipped():
    students, _ = parse_preferences(MISSING_CHOICES)
    assert students[0]['choices'] == ['Alpha']


def test_student_column_header():
    students, _ = parse_preferences(STUDENT_HEADER_CSV)
    assert students[0]['name'] == 'Frank'


def test_empty_raises():
    with pytest.raises(ValueError):
        parse_preferences('')


def test_only_header_raises():
    with pytest.raises(ValueError):
        parse_preferences('Name,Choice1\n')


def test_duplicate_names_deduplicated():
    csv = "Name,Choice1\nAlice,Alpha\nAlice,Beta\n"
    students, _ = parse_preferences(csv)
    names = [s['name'] for s in students]
    assert len(set(names)) == 2


def test_bom_stripped():
    content = '\ufeffName,Choice1\nBob,Alpha\n'
    students, _ = parse_preferences(content)
    assert students[0]['name'] == 'Bob'
