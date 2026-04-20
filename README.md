# Capstone Project Matcher

A web application that uses **Integer Linear Programming** to optimally assign students to capstone projects based on their ranked preferences, maximizing the number of students who receive a top-choice project.

Built for the ECCS Capstone Assignment workflow.

---

## Features

- Upload student preferences via `.csv` or `.txt` file
- Configure per-project minimum and maximum capacity constraints
- ILP optimizer (PuLP/CBC) maximizes total preference satisfaction
- Visual results: doughnut chart, ranked assignment table, project group cards
- Export final assignments to CSV

---

## Requirements

- Python 3.10+
- pip

---

## Installation

```bash
git clone https://github.com/quintonfesq04/ai-final-project.git
cd ai-final-project
pip install -r requirements.txt
```

---

## Running the App

```bash
python app.py
```

Then open [http://localhost:5000](http://localhost:5000) in your browser.

---

## Input File Format

Upload a `.csv` or `.txt` file with the following structure:

| Name         | Choice1             | Choice2  | Choice3     | Choice4      | Choice5    | Choice6       |
|--------------|---------------------|----------|-------------|--------------|------------|---------------|
| Alice Johnson | Autonomous Vehicles | Robotics | AI Research | Cybersecurity | IoT Systems | Data Analytics |
| Bob Smith    | Robotics            | AI Research | Autonomous Vehicles | Data Analytics | IoT Systems | Cybersecurity |

- **First column**: student name (header may be `Name`, `Student`, or `Student Name`)
- **Remaining columns**: project choices in preference order (most preferred first)
- Supports comma, tab, and semicolon delimiters
- Students must provide **up to 6 choices** out of 20–30 available projects

A downloadable template is available in the app UI.

---

## Running Tests

```bash
pip install pytest
pytest tests/
```

---

## Project Structure

```
ai-final-project/
├── app.py              # Flask web server and API routes
├── optimizer.py        # ILP optimization logic (PuLP)
├── parser_module.py    # CSV/TXT file parser
├── requirements.txt
├── templates/
│   └── index.html      # Single-page frontend
├── static/
│   ├── css/style.css
│   └── js/main.js
├── tests/
│   ├── test_optimizer.py
│   └── test_parser.py
├── README.md
└── ROBOTS.md
```

---

## AI Tools Used

This project was built using **Claude Code** (Anthropic) as the primary AI agent for code generation, architecture decisions, and implementation. All generated code was reviewed and validated by the development team.

- **Claude Sonnet 4.6** — agentic code generation via Claude Code CLI
- **PuLP** — open-source linear programming library (CBC solver)
- **Flask** — Python web framework
- **Bootstrap 5 / Chart.js** — frontend UI components (CDN)
