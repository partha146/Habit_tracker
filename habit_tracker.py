"""
Habit Tracker Desktop App  –  v3
• Two tabs: Good Habits + Mood  |  Bad Habits (red chart)
• No-flicker cell toggle + mood toggle
• Filled-area mood graph (same style as daily progress)
• Graph x-axis aligns with date columns
• Borderless maximised window; taskbar/alt-tab via WS_EX_APPWINDOW
"""

import tkinter as tk
from tkinter import messagebox, simpledialog
import json, os, calendar, datetime, sys

# ── Windows: declare DPI awareness BEFORE any window is created ───────────────
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# ─── Smooth-curve helper (used by all graphs) ─────────────────────────────────
def _smooth_curve(xs, ys, n=400, ymin=None, ymax=None):
    import numpy as np
    xs = np.asarray(xs, float); ys = np.asarray(ys, float)
    if len(xs) < 2:
        return xs, ys
    x_fine = np.linspace(xs[0], xs[-1], n)
    try:
        from scipy.interpolate import PchipInterpolator
        y_fine = PchipInterpolator(xs, ys)(x_fine)
    except ImportError:
        y_fine = np.empty_like(x_fine)
        for i in range(len(xs) - 1):
            x0, x1 = xs[i], xs[i+1]; y0, y1 = ys[i], ys[i+1]
            m0 = (ys[i+1]-ys[i-1])/(xs[i+1]-xs[i-1]) if i>0 else (y1-y0)/(x1-x0)
            m1 = (ys[i+2]-ys[i])/(xs[i+2]-xs[i]) if i<len(xs)-2 else (y1-y0)/(x1-x0)
            dx = x1-x0
            mask = (x_fine>=x0) & (x_fine<=x1)
            t = (x_fine[mask]-x0)/dx
            h00=2*t**3-3*t**2+1; h10=t**3-2*t**2+t
            h01=-2*t**3+3*t**2;  h11=t**3-t**2
            y_fine[mask] = h00*y0+h10*dx*m0+h01*y1+h11*dx*m1
    if ymin is not None and ymax is not None:
        y_fine = np.clip(y_fine, ymin, ymax)
    return x_fine, y_fine

# ─── Persistence ──────────────────────────────────────────────────────────────
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "habit_data.json")

def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        # migrate: ensure bad-habits keys exist
        d.setdefault("bad_habits",  DEFAULT_BAD_HABITS[:])
        d.setdefault("bad_records", {})
        return d
    return {
        "habits":      DEFAULT_HABITS[:],
        "records":     {},
        "goal":        "Being Productive",
        "moods":       {},
        "bad_habits":  DEFAULT_BAD_HABITS[:],
        "bad_records": {},
    }

def save_data(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def month_key(y, m): return f"{y}-{m:02d}"

# ─── Defaults ─────────────────────────────────────────────────────────────────
DEFAULT_HABITS = [
    "Wake up before 7am", "Exercise / Meditate", "Check DMs / Email",
    "Study (2hrs+)", "Drink H₂O (2.3L)", "Do Work",
    "No Sugar / Junk food", "Everything Groomed",
    "Read book / Editorial", "Feel Gratitude", "Plan Next Day",
    "Learn New Things", "Sleep before 12am",
]

DEFAULT_BAD_HABITS = [
    "Junk Food", "Social Media > 2hrs", "Skipped Workout",
    "Slept Late (12am+)", "Wasted Time", "Overspending",
]

MOOD_LEVELS = ["Awesome 🤩", "Good 😊", "Normal 😐", "Stressed 😤", "Tired 😴", "F**ked 😵"]
MOOD_COLORS = ["#4CAF50",   "#8BC34A", "#FFC107",   "#FF9800",    "#F44336",  "#9C27B0"]
MOOD_SCORES = [5, 4, 3, 2, 1, 0]

# ─── Palette ──────────────────────────────────────────────────────────────────
BG_DARK    = "#0F0F1A"
BG_CARD    = "#1A1A2E"
BG_HEADER  = "#16213E"
ACCENT     = "#7C3AED"
ACCENT2    = "#A78BFA"
FAIL_CLR   = "#EF4444"
WARN_CLR   = "#F59E0B"
TEXT_WHITE = "#F1F5F9"
TEXT_MUTED = "#94A3B8"
GRID_LINE  = "#2D2D44"
ROW_ALT    = "#1E1E32"
ROW_HOVER  = "#252540"
TODAY_TINT = "#1E1245"

FT  = ("Segoe UI", 22, "bold")
FH  = ("Segoe UI", 11, "bold")
FB  = ("Segoe UI", 10)
FS  = ("Segoe UI", 9)
FXS = ("Segoe UI", 7)
FEM = ("Segoe UI", 11)

# ─── Main window ──────────────────────────────────────────────────────────────
class HabitTrackerApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.data = load_data()
        self.today = datetime.date.today()
        self.cur_year  = self.today.year
        self.cur_month = self.today.month
        self.active_tab = "good"   # "good" | "bad"

        self.overrideredirect(True)
        self.state("zoomed")
        self.configure(bg=BG_DARK)

        self._drag_win_x = 0
        self._drag_win_y = 0

        self._build_chrome()
        self.after(50,  self.refresh_grid)
        self.after(100, self._fix_taskbar)
        self._schedule_midnight_refresh()

    # ── Midnight refresh ───────────────────────────────────────────────────────
    def _schedule_midnight_refresh(self):
        now = datetime.datetime.now()
        tomorrow = (now + datetime.timedelta(days=1)).replace(hour=0, minute=0, second=2, microsecond=0)
        self.after(int((tomorrow - now).total_seconds() * 1000), self._midnight_tick)

    def _midnight_tick(self):
        self.today = datetime.date.today()
        self.refresh_grid()
        self._schedule_midnight_refresh()

    # ═══════════════════════════════════════════════════════════════════════════
    # Chrome
    # ═══════════════════════════════════════════════════════════════════════════
    def _build_chrome(self):
        top = tk.Frame(self, bg=BG_HEADER, pady=10)
        top.pack(fill="x")
        top.bind("<Button-1>",  self._win_drag_start)
        top.bind("<B1-Motion>", self._win_drag_move)

        # Window controls (right, first so they anchor right)
        ctrl = tk.Frame(top, bg=BG_HEADER)
        ctrl.pack(side="right", padx=8)
        tk.Button(ctrl, text=" ✕ ", command=self._on_close,
                  font=("Segoe UI", 11), bg=BG_HEADER, fg="#FF5F57",
                  activebackground="#FF5F57", activeforeground="white",
                  relief="flat", cursor="hand2").pack(side="right", padx=2)
        tk.Button(ctrl, text=" — ", command=self._win_minimise,
                  font=("Segoe UI", 11), bg=BG_HEADER, fg=TEXT_MUTED,
                  activebackground=BG_CARD, activeforeground="white",
                  relief="flat", cursor="hand2").pack(side="right", padx=2)
        tk.Button(ctrl, text=" ⛶ ", command=self._win_toggle_max,
                  font=("Segoe UI", 11), bg=BG_HEADER, fg=TEXT_MUTED,
                  activebackground=BG_CARD, activeforeground="white",
                  relief="flat", cursor="hand2").pack(side="right", padx=2)

        # Month nav (right)
        nav = tk.Frame(top, bg=BG_HEADER)
        nav.pack(side="right", padx=18)
        tk.Button(nav, text="◀", command=self._prev_month, font=FH,
                  bg=BG_CARD, fg=ACCENT2, relief="flat", padx=10, pady=4,
                  activebackground=ACCENT, activeforeground="white", cursor="hand2").pack(side="left")
        self.month_label = tk.Label(nav, font=FH, bg=BG_HEADER, fg=TEXT_WHITE, width=14)
        self.month_label.pack(side="left", padx=8)
        tk.Button(nav, text="▶", command=self._next_month, font=FH,
                  bg=BG_CARD, fg=ACCENT2, relief="flat", padx=10, pady=4,
                  activebackground=ACCENT, activeforeground="white", cursor="hand2").pack(side="left")
        tk.Button(nav, text="Today", command=self._goto_today, font=FS,
                  bg=ACCENT, fg="white", relief="flat", padx=8, pady=4,
                  activebackground=ACCENT2, cursor="hand2").pack(side="left", padx=(12, 0))

        # Title (left)
        tk.Label(top, text="✨", font=("Segoe UI", 20), bg=BG_HEADER, fg=ACCENT2).pack(side="left", padx=(18, 4))
        tk.Label(top, text="Being a Better Version of Me", font=FT,
                 bg=BG_HEADER, fg=TEXT_WHITE).pack(side="left")

        # ── Tab buttons ───────────────────────────────────────────────────────
        tab_bar = tk.Frame(top, bg=BG_HEADER)
        tab_bar.pack(side="left", padx=20)

        self._tab_btns = {}
        tabs = [("good", "🌟  Good Habits"), ("bad", "⚠️  Bad Habits")]
        for tab_id, label in tabs:
            btn = tk.Button(
                tab_bar, text=label, font=FS,
                relief="flat", padx=12, pady=6, cursor="hand2",
                command=lambda t=tab_id: self._switch_tab(t),
            )
            btn.pack(side="left", padx=3)
            self._tab_btns[tab_id] = btn
        self._update_tab_styles()

        # Focus badge
        self.goal_var = tk.StringVar(value=self.data.get("goal", "Being Productive"))
        gf = tk.Frame(top, bg=ACCENT, padx=10, pady=4)
        gf.pack(side="left", padx=10)
        tk.Label(gf, text="FOCUS:", font=FS, bg=ACCENT, fg="white").pack(side="left")
        ge = tk.Entry(gf, textvariable=self.goal_var, font=FS,
                      bg=ACCENT, fg="white", insertbackground="white",
                      relief="flat", width=22)
        ge.pack(side="left", padx=(4, 0))
        ge.bind("<Return>",   lambda e: self._save_goal())
        ge.bind("<FocusOut>", lambda e: self._save_goal())

        # Body
        body = tk.Frame(self, bg=BG_DARK)
        body.pack(fill="both", expand=True)

        self.sidebar = tk.Frame(body, bg=BG_CARD, width=180)
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)
        self._build_sidebar(self.sidebar)

        right = tk.Frame(body, bg=BG_DARK)
        right.pack(side="left", fill="both", expand=True)
        self._build_scroll_area(right)

    def _switch_tab(self, tab_id):
        if self.active_tab == tab_id:
            return
        self.active_tab = tab_id
        self._update_tab_styles()
        # Rebuild sidebar for new tab
        for w in self.sidebar.winfo_children():
            w.destroy()
        self._build_sidebar(self.sidebar)
        self.refresh_grid()

    def _update_tab_styles(self):
        for tab_id, btn in self._tab_btns.items():
            if tab_id == self.active_tab:
                btn.config(bg=ACCENT, fg="white", activebackground=ACCENT2, activeforeground="white")
            else:
                btn.config(bg=BG_CARD, fg=TEXT_MUTED, activebackground=BG_HEADER, activeforeground=TEXT_WHITE)

    # ── Custom window controls ─────────────────────────────────────────────────
    def _win_drag_start(self, e): self._drag_win_x=e.x_root-self.winfo_x(); self._drag_win_y=e.y_root-self.winfo_y()
    def _win_drag_move(self, e):
        if self.state() != "zoomed":
            self.geometry(f"+{e.x_root-self._drag_win_x}+{e.y_root-self._drag_win_y}")

    def _fix_taskbar(self):
        if sys.platform != "win32": return
        try:
            import ctypes
            GWL_EXSTYLE=-20; WS_EX_APPWINDOW=0x00040000; WS_EX_TOOLWINDOW=0x00000080
            hwnd = ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW)
            ctypes.windll.user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, 0x0027)
        except Exception: pass

    def _win_minimise(self):
        if sys.platform == "win32":
            try:
                import ctypes
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id()) or self.winfo_id()
                ctypes.windll.user32.ShowWindow(hwnd, 6)  # SW_MINIMIZE
                return
            except Exception: pass
        self.iconify()

    def _win_toggle_max(self):
        if self.state() == "zoomed": self.state("normal"); self.geometry("1360x860")
        else: self.state("zoomed")

    # ── Sidebar ────────────────────────────────────────────────────────────────
    def _build_sidebar(self, parent):
        is_bad = (self.active_tab == "bad")
        label  = "BAD HABITS" if is_bad else "HABITS"
        tk.Label(parent, text=label, font=FH, bg=BG_CARD,
                 fg=FAIL_CLR if is_bad else ACCENT2, pady=14).pack(fill="x", padx=10)

        self._drag_idx = self._drag_ghost = self._drag_target = None

        lf = tk.Frame(parent, bg=BG_CARD)
        lf.pack(fill="both", expand=True, padx=6)
        self.habit_listbox = tk.Listbox(
            lf, bg=BG_CARD, fg=TEXT_WHITE, font=FS,
            selectbackground=FAIL_CLR if is_bad else ACCENT,
            selectforeground="white", relief="flat",
            activestyle="none", bd=0, highlightthickness=0, cursor="hand2",
        )
        self.habit_listbox.pack(fill="both", expand=True)
        lb = self.habit_listbox
        lb.bind("<Button-1>",        self._drag_start)
        lb.bind("<B1-Motion>",       self._drag_motion)
        lb.bind("<ButtonRelease-1>", self._drag_drop)

        tk.Label(parent, text="⠿ drag to reorder", font=("Segoe UI", 7),
                 bg=BG_CARD, fg=GRID_LINE).pack(pady=(0, 2))

        bf = tk.Frame(parent, bg=BG_CARD, pady=8)
        bf.pack(fill="x", padx=6)
        add_cmd    = self._add_bad_habit    if is_bad else self._add_habit
        rename_cmd = self._rename_bad_habit if is_bad else self._rename_habit
        remove_cmd = self._remove_bad_habit if is_bad else self._remove_habit
        for txt, cmd in [("+ Add", add_cmd), ("✎ Rename", rename_cmd), ("✕ Remove", remove_cmd)]:
            tk.Button(bf, text=txt, command=cmd, font=FS,
                      bg=BG_DARK, fg=TEXT_WHITE, relief="flat", pady=5,
                      activebackground=FAIL_CLR if is_bad else ACCENT,
                      activeforeground="white", cursor="hand2").pack(fill="x", pady=2)

        tk.Label(parent, text="THIS MONTH", font=FS, bg=BG_CARD, fg=TEXT_MUTED).pack(pady=(10, 2))
        self.stats_label = tk.Label(parent, text="", font=FS, bg=BG_CARD,
                                    fg=FAIL_CLR if is_bad else ACCENT2, justify="left")
        self.stats_label.pack(padx=10, fill="x")

    # ── Drag-and-drop ──────────────────────────────────────────────────────────
    def _habits_list(self):
        return self.data["bad_habits"] if self.active_tab == "bad" else self.data["habits"]

    def _drag_start(self, event):
        lb  = self.habit_listbox
        idx = lb.nearest(event.y)
        h   = self._habits_list()
        if idx < 0 or idx >= len(h): return
        self._drag_idx = idx; self._drag_target = idx
        lb.selection_clear(0, "end"); lb.selection_set(idx)
        ghost = tk.Toplevel(self)
        ghost.overrideredirect(True); ghost.attributes("-alpha", 0.80); ghost.attributes("-topmost", True)
        tk.Label(ghost, text=f"  {h[idx]}  ", font=FS, bg=ACCENT, fg="white",
                 relief="flat", padx=4, pady=4).pack()
        self._drag_ghost = ghost; self._move_ghost(event)

    def _drag_motion(self, event):
        if self._drag_idx is None: return
        self._move_ghost(event)
        lb = self.habit_listbox; h = self._habits_list()
        target = max(0, min(lb.nearest(event.y), len(h) - 1))
        if target != self._drag_target:
            self._drag_target = target
            tmp = h[:]; item = tmp.pop(self._drag_idx); tmp.insert(target, item)
            lb.delete(0, "end")
            for i, x in enumerate(tmp): lb.insert("end", f"  {x}")
            lb.itemconfig(target, bg=ACCENT, fg="white")
            lb.itemconfig(self._drag_idx, bg=ROW_ALT, fg=TEXT_MUTED)

    def _drag_drop(self, event):
        if self._drag_idx is None: return
        if self._drag_ghost: self._drag_ghost.destroy(); self._drag_ghost = None
        h = self._habits_list()
        target = self._drag_target if self._drag_target is not None else self._drag_idx
        if target != self._drag_idx:
            item = h.pop(self._drag_idx); h.insert(target, item)
            save_data(self.data); self.refresh_grid()
        else:
            lb = self.habit_listbox
            for i in range(lb.size()): lb.itemconfig(i, bg=BG_CARD, fg=TEXT_WHITE)
        self._drag_idx = self._drag_target = None

    def _move_ghost(self, event):
        if self._drag_ghost:
            self._drag_ghost.geometry(f"+{event.x_root+12}+{event.y_root-10}")

    # ── Scroll area ────────────────────────────────────────────────────────────
    def _build_scroll_area(self, parent):
        self.canvas = tk.Canvas(parent, bg=BG_DARK, highlightthickness=0)
        v_sb = tk.Scrollbar(parent, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=v_sb.set)
        v_sb.pack(side="right", fill="y")
        self.canvas.pack(fill="both", expand=True)
        self.inner = tk.Frame(self.canvas, bg=BG_DARK)
        self._cwin  = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.inner.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.bind("<Configure>", self._on_canvas_resize)
        self.canvas.bind_all("<MouseWheel>", lambda e: self.canvas.yview_scroll(int(-1*(e.delta/120)), "units"))

    def _on_canvas_resize(self, event): self._update_canvas_width(event.width)

    def _update_canvas_width(self, canvas_w=None):
        SIDEBAR_W   = 195
        dim         = calendar.monthrange(self.cur_year, self.cur_month)[1]
        content_min = 220 + dim * 32 + 70
        screen_based = self.winfo_screenwidth() - SIDEBAR_W
        self.canvas.itemconfig(self._cwin, width=max(screen_based, content_min, canvas_w or 0))

    # ═══════════════════════════════════════════════════════════════════════════
    # Grid rebuild
    # ═══════════════════════════════════════════════════════════════════════════
    def refresh_grid(self):
        for w in self.inner.winfo_children():
            w.destroy()
        self.today = datetime.date.today()
        self._update_canvas_width()

        y, m = self.cur_year, self.cur_month
        self.month_label.config(text=datetime.date(y, m, 1).strftime("%B  %Y"))
        dim = calendar.monthrange(y, m)[1]
        mk  = month_key(y, m)

        is_bad  = (self.active_tab == "bad")
        habits  = self.data["bad_habits"]  if is_bad else self.data["habits"]
        records = self.data["bad_records"].get(mk, {}) if is_bad else self.data["records"].get(mk, {})
        moods   = self.data["moods"].get(mk, {})

        # sidebar list
        self.habit_listbox.delete(0, "end")
        for h in habits:
            self.habit_listbox.insert("end", f"  {h}")

        G = tk.Frame(self.inner, bg=BG_DARK)
        G.pack(fill="x", padx=4, pady=4)
        G.columnconfigure(0, minsize=220, weight=0)
        for d in range(1, dim + 1):
            G.columnconfigure(d, minsize=32, weight=1)
        G.columnconfigure(dim + 1, minsize=58, weight=0)

        crow = 0

        def section_banner(text, grid_row, color=ACCENT):
            fr = tk.Frame(G, bg=BG_HEADER)
            fr.grid(row=grid_row, column=0, columnspan=dim+2, sticky="ew", pady=(8, 0))
            tk.Label(fr, text=text, font=("Segoe UI", 9, "bold"),
                     bg=BG_HEADER, fg=color, padx=10, pady=5).pack(side="left")
            return grid_row + 1

        def divider(grid_row, color=ACCENT, h=2):
            tk.Frame(G, bg=color, height=h).grid(
                row=grid_row, column=0, columnspan=dim+2, sticky="ew")
            return grid_row + 1

        today_d = self.today.day if y==self.today.year and m==self.today.month else -1

        def day_bg(base, d): return TODAY_TINT if d == today_d else base

        # ── Date header ───────────────────────────────────────────────────────
        hdr_title = "BAD HABITS / TO AVOID" if is_bad else "HABIT / ROUTINE"
        tk.Label(G, text=hdr_title, font=FH, bg=BG_HEADER,
                 fg=FAIL_CLR if is_bad else ACCENT2, anchor="w", padx=8).grid(
            row=crow, column=0, sticky="ew", ipady=6)

        for d in range(1, dim+1):
            dt = datetime.date(y, m, d)
            is_today = (d == today_d); is_we = dt.weekday() >= 5
            bg = ACCENT if is_today else day_bg(BG_HEADER, d)
            fg = "white" if is_today else (ACCENT2 if is_we else TEXT_MUTED)
            tk.Label(G, text=str(d),
                     font=("Segoe UI", 9, "bold") if is_today else FS,
                     bg=bg, fg=fg, anchor="center").grid(
                row=crow, column=d, sticky="ew", padx=1, ipady=4)

        tk.Label(G, text="TOTAL", font=FH, bg=BG_HEADER, fg=ACCENT2, anchor="center").grid(
            row=crow, column=dim+1, sticky="ew", padx=(4,2), ipady=6)
        crow += 1

        # day-letter row
        tk.Label(G, text="", bg=BG_HEADER).grid(row=crow, column=0, sticky="ew")
        for d in range(1, dim+1):
            dt = datetime.date(y, m, d)
            fg = ACCENT2 if dt.weekday()>=5 else TEXT_MUTED
            tk.Label(G, text=dt.strftime("%a")[0], font=FXS,
                     bg=day_bg(BG_HEADER, d), fg=fg, anchor="center").grid(
                row=crow, column=d, sticky="ew", padx=1, pady=(0,3))
        tk.Label(G, text="", bg=BG_HEADER).grid(row=crow, column=dim+1, sticky="ew")
        crow += 1

        crow = divider(crow, FAIL_CLR if is_bad else ACCENT)
        banner_color = FAIL_CLR if is_bad else ACCENT
        crow = section_banner("BAD HABITS (mark when done)" if is_bad else "HABIT ROUTINE", crow, banner_color)

        # ── Habit rows ────────────────────────────────────────────────────────
        self.check_vars   = {}
        self._pill_labels = {}
        chk_accent = FAIL_CLR if is_bad else ACCENT

        for i, habit in enumerate(habits):
            row_bg = BG_CARD if i%2==0 else ROW_ALT
            total  = 0
            lbl = tk.Label(G, text=f"{i+1}. {habit}", font=FB,
                           bg=row_bg, fg=TEXT_WHITE, anchor="w", padx=8)
            lbl.grid(row=crow, column=0, sticky="ew", ipady=5)
            lbl.bind("<Enter>", lambda e, r=crow: self._row_hover(G, r, dim, ROW_HOVER))
            lbl.bind("<Leave>", lambda e, r=crow, c=row_bg: self._row_hover(G, r, dim, c))

            for d in range(1, dim+1):
                checked = records.get(habit, {}).get(str(d), False)
                if checked: total += 1
                var = tk.BooleanVar(value=checked)
                self.check_vars[(habit, d)] = var
                if checked:    cell_bg = chk_accent
                elif d==today_d: cell_bg = TODAY_TINT
                else:          cell_bg = row_bg
                cell = tk.Label(G,
                    text="✓" if checked else "·",
                    font=("Segoe UI", 10, "bold") if checked else ("Segoe UI", 12),
                    bg=cell_bg,
                    fg=("white" if checked else (ACCENT2 if d==today_d else GRID_LINE)),
                    anchor="center", cursor="hand2")
                cell.grid(row=crow, column=d, sticky="ew", padx=1, pady=2)
                cell.bind("<Button-1>",
                          lambda e, h=habit, day=d, v=var, c=cell, rb=row_bg:
                          self._toggle_cell(h, day, v, c, rb, dim, chk_accent))

            pct = int(total/dim*100)
            pill_bg = chk_accent if pct>=70 else (WARN_CLR if pct>=40 else FAIL_CLR)
            if is_bad: pill_bg = FAIL_CLR if total>0 else BG_CARD
            pill = tk.Label(G, text=str(total), font=("Segoe UI", 10, "bold"),
                            bg=pill_bg, fg="white", anchor="center")
            pill.grid(row=crow, column=dim+1, sticky="ew", padx=(4,2), pady=2)
            self._pill_labels[habit] = pill
            crow += 1

        # ── Progress chart ─────────────────────────────────────────────────────
        crow = divider(crow, GRID_LINE, 1)
        n_habits = len(habits)
        day_pct = [
            int(sum(1 for h in habits if records.get(h,{}).get(str(d),False)) / n_habits * 100)
            if n_habits else 0
            for d in range(1, dim+1)
        ]
        area_frame = tk.Frame(G, bg=BG_CARD)
        area_frame.grid(row=crow, column=0, columnspan=dim+2, sticky="ew", padx=0, pady=(0,6))
        crow += 1
        chart_color = "#FF4444" if is_bad else "#4ADE80"
        chart_title = "Bad Habit Frequency" if is_bad else "Daily progress"
        chart_sub   = "Days you gave in to a bad habit." if is_bad else "Your completed habits as a percentage of your daily goal."
        self._draw_area_chart(area_frame, day_pct, dim, chart_color, chart_title, chart_sub, is_bad)
        self._area_frame = area_frame

        # ── Mood section (Good tab only) ───────────────────────────────────────
        if not is_bad:
            crow = divider(crow, GRID_LINE, 1)
            crow = section_banner("MOOD TRACKER", crow)

            self._mood_dots = {}  # (day, mood_idx) → label widget

            for mi, (mood, mcolor) in enumerate(zip(MOOD_LEVELS, MOOD_COLORS)):
                row_bg = BG_CARD if mi%2==0 else ROW_ALT
                tk.Label(G, text=mood, font=FB, bg=row_bg,
                         fg=mcolor, anchor="w", padx=8).grid(
                    row=crow, column=0, sticky="ew", ipady=4)
                for d in range(1, dim+1):
                    selected = moods.get(str(d)) == mood
                    dot = tk.Label(G, text="●" if selected else "○", font=FEM,
                                   bg=day_bg(row_bg, d),
                                   fg=mcolor if selected else GRID_LINE,
                                   anchor="center", cursor="hand2")
                    dot.grid(row=crow, column=d, sticky="ew", padx=1, pady=2)
                    dot.bind("<Button-1>", lambda e, mo=mood, day=d: self._set_mood(mo, day))
                    self._mood_dots[(d, mi)] = dot
                tk.Label(G, text="", bg=row_bg).grid(row=crow, column=dim+1, sticky="ew")
                crow += 1

            # Mood area chart (same style as progress chart)
            crow = divider(crow, GRID_LINE, 1)
            mg_frame = tk.Frame(G, bg=BG_CARD)
            mg_frame.grid(row=crow, column=0, columnspan=dim+2, sticky="ew", padx=0, pady=(0,8))
            crow += 1
            self._draw_mood_chart(mg_frame, moods, dim)
            self._mg_frame = mg_frame
        else:
            self._mg_frame = None

        # Store chart context
        self._chart_dim    = dim
        self._chart_mk     = mk
        self._chart_habits = habits
        self._chart_is_bad = is_bad
        self._chart_color  = chart_color

        self._update_stats(records, habits, dim, is_bad)

    # ═══════════════════════════════════════════════════════════════════════════
    # Charts
    # ═══════════════════════════════════════════════════════════════════════════
    def _chart_margins(self, dim):
        """Return (left_frac, right_frac) so x-axis aligns with day columns."""
        SIDEBAR_W = 195
        total_w   = max(self.winfo_screenwidth() - SIDEBAR_W, 1)
        name_w    = 220 + 4   # name col + padx
        total_col = 58  + 4
        left_f  = name_w  / total_w
        right_f = 1.0 - total_col / total_w
        return left_f, right_f

    def _draw_area_chart(self, parent, day_pct, dim, line_color, title, subtitle, is_bad=False):
        """Filled area chart — green for good habits, red for bad habits."""
        avg = int(sum(day_pct) / len(day_pct)) if day_pct else 0
        xs  = list(range(1, dim+1))

        hdr = tk.Frame(parent, bg=BG_CARD)
        hdr.pack(fill="x", padx=12, pady=(10, 0))
        tk.Label(hdr, text=title, font=("Segoe UI", 13, "bold"),
                 bg=BG_CARD, fg=TEXT_WHITE).pack(side="left")
        avg_label = f"{avg}% marked" if is_bad else f"{avg}% average"
        tk.Label(hdr, text=avg_label, font=("Segoe UI", 11),
                 bg=BG_CARD, fg=line_color).pack(side="right")
        tk.Label(parent, text=subtitle, font=("Segoe UI", 8),
                 bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w", padx=14)

        try:
            import matplotlib; matplotlib.use("TkAgg")
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            import numpy as np

            dpi = 90
            screen_w = self.winfo_screenwidth()
            fig_w = max(10, (screen_w - 210) / dpi)
            left_f, right_f = self._chart_margins(dim)

            fig = Figure(figsize=(fig_w, 2.8), dpi=dpi, facecolor=BG_CARD)
            ax  = fig.add_subplot(111, facecolor=BG_CARD)
            fig.subplots_adjust(left=left_f, right=right_f, top=0.92, bottom=0.12)

            ys = day_pct
            x_fine, y_fine = _smooth_curve(np.array(xs, float), np.array(ys, float),
                                           n=400, ymin=0, ymax=100)
            ax.fill_between(x_fine, y_fine, alpha=0.22, color=line_color, zorder=1)
            ax.plot(x_fine, y_fine, color=line_color, linewidth=2.0, zorder=2)
            ax.scatter(xs, ys, color=line_color, s=30, zorder=3,
                       edgecolors=BG_CARD, linewidths=0.8)

            ax.set_xlim(0.5, dim+0.5)
            ax.set_ylim(-5, 108)
            ax.set_xticks(xs)
            ax.set_xticklabels([str(d) for d in xs], fontsize=6.5, color=TEXT_MUTED)
            ax.set_yticks([0, 25, 50, 75, 100])
            ax.set_yticklabels(["0%","25%","50%","75%","100%"], fontsize=7, color=TEXT_MUTED)
            ax.tick_params(axis="both", length=0)
            for sp in ax.spines.values(): sp.set_visible(False)
            ax.grid(axis="y", color=GRID_LINE, linewidth=0.5, alpha=0.6)
            ax.axhline(100, color=GRID_LINE, linewidth=0.5, linestyle="--", alpha=0.4)

            cv = FigureCanvasTkAgg(fig, master=parent)
            cv.draw()
            cv.get_tk_widget().pack(fill="x", padx=0, pady=(4, 10))

        except ImportError:
            self._fallback_area_canvas(parent, day_pct, dim, line_color)

    def _fallback_area_canvas(self, parent, day_pct, dim, color):
        H = 160
        cv = tk.Canvas(parent, bg=BG_CARD, height=H, highlightthickness=0)
        cv.pack(fill="x", padx=6, pady=(4,10))
        cv.update_idletasks()
        W = cv.winfo_width() or 900
        PL,PR,PT,PB = 42,12,10,24
        def px(d): return PL+(d-1)/max(dim-1,1)*(W-PL-PR)
        def py(p): return PT+(1-p/100)*(H-PT-PB)
        for p in [0,25,50,75,100]:
            yy=py(p); cv.create_line(PL,yy,W-PR,yy,fill=GRID_LINE,dash=(3,4))
            cv.create_text(PL-4,yy,text=f"{p}%",anchor="e",fill=TEXT_MUTED,font=FXS)
        if dim>0:
            pts=[]
            for d in range(1,dim+1): pts+=[px(d),py(day_pct[d-1])]
            poly=[px(1),py(0)]+pts+[px(dim),py(0)]
            cv.create_polygon(poly,fill=color,stipple="gray25",outline="",smooth=True)
            if len(pts)>=4: cv.create_line(*pts,fill=color,width=2,smooth=True)
            for d in range(1,dim+1):
                x,y=px(d),py(day_pct[d-1])
                cv.create_oval(x-3,y-3,x+3,y+3,fill=color,outline=BG_CARD,width=1)

    def _draw_mood_chart(self, parent, moods, dim):
        """Mood score as a filled area chart — same visual style as the habit chart."""
        xs, ys, colors = [], [], []
        for d in range(1, dim+1):
            mood = moods.get(str(d))
            if mood and mood in MOOD_LEVELS:
                idx = MOOD_LEVELS.index(mood)
                xs.append(d); ys.append(MOOD_SCORES[idx]); colors.append(MOOD_COLORS[idx])

        hdr = tk.Frame(parent, bg=BG_CARD)
        hdr.pack(fill="x", padx=12, pady=(10,0))
        tk.Label(hdr, text="Mood Graph", font=("Segoe UI", 13, "bold"),
                 bg=BG_CARD, fg=TEXT_WHITE).pack(side="left")
        if xs:
            avg_score = sum(ys)/len(ys)
            avg_lbl = MOOD_LEVELS[min(range(len(MOOD_SCORES)),
                                      key=lambda i: abs(MOOD_SCORES[i]-avg_score))]
            tk.Label(hdr, text=f"avg: {avg_lbl.split()[0]}", font=("Segoe UI",11),
                     bg=BG_CARD, fg=ACCENT2).pack(side="right")
        tk.Label(parent, text="Your mood score per day (5=Awesome → 0=F**ked).",
                 font=("Segoe UI", 8), bg=BG_CARD, fg=TEXT_MUTED).pack(anchor="w", padx=14)

        try:
            import matplotlib; matplotlib.use("TkAgg")
            from matplotlib.figure import Figure
            from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
            import numpy as np

            dpi = 90
            screen_w = self.winfo_screenwidth()
            fig_w = max(10, (screen_w - 210) / dpi)
            left_f, right_f = self._chart_margins(dim)

            fig = Figure(figsize=(fig_w, 2.5), dpi=dpi, facecolor=BG_CARD)
            ax  = fig.add_subplot(111, facecolor=BG_CARD)
            fig.subplots_adjust(left=left_f, right=right_f, top=0.92, bottom=0.12)

            if len(xs) >= 2:
                x_fine, y_fine = _smooth_curve(np.array(xs, float), np.array(ys, float),
                                               n=400, ymin=0, ymax=5)
                ax.fill_between(x_fine, y_fine, alpha=0.18, color=ACCENT2, zorder=1)
                ax.plot(x_fine, y_fine, color=ACCENT2, linewidth=2.2, zorder=2)
            if xs:
                ax.scatter(xs, ys, c=colors, s=60, zorder=3, edgecolors=BG_CARD, linewidths=1)

            # draw all days on x-axis so it aligns with the grid
            all_days = list(range(1, dim+1))
            ax.set_xlim(0.5, dim+0.5)
            ax.set_ylim(-0.5, 5.5)
            ax.set_xticks(all_days)
            ax.set_xticklabels([str(d) for d in all_days], fontsize=6.5, color=TEXT_MUTED)
            ax.set_yticks(MOOD_SCORES)
            ax.set_yticklabels(["F**ked","Tired","Stressed","Normal","Good","Awesome"],
                               fontsize=7, color=TEXT_MUTED)
            ax.tick_params(axis="both", length=0)
            for sp in ax.spines.values(): sp.set_color(GRID_LINE)
            ax.grid(True, color=GRID_LINE, linewidth=0.4, alpha=0.5)

            cv = FigureCanvasTkAgg(fig, master=parent)
            cv.draw()
            cv.get_tk_widget().pack(fill="x", padx=0, pady=(4,10))

        except ImportError:
            self._fallback_mood_canvas(parent, moods, dim)

    def _fallback_mood_canvas(self, parent, moods, dim):
        cv = tk.Canvas(parent, bg=BG_CARD, height=120, highlightthickness=0)
        cv.pack(fill="x", padx=6, pady=4)
        cv.update_idletasks()
        W=cv.winfo_width() or 900; H,pl,pr,pt,pb=110,70,20,10,24
        for i,label in enumerate(["F**ked","Tired","Stressed","Normal","Good","Awesome"]):
            yy=pt+(5-i)/5*(H-pt-pb)
            cv.create_text(pl-4,yy,text=label,anchor="e",fill=TEXT_MUTED,font=FXS)
            cv.create_line(pl,yy,W-pr,yy,fill=GRID_LINE,dash=(2,4))
        xs,ys,cs=[],[],[]
        for d in range(1,dim+1):
            mood=moods.get(str(d))
            if mood in MOOD_LEVELS:
                idx=MOOD_LEVELS.index(mood)
                x=pl+(d-1)/max(dim-1,1)*(W-pl-pr); y=pt+(5-MOOD_SCORES[idx])/5*(H-pt-pb)
                xs.append(x); ys.append(y); cs.append(MOOD_COLORS[idx])
        if len(xs)>=2:
            pts=[]
            for x,y in zip(xs,ys): pts+=[x,y]
            cv.create_line(*pts,fill=ACCENT2,width=2,smooth=True)
        for x,y,c in zip(xs,ys,cs):
            cv.create_oval(x-5,y-5,x+5,y+5,fill=c,outline=BG_CARD,width=1)

    # ─── Targeted chart redraw (no grid flicker) ───────────────────────────────
    def _redraw_charts(self):
        mk      = getattr(self,"_chart_mk",     month_key(self.cur_year,self.cur_month))
        dim     = getattr(self,"_chart_dim",    calendar.monthrange(self.cur_year,self.cur_month)[1])
        habits  = getattr(self,"_chart_habits", self.data["habits"])
        is_bad  = getattr(self,"_chart_is_bad", False)
        c_color = getattr(self,"_chart_color",  "#4ADE80")
        records = (self.data["bad_records"] if is_bad else self.data["records"]).get(mk, {})
        moods   = self.data["moods"].get(mk, {})
        n       = len(habits)
        day_pct = [
            int(sum(1 for h in habits if records.get(h,{}).get(str(d),False))/n*100) if n else 0
            for d in range(1, dim+1)
        ]
        c_title = "Bad Habit Frequency" if is_bad else "Daily progress"
        c_sub   = "Days you gave in to a bad habit." if is_bad else "Your completed habits as a percentage of your daily goal."

        if hasattr(self,"_area_frame") and self._area_frame.winfo_exists():
            for w in self._area_frame.winfo_children(): w.destroy()
            self._draw_area_chart(self._area_frame, day_pct, dim, c_color, c_title, c_sub, is_bad)

        if not is_bad and hasattr(self,"_mg_frame") and self._mg_frame and self._mg_frame.winfo_exists():
            for w in self._mg_frame.winfo_children(): w.destroy()
            self._draw_mood_chart(self._mg_frame, moods, dim)

    # ─── Row hover ─────────────────────────────────────────────────────────────
    def _row_hover(self, G, grid_row, dim, color):
        for col in range(dim+2):
            w = G.grid_slaves(row=grid_row, column=col)
            if w:
                try: w[0].config(bg=color)
                except tk.TclError: pass

    # ═══════════════════════════════════════════════════════════════════════════
    # Toggle helpers
    # ═══════════════════════════════════════════════════════════════════════════
    def _toggle_cell(self, habit, day, var, cell_label, row_bg, dim, chk_accent):
        new_val = not var.get(); var.set(new_val)
        mk = month_key(self.cur_year, self.cur_month)
        is_bad = (self.active_tab == "bad")
        store  = "bad_records" if is_bad else "records"
        self.data[store].setdefault(mk,{}).setdefault(habit,{})[str(day)] = new_val
        save_data(self.data)

        today_d = self.today.day if self.cur_year==self.today.year and self.cur_month==self.today.month else -1
        unc_bg = TODAY_TINT if day==today_d else row_bg
        unc_fg = ACCENT2    if day==today_d else GRID_LINE
        cell_label.config(
            text="✓" if new_val else "·",
            font=("Segoe UI",10,"bold") if new_val else ("Segoe UI",12),
            bg=chk_accent if new_val else unc_bg,
            fg="white" if new_val else unc_fg,
        )

        records = self.data[store].get(mk, {})
        total   = sum(1 for d in range(1,dim+1) if records.get(habit,{}).get(str(d),False))
        pct     = int(total/dim*100) if dim else 0
        if is_bad:
            pill_bg = FAIL_CLR if total > 0 else BG_CARD
        else:
            pill_bg = chk_accent if pct>=70 else (WARN_CLR if pct>=40 else FAIL_CLR)
        if habit in self._pill_labels:
            self._pill_labels[habit].config(text=str(total), bg=pill_bg)

        self._update_stats(records, self._habits_list(), dim, is_bad)
        self._redraw_charts()

    def _set_mood(self, mood, day):
        """Toggle mood for a day — no full grid refresh."""
        mk = month_key(self.cur_year, self.cur_month)
        m  = self.data["moods"].setdefault(mk, {})
        old_mood = m.get(str(day))
        if old_mood == mood:
            del m[str(day)]
            new_mood = None
        else:
            m[str(day)] = mood
            new_mood = mood
        save_data(self.data)

        # Update only the dot widgets for this day (no grid rebuild)
        dim = self._chart_dim if hasattr(self, "_chart_dim") else calendar.monthrange(self.cur_year,self.cur_month)[1]
        for mi, (mlabel, mcolor) in enumerate(zip(MOOD_LEVELS, MOOD_COLORS)):
            dot = self._mood_dots.get((day, mi))
            if dot and dot.winfo_exists():
                selected = (new_mood == mlabel)
                dot.config(text="●" if selected else "○",
                           fg=mcolor if selected else GRID_LINE)

        # Redraw only the mood chart
        if hasattr(self,"_mg_frame") and self._mg_frame and self._mg_frame.winfo_exists():
            moods = self.data["moods"].get(mk, {})
            for w in self._mg_frame.winfo_children(): w.destroy()
            self._draw_mood_chart(self._mg_frame, moods, dim)

    # ═══════════════════════════════════════════════════════════════════════════
    # Stats
    # ═══════════════════════════════════════════════════════════════════════════
    def _update_stats(self, records, habits, dim, is_bad=False):
        today_num = self.today.day if (self.cur_year==self.today.year and self.cur_month==self.today.month) else dim
        possible  = len(habits) * today_num
        done = sum(
            sum(1 for d in range(1,today_num+1) if records.get(h,{}).get(str(d),False))
            for h in habits
        )
        pct    = int(done/possible*100) if possible else 0
        streak = self._calc_streak(is_bad)
        best   = max(habits, key=lambda h: sum(1 for d in range(1,dim+1) if records.get(h,{}).get(str(d),False)), default="—")
        bc     = sum(1 for d in range(1,dim+1) if records.get(best,{}).get(str(d),False))
        if is_bad:
            self.stats_label.config(text=(
                f"⚠️  {done} bad acts\n"
                f"📉  {pct}% rate\n"
                f"😤  {streak}d streak\n"
                f"🔴  {best[:18]}\n"
                f"    ({bc} days)"
            ))
        else:
            self.stats_label.config(text=(
                f"✅  {done}/{possible}\n"
                f"📈  {pct}% done\n"
                f"🔥  {streak}d streak\n"
                f"🏆  {best[:18]}\n"
                f"    ({bc} days)"
            ))

    def _calc_streak(self, is_bad=False):
        habits = self.data["bad_habits"] if is_bad else self.data["habits"]
        store  = "bad_records" if is_bad else "records"
        if not habits: return 0
        streak, date = 0, datetime.date.today()
        while True:
            rec  = self.data[store].get(month_key(date.year,date.month), {})
            done = sum(1 for h in habits if rec.get(h,{}).get(str(date.day),False))
            if done == 0: break
            streak += 1; date -= datetime.timedelta(days=1)
        return streak

    # ═══════════════════════════════════════════════════════════════════════════
    # Navigation
    # ═══════════════════════════════════════════════════════════════════════════
    def _prev_month(self):
        if self.cur_month==1: self.cur_month=12; self.cur_year-=1
        else: self.cur_month-=1
        self.refresh_grid()

    def _next_month(self):
        if self.cur_month==12: self.cur_month=1; self.cur_year+=1
        else: self.cur_month+=1
        self.refresh_grid()

    def _goto_today(self):
        self.cur_year=self.today.year; self.cur_month=self.today.month
        self.refresh_grid()

    # ═══════════════════════════════════════════════════════════════════════════
    # Habit management — Good tab
    # ═══════════════════════════════════════════════════════════════════════════
    def _add_habit(self):
        name = simpledialog.askstring("Add Habit","Habit name:",parent=self)
        if name and name.strip():
            self.data["habits"].append(name.strip()); save_data(self.data); self.refresh_grid()

    def _rename_habit(self):
        sel = self.habit_listbox.curselection()
        if not sel: messagebox.showinfo("Select","Select a habit first.",parent=self); return
        idx,old = sel[0], self.data["habits"][sel[0]]
        new = simpledialog.askstring("Rename","New name:",initialvalue=old,parent=self)
        if new and new.strip() and new.strip()!=old:
            for mk in self.data["records"]:
                if old in self.data["records"][mk]:
                    self.data["records"][mk][new.strip()] = self.data["records"][mk].pop(old)
            self.data["habits"][idx]=new.strip(); save_data(self.data); self.refresh_grid()

    def _remove_habit(self):
        sel = self.habit_listbox.curselection()
        if not sel: messagebox.showinfo("Select","Select a habit first.",parent=self); return
        name = self.data["habits"][sel[0]]
        if messagebox.askyesno("Remove",f'Remove "{name}"?',parent=self):
            self.data["habits"].pop(sel[0]); save_data(self.data); self.refresh_grid()

    # ── Bad habits management ──────────────────────────────────────────────────
    def _add_bad_habit(self):
        name = simpledialog.askstring("Add Bad Habit","Bad habit name:",parent=self)
        if name and name.strip():
            self.data["bad_habits"].append(name.strip()); save_data(self.data); self.refresh_grid()

    def _rename_bad_habit(self):
        sel = self.habit_listbox.curselection()
        if not sel: messagebox.showinfo("Select","Select a habit first.",parent=self); return
        idx,old = sel[0], self.data["bad_habits"][sel[0]]
        new = simpledialog.askstring("Rename","New name:",initialvalue=old,parent=self)
        if new and new.strip() and new.strip()!=old:
            for mk in self.data["bad_records"]:
                if old in self.data["bad_records"][mk]:
                    self.data["bad_records"][mk][new.strip()] = self.data["bad_records"][mk].pop(old)
            self.data["bad_habits"][idx]=new.strip(); save_data(self.data); self.refresh_grid()

    def _remove_bad_habit(self):
        sel = self.habit_listbox.curselection()
        if not sel: messagebox.showinfo("Select","Select a habit first.",parent=self); return
        name = self.data["bad_habits"][sel[0]]
        if messagebox.askyesno("Remove",f'Remove "{name}"?',parent=self):
            self.data["bad_habits"].pop(sel[0]); save_data(self.data); self.refresh_grid()

    # ═══════════════════════════════════════════════════════════════════════════
    # Misc
    # ═══════════════════════════════════════════════════════════════════════════
    def _save_goal(self):
        self.data["goal"] = self.goal_var.get(); save_data(self.data)

    def _on_close(self):
        save_data(self.data); self.destroy()

# ─── Entry point ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = HabitTrackerApp()
    app.mainloop()
