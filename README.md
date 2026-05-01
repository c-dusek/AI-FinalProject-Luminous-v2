# Capstone Project Matcher

Capstone Project Matcher is a desktop application that assigns students to capstone projects based on ranked preferences and per-project seat limits.

The current version uses a Tkinter interface and supports three assignment strategies:

- Linear Programming for the mathematically optimal assignment
- Genetic Algorithm for a fast heuristic alternative
- Brute Force for exhaustive search on very small inputs

## Features

- Load student preference files from `.csv` or `.txt`
- Detect comma, tab, and semicolon delimiters automatically
- Configure minimum and maximum seats for every project
- Preview imported students and ranked choices before running
- Compare solver strategies from the same UI
- Review assignment tables, project groups, and summary statistics
- Export full assignments and grouped rosters to CSV

## Requirements

- Python 3.10+
- `pip`
- Tkinter available in your Python install

## Installation

```bash
git clone <your-repo-url>
cd AI-FinalProject-Luminous-v2
pip install -r requirements.txt
```

## Running the App

```bash
python app.py
```

This opens the desktop UI directly. There is no web server and no browser step in the current version.

## Desktop Workflow

1. Load a `.csv` or `.txt` preference file.
2. Review the student preview table.
3. Set per-project minimum and maximum seat limits.
4. Choose an algorithm.
5. Run the assignment.
6. Export the results or project groups as CSV.

Keyboard shortcuts:

- `Ctrl+O` opens a preference file
- `Ctrl+R` runs the optimizer
- `Ctrl+E` exports assignment results

## Input File Format

The parser expects a header row followed by one row per student.

Example:

| Name | Choice1 | Choice2 | Choice3 | Choice4 |
|---|---|---|---|---|
| Alice Johnson | Autonomous Vehicles | Robotics | AI Research | Cybersecurity |
| Bob Smith | Robotics | AI Research | Autonomous Vehicles | Data Analytics |

Rules:

- The first column should be the student name.
- Accepted name headers include `Name`, `Student`, and `Student Name`.
- Every remaining column is treated as a ranked project choice from left to right.
- Blank choice cells are skipped.
- Duplicate student names are auto-renamed with suffixes like `(2)`.

## Solver Notes

- Linear Programming is the recommended default.
- Genetic Algorithm can help on larger or awkwardly constrained inputs, but it is heuristic and may not be globally optimal.
- Brute Force is exact, but only practical for very small class sizes.

Every student is assigned to exactly one project. Projects can remain empty when their minimum seat count is `0`.

## Running Tests

```bash
pytest tests/
```

## Project Structure

```text
AI-FinalProject-Luminous-v2/
|-- app.py              # Launches the desktop application
|-- front_end.py        # Tkinter UI, file loading, results views, exports
|-- optimizer.py        # Linear programming, genetic, and brute-force solvers
|-- parser_module.py    # Preference file parsing and normalization
|-- requirements.txt
|-- sample_preferences.csv
|-- sample_preferences.txt
|-- tests/
|   |-- test_optimizer.py
|   `-- test_parser.py
|-- README.md
`-- ROBOTS.md
```

## Dependencies

- `pulp` for optimization
- Tkinter from the Python standard library for the desktop UI
