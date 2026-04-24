import csv
import io


def parse_preferences(content: str):
    """
    Parse a CSV or TXT file of student capstone preferences.

    Expected format (header row required):
        Name,Choice1,Choice2,Choice3,Choice4,Choice5,Choice6
        Alice,Project A,Project B,Project C,Project D,Project E,Project F

    The name column may be labeled: Name, Student, Student Name, etc.
    Choice columns may be labeled: Choice1..N, Rank1..N, or any other label
    that is not the name column. Values are ordered by preference (first = top choice).

    Supports comma, tab, and semicolon delimiters.

    Returns:
        students : list of {"name": str, "choices": [str, ...]}
        projects : set of all project name strings
    """
    content = content.strip()
    if not content:
        raise ValueError("File is empty")

    delimiter = _detect_delimiter(content)
    reader = csv.reader(io.StringIO(content), delimiter=delimiter)
    rows = [row for row in reader if any(cell.strip() for cell in row)]

    if len(rows) < 2:
        raise ValueError("File must have a header row and at least one student row")

    header = [h.strip() for h in rows[0]]
    name_col = _find_name_column(header)

    choice_cols = [i for i in range(len(header)) if i != name_col]

    students = []
    all_projects: set = set()
    seen_names: dict = {}

    for row in rows[1:]:
        while len(row) < len(header):
            row.append("")

        name = row[name_col].strip()
        if not name:
            continue

        # Deduplicate names
        if name in seen_names:
            seen_names[name] += 1
            name = f"{name} ({seen_names[name]})"
        else:
            seen_names[name] = 1

        choices = []
        for col in choice_cols:
            val = row[col].strip() if col < len(row) else ""
            if val:
                choices.append(val)
                all_projects.add(val)

        students.append({"name": name, "choices": choices})

    return students, all_projects


def _detect_delimiter(content: str) -> str:
    # Sample up to the first 5 non-empty lines so a sparse header doesn't
    # throw off the count.
    lines = [ln for ln in content.split("\n") if ln.strip()][:5]
    sample = "\n".join(lines)
    counts = {
        ",":  sample.count(","),
        "\t": sample.count("\t"),
        ";":  sample.count(";"),
    }
    return max(counts, key=counts.get)


def _find_name_column(header: list) -> int:
    name_keywords = {"name", "student", "student name", "studentname"}
    for i, h in enumerate(header):
        if h.lower().strip() in name_keywords:
            return i
    return 0
