from __future__ import annotations

import csv
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from optimizer import SUPPORTED_TECHNIQUES, optimize_assignments
from parser_module import parse_preferences


class ScrollableFrame(ttk.Frame):
    def __init__(self, master: tk.Misc, **kwargs) -> None:
        super().__init__(master, **kwargs)
        canvas = tk.Canvas(self, highlightthickness=0, background="#f5efe6")
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=canvas.yview)
        self.inner = ttk.Frame(canvas)

        self.inner.bind(
            "<Configure>",
            lambda event: canvas.configure(scrollregion=canvas.bbox("all")),
        )

        window = canvas.create_window((0, 0), window=self.inner, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        def resize_inner(event: tk.Event) -> None:
            canvas.itemconfigure(window, width=event.width)

        canvas.bind("<Configure>", resize_inner)

        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)


class CapstoneDesktopApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Capstone Project Matcher")
        self.root.geometry("1380x900")
        self.root.minsize(1180, 760)
        self.root.configure(bg="#f5efe6")

        self.students: list[dict[str, list[str] | str]] = []
        self.projects: list[str] = []
        self.last_result: dict | None = None
        self.project_inputs: dict[str, dict[str, tk.StringVar | ttk.Label]] = {}

        supported = sorted(SUPPORTED_TECHNIQUES.items(), key=lambda item: item[1])
        self.technique_labels = {label: key for key, label in supported}

        first_label = supported[0][1] if supported else "Linear Programming"
        self.file_var = tk.StringVar(value="No file selected")
        self.status_var = tk.StringVar(value="Upload a student preference file to begin.")
        self.summary_var = tk.StringVar(value="Results will appear here after you run the optimizer.")
        self.technique_var = tk.StringVar(value=first_label)
        self.default_max_var = tk.StringVar(value="5")

        self._configure_style()
        self._build_ui()

    def _configure_style(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TFrame", background="#f5efe6")
        style.configure("Card.TFrame", background="#fffaf4")
        style.configure("Sidebar.TFrame", background="#18324a")
        style.configure("Title.TLabel", background="#f5efe6", foreground="#18324a", font=("Georgia", 24, "bold"))
        style.configure("Body.TLabel", background="#f5efe6", foreground="#4c5b66", font=("Segoe UI", 10))
        style.configure("CardTitle.TLabel", background="#fffaf4", foreground="#18324a", font=("Georgia", 14, "bold"))
        style.configure("CardBody.TLabel", background="#fffaf4", foreground="#55646f", font=("Segoe UI", 10))
        style.configure("SidebarTitle.TLabel", background="#18324a", foreground="#f8f1e7", font=("Georgia", 18, "bold"))
        style.configure("SidebarBody.TLabel", background="#18324a", foreground="#dce7ef", font=("Segoe UI", 10))
        style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"))
        style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
        style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(0, weight=1)

        self._build_sidebar()
        self._build_content()

    def _build_sidebar(self) -> None:
        sidebar = ttk.Frame(self.root, style="Sidebar.TFrame", padding=22)
        sidebar.grid(row=0, column=0, sticky="nsew")
        sidebar.configure(width=280)

        ttk.Label(sidebar, text="Desktop Matcher", style="SidebarTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            sidebar,
            text="A native desktop front end for your teammate's parser and optimization algorithm.",
            style="SidebarBody.TLabel",
            wraplength=220,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(10, 22))

        steps = [
            "1. Upload a .csv or .txt file with student rankings.",
            "2. Review the detected students and projects.",
            "3. Set minimum and maximum seats for each project.",
            "4. Run the optimizer and export the assignments.",
        ]
        for index, step in enumerate(steps, start=2):
            ttk.Label(
                sidebar,
                text=step,
                style="SidebarBody.TLabel",
                wraplength=220,
                justify="left",
            ).grid(row=index, column=0, sticky="w", pady=5)

    def _build_content(self) -> None:
        content = ttk.Frame(self.root, padding=(24, 20))
        content.grid(row=0, column=1, sticky="nsew")
        content.columnconfigure(0, weight=1)
        content.rowconfigure(2, weight=1)
        content.rowconfigure(3, weight=1)

        ttk.Label(content, text="Capstone Project Matcher", style="Title.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            content,
            text="Desktop workflow for parsing preference files and running the existing backend optimizer.",
            style="Body.TLabel",
        ).grid(row=1, column=0, sticky="w", pady=(4, 16))

        top = ttk.Frame(content)
        top.grid(row=2, column=0, sticky="nsew")
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, weight=1)
        top.rowconfigure(0, weight=1)

        self._build_file_card(top)
        self._build_controls_card(top)

        bottom = ttk.Frame(content)
        bottom.grid(row=3, column=0, sticky="nsew", pady=(12, 0))
        bottom.columnconfigure(0, weight=1)
        bottom.columnconfigure(1, weight=1)
        bottom.rowconfigure(0, weight=1)

        self._build_constraints_card(bottom)
        self._build_results_card(bottom)

    def _build_file_card(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=18)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(3, weight=1)

        ttk.Label(card, text="Student Preferences", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            card,
            text="Supports the same CSV/TXT format your current parser expects: first column is the student name and the remaining columns are ranked choices.",
            style="CardBody.TLabel",
            wraplength=480,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(6, 14))

        bar = ttk.Frame(card, style="Card.TFrame")
        bar.grid(row=2, column=0, sticky="ew")
        bar.columnconfigure(0, weight=1)

        ttk.Label(bar, textvariable=self.file_var, style="CardBody.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(bar, text="Choose File", style="Accent.TButton", command=self._load_file).grid(row=0, column=1)

        self.preview_tree = ttk.Treeview(card, columns=("name", "choices"), show="headings", height=10)
        self.preview_tree.heading("name", text="Student")
        self.preview_tree.heading("choices", text="Ranked Choices")
        self.preview_tree.column("name", width=180, anchor="w")
        self.preview_tree.column("choices", width=420, anchor="w")
        self.preview_tree.grid(row=3, column=0, sticky="nsew", pady=(14, 0))

    def _build_controls_card(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=18)
        card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        card.columnconfigure(0, weight=1)

        ttk.Label(card, text="Run Optimizer", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            card,
            text="This desktop app talks directly to the existing Python optimizer module rather than a Flask server.",
            style="CardBody.TLabel",
            wraplength=420,
            justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(6, 14))

        ttk.Label(card, text="Technique", style="CardBody.TLabel").grid(row=2, column=0, sticky="w")
        self.technique_box = ttk.Combobox(
            card,
            textvariable=self.technique_var,
            state="readonly",
            values=list(self.technique_labels.keys()),
        )
        self.technique_box.grid(row=3, column=0, sticky="ew", pady=(4, 12))

        defaults = ttk.Frame(card, style="Card.TFrame")
        defaults.grid(row=4, column=0, sticky="ew", pady=(0, 12))
        ttk.Label(defaults, text="Default max seats", style="CardBody.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(defaults, textvariable=self.default_max_var, width=8).grid(row=0, column=1, padx=(10, 10))
        ttk.Button(defaults, text="Apply To All", command=self._apply_default_max).grid(row=0, column=2)

        action_row = ttk.Frame(card, style="Card.TFrame")
        action_row.grid(row=5, column=0, sticky="w", pady=(6, 8))
        ttk.Button(action_row, text="Run Assignment", style="Accent.TButton", command=self._run_optimizer).grid(
            row=0, column=0, padx=(0, 10)
        )
        ttk.Button(action_row, text="Export CSV", command=self._export_results).grid(row=0, column=1)

        ttk.Label(card, textvariable=self.status_var, style="CardBody.TLabel", wraplength=420, justify="left").grid(
            row=6, column=0, sticky="w", pady=(8, 0)
        )

    def _build_constraints_card(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=18)
        card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)

        ttk.Label(card, text="Project Constraints", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")

        self.constraints_frame = ScrollableFrame(card)
        self.constraints_frame.grid(row=1, column=0, sticky="nsew", pady=(12, 0))
        self.constraints_frame.inner.columnconfigure(0, weight=1)

        headers = ttk.Frame(self.constraints_frame.inner, style="Card.TFrame")
        headers.grid(row=0, column=0, sticky="ew", pady=(0, 6))
        headers.columnconfigure(0, weight=1)
        ttk.Label(headers, text="Project", style="CardBody.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(headers, text="Interest", style="CardBody.TLabel").grid(row=0, column=1, padx=12)
        ttk.Label(headers, text="Min", style="CardBody.TLabel").grid(row=0, column=2, padx=12)
        ttk.Label(headers, text="Max", style="CardBody.TLabel").grid(row=0, column=3, padx=12)

    def _build_results_card(self, parent: ttk.Frame) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=18)
        card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(2, weight=1)
        card.rowconfigure(4, weight=1)

        ttk.Label(card, text="Results", style="CardTitle.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(card, textvariable=self.summary_var, style="CardBody.TLabel", wraplength=480, justify="left").grid(
            row=1, column=0, sticky="w", pady=(6, 12)
        )

        self.assignment_tree = ttk.Treeview(card, columns=("student", "project", "rank"), show="headings", height=10)
        self.assignment_tree.heading("student", text="Student")
        self.assignment_tree.heading("project", text="Assigned Project")
        self.assignment_tree.heading("rank", text="Preference Rank")
        self.assignment_tree.column("student", width=180, anchor="w")
        self.assignment_tree.column("project", width=200, anchor="w")
        self.assignment_tree.column("rank", width=110, anchor="center")
        self.assignment_tree.grid(row=2, column=0, sticky="nsew")

        ttk.Label(card, text="Project Groups", style="CardTitle.TLabel").grid(row=3, column=0, sticky="w", pady=(16, 8))

        self.group_tree = ttk.Treeview(card, columns=("project", "count", "members"), show="headings", height=8)
        self.group_tree.heading("project", text="Project")
        self.group_tree.heading("count", text="Students")
        self.group_tree.heading("members", text="Members")
        self.group_tree.column("project", width=180, anchor="w")
        self.group_tree.column("count", width=80, anchor="center")
        self.group_tree.column("members", width=240, anchor="w")
        self.group_tree.grid(row=4, column=0, sticky="nsew")

    def _load_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose student preference file",
            filetypes=[("Data Files", "*.csv *.txt"), ("CSV Files", "*.csv"), ("Text Files", "*.txt")],
        )
        if not path:
            return

        file_path = Path(path)
        try:
            content = file_path.read_text(encoding="utf-8-sig")
            students, projects = parse_preferences(content)
        except Exception as exc:
            messagebox.showerror("Parse error", str(exc))
            self.status_var.set("The selected file could not be parsed.")
            return

        if not students:
            messagebox.showwarning("No students found", "The file did not contain any usable student preference rows.")
            return

        self.students = students
        self.projects = sorted(projects)
        self.last_result = None
        self.file_var.set(file_path.name)
        self.status_var.set(f"Loaded {len(self.students)} students and {len(self.projects)} projects.")
        self.summary_var.set("Review project seat limits, then run the optimizer.")

        self._populate_preview()
        self._populate_constraints()
        self._clear_tree(self.assignment_tree)
        self._clear_tree(self.group_tree)

    def _populate_preview(self) -> None:
        self._clear_tree(self.preview_tree)
        for student in self.students[:40]:
            joined = " | ".join(student["choices"])
            self.preview_tree.insert("", "end", values=(student["name"], joined))

    def _populate_constraints(self) -> None:
        for child in list(self.constraints_frame.inner.winfo_children())[1:]:
            child.destroy()

        self.project_inputs.clear()

        interest = {project: 0 for project in self.projects}
        for student in self.students:
            for project in student["choices"]:
                if project in interest:
                    interest[project] += 1

        default_max = self._safe_positive_int(self.default_max_var.get(), fallback=5)

        for row_index, project in enumerate(self.projects, start=1):
            row = ttk.Frame(self.constraints_frame.inner, style="Card.TFrame")
            row.grid(row=row_index, column=0, sticky="ew", pady=4)
            row.columnconfigure(0, weight=1)

            min_var = tk.StringVar(value="0")
            max_var = tk.StringVar(value=str(default_max))

            ttk.Label(row, text=project, style="CardBody.TLabel").grid(row=0, column=0, sticky="w")
            ttk.Label(row, text=str(interest[project]), style="CardBody.TLabel").grid(row=0, column=1, padx=12)
            ttk.Entry(row, textvariable=min_var, width=8).grid(row=0, column=2, padx=12)
            ttk.Entry(row, textvariable=max_var, width=8).grid(row=0, column=3, padx=12)

            self.project_inputs[project] = {"min": min_var, "max": max_var}

    def _apply_default_max(self) -> None:
        default_max = self._safe_positive_int(self.default_max_var.get(), fallback=None)
        if default_max is None:
            messagebox.showwarning("Invalid value", "Default max seats must be a positive integer.")
            return

        for vars_for_project in self.project_inputs.values():
            vars_for_project["max"].set(str(default_max))

        self.status_var.set(f"Applied max seats = {default_max} to all projects.")

    def _gather_constraints(self) -> dict[str, dict[str, int]] | None:
        constraints: dict[str, dict[str, int]] = {}

        for project, vars_for_project in self.project_inputs.items():
            min_value = self._safe_non_negative_int(vars_for_project["min"].get())
            max_value = self._safe_positive_int(vars_for_project["max"].get(), fallback=None)

            if min_value is None or max_value is None:
                messagebox.showerror("Invalid constraints", f"Project '{project}' has a non-numeric seat value.")
                return None

            if min_value > max_value:
                messagebox.showerror(
                    "Invalid constraints",
                    f"Project '{project}' has a minimum greater than its maximum.",
                )
                return None

            constraints[project] = {"min": min_value, "max": max_value}

        return constraints

    def _run_optimizer(self) -> None:
        if not self.students or not self.projects:
            messagebox.showinfo("Missing file", "Load a student preference file before running the optimizer.")
            return

        constraints = self._gather_constraints()
        if constraints is None:
            return

        technique_label = self.technique_var.get()
        technique_key = self.technique_labels.get(technique_label)
        if not technique_key:
            messagebox.showerror("Technique error", "No supported optimization technique is selected.")
            return

        total_min = sum(item["min"] for item in constraints.values())
        if total_min > len(self.students):
            messagebox.showerror(
                "Constraint error",
                f"Project minimums total {total_min}, but only {len(self.students)} students are loaded.",
            )
            return

        if technique_key == "brute_force" and len(self.students) > 12:
            confirmed = messagebox.askyesno(
                "Performance warning",
                f"Brute Force with {len(self.students)} students may take a very long time.\n\n"
                "Consider using Linear Programming or Genetic Algorithm for faster results.\n\n"
                "Continue anyway?",
            )
            if not confirmed:
                return

        try:
            result = optimize_assignments(self.students, constraints, technique=technique_key)
        except Exception as exc:
            messagebox.showerror("Optimizer error", str(exc))
            self.status_var.set("The backend optimizer raised an exception.")
            return

        if "error" in result:
            messagebox.showerror("Optimization failed", result["error"])
            self.status_var.set(result["error"])
            return

        self.last_result = result
        self.status_var.set(f"Optimization completed using {result['stats'].get('technique_label', technique_label)}.")
        self._render_results(result)

    def _render_results(self, result: dict) -> None:
        assignments = result.get("assignments", {})
        groups = result.get("project_groups", {})
        stats = result.get("stats", {})

        self._clear_tree(self.assignment_tree)
        self._clear_tree(self.group_tree)

        for student_name in sorted(assignments):
            info = assignments[student_name]
            rank = info.get("rank")
            rank_text = f"Choice {rank}" if rank else "Outside choices"
            self.assignment_tree.insert("", "end", values=(student_name, info["project"], rank_text))

        for project_name in sorted(groups):
            members = groups[project_name]
            self.group_tree.insert("", "end", values=(project_name, len(members), ", ".join(members)))

        rank_counts = stats.get("rank_counts", {})
        first_choice = rank_counts.get("1", 0)
        top_three = sum(rank_counts.get(str(rank), 0) for rank in range(1, 4))
        total_students = stats.get("total_students", len(assignments))
        summary = (
            f"{stats.get('technique_label', self.technique_var.get())} assigned {total_students} students. "
            f"First-choice matches: {first_choice}. Top-3 matches: {top_three}. "
            f"Outside listed preferences: {stats.get('unranked_count', 0)}. "
            f"Objective score: {stats.get('objective_value', 0)}."
        )
        self.summary_var.set(summary)

    def _export_results(self) -> None:
        if not self.last_result:
            messagebox.showinfo("No results", "Run the optimizer before exporting a CSV.")
            return

        path = filedialog.asksaveasfilename(
            title="Export assignments",
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv")],
        )
        if not path:
            return

        assignments = self.last_result.get("assignments", {})
        with Path(path).open("w", encoding="utf-8", newline="") as file_handle:
            writer = csv.writer(file_handle)
            writer.writerow(["Student Name", "Assigned Project", "Preference Rank"])
            for student_name in sorted(assignments):
                info = assignments[student_name]
                rank = info.get("rank")
                writer.writerow(
                    [
                        student_name,
                        info["project"],
                        f"Choice {rank}" if rank else "Outside listed choices",
                    ]
                )

        self.status_var.set(f"Exported assignments to {Path(path).name}.")

    def _clear_tree(self, tree: ttk.Treeview) -> None:
        for item in tree.get_children():
            tree.delete(item)

    def _safe_non_negative_int(self, value: str) -> int | None:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return None
        return parsed if parsed >= 0 else None

    def _safe_positive_int(self, value: str, fallback: int | None) -> int | None:
        try:
            parsed = int(value)
        except (TypeError, ValueError):
            return fallback
        return parsed if parsed > 0 else fallback


def main() -> None:
    root = tk.Tk()
    CapstoneDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
