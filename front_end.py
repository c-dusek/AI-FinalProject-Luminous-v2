"""Tkinter desktop interface for the Capstone Project Matcher."""

from __future__ import annotations

import csv
import threading
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from optimizer import SUPPORTED_TECHNIQUES, optimize_assignments
from parser_module import parse_preferences

# ── colour palette ────────────────────────────────────────────────────────────
_BG      = "#f1f5f9"
_SIDEBAR = "#1e3a5f"
_CARD    = "#ffffff"
_T1      = "#111827"
_T2      = "#374151"
_T3      = "#6b7280"
_BORDER  = "#e5e7eb"
_OK      = "#16a34a"
_WARN    = "#d97706"
_ERR     = "#dc2626"

# background / foreground per preference rank for treeview row tags
_RANK_ROW: dict[str, tuple[str, str]] = {
    "1": ("#dcfce7", "#166534"),
    "2": ("#dbeafe", "#1e40af"),
    "3": ("#ede9fe", "#5b21b6"),
    "4": ("#fef9c3", "#854d0e"),
    "5": ("#ffedd5", "#9a3412"),
    "6": ("#fee2e2", "#991b1b"),
}
_OUT_BG, _OUT_FG = "#f3f4f6", _T2

# sidebar descriptions per algorithm
_ALGO_INFO: dict[str, str] = {
    "Linear Programming": (
        "Finds the mathematically optimal assignment every time. "
        "Uses Integer Linear Programming (PuLP/CBC). "
        "Fast for typical class sizes (≤300 students). Recommended default."
    ),
    "Genetic Algorithm": (
        "Heuristic evolutionary search. Handles large or tightly "
        "constrained inputs well. May not be globally optimal but "
        "usually gets very close. Good fallback when LP is slow."
    ),
    "Brute Force": (
        "Exhaustive backtracking — guaranteed optimal but only "
        "practical for ≤12 students. Use LP or GA for larger classes."
    ),
}

_SPINNER = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]


# ── small utilities ───────────────────────────────────────────────────────────

def _safe_nn(v: str) -> int | None:
    """Parse a non-negative integer, return None on failure."""
    try:
        n = int(v)
        return n if n >= 0 else None
    except (TypeError, ValueError):
        return None


def _safe_pos(v: str) -> int | None:
    """Parse a positive integer, return None on failure."""
    try:
        n = int(v)
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


def _clear(tree: ttk.Treeview) -> None:
    """Remove every row from a Treeview widget."""
    tree.delete(*tree.get_children())


def _make_tree(
    parent: tk.Widget,
    cols: list[tuple[str, str, int, str]],
    height: int = 10,
) -> ttk.Treeview:
    """
    Build a Treeview with an attached vertical scrollbar inside *parent*.
    *parent* should be a Frame that fills its allocated space.
    Columns: list of (col_id, heading_text, pixel_width, anchor).
    """
    parent.columnconfigure(0, weight=1)
    parent.rowconfigure(0, weight=1)

    vsb = ttk.Scrollbar(parent, orient="vertical")
    tree = ttk.Treeview(
        parent,
        columns=[c[0] for c in cols],
        show="headings",
        height=height,
        yscrollcommand=vsb.set,
    )
    vsb.configure(command=tree.yview)
    tree.grid(row=0, column=0, sticky="nsew")
    vsb.grid(row=0, column=1, sticky="ns")

    for cid, heading, width, anchor in cols:
        tree.heading(cid, text=heading,
                     command=lambda c=cid: _sort_col(tree, c, False))
        tree.column(cid, width=width, anchor=anchor, minwidth=40)

    return tree


def _sort_col(tree: ttk.Treeview, col: str, reverse: bool) -> None:
    """Sort a Treeview column, preferring numeric ordering when possible."""
    rows = [(tree.set(r, col), r) for r in tree.get_children("")]
    try:
        rows.sort(
            key=lambda x: int(x[0]) if str(x[0]).lstrip("-").isdigit() else x[0].lower(),
            reverse=reverse,
        )
    except Exception:
        rows.sort(reverse=reverse)
    for i, (_, r) in enumerate(rows):
        tree.move(r, "", i)
    tree.heading(col, command=lambda: _sort_col(tree, col, not reverse))


# ── scrollable frame ──────────────────────────────────────────────────────────

class _ScrollFrame(ttk.Frame):
    """Vertically scrollable frame with cross-platform mousewheel support."""

    def __init__(self, master: tk.Misc, **kw: object) -> None:
        super().__init__(master, **kw)
        self._cv = tk.Canvas(self, highlightthickness=0, bg=_CARD)
        _vsb = ttk.Scrollbar(self, orient="vertical", command=self._cv.yview)
        self.inner = ttk.Frame(self._cv, style="Card.TFrame")

        self.inner.bind(
            "<Configure>",
            lambda e: self._cv.configure(scrollregion=self._cv.bbox("all")),
        )
        _win = self._cv.create_window((0, 0), window=self.inner, anchor="nw")
        self._cv.configure(yscrollcommand=_vsb.set)
        self._cv.bind(
            "<Configure>",
            lambda e: self._cv.itemconfigure(_win, width=e.width),
        )

        self._cv.grid(row=0, column=0, sticky="nsew")
        _vsb.grid(row=0, column=1, sticky="ns")
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        # Activate/deactivate mousewheel when cursor enters/leaves
        for w in (self._cv, self.inner):
            w.bind("<Enter>", self._bind_wheel)
            w.bind("<Leave>", self._unbind_wheel)

    def _bind_wheel(self, _: tk.Event) -> None:
        self._cv.bind_all("<MouseWheel>", self._on_wheel)
        self._cv.bind_all("<Button-4>", lambda e: self._cv.yview_scroll(-1, "units"))
        self._cv.bind_all("<Button-5>", lambda e: self._cv.yview_scroll(1, "units"))

    def _unbind_wheel(self, _: tk.Event) -> None:
        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self._cv.unbind_all(seq)

    def _on_wheel(self, event: tk.Event) -> None:
        delta = event.delta
        # macOS sends small deltas (1-3); Windows sends multiples of 120
        units = -int(delta / 120) if abs(delta) >= 10 else -int(delta)
        self._cv.yview_scroll(units, "units")


# ── rank distribution bar chart ───────────────────────────────────────────────

class _RankChart(tk.Canvas):
    """Horizontal bar chart of preference rank distribution, drawn on a Canvas."""

    _LEFT  = 120   # px reserved for labels on the left
    _BAR_H = 22
    _GAP   = 6

    def draw(self, rank_counts: dict, unranked: int, total: int) -> None:
        self.delete("all")
        if not total:
            self.create_text(
                10, 20, text="No data yet.", anchor="nw",
                font=("Segoe UI", 10), fill=_T3,
            )
            return

        rows: list[tuple[str, int, str]] = []
        for r in range(1, 10):
            cnt = rank_counts.get(str(r), 0)
            if cnt:
                bg, _ = _RANK_ROW.get(str(r), (_OUT_BG, _OUT_FG))
                rows.append((f"Choice {r}", cnt, bg))
        if unranked:
            rows.append(("Outside prefs", unranked, _OUT_BG))

        needed_h = len(rows) * (self._BAR_H + self._GAP) + 30
        self.configure(height=max(needed_h, 80))
        self.update_idletasks()
        w = max(self.winfo_width(), 300)
        bar_area = w - self._LEFT - 110  # 110px right margin for count labels

        y = 14
        for label, cnt, bg in rows:
            pct = cnt / total
            fill_px = max(int(pct * bar_area), 3)
            # row label
            self.create_text(
                self._LEFT - 8, y + self._BAR_H // 2,
                text=label, anchor="e",
                font=("Segoe UI", 9), fill=_T2,
            )
            # background track
            self.create_rectangle(
                self._LEFT, y,
                self._LEFT + bar_area, y + self._BAR_H,
                fill="#f3f4f6", outline=_BORDER,
            )
            # filled bar
            self.create_rectangle(
                self._LEFT, y,
                self._LEFT + fill_px, y + self._BAR_H,
                fill=bg, outline="",
            )
            # count + percent label
            self.create_text(
                self._LEFT + fill_px + 6, y + self._BAR_H // 2,
                text=f"{cnt}  ({pct:.0%})",
                anchor="w", font=("Segoe UI", 9), fill=_T2,
            )
            y += self._BAR_H + self._GAP


# ── main application ──────────────────────────────────────────────────────────

class CapstoneDesktopApp:
    """Main desktop window and controller for the assignment workflow."""

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Capstone Project Matcher")
        self.root.geometry("1440x900")
        self.root.minsize(1100, 720)
        self.root.configure(bg=_BG)

        # ── application state ──────────────────────────────────────────
        self.students:       list[dict]                           = []
        self.projects:       list[str]                            = []
        self.last_result:    dict | None                          = None
        self.project_inputs: dict[str, dict[str, tk.StringVar]]  = {}
        self._running        = False
        self._spinner_idx    = 0

        supported = sorted(SUPPORTED_TECHNIQUES.items(), key=lambda kv: kv[1])
        self._tech_labels    = {label: key for key, label in supported}
        first_label          = supported[0][1] if supported else "Linear Programming"

        self.file_var        = tk.StringVar(value="No file loaded")
        self.status_var      = tk.StringVar(value="Load a preference file to begin.")
        self.technique_var   = tk.StringVar(value=first_label)
        self.default_min_var = tk.StringVar(value="1")
        self.default_max_var = tk.StringVar(value="6")

        self.technique_var.trace_add("write", lambda *_: self._refresh_algo_info())

        self._configure_styles()
        self._build_ui()
        self._bind_shortcuts()

    # ── ttk styles ────────────────────────────────────────────────────────────

    def _configure_styles(self) -> None:
        s = ttk.Style()
        s.theme_use("clam")

        s.configure("TFrame",           background=_BG)
        s.configure("Card.TFrame",      background=_CARD)
        s.configure("Sidebar.TFrame",   background=_SIDEBAR)
        s.configure("Status.TFrame",    background=_BORDER)
        s.configure("Tab.TFrame",       background=_CARD)

        # labels
        s.configure("H1.TLabel",        background=_BG,      foreground=_T1,
                    font=("Segoe UI", 18, "bold"))
        s.configure("Sub.TLabel",       background=_BG,      foreground=_T3,
                    font=("Segoe UI", 10))
        s.configure("CardH.TLabel",     background=_CARD,    foreground=_T1,
                    font=("Segoe UI", 12, "bold"))
        s.configure("CardBody.TLabel",  background=_CARD,    foreground=_T2,
                    font=("Segoe UI", 10))
        s.configure("CardMeta.TLabel",  background=_CARD,    foreground=_T3,
                    font=("Segoe UI", 9))
        s.configure("CardOK.TLabel",    background=_CARD,    foreground=_OK,
                    font=("Segoe UI", 10, "bold"))
        s.configure("CardWarn.TLabel",  background=_CARD,    foreground=_WARN,
                    font=("Segoe UI", 10))
        s.configure("SBH.TLabel",       background=_SIDEBAR, foreground="#f8fafc",
                    font=("Segoe UI", 13, "bold"))
        s.configure("SBBody.TLabel",    background=_SIDEBAR, foreground="#cbd5e1",
                    font=("Segoe UI", 9))
        s.configure("SBStep.TLabel",    background=_SIDEBAR, foreground="#e2e8f0",
                    font=("Segoe UI", 10, "bold"))
        s.configure("Status.TLabel",    background=_BORDER,  foreground=_T2,
                    font=("Segoe UI", 9))
        s.configure("StatNum.TLabel",   background=_CARD,    foreground=_T1,
                    font=("Segoe UI", 22, "bold"))
        s.configure("StatLbl.TLabel",   background=_CARD,    foreground=_T3,
                    font=("Segoe UI", 9))

        # buttons
        s.configure("Accent.TButton",   font=("Segoe UI", 10, "bold"))

        # treeview
        s.configure("Treeview",
                    rowheight=26, font=("Segoe UI", 10),
                    background=_CARD, fieldbackground=_CARD, foreground=_T1)
        s.configure("Treeview.Heading",
                    font=("Segoe UI", 10, "bold"),
                    background="#f8fafc", foreground=_T1)
        s.map("Treeview",
              background=[("selected", "#bfdbfe")],
              foreground=[("selected", _T1)])

        # notebook
        s.configure("TNotebook",        background=_CARD)
        s.configure("TNotebook.Tab",    font=("Segoe UI", 10),
                    background="#f1f5f9", foreground=_T2, padding=(12, 6))
        s.map("TNotebook.Tab",
              background=[("selected", _CARD)],
              foreground=[("selected", _T1)])

    # ── root layout ───────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # col 0 = fixed sidebar; col 1 = stretchy content
        # row 0 = header; row 1 = main (weight); row 2 = status bar
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(1, weight=1)

        self._build_sidebar()
        self._build_header()
        self._build_main()
        self._build_statusbar()

    # ── sidebar ───────────────────────────────────────────────────────────────

    def _build_sidebar(self) -> None:
        sb = ttk.Frame(self.root, style="Sidebar.TFrame", width=238)
        sb.grid(row=0, column=0, rowspan=3, sticky="nsew")
        sb.grid_propagate(False)   # enforce fixed width

        ttk.Label(sb, text="Capstone\nProject Matcher",
                  style="SBH.TLabel", justify="left",
                  ).pack(anchor="w", padx=18, pady=(24, 4))
        ttk.Label(sb,
                  text="Preference-based student\nassignment optimizer.",
                  style="SBBody.TLabel", justify="left",
                  ).pack(anchor="w", padx=18, pady=(0, 18))

        ttk.Separator(sb, orient="horizontal").pack(fill="x", padx=18, pady=(0, 14))

        steps = [
            ("Step 1 — Load file",
             "Upload a .csv or .txt with student\npreference rankings."),
            ("Step 2 — Set seat limits",
             "Configure min / max seats per project.\nDefaults are pre-filled."),
            ("Step 3 — Choose algorithm",
             "LP finds the global optimum.\nGA handles large/edge-case inputs."),
            ("Step 4 — Run & export",
             "Click Run Assignment, review the stats\ntab, then export to CSV."),
        ]
        for title, desc in steps:
            ttk.Label(sb, text=title, style="SBStep.TLabel",
                      ).pack(anchor="w", padx=18, pady=(10, 2))
            ttk.Label(sb, text=desc, style="SBBody.TLabel",
                      justify="left", wraplength=200,
                      ).pack(anchor="w", padx=18)

        ttk.Separator(sb, orient="horizontal").pack(fill="x", padx=18, pady=(18, 12))

        ttk.Label(sb, text="Algorithm info", style="SBStep.TLabel",
                  ).pack(anchor="w", padx=18, pady=(0, 4))
        self._algo_info_lbl = ttk.Label(
            sb, text="", style="SBBody.TLabel",
            justify="left", wraplength=200,
        )
        self._algo_info_lbl.pack(anchor="w", padx=18)
        self._refresh_algo_info()

    def _refresh_algo_info(self) -> None:
        """Keep the sidebar description synced with the selected algorithm."""
        label = self.technique_var.get()
        info  = _ALGO_INFO.get(label, "")
        self._algo_info_lbl.configure(text=info)

    # ── header bar ────────────────────────────────────────────────────────────

    def _build_header(self) -> None:
        hdr = ttk.Frame(self.root, padding=(20, 14, 20, 10))
        hdr.grid(row=0, column=1, sticky="ew")
        hdr.columnconfigure(1, weight=1)

        ttk.Label(hdr, text="Capstone Project Matcher",
                  style="H1.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            hdr,
            text="Integer-programming & heuristic optimizer for student–project assignment.",
            style="Sub.TLabel",
        ).grid(row=1, column=0, sticky="w")

        badge = ttk.Frame(hdr)
        badge.grid(row=0, column=1, rowspan=2, sticky="e")
        ttk.Label(badge, text="File loaded:  ", style="Sub.TLabel",
                  ).pack(side="left")
        ttk.Label(badge, textvariable=self.file_var, style="Sub.TLabel",
                  font=("Segoe UI", 10, "bold"),
                  ).pack(side="left")

    # ── main 2×2 card grid ────────────────────────────────────────────────────

    def _build_main(self) -> None:
        # The interface uses a 2x2 dashboard so inputs and results stay visible
        # together without forcing the user through separate screens.
        main = ttk.Frame(self.root, padding=(14, 4, 14, 8))
        main.grid(row=1, column=1, sticky="nsew")
        main.columnconfigure(0, weight=5, minsize=360)
        main.columnconfigure(1, weight=6, minsize=400)
        main.rowconfigure(0, weight=3, minsize=240)
        main.rowconfigure(1, weight=5)

        self._build_file_card(main)
        self._build_controls_card(main)
        self._build_constraints_card(main)
        self._build_results_card(main)

    def _build_statusbar(self) -> None:
        bar = ttk.Frame(self.root, style="Status.TFrame", height=28)
        bar.grid(row=2, column=0, columnspan=2, sticky="ew")
        bar.grid_propagate(False)
        ttk.Label(bar, textvariable=self.status_var,
                  style="Status.TLabel").pack(side="left", padx=12, pady=5)
        self._spin_lbl = ttk.Label(bar, text="", style="Status.TLabel")
        self._spin_lbl.pack(side="right", padx=12)

    # ── card helper ───────────────────────────────────────────────────────────

    def _card(self, parent: tk.Widget, row: int, col: int,
              padx: tuple = (0, 6), pady: tuple = (0, 6)) -> ttk.Frame:
        f = ttk.Frame(parent, style="Card.TFrame", padding=16)
        f.grid(row=row, column=col, sticky="nsew", padx=padx, pady=pady)
        return f

    # ── file card (top-left) ──────────────────────────────────────────────────

    def _build_file_card(self, parent: ttk.Frame) -> None:
        card = self._card(parent, 0, 0, padx=(0, 6), pady=(0, 6))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(3, weight=1)

        ttk.Label(card, text="Student Preferences",
                  style="CardH.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Label(
            card,
            text="CSV or TXT: first column = student name, remaining columns = ranked choices (left to right).",
            style="CardMeta.TLabel", wraplength=340, justify="left",
        ).grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 10))

        bar = ttk.Frame(card, style="Card.TFrame")
        bar.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 10))
        bar.columnconfigure(0, weight=1)
        ttk.Label(bar, textvariable=self.file_var,
                  style="CardMeta.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Button(bar, text="Choose File …", style="Accent.TButton",
                   command=self._load_file).grid(row=0, column=1)

        # scrolled preview treeview
        holder = ttk.Frame(card, style="Card.TFrame")
        holder.grid(row=3, column=0, columnspan=2, sticky="nsew")
        self.preview_tree = _make_tree(
            holder,
            [
                ("name",    "Student",                    160, "w"),
                ("choices", "Ranked Choices (preview)",   340, "w"),
            ],
            height=7,
        )

    # ── controls card (top-right) ─────────────────────────────────────────────

    def _build_controls_card(self, parent: ttk.Frame) -> None:
        card = self._card(parent, 0, 1, padx=(6, 0), pady=(0, 6))
        card.columnconfigure(0, weight=1)

        ttk.Label(card, text="Run Optimizer",
                  style="CardH.TLabel").grid(row=0, column=0, sticky="w", pady=(0, 4))

        # algorithm selector
        ttk.Label(card, text="Algorithm", style="CardBody.TLabel",
                  ).grid(row=1, column=0, sticky="w")
        self.technique_box = ttk.Combobox(
            card,
            textvariable=self.technique_var,
            state="readonly",
            values=list(self._tech_labels.keys()),
        )
        self.technique_box.grid(row=2, column=0, sticky="ew", pady=(4, 14))

        # default seat controls
        seats = ttk.Frame(card, style="Card.TFrame")
        seats.grid(row=3, column=0, sticky="ew", pady=(0, 14))
        seats.columnconfigure(1, weight=1)

        ttk.Label(seats, text="Default min seats",
                  style="CardBody.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Entry(seats, textvariable=self.default_min_var,
                  width=7).grid(row=0, column=1, padx=8, sticky="ew")
        ttk.Button(seats, text="Apply to all",
                   command=self._apply_default_min).grid(row=0, column=2)

        ttk.Label(seats, text="Default max seats",
                  style="CardBody.TLabel").grid(row=1, column=0, sticky="w",
                                                pady=(8, 0))
        ttk.Entry(seats, textvariable=self.default_max_var,
                  width=7).grid(row=1, column=1, padx=8, sticky="ew",
                                pady=(8, 0))
        ttk.Button(seats, text="Apply to all",
                   command=self._apply_default_max).grid(row=1, column=2,
                                                         pady=(8, 0))

        ttk.Separator(card, orient="horizontal").grid(
            row=4, column=0, sticky="ew", pady=(0, 12))

        # action buttons
        actions = ttk.Frame(card, style="Card.TFrame")
        actions.grid(row=5, column=0, sticky="w")
        self._run_btn = ttk.Button(
            actions, text="▶  Run Assignment",
            style="Accent.TButton", command=self._run_optimizer,
        )
        self._run_btn.grid(row=0, column=0, padx=(0, 10))
        ttk.Button(actions, text="Export CSV",
                   command=self._export_results).grid(row=0, column=1, padx=(0, 10))
        ttk.Button(actions, text="Export Groups CSV",
                   command=self._export_groups).grid(row=0, column=2)

        ttk.Label(card, text="Ctrl+O  open file    Ctrl+R  run    Ctrl+E  export",
                  style="CardMeta.TLabel").grid(row=6, column=0, sticky="w",
                                                pady=(12, 0))

    # ── constraints card (bottom-left) ────────────────────────────────────────

    def _build_constraints_card(self, parent: ttk.Frame) -> None:
        card = self._card(parent, 1, 0, padx=(0, 6), pady=(6, 0))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(2, weight=1)

        ttk.Label(card, text="Project Seat Limits",
                  style="CardH.TLabel").grid(row=0, column=0, sticky="w")
        ttk.Label(
            card,
            text="Each project must have min ≤ max.  "
                 "A project can be left empty (min = 0) if not needed.",
            style="CardMeta.TLabel", wraplength=340, justify="left",
        ).grid(row=1, column=0, sticky="w", pady=(4, 10))

        # scrollable constraint rows
        self._constraints_scroll = _ScrollFrame(card, style="Card.TFrame")
        self._constraints_scroll.grid(row=2, column=0, sticky="nsew")

        # sticky column header inside the scroll area
        hdr = ttk.Frame(self._constraints_scroll.inner, style="Card.TFrame")
        hdr.grid(row=0, column=0, sticky="ew", pady=(0, 4))
        hdr.columnconfigure(0, weight=1)
        ttk.Label(hdr, text="Project",   style="CardMeta.TLabel",
                  ).grid(row=0, column=0, sticky="w")
        ttk.Label(hdr, text="Interest",  style="CardMeta.TLabel",
                  ).grid(row=0, column=1, padx=(8, 8))
        ttk.Label(hdr, text="Min seats", style="CardMeta.TLabel",
                  ).grid(row=0, column=2, padx=(0, 8))
        ttk.Label(hdr, text="Max seats", style="CardMeta.TLabel",
                  ).grid(row=0, column=3, padx=(0, 4))

    # ── results card (bottom-right) ───────────────────────────────────────────

    def _build_results_card(self, parent: ttk.Frame) -> None:
        card = self._card(parent, 1, 1, padx=(6, 0), pady=(6, 0))
        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)

        ttk.Label(card, text="Results",
                  style="CardH.TLabel").grid(row=0, column=0, sticky="w",
                                             pady=(0, 8))

        nb = ttk.Notebook(card)
        nb.grid(row=1, column=0, sticky="nsew")

        self._build_assignments_tab(nb)
        self._build_groups_tab(nb)
        self._build_stats_tab(nb)

    def _build_assignments_tab(self, nb: ttk.Notebook) -> None:
        tab = ttk.Frame(nb, style="Card.TFrame", padding=6)
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(1, weight=1)
        nb.add(tab, text="  Assignments  ")

        self._assign_summary = ttk.Label(
            tab, text="Run the optimizer to see results.",
            style="CardMeta.TLabel", wraplength=480, justify="left",
        )
        self._assign_summary.grid(row=0, column=0, sticky="w", pady=(0, 6))

        holder = ttk.Frame(tab, style="Card.TFrame")
        holder.grid(row=1, column=0, sticky="nsew")
        self.assign_tree = _make_tree(
            holder,
            [
                ("student", "Student",          180, "w"),
                ("project", "Assigned Project", 200, "w"),
                ("rank",    "Rank",             110, "center"),
            ],
            height=12,
        )
        # configure rank colour tags
        self.assign_tree.tag_configure("outside", background=_OUT_BG, foreground=_OUT_FG)
        for key, (bg, fg) in _RANK_ROW.items():
            self.assign_tree.tag_configure(f"rank_{key}", background=bg, foreground=fg)

    def _build_groups_tab(self, nb: ttk.Notebook) -> None:
        tab = ttk.Frame(nb, style="Card.TFrame", padding=6)
        tab.columnconfigure(0, weight=1)
        tab.rowconfigure(0, weight=1)
        nb.add(tab, text="  Project Groups  ")

        holder = ttk.Frame(tab, style="Card.TFrame")
        holder.grid(row=0, column=0, sticky="nsew")
        self.groups_tree = _make_tree(
            holder,
            [
                ("project", "Project",  180, "w"),
                ("count",   "Students",  80, "center"),
                ("members", "Members",  340, "w"),
            ],
            height=14,
        )

    def _build_stats_tab(self, nb: ttk.Notebook) -> None:
        tab = ttk.Frame(nb, style="Card.TFrame", padding=(10, 10))
        tab.columnconfigure(0, weight=1)
        tab.columnconfigure(1, weight=1)
        tab.columnconfigure(2, weight=1)
        tab.columnconfigure(3, weight=1)
        tab.rowconfigure(1, weight=1)
        nb.add(tab, text="  Statistics  ")

        # ── stat boxes row ─────────────────────────────────────────────
        stat_cols = [
            ("_stat_total",   "Total students"),
            ("_stat_first",   "Got 1st choice"),
            ("_stat_top3",    "Top-3 match"),
            ("_stat_outside", "Outside prefs"),
        ]
        for col_idx, (attr, lbl_text) in enumerate(stat_cols):
            box = ttk.Frame(tab, style="Card.TFrame", padding=10,
                            relief="solid", borderwidth=1)
            box.grid(row=0, column=col_idx, sticky="ew",
                     padx=(0 if col_idx == 0 else 6, 0), pady=(0, 12))
            num_lbl = ttk.Label(box, text="—", style="StatNum.TLabel")
            num_lbl.pack()
            ttk.Label(box, text=lbl_text, style="StatLbl.TLabel").pack()
            setattr(self, attr, num_lbl)

        # ── bar chart ──────────────────────────────────────────────────
        chart_holder = ttk.Frame(tab, style="Card.TFrame")
        chart_holder.grid(row=1, column=0, columnspan=4, sticky="nsew")
        chart_holder.columnconfigure(0, weight=1)
        chart_holder.rowconfigure(0, weight=1)
        self._rank_chart = _RankChart(chart_holder, bg=_CARD, bd=0,
                                      highlightthickness=0)
        self._rank_chart.pack(fill="both", expand=True)

        # ── objective + technique line ─────────────────────────────────
        self._stat_footer = ttk.Label(
            tab, text="", style="CardMeta.TLabel",
        )
        self._stat_footer.grid(row=2, column=0, columnspan=4, sticky="w",
                               pady=(8, 0))

    # ── keyboard shortcuts ────────────────────────────────────────────────────

    def _bind_shortcuts(self) -> None:
        self.root.bind_all("<Control-o>", lambda e: self._load_file())
        self.root.bind_all("<Control-r>", lambda e: self._run_optimizer())
        self.root.bind_all("<Control-e>", lambda e: self._export_results())

    # ── file loading ──────────────────────────────────────────────────────────

    def _load_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Choose student preference file",
            filetypes=[
                ("Data files", "*.csv *.txt"),
                ("CSV files",  "*.csv"),
                ("Text files", "*.txt"),
            ],
        )
        if not path:
            return

        fp = Path(path)
        try:
            # utf-8-sig strips a BOM automatically, which is common in files
            # exported from spreadsheet tools.
            content          = fp.read_text(encoding="utf-8-sig")
            students, projs  = parse_preferences(content)
        except Exception as exc:
            messagebox.showerror("Parse error", str(exc))
            self.status_var.set("File could not be parsed.")
            return

        if not students:
            messagebox.showwarning("Empty file",
                                   "No usable student rows found in that file.")
            return

        self.students    = students
        self.projects    = sorted(projs)
        self.last_result = None

        self.file_var.set(fp.name)
        self.status_var.set(
            f"Loaded {len(self.students)} students across {len(self.projects)} projects."
        )

        self._populate_preview()
        self._populate_constraints()
        _clear(self.assign_tree)
        _clear(self.groups_tree)
        self._reset_stats()

    def _populate_preview(self) -> None:
        """Show a quick preview of the first imported student rows."""
        _clear(self.preview_tree)
        for s in self.students[:50]:
            self.preview_tree.insert(
                "", "end",
                values=(s["name"], "  →  ".join(s["choices"])),
            )

    def _populate_constraints(self) -> None:
        # destroy all rows (keep header at index 0)
        children = list(self._constraints_scroll.inner.winfo_children())
        for child in children[1:]:
            child.destroy()
        self.project_inputs.clear()

        # interest = number of students who ranked each project at all
        interest: dict[str, int] = {p: 0 for p in self.projects}
        for s in self.students:
            for p in s["choices"]:
                if p in interest:
                    interest[p] += 1

        default_min = _safe_nn(self.default_min_var.get()) or 1
        default_max = _safe_pos(self.default_max_var.get()) or 6

        for row_idx, project in enumerate(self.projects, start=1):
            row = ttk.Frame(self._constraints_scroll.inner, style="Card.TFrame")
            row.grid(row=row_idx, column=0, sticky="ew", pady=3)
            row.columnconfigure(0, weight=1)

            min_var = tk.StringVar(value=str(default_min))
            max_var = tk.StringVar(value=str(default_max))

            ttk.Label(row, text=project, style="CardBody.TLabel",
                      ).grid(row=0, column=0, sticky="w")
            ttk.Label(row, text=str(interest[project]),
                      style="CardMeta.TLabel",
                      ).grid(row=0, column=1, padx=(8, 8))
            ttk.Entry(row, textvariable=min_var, width=6,
                      ).grid(row=0, column=2, padx=(0, 8))
            ttk.Entry(row, textvariable=max_var, width=6,
                      ).grid(row=0, column=3, padx=(0, 4))

            self.project_inputs[project] = {"min": min_var, "max": max_var}

            # bind mousewheel on each row so it propagates to the canvas
            row.bind("<Enter>", self._constraints_scroll._bind_wheel)
            row.bind("<Leave>", self._constraints_scroll._unbind_wheel)
            for child in row.winfo_children():
                child.bind("<Enter>", self._constraints_scroll._bind_wheel)
                child.bind("<Leave>", self._constraints_scroll._unbind_wheel)

    # ── apply-default buttons ─────────────────────────────────────────────────

    def _apply_default_min(self) -> None:
        v = _safe_nn(self.default_min_var.get())
        if v is None:
            messagebox.showwarning("Invalid", "Min seats must be a non-negative integer.")
            return
        for d in self.project_inputs.values():
            d["min"].set(str(v))
        self.status_var.set(f"Applied min seats = {v} to all projects.")

    def _apply_default_max(self) -> None:
        v = _safe_pos(self.default_max_var.get())
        if v is None:
            messagebox.showwarning("Invalid", "Max seats must be a positive integer.")
            return
        for d in self.project_inputs.values():
            d["max"].set(str(v))
        self.status_var.set(f"Applied max seats = {v} to all projects.")

    # ── constraint gathering & validation ────────────────────────────────────

    def _gather_constraints(self) -> dict[str, dict[str, int]] | None:
        """Read seat limits from the form and stop on the first invalid row."""
        out: dict[str, dict[str, int]] = {}
        for proj, d in self.project_inputs.items():
            mn = _safe_nn(d["min"].get())
            mx = _safe_pos(d["max"].get())
            if mn is None or mx is None:
                messagebox.showerror(
                    "Invalid constraints",
                    f"'{proj}' has a non-numeric seat value.",
                )
                return None
            if mn > mx:
                messagebox.showerror(
                    "Invalid constraints",
                    f"'{proj}': min ({mn}) is greater than max ({mx}).",
                )
                return None
            out[proj] = {"min": mn, "max": mx}
        return out

    # ── optimizer runner (threaded) ───────────────────────────────────────────

    def _run_optimizer(self) -> None:
        if self._running:
            return
        if not self.students:
            messagebox.showinfo("No data", "Load a preference file first.")
            return

        constraints = self._gather_constraints()
        if constraints is None:
            return

        technique_label = self.technique_var.get()
        technique_key   = self._tech_labels.get(technique_label)
        if not technique_key:
            messagebox.showerror("Algorithm error", "No valid algorithm selected.")
            return

        total_max = sum(v["max"] for v in constraints.values())
        if total_max < len(self.students):
            messagebox.showerror(
                "Capacity error",
                f"Max seats total {total_max} but {len(self.students)} students loaded.\n"
                "Raise the maximum seat counts.",
            )
            return

        total_min = sum(v["min"] for v in constraints.values())
        if total_min > len(self.students):
            messagebox.showerror(
                "Capacity error",
                f"Min seats total {total_min} but only {len(self.students)} students loaded.\n"
                "Lower the minimum seat counts.",
            )
            return

        if technique_key == "brute_force" and len(self.students) > 12:
            if not messagebox.askyesno(
                "Performance warning",
                f"Brute Force with {len(self.students)} students will be very slow.\n\n"
                "Linear Programming gives the same optimal result in milliseconds.\n\n"
                "Continue with Brute Force anyway?",
            ):
                return

        self._running = True
        self._run_btn.configure(state="disabled", text="Running …")
        self.status_var.set("Optimizer running …")
        self._start_spinner()

        # Run the optimizer off the Tk event loop so the window remains
        # responsive while CBC or the heuristic solvers are working.
        threading.Thread(
            target=self._do_optimize,
            args=(self.students[:], constraints, technique_key),
            daemon=True,
        ).start()

    def _do_optimize(
        self,
        students: list,
        constraints: dict,
        technique: str,
    ) -> None:
        """Execute the selected algorithm in a worker thread."""
        try:
            result = optimize_assignments(students, constraints, technique=technique)
        except Exception as exc:
            result = {"error": str(exc)}
        # Tk widgets must be updated on the main thread, so hand the result back
        # through the event loop instead of touching widgets directly here.
        self.root.after(0, self._on_optimize_done, result)

    def _on_optimize_done(self, result: dict) -> None:
        """Restore UI state and either surface an error or render results."""
        self._running = False
        self._stop_spinner()
        self._run_btn.configure(state="normal", text="▶  Run Assignment")

        if "error" in result:
            messagebox.showerror("Optimization failed", result["error"])
            self.status_var.set("Optimization failed — see error dialog.")
            return

        self.last_result = result
        tech_label = result["stats"].get("technique_label", self.technique_var.get())
        self.status_var.set(f"Done — {tech_label}   |   "
                            f"Objective score: {result['stats'].get('objective_value', 0)}")
        self._render_results(result)

    # ── spinner (status bar) ──────────────────────────────────────────────────

    def _start_spinner(self) -> None:
        self._spinner_idx = 0
        self._tick_spinner()

    def _tick_spinner(self) -> None:
        if not self._running:
            return
        self._spin_lbl.configure(
            text=_SPINNER[self._spinner_idx % len(_SPINNER)] + "  running"
        )
        self._spinner_idx += 1
        self.root.after(100, self._tick_spinner)

    def _stop_spinner(self) -> None:
        self._spin_lbl.configure(text="")

    # ── render results ────────────────────────────────────────────────────────

    def _render_results(self, result: dict) -> None:
        """Push a solver result into the assignments, groups, and stats views."""
        assignments = result.get("assignments", {})
        groups      = result.get("project_groups", {})
        stats       = result.get("stats", {})

        # ── Assignments tab ────────────────────────────────────────────
        _clear(self.assign_tree)
        for sname in sorted(assignments):
            info    = assignments[sname]
            rank    = info.get("rank")
            tag     = f"rank_{rank}" if rank and str(rank) in _RANK_ROW else "outside"
            rank_tx = f"Choice {rank}" if rank else "Outside choices"
            self.assign_tree.insert(
                "", "end",
                values=(sname, info["project"], rank_tx),
                tags=(tag,),
            )

        # ── Groups tab ────────────────────────────────────────────────
        _clear(self.groups_tree)
        for pname in sorted(groups):
            members = groups[pname]
            self.groups_tree.insert(
                "", "end",
                values=(pname, len(members), ", ".join(members)),
            )

        # ── Stats tab ────────────────────────────────────────────────
        rank_counts  = stats.get("rank_counts", {})
        unranked     = stats.get("unranked_count", 0)
        total        = stats.get("total_students", len(assignments))
        first_choice = rank_counts.get("1", 0)
        top_three    = sum(rank_counts.get(str(r), 0) for r in range(1, 4))

        def _pct(n: int) -> str:
            return f"{n}  ({n/total:.0%})" if total else str(n)

        self._stat_total.configure(text=str(total))
        self._stat_first.configure(text=_pct(first_choice))
        self._stat_top3.configure(text=_pct(top_three))
        self._stat_outside.configure(text=_pct(unranked))

        self._rank_chart.draw(rank_counts, unranked, total)

        tech_label = stats.get("technique_label", self.technique_var.get())
        obj        = stats.get("objective_value", 0)
        self._stat_footer.configure(
            text=f"Algorithm: {tech_label}   ·   Objective score: {obj}   "
                 f"(higher = more students matched to preferred projects)"
        )

        # summary line in Assignments tab header
        self._assign_summary.configure(
            text=(
                f"{tech_label} — {total} students assigned.   "
                f"1st choice: {first_choice}   "
                f"Top-3: {top_three}   "
                f"Outside prefs: {unranked}   "
                f"Click any column header to sort."
            )
        )

    def _reset_stats(self) -> None:
        """Clear the results area when nothing has been computed yet."""
        for attr in ("_stat_total", "_stat_first", "_stat_top3", "_stat_outside"):
            getattr(self, attr).configure(text="—")
        self._rank_chart.draw({}, 0, 0)
        self._stat_footer.configure(text="")
        self._assign_summary.configure(
            text="Run the optimizer to see results.")

    # ── export ────────────────────────────────────────────────────────────────

    def _export_results(self) -> None:
        if not self.last_result:
            messagebox.showinfo("No results", "Run the optimizer before exporting.")
            return

        path = filedialog.asksaveasfilename(
            title="Export all assignments",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if not path:
            return

        assignments = self.last_result.get("assignments", {})
        stats       = self.last_result.get("stats", {})
        with Path(path).open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            # Include a short metadata block so exported files preserve the
            # algorithm choice and objective score that produced them.
            w.writerow(["# Algorithm", stats.get("technique_label", "")])
            w.writerow(["# Objective score", stats.get("objective_value", "")])
            w.writerow(["# Total students", stats.get("total_students", "")])
            w.writerow([])
            w.writerow(["Student Name", "Assigned Project", "Preference Rank"])
            for sname in sorted(assignments):
                info = assignments[sname]
                rank = info.get("rank")
                w.writerow([
                    sname,
                    info["project"],
                    f"Choice {rank}" if rank else "Outside listed choices",
                ])

        self.status_var.set(f"Exported assignments → {Path(path).name}")

    def _export_groups(self) -> None:
        """Export one row per project with member names collapsed into a cell."""
        if not self.last_result:
            messagebox.showinfo("No results", "Run the optimizer before exporting.")
            return

        path = filedialog.asksaveasfilename(
            title="Export project groups",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if not path:
            return

        groups = self.last_result.get("project_groups", {})
        with Path(path).open("w", encoding="utf-8", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["Project", "Student Count", "Members"])
            for pname in sorted(groups):
                members = groups[pname]
                w.writerow([pname, len(members), "; ".join(members)])

        self.status_var.set(f"Exported project groups → {Path(path).name}")


# ── entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    """Create and run the desktop application."""
    root = tk.Tk()
    CapstoneDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
