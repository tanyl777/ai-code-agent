#!/usr/bin/env python3
"""
AI 编程助手 — 图形化界面 (tkinter)

用法:
    python gui.py

特性:
    - 4 个功能标签页：代码生成 / 审查 / 测试 / Commit
    - 菜单栏 → ⚙️ 设置 → API 密钥 + 模型厂商选择
    - API Key 本地保存，启动自动重连
    - 后台异步执行，界面不卡顿
"""

import io
import json
import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
from typing import Any

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from agent import get_llm, create_agent, reset_agent, reconfigure_llm, clear_cache, cache_stats
from config import DEFAULT_CONFIG
from tools.code_interpreter import generate_and_run, _execute_code, SAFE_BUILTINS
from tools.static_reviewer import review_code
from tools.git_commit import _get_diffs, _generate_commit_message, _get_changed_files, _get_branch
from tools.test_generator import generate_and_test

# ═══════════════════════════════════════════════════
# 模型厂商预设
# ═══════════════════════════════════════════════════
PROVIDERS = {
    "DeepSeek": {
        "base_url": "https://api.deepseek.com/anthropic",
        "models": ["deepseek-chat", "deepseek-v3", "deepseek-r1", "deepseek-v4-pro[1m]"],
    },
    "Anthropic Claude": {
        "base_url": "https://api.anthropic.com",
        "models": ["claude-sonnet-4-6", "claude-opus-4-8", "claude-haiku-4-5",
                    "claude-sonnet-4-5"],
    },
    "Ollama (本地)": {
        "base_url": "http://localhost:11434",
        "models": ["qwen3", "llama3", "codellama", "deepseek-r1:8b", "mistral"],
    },
    "自定义": {
        "base_url": "",
        "models": [],
    },
}

SETTINGS_FILE = os.path.join(os.path.dirname(__file__), ".gui_settings.json")

# VS Code 风格主题
THEMES = {
    "Dark (默认)": {"bg":"#1e1e1e","panel":"#252526","editor_bg":"#1e1e1e","editor_fg":"#d4d4d4",
                     "output_bg":"#1e1e1e","output_fg":"#d4d4d4","line_bg":"#252526",
                     "accent":"#007acc","btn_bg":"#0e639c","btn_fg":"#fff","status_bg":"#007acc","status_fg":"#fff"},
    "Light":       {"bg":"#fff","panel":"#f3f3f3","editor_bg":"#fff","editor_fg":"#333",
                     "output_bg":"#fff","output_fg":"#333","line_bg":"#f3f3f3",
                     "accent":"#007acc","btn_bg":"#007acc","btn_fg":"#fff","status_bg":"#007acc","status_fg":"#fff"},
}


# ═══════════════════════════════════════════════════
# 设置对话框
# ═══════════════════════════════════════════════════
class SettingsDialog(tk.Toplevel):
    """Modal settings dialog for API configuration."""

    def __init__(self, parent, on_connect, current_theme="Dark (默认)"):
        super().__init__(parent)
        self.on_connect = on_connect
        self._parent_gui: Any = None  # set by parent after creation
        self.current_theme = current_theme
        self.title("⚙️ API 设置")
        self.geometry("500x440")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self._build()
        self._load()
        self.protocol("WM_DELETE_WINDOW", self.destroy)

    def _build(self):
        # ── API Key ──
        frame = ttk.LabelFrame(self, text="🔑 API 密钥", padding=10)
        frame.pack(fill=tk.X, padx=12, pady=(12, 4))

        row = ttk.Frame(frame)
        row.pack(fill=tk.X)
        ttk.Label(row, text="Key:", width=5).pack(side=tk.LEFT)
        self.api_key_var = tk.StringVar()
        self.key_entry = ttk.Entry(row, textvariable=self.api_key_var, show="●", width=42)
        self.key_entry.pack(side=tk.LEFT, padx=5)
        self.show_var = tk.BooleanVar()
        ttk.Checkbutton(row, text="👁", variable=self.show_var,
                        command=lambda: self.key_entry.config(show="" if self.show_var.get() else "●"),
                        width=3).pack(side=tk.LEFT)

        # ── Provider + Model ──
        frame2 = ttk.LabelFrame(self, text="🤖 模型选择", padding=10)
        frame2.pack(fill=tk.X, padx=12, pady=4)

        r1 = ttk.Frame(frame2)
        r1.pack(fill=tk.X, padx=12, pady=6)
        ttk.Label(r1, text="厂商:", width=8).pack(side=tk.LEFT)
        self.provider_var = tk.StringVar(value="DeepSeek")
        self.provider_cb = ttk.Combobox(r1, textvariable=self.provider_var,
                                        values=list(PROVIDERS.keys()), state="readonly", width=20)
        self.provider_cb.pack(side=tk.LEFT, padx=5)
        self.provider_cb.bind("<<ComboboxSelected>>", self._on_provider)

        r2 = ttk.Frame(frame2)
        r2.pack(fill=tk.X, padx=12, pady=6)
        ttk.Label(r2, text="模型:", width=8).pack(side=tk.LEFT)
        self.model_var = tk.StringVar()
        self.model_cb = ttk.Combobox(r2, textvariable=self.model_var, width=38)
        self.model_cb.pack(side=tk.LEFT, padx=5)

        r3 = ttk.Frame(frame2)
        r3.pack(fill=tk.X, padx=12, pady=6)
        ttk.Label(r3, text="API URL:", width=8).pack(side=tk.LEFT)
        self.url_var = tk.StringVar()
        ttk.Entry(r3, textvariable=self.url_var, width=42).pack(side=tk.LEFT, padx=5)

        self._on_provider()

        # ── 主题 ──
        frame3 = ttk.LabelFrame(self, text="🎨 主题 (仿 VSCode)", padding=10)
        frame3.pack(fill=tk.X, padx=12, pady=4)
        tr = ttk.Frame(frame3); tr.pack(fill=tk.X, padx=12, pady=6)
        ttk.Label(tr, text="配色:", width=8).pack(side=tk.LEFT)
        self.theme_var = tk.StringVar(value=self.current_theme)
        tc = ttk.Combobox(tr, textvariable=self.theme_var, values=list(THEMES.keys()),
                          state="readonly", width=28)
        tc.pack(side=tk.LEFT, padx=5)
        tc.bind("<<ComboboxSelected>>", lambda e: self._preview_theme())
        ttk.Button(tr, text="预览", command=self._preview_theme).pack(side=tk.LEFT, padx=5)

        # ── Buttons ──
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill=tk.X, padx=12, pady=(12, 10))
        self.status_lbl = ttk.Label(btn_frame, text="", foreground="gray")
        self.status_lbl.pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="取消", command=self.destroy).pack(side=tk.RIGHT, padx=5)
        self.test_btn = ttk.Button(btn_frame, text="🔗 测试连接", command=self._test_connection)
        self.test_btn.pack(side=tk.RIGHT, padx=5)
        self.save_btn = ttk.Button(btn_frame, text="💾 保存并连接", command=self._save_and_connect)
        self.save_btn.pack(side=tk.RIGHT, padx=5)

    def _on_provider(self, event=None):
        p = self.provider_var.get()
        info = PROVIDERS.get(p, {})
        self.url_var.set(info.get("base_url", ""))
        models = info.get("models", [])
        self.model_cb.config(values=models, state="readonly" if models else "normal")
        if models:
            self.model_var.set(models[0])
        if p == "自定义":
            self.model_cb.config(state="normal")

    def _preview_theme(self):
        """Live preview theme on main window."""
        name = self.theme_var.get()
        if hasattr(self, '_parent_gui') and self._parent_gui:
            self._parent_gui._apply_theme(name)

    def _get_values(self):
        return {
            "api_key": self.api_key_var.get().strip(),
            "provider": self.provider_var.get(),
            "model": self.model_var.get().strip(),
            "base_url": self.url_var.get().strip(),
            "theme": self.theme_var.get() if hasattr(self, 'theme_var') else "Dark (默认)",
        }

    def _test_connection(self):
        v = self._get_values()
        if not v["api_key"] and v["provider"] != "Ollama (本地)":
            self.status_lbl.config(text="⚠ 请先填入 API Key", foreground="red")
            return
        self.status_lbl.config(text="⏳ 测试中...", foreground="gray")
        self.test_btn.config(state="disabled")
        self.save_btn.config(state="disabled")
        threading.Thread(target=self._do_test, args=(v,), daemon=True).start()

    def _do_test(self, v):
        try:
            reconfigure_llm(api_key=v["api_key"], model=v["model"], base_url=v["base_url"])
            llm = get_llm()
            resp = llm.invoke("hi")
            text = resp.content if hasattr(resp, "content") else str(resp)
            if isinstance(text, list):
                text = str(text)
            self._update_status(f"✅ 连接成功！响应: {text[:50].strip()}...", "green", True)
        except Exception as e:
            self._update_status(f"❌ 连接失败: {e}", "red", True)

    def _update_status(self, msg, color, enable_buttons):
        def _do():
            self.status_lbl.config(text=msg, foreground=color)
            self.test_btn.config(state="normal")
            self.save_btn.config(state="normal")
        self.after(0, _do)

    def _save_and_connect(self):
        v = self._get_values()
        if not v["api_key"] and v["provider"] != "Ollama (本地)":
            self.status_lbl.config(text="⚠ 请先填入 API Key", foreground="red")
            return
        self.status_lbl.config(text="⏳ 连接中...", foreground="gray")
        threading.Thread(target=self._do_save_connect, args=(v,), daemon=True).start()

    def _do_save_connect(self, v):
        try:
            reconfigure_llm(api_key=v["api_key"], model=v["model"], base_url=v["base_url"])
            llm = get_llm()
            resp = llm.invoke("hi")
            text = resp.content if hasattr(resp, "content") else str(resp)
            if isinstance(text, list):
                text = str(text)
            # Save to file
            try:
                with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
                    json.dump(v, f, ensure_ascii=False, indent=2)
            except OSError:
                pass
            self.after(0, lambda: self.on_connect(v, True))
            self.after(0, self.destroy)
        except Exception as e:
            self._update_status(f"❌ 失败: {e}", "red", True)

    def _load(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("provider") in PROVIDERS:
                    self.provider_var.set(data["provider"])
                    self._on_provider()
                if data.get("model"):
                    self.model_var.set(data["model"])
                if data.get("base_url"):
                    self.url_var.set(data["base_url"])
                if data.get("api_key"):
                    self.api_key_var.set(data["api_key"])
                if data.get("theme") in THEMES:
                    self.theme_var.set(data["theme"])
                    self.current_theme = data["theme"]
        except (OSError, json.JSONDecodeError):
            pass


# ═══════════════════════════════════════════════════
# 主窗口
# ═══════════════════════════════════════════════════
class AIAgentGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("AI 编程助手 Agent")
        self.root.geometry("960x700")
        self.root.minsize(780, 500)
        self._llm_ready = False
        self._last_test_code = ""
        self._current_theme = "Dark (默认)"
        self._load_theme()

        self._setup_style()
        self._build_menu()
        self._build_main()
        threading.Thread(target=self._auto_connect, daemon=True).start()

    def _load_theme(self):
        try:
            if os.path.exists(SETTINGS_FILE):
                d = json.load(open(SETTINGS_FILE, encoding="utf-8"))
                if d.get("theme") in THEMES: self._current_theme = d["theme"]
        except: pass

    def _apply_theme(self, name):
        if name not in THEMES: return
        self._current_theme = name
        t = THEMES[name]
        self.root.configure(bg=t["bg"])
        # ttk
        s = ttk.Style()
        s.configure("TNotebook", background=t["bg"])
        s.configure("TNotebook.Tab", background=t["panel"], foreground=t["editor_fg"])
        s.map("TNotebook.Tab", background=[("selected", t["accent"])], foreground=[("selected", t["btn_fg"])])
        s.configure("TFrame", background=t["bg"])
        # tk widgets
        self._recolor(self.root, t)

    def _recolor(self, parent, t):
        for c in parent.winfo_children():
            try:
                cl = c.winfo_class()
                if cl in ("Frame","Labelframe"): c.configure(bg=t["bg"])
                elif cl == "Label": c.configure(bg=t["bg"])
                elif cl == "Text": c.configure(bg=t["editor_bg"], fg=t["editor_fg"], insertbackground=t["editor_fg"])
                elif cl == "Canvas": c.configure(bg=t["line_bg"])
                elif cl == "Entry": c.configure(bg=t["editor_bg"], fg=t["editor_fg"], insertbackground=t["editor_fg"])
            except: pass
            self._recolor(c, t)

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        # Custom colors
        style.configure("Title.TLabel", font=("Microsoft YaHei UI", 15, "bold"))
        style.configure("Subtitle.TLabel", font=("Microsoft YaHei UI", 9), foreground="#666")
        style.configure("Section.TLabel", font=("Microsoft YaHei UI", 10, "bold"))
        style.configure("Status.TLabel", font=("Microsoft YaHei UI", 9))
        style.configure("Primary.TButton", font=("Microsoft YaHei UI", 10))

    def _build_menu(self):
        menubar = tk.Menu(self.root, font=("Microsoft YaHei UI", 9))

        # Settings menu
        settings_menu = tk.Menu(menubar, tearoff=0, font=("Microsoft YaHei UI", 9))
        settings_menu.add_command(label="⚙️ API 配置", command=self._open_settings)
        settings_menu.add_command(label="🗑 清除缓存", command=self._do_clear_cache)
        settings_menu.add_separator()
        settings_menu.add_command(label="退出", command=self.root.quit)
        menubar.add_cascade(label="设置", menu=settings_menu)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0, font=("Microsoft YaHei UI", 9))
        help_menu.add_command(label="📖 使用指南", command=self._show_help)
        help_menu.add_command(label="ℹ️ 关于", command=self._show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)

        self.root.config(menu=menubar)

    def _build_main(self):
        # ── Header ──
        header = ttk.Frame(self.root, padding=(15, 12, 15, 5))
        header.pack(fill=tk.X)
        ttk.Label(header, text="🤖 AI 编程助手", style="Title.TLabel").pack(side=tk.LEFT)
        self.conn_dot = ttk.Label(header, text="🔴", font=("", 12))
        self.conn_dot.pack(side=tk.RIGHT, padx=(0, 5))
        self.conn_label = ttk.Label(header, text="未连接", style="Subtitle.TLabel")
        self.conn_label.pack(side=tk.RIGHT)

        # ── Connection hint (thin bar, shown when not connected) ──
        self.banner = tk.Frame(self.root, bg="#5a3e00", height=28)
        self._build_banner()

        # ── Notebook (always visible; LLM tabs check connection) ──
        self.notebook = ttk.Notebook(self.root, padding=5)
        self._build_code_tab()
        self._build_review_tab()
        self._build_test_tab()
        self._build_commit_tab()
        self._build_editor_tab()
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=(0, 5))

        # ── Status bar ──
        self.status_var = tk.StringVar(value="就绪 — 请通过菜单 设置 → ⚙️ API 配置 连接模型")
        status_bar = ttk.Label(
            self.root, textvariable=self.status_var, relief=tk.SUNKEN,
            anchor=tk.W, padding=(12, 4), style="Status.TLabel",
        )
        status_bar.pack(fill=tk.X, side=tk.BOTTOM)

    def _build_banner(self):
        """Connection hint bar."""
        for w in self.banner.winfo_children():
            w.destroy()
        tk.Label(self.banner, text="⚠ 未连接 AI 模型  |  代码生成/审查/测试/提交 不可用  |  📄 文本编辑器可正常使用",
                font=("Microsoft YaHei UI", 9), bg="#5a3e00", fg="#ffcc00").pack(side=tk.LEFT, padx=12, pady=4)
        tk.Button(self.banner, text="⚙️ 连接", command=self._open_settings,
                  font=("Microsoft YaHei UI", 8), bg="#007acc", fg="white",
                  relief=tk.FLAT, padx=8).pack(side=tk.RIGHT, padx=8, pady=2)

    # ═══════════════════════════════════════════════
    # Connection management
    # ═══════════════════════════════════════════════
    def _open_settings(self):
        dlg = SettingsDialog(self.root, self._on_connected, self._current_theme)
        dlg._parent_gui = self

    def _on_connected(self, settings, success):
        if success:
            if settings.get("theme"): self._apply_theme(settings["theme"])
            self._llm_ready = True
            self.conn_dot.config(text="🟢")
            self.conn_label.config(
                text=f"{settings['provider']} / {settings['model']}",
                foreground="#2d7d46",
            )
            self._set_status(f"🟢 已连接 — {settings['provider']} / {settings['model']}")
            self.banner.pack_forget()

    def _auto_connect(self):
        """Try auto-connect (runs in thread)."""
        try:
            if os.path.exists(SETTINGS_FILE):
                with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                api_key = data.get("api_key", "")
                if api_key:
                    reconfigure_llm(api_key=api_key, model=data.get("model",""), base_url=data.get("base_url",""))
                    llm = get_llm()
                    resp = llm.invoke("hi")
                    self.root.after(0, lambda: self._on_connected(data, True))
                    return
        except Exception: pass
        self.root.after(0, lambda: self.banner.pack(fill=tk.X, padx=5, pady=(0, 3)))

    def _ensure_ready(self) -> bool:
        if not self._llm_ready:
            messagebox.showwarning("未连接", "请先设置 API：菜单栏 → 设置 → ⚙️ API 配置")
            return False
        return True

    def _do_clear_cache(self):
        removed = clear_cache()
        stats = cache_stats()
        messagebox.showinfo("缓存清理", f"已清理 {removed} 条\n当前: {stats['entries']} 条 / {stats['size_kb']} KB")

    # ═══════════════════════════════════════════════
    # ═══════════════════════════════════════════════
    # Tab 1: 代码生成
    # ═══════════════════════════════════════════════
    def _build_code_tab(self):
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="  📝 代码生成  ")

        # ── Row 1: Input ──
        ttk.Label(tab, text="用自然语言描述你想要的功能：", style="Section.TLabel").pack(anchor=tk.W)
        hint = ttk.Label(tab, text='提示：越具体越好，例如: 实现一个二分查找函数，输入有序列表和目标值，返回索引或 -1',
                         foreground="#999", font=("Microsoft YaHei UI", 8))
        hint.pack(anchor=tk.W)

        input_frame = ttk.Frame(tab)
        input_frame.pack(fill=tk.X, pady=(5, 0))
        self.code_input = scrolledtext.ScrolledText(input_frame, height=3, font=("Consolas", 10),
                                                     relief=tk.GROOVE, borderwidth=1)
        self.code_input.pack(fill=tk.X, side=tk.LEFT, expand=True)
        self.code_input.insert("1.0", "实现一个归并排序函数，输入列表返回排序后的列表")

        gen_btn_frame = ttk.Frame(input_frame)
        gen_btn_frame.pack(side=tk.RIGHT, padx=(5, 0), fill=tk.Y)
        ttk.Button(gen_btn_frame, text="🚀\n生成", command=self._do_code_gen, width=6).pack(pady=2)

        # ── Action bar (pack FIRST at bottom to ensure visibility) ──
        code_btn_frame = ttk.Frame(tab)
        code_btn_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
        ttk.Button(code_btn_frame, text="▶ 运行", command=self._do_run_code).pack(side=tk.LEFT, padx=3)
        ttk.Button(code_btn_frame, text="🐛 Debug", command=self._do_debug_code).pack(side=tk.LEFT, padx=3)
        ttk.Button(code_btn_frame, text="💾 保存", command=self._save_generated_code).pack(side=tk.LEFT, padx=3)
        ttk.Button(code_btn_frame, text="🔍 审查 →", command=self._jump_gen_to_review).pack(side=tk.LEFT, padx=3)
        ttk.Button(code_btn_frame, text="🧪 测试 →", command=self._jump_gen_to_test).pack(side=tk.LEFT, padx=3)
        self.code_json_var = tk.BooleanVar()
        ttk.Checkbutton(code_btn_frame, text="JSON", variable=self.code_json_var).pack(side=tk.LEFT, padx=5)
        ttk.Button(code_btn_frame, text="清空", command=self._clear_code_tab).pack(side=tk.RIGHT, padx=3)

        # ── Row 2: Code + output (resizable PanedWindow) ──
        ttk.Label(tab, text="代码（可直接编辑, 点击行号设断点, 拖拽分隔条调整大小）：",
                  style="Section.TLabel").pack(anchor=tk.W, pady=(10, 0))

        self.code_pane = tk.PanedWindow(tab, orient=tk.VERTICAL, bg="#555",
                                         sashwidth=8, sashrelief=tk.RAISED)
        self.code_pane.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        # Top: editor + line numbers
        editor_frame = tk.Frame(self.code_pane)
        self._breakpoints: set[int] = set()
        self.line_canvas = tk.Canvas(editor_frame, width=40, bg="#252525", highlightthickness=0)
        self.line_canvas.pack(side=tk.LEFT, fill=tk.Y)
        self.line_canvas.bind("<Button-1>", self._on_line_click)
        self.code_editor = tk.Text(editor_frame, font=("Consolas", 11), relief=tk.FLAT,
                                    bg="#1e1e1e", fg="#d4d4d4", insertbackground="white",
                                    undo=True, wrap=tk.NONE)
        self.code_editor.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.code_editor.insert("1.0", "# 点击 生成 按钮，或直接在此编写/粘贴代码\n")
        self.code_editor.bind("<KeyRelease>", lambda e: self._update_line_numbers())
        self.code_editor.bind("<MouseWheel>", lambda e: self._update_line_numbers())
        self.code_pane.add(editor_frame, stretch="always")

        # Bottom: execution output
        self.run_output = tk.Text(self.code_pane, font=("Consolas", 10), relief=tk.FLAT,
                                   bg="#f5f5f5", fg="#333", state=tk.DISABLED)
        self.code_pane.add(self.run_output, stretch="always")

        self._update_line_numbers()

        self._last_generated_code = ""

    def _line_height(self): return 17

    def _update_line_numbers(self):
        """Redraw line numbers with breakpoint markers."""
        self.line_canvas.delete("all")
        code = self.code_editor.get("1.0", tk.END)
        n = code.count("\n") + (0 if code.endswith("\n") else 1)
        lh = self._line_height()
        for i in range(1, n + 1):
            y0 = (i - 1) * lh + 2
            if i in self._breakpoints:
                self.line_canvas.create_rectangle(0, y0, 38, y0 + lh, fill="#e51400", outline="#e51400")
                self.line_canvas.create_text(19, y0 + lh/2, text=str(i), fill="white", font=("Consolas", 7, "bold"))
            else:
                self.line_canvas.create_text(30, y0 + lh/2, text=str(i), anchor=tk.E,
                                              fill="#888", font=("Consolas", 7))

    def _on_line_click(self, event):
        """Toggle breakpoint on clicked line number."""
        ln = event.y // self._line_height() + 1
        total = int(self.code_editor.index("end-1c").split(".")[0])
        if 1 <= ln <= total + 1:
            if ln in self._breakpoints: self._breakpoints.discard(ln)
            else: self._breakpoints.add(ln)
            self._update_line_numbers()

    def _clear_code_tab(self):
        """Clear editor, output, and breakpoints."""
        self._breakpoints.clear()
        self.code_editor.delete("1.0", tk.END)
        self.run_output.config(state=tk.NORMAL)
        self.run_output.delete("1.0", tk.END)
        self.run_output.config(state=tk.DISABLED)
        self._update_line_numbers()

    def _get_code_from_editor(self) -> str:
        """Get current code from the editor."""
        code = self.code_editor.get("1.0", tk.END).strip()
        if code.startswith("# 点击"): return ""
        return code

    def _set_code_editor(self, code: str):
        """Set code in the editor (UI thread safe)."""
        def _do():
            self.code_editor.delete("1.0", tk.END)
            self.code_editor.insert("1.0", code)
            self._update_line_numbers()
        self.root.after(0, _do)

    def _append_run_output(self, text: str):
        """Append to the run output area."""
        def _do():
            self.run_output.config(state=tk.NORMAL)
            self.run_output.insert(tk.END, text)
            self.run_output.see(tk.END)
            self.run_output.config(state=tk.DISABLED)
        self.root.after(0, _do)

    def _clear_run_output(self):
        def _do():
            self.run_output.config(state=tk.NORMAL)
            self.run_output.delete("1.0", tk.END)
            self.run_output.config(state=tk.DISABLED)
        self.root.after(0, _do)

    def _do_code_gen(self):
        if not self._ensure_ready(): return
        request = self.code_input.get("1.0", tk.END).strip()
        if not request:
            messagebox.showwarning("提示", "请输入需求描述")
            return
        self._set_status("⏳ 正在生成代码...")
        self._run_async(lambda: self._sync_code_gen(request))

    def _sync_code_gen(self, request: str):
        try:
            llm = get_llm()
            result = generate_and_run(request, llm)
            if result["status"] == "success":
                code = result.get("content", "")
                self._set_code_editor(code)
                self._last_generated_code = code
                self._clear_run_output()
                self._append_run_output(f"✅ 生成成功 (第{result['metadata']['attempts']}次尝试)\n{'═'*40}\n")
                stdout = result.get("metadata", {}).get("stdout", "")
                if stdout:
                    self._append_run_output(stdout)
                self._set_status(f"✅ 成功 (第{result['metadata']['attempts']}次尝试)")
            else:
                self._set_code_editor(result.get("content", ""))
                self._clear_run_output()
                self._append_run_output(f"❌ 执行失败 (已尝试{result['metadata']['attempts']}次修正)\n{'═'*40}\n")
                exc = result.get("metadata", {}).get("exception", "")
                if exc:
                    self._append_run_output(exc)
                self._set_status("❌ 失败")
        except Exception as e:
            self._clear_run_output()
            self._append_run_output(f"❌ 异常: {e}")
            self._set_status(f"❌ 错误: {e}")

    def _do_run_code(self):
        """Run the code currently in the editor."""
        code = self._get_code_from_editor()
        if not code:
            messagebox.showwarning("提示", "代码为空，请先生成代码或粘贴代码")
            return
        self._set_status("⏳ 正在执行...")
        self._clear_run_output()
        self._append_run_output("▶ 运行中...\n" + "═" * 40 + "\n")
        self._run_async(lambda: self._sync_run_code(code))

    def _sync_run_code(self, code: str):
        try:
            result = _execute_code(code)
            if result["exception"] is None:
                if result["stdout"]:
                    self._append_run_output(result["stdout"])
                else:
                    self._append_run_output("(无输出)\n")
                self._append_run_output("\n✅ 执行成功")
                self._set_status("✅ 运行成功")
            else:
                if result["stdout"]:
                    self._append_run_output(result["stdout"])
                self._append_run_output(f"\n❌ 运行错误:\n{result['exception']}")
                self._set_status("❌ 运行错误")
        except Exception as e:
            self._append_run_output(f"\n❌ 异常: {e}")
            self._set_status(f"❌ 错误: {e}")

    def _do_debug_code(self):
        """Run code in debug mode — show line trace, full var dump at breakpoints."""
        code = self._get_code_from_editor()
        if not code:
            messagebox.showwarning("提示", "代码为空，请先生成代码或粘贴代码")
            return
        bps = self._breakpoints.copy()
        info = f"{len(bps)} 个断点" if bps else "全部行追踪"
        self._set_status(f"🐛 Debug 运行中 ({info})...")
        self._clear_run_output()
        self._append_run_output(f"🐛 Debug — 断点: {sorted(bps) if bps else '全部行'}\n{'═'*60}\n")
        self._run_async(lambda: self._sync_debug_code(code, bps))

    def _sync_debug_code(self, code: str, breakpoints: set[int]):
        import io as _io, sys as _sys, traceback as _tb
        source_lines = code.split("\n")
        trace_lines = []
        bps = breakpoints

        def _trace_func(frame, event, arg):
            if event == "line":
                ln = frame.f_lineno
                is_bp = ln in bps
                if is_bp or not bps:
                    src = source_lines[ln-1].strip() if ln <= len(source_lines) else f"<L{ln}>"
                    marker = "🔴" if is_bp else "  "
                    trace_lines.append(f"{marker} L{ln:>3d}: {src}")
                    if is_bp:
                        trace_lines.append(f"    {'═'*20} 断点 L{ln} 变量快照 {'═'*20}")
                        for k, v in frame.f_locals.items():
                            if not k.startswith("__"):
                                trace_lines.append(f"    📌 {k} = {repr(v)[:120]}")
                        trace_lines.append(f"    {'═'*54}")
            return _trace_func

        sc, ec = _io.StringIO(), _io.StringIO()
        _os, _oe = _sys.stdout, _sys.stderr
        _sys.stdout, _sys.stderr = sc, ec
        try:
            _sys.settrace(_trace_func)
            exec(code, {"__builtins__": SAFE_BUILTINS, "__name__": "__main__"})
            _sys.settrace(None)
            self._append_run_output("\n".join(trace_lines) + "\n" + "─"*60 + "\n")
            if sc.getvalue(): self._append_run_output(f"【输出】\n{sc.getvalue()}")
            if ec.getvalue(): self._append_run_output(f"【错误】\n{ec.getvalue()}")
            hits = len([l for l in trace_lines if l.startswith("🔴")])
            self._append_run_output(f"\n✅ Debug 完成 — {len(trace_lines)} 行追踪, {hits} 个断点命中")
            self._set_status(f"🐛 Debug 完成 — {hits} 断点命中")
        except Exception:
            _sys.settrace(None)
            self._append_run_output("\n".join(trace_lines) + "\n" + "─"*60 + "\n")
            if sc.getvalue(): self._append_run_output(f"【输出】\n{sc.getvalue()}")
            self._append_run_output(f"\n❌ 异常:\n{_tb.format_exc()}")
            self._set_status("🐛 Debug — 执行出错")
        finally:
            _sys.stdout, _sys.stderr = _os, _oe

    # ═══════════════════════════════════════════════
    # Tab 2: 代码审查
    # ═══════════════════════════════════════════════
    def _build_review_tab(self):
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="  🔍 代码审查  ")

        top_row = ttk.Frame(tab)
        top_row.pack(fill=tk.X)
        ttk.Label(top_row, text="Python 文件路径 或 直接粘贴代码：", style="Section.TLabel").pack(side=tk.LEFT)
        ttk.Button(top_row, text="📂 选择文件", command=self._browse_review_file).pack(side=tk.RIGHT, padx=5)

        self.review_input = scrolledtext.ScrolledText(
            tab, height=10, font=("Consolas", 10), relief=tk.GROOVE, borderwidth=1,
        )
        self.review_input.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        opt_frame = ttk.Frame(tab)
        opt_frame.pack(fill=tk.X, pady=5)
        ttk.Label(opt_frame, text="圈复杂度阈值:").pack(side=tk.LEFT)
        self.complexity_var = tk.IntVar(value=DEFAULT_CONFIG.review_max_complexity)
        ttk.Spinbox(opt_frame, from_=1, to=50, textvariable=self.complexity_var, width=5).pack(side=tk.LEFT, padx=5)

        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="🔍 开始审查", command=self._do_review).pack(side=tk.LEFT, padx=5)
        self.review_json_var = tk.BooleanVar()
        ttk.Checkbutton(btn_frame, text="JSON 输出", variable=self.review_json_var).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="清空输出", command=lambda: self.review_output.delete("1.0", tk.END)).pack(
            side=tk.RIGHT, padx=5)

        ttk.Label(tab, text="审查报告：", style="Section.TLabel").pack(anchor=tk.W)
        self.review_output = scrolledtext.ScrolledText(
            tab, font=("Consolas", 10), relief=tk.GROOVE, borderwidth=1,
        )
        self.review_output.pack(fill=tk.BOTH, expand=True)

        # Action bar
        self.review_actions = ttk.Frame(tab)
        self.review_actions.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(self.review_actions, text="🧪 生成测试 →", command=self._jump_to_test_with_code).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.review_actions, text="📋 生成 Commit →", command=self._jump_to_commit).pack(side=tk.LEFT, padx=5)
        self.review_actions.pack_forget()

    def _browse_review_file(self):
        path = filedialog.askopenfilename(filetypes=[("Python files", "*.py"), ("All files", "*.*")])
        if path:
            self.review_input.delete("1.0", tk.END)
            self.review_input.insert("1.0", path)

    def _do_review(self):
        if not self._ensure_ready(): return
        source = self.review_input.get("1.0", tk.END).strip()
        if not source:
            messagebox.showwarning("提示", "请输入文件路径或代码")
            return
        self._set_status("⏳ 正在审查代码...")
        self._run_async(lambda: self._sync_review(source, self.complexity_var.get()))

    def _sync_review(self, source: str, complexity: int):
        try:
            result = review_code(source, complexity)
            self._show_result(self.review_output, result, is_json=self.review_json_var.get())
            self._show_actions(self.review_actions)
            n = result["metadata"]["total_issues"]
            self._set_status(f"审查完成 — {n} 个问题" if n else "✅ 审查通过，未发现问题")
        except Exception as e:
            self._show_error(self.review_output, e)
            self._set_status(f"❌ 错误: {e}")

    # ═══════════════════════════════════════════════
    # Tab 3: 测试生成
    # ═══════════════════════════════════════════════
    def _build_test_tab(self):
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="  🧪 测试生成  ")

        top_row = ttk.Frame(tab)
        top_row.pack(fill=tk.X)
        ttk.Label(top_row, text="Python 源文件路径 或 粘贴源代码：", style="Section.TLabel").pack(side=tk.LEFT)
        ttk.Button(top_row, text="📂 选择文件", command=self._browse_test_file).pack(side=tk.RIGHT, padx=5)

        self.test_input = scrolledtext.ScrolledText(
            tab, height=10, font=("Consolas", 10), relief=tk.GROOVE, borderwidth=1,
        )
        self.test_input.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        opt_frame = ttk.Frame(tab)
        opt_frame.pack(fill=tk.X, pady=5)
        ttk.Label(opt_frame, text="最大修正次数:").pack(side=tk.LEFT)
        self.retry_var = tk.IntVar(value=2)
        ttk.Spinbox(opt_frame, from_=0, to=5, textvariable=self.retry_var, width=5).pack(side=tk.LEFT, padx=5)

        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="🧪 生成测试", command=self._do_test_gen).pack(side=tk.LEFT, padx=5)
        self.test_json_var = tk.BooleanVar()
        ttk.Checkbutton(btn_frame, text="JSON 输出", variable=self.test_json_var).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="💾 保存测试代码", command=self._save_test_code).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="清空输出", command=lambda: self.test_output.delete("1.0", tk.END)).pack(
            side=tk.RIGHT, padx=5)

        ttk.Label(tab, text="生成的测试代码 & 执行结果：", style="Section.TLabel").pack(anchor=tk.W)
        self.test_output = scrolledtext.ScrolledText(
            tab, font=("Consolas", 10), relief=tk.GROOVE, borderwidth=1,
        )
        self.test_output.pack(fill=tk.BOTH, expand=True)

        # Action bar
        self.test_actions = ttk.Frame(tab)
        self.test_actions.pack(fill=tk.X, pady=(5, 0))
        ttk.Button(self.test_actions, text="🔍 审查测试代码 →", command=self._jump_to_review_with_test).pack(side=tk.LEFT, padx=5)
        ttk.Button(self.test_actions, text="📋 生成 Commit →", command=self._jump_to_commit).pack(side=tk.LEFT, padx=5)
        self.test_actions.pack_forget()

    def _browse_test_file(self):
        path = filedialog.askopenfilename(filetypes=[("Python files", "*.py"), ("All files", "*.*")])
        if path:
            self.test_input.delete("1.0", tk.END)
            self.test_input.insert("1.0", path)

    def _save_test_code(self):
        if not self._last_test_code:
            messagebox.showwarning("提示", "请先生成测试代码")
            return
        from pathlib import Path
        default_dir = Path(self.repo_path_var.get()).resolve() / "tests"
        default_dir.mkdir(parents=True, exist_ok=True)
        path = filedialog.asksaveasfilename(
            defaultextension=".py", filetypes=[("Python files", "*.py")],
            initialdir=str(default_dir), initialfile="test_generated.py",
        )
        if path:
            Path(path).write_text(self._last_test_code, encoding="utf-8")
            self._set_status(f"💾 已保存到: {path}")

    def _do_test_gen(self):
        if not self._ensure_ready(): return
        source = self.test_input.get("1.0", tk.END).strip()
        if not source:
            messagebox.showwarning("提示", "请输入文件路径或代码")
            return
        self._set_status("⏳ 正在生成测试...")
        self._run_async(lambda: self._sync_test_gen(source, self.retry_var.get()))

    def _sync_test_gen(self, source: str, max_retries: int):
        try:
            llm = get_llm()
            result = generate_and_test(source, llm, max_retries=max_retries)
            self._last_test_code = result.get("content", "")
            self._show_result(self.test_output, result, is_json=self.test_json_var.get())
            self._show_actions(self.test_actions)
            ok = result["status"] == "success"
            self._set_status("✅ 测试通过" if ok else "❌ 测试失败")
        except Exception as e:
            self._show_error(self.test_output, e)
            self._set_status(f"❌ 错误: {e}")

    # ═══════════════════════════════════════════════
    # Tab 4: Commit 生成
    # ═══════════════════════════════════════════════
    def _build_commit_tab(self):
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="  📋 Commit 生成  ")

        # Row 1: Repo path (LOCAL directory, not URL!)
        top_row = ttk.Frame(tab)
        top_row.pack(fill=tk.X)
        ttk.Label(top_row, text="本地仓库：", style="Section.TLabel").pack(side=tk.LEFT)
        self.repo_path_var = tk.StringVar(value=".")
        ttk.Entry(top_row, textvariable=self.repo_path_var, width=30).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_row, text="📂 浏览", command=self._browse_repo).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_row, text="📊 查看变更", command=self._do_show_diff).pack(side=tk.LEFT, padx=2)
        ttk.Button(top_row, text="📦 暂存全部", command=self._do_stage_all).pack(side=tk.LEFT, padx=2)
        ttk.Label(top_row, text="  ← 本地目录，如 . 或 C:\\项目", foreground="#999",
                  font=("Microsoft YaHei UI", 8)).pack(side=tk.LEFT)

        # Row 2: Remote URL (GitHub URL for push)
        remote_row = ttk.Frame(tab)
        remote_row.pack(fill=tk.X, pady=(5, 0))
        ttk.Label(remote_row, text="推送地址：", style="Section.TLabel").pack(side=tk.LEFT)
        self.remote_var = tk.StringVar(value="https://github.com/tanyl777/ai-code-agent")
        ttk.Entry(remote_row, textvariable=self.remote_var, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(remote_row, text="🔗 设置", command=self._do_set_remote).pack(side=tk.LEFT, padx=2)
        ttk.Button(remote_row, text="📋 检测", command=self._do_detect_remote).pack(side=tk.LEFT, padx=2)
        ttk.Label(remote_row, text="  ← 推送目标，如 https://github.com/...", foreground="#999",
                  font=("Microsoft YaHei UI", 8)).pack(side=tk.LEFT)

        ttk.Label(tab, text="变更预览：", style="Section.TLabel").pack(anchor=tk.W, pady=(10, 0))
        self.diff_output = scrolledtext.ScrolledText(
            tab, height=10, font=("Consolas", 9), relief=tk.GROOVE, borderwidth=1,
        )
        self.diff_output.pack(fill=tk.BOTH, expand=True, pady=(5, 0))

        btn_frame = ttk.Frame(tab)
        btn_frame.pack(fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="📝 生成 Commit Message", command=self._do_commit).pack(side=tk.LEFT, padx=5)
        self.commit_json_var = tk.BooleanVar()
        ttk.Checkbutton(btn_frame, text="JSON 输出", variable=self.commit_json_var).pack(side=tk.LEFT, padx=10)
        ttk.Button(btn_frame, text="清空输出",
                   command=lambda: [self.diff_output.delete("1.0", tk.END),
                                    self.commit_output.delete("1.0", tk.END)]).pack(side=tk.RIGHT, padx=5)

        ttk.Label(tab, text="建议的 Commit Message：", style="Section.TLabel").pack(anchor=tk.W)
        self.commit_output = scrolledtext.ScrolledText(
            tab, height=6, font=("Consolas", 10), relief=tk.GROOVE, borderwidth=1,
        )
        self.commit_output.pack(fill=tk.BOTH, expand=True)

        # Commit action bar
        self.commit_actions = ttk.Frame(tab)
        self.commit_actions.pack(fill=tk.X, pady=(5, 0))
        self.commit_btn = ttk.Button(self.commit_actions, text="✅ 提交 (git commit)", command=self._do_git_commit)
        self.commit_btn.pack(side=tk.LEFT, padx=5)
        self.push_btn = ttk.Button(self.commit_actions, text="🚀 提交并推送 GitHub", command=self._do_commit_and_push)
        self.push_btn.pack(side=tk.LEFT, padx=5)
        self._last_commit_msg = ""
        self.commit_actions.pack_forget()

    def _browse_repo(self):
        path = filedialog.askdirectory(title="选择 Git 仓库目录")
        if path:
            self.repo_path_var.set(path)
            self._do_detect_remote()

    def _do_stage_all(self):
        """Stage all changes (git add -A)."""
        from tools.git_commit import git_add
        repo = self._check_repo()
        if not repo: return
        self._set_status("⏳ 正在暂存所有文件...")
        ok, out = git_add(repo)
        if ok:
            self._set_status("✅ 已暂存全部变更 (git add -A)")
            self._do_show_diff()
        else:
            self._set_status(f"❌ 暂存失败: {out}")

    def _do_set_remote(self):
        """Set the origin remote URL."""
        import subprocess
        repo = self._check_repo()
        if not repo: return
        url = self.remote_var.get().strip()
        if not url:
            messagebox.showwarning("提示", "请输入 GitHub 仓库 URL")
            return
        try:
            # Check if origin already exists
            r = subprocess.run(["git", "-C", str(repo), "remote", "get-url", "origin"],
                              capture_output=True, text=True)
            if r.returncode == 0:
                # Update existing
                subprocess.run(["git", "-C", str(repo), "remote", "set-url", "origin", url], check=True)
                self._set_status(f"✅ 远程仓库已更新: {url}")
            else:
                # Add new
                subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", url], check=True)
                self._set_status(f"✅ 远程仓库已设置: {url}")
        except subprocess.SubprocessError as e:
            self._set_status(f"❌ 设置失败: {e}")

    def _do_detect_remote(self):
        """Auto-detect the origin remote URL."""
        from pathlib import Path
        from tools.git_commit import git_get_remote
        repo = Path(self.repo_path_var.get()).resolve()
        if (repo / ".git").exists():
            remote = git_get_remote(str(repo))
            if remote:
                self.remote_var.set(remote)
                self._set_status(f"检测到远程: {remote}")

    def _check_repo(self) -> str | None:
        """Validate repo path. Return repo string or None (with error popup)."""
        from pathlib import Path
        raw = self.repo_path_var.get().strip()
        if raw.startswith("http://") or raw.startswith("https://"):
            messagebox.showwarning(
                "路径错误",
                f"「本地仓库」需要本地目录路径，不是网址。\n\n"
                f"你输入的是:\n  {raw}\n\n"
                f"正确做法:\n"
                f"  1. 先用 git clone {raw} 克隆到本地\n"
                f"  2. 本地仓库填克隆后的目录路径（如 . 或项目文件夹）\n"
                f"  3. 推送地址填 {raw}"
            )
            return None
        repo = Path(raw).resolve()
        if not (repo / ".git").exists():
            messagebox.showwarning(
                "不是 Git 仓库",
                f"目录下没有 .git 文件夹:\n  {repo}\n\n"
                f"请用 git init 初始化，或 git clone 克隆仓库。"
            )
            return None
        return str(repo)

    def _do_show_diff(self):
        repo = self._check_repo()
        if not repo: return
        self._set_status("⏳ 正在读取 git diff...")
        try:
            staged, unstaged = _get_diffs(str(repo))
            files = _get_changed_files(str(repo))
            self.diff_output.delete("1.0", tk.END)
            self.diff_output.insert("1.0", (
                f"📁 变更文件 ({len(files)}):\n" +
                "\n".join(f"  • {f}" for f in files[:20]) +
                ("\n  ..." if len(files) > 20 else "") +
                f"\n\n{'='*60}\n📌 已暂存 (Staged):\n{'='*60}\n{(staged or '(无)')[:3000]}" +
                f"\n\n{'='*60}\n📌 未暂存 (Unstaged):\n{'='*60}\n{(unstaged or '(无)')[:3000]}"
            ))
            self._set_status(f"已显示 {len(files)} 个变更文件")
        except Exception as e:
            self._show_error(self.diff_output, e)

    def _do_commit(self):
        if not self._ensure_ready(): return
        repo = self._check_repo()
        if not repo: return
        self._set_status("⏳ 正在生成 commit message...")
        self._run_async(lambda: self._sync_commit(repo))

    def _sync_commit(self, repo: str):
        try:
            staged, unstaged = _get_diffs(repo)
            files = _get_changed_files(repo)
            branch = _get_branch(repo)
            if not staged and not unstaged:
                self._show_commit_text("ℹ️ 当前仓库没有变更\n")
                self._set_status("无变更")
                return
            if not staged and unstaged:
                # Auto-stage all changes
                from tools.git_commit import git_add
                ok, out = git_add(repo)
                if not ok:
                    self._show_commit_text(f"❌ 自动暂存失败: {out}\n\n未暂存文件: {', '.join(files)}\n请点击 📦 暂存全部")
                    self._set_status("❌ 暂存失败，请手动操作")
                    return
                # Re-read diffs after staging
                staged, unstaged = _get_diffs(repo)
                files = _get_changed_files(repo)
            llm = get_llm()
            msg = _generate_commit_message(staged, unstaged, files, llm)

            # Build clean Conventional Commits message
            msg_type = msg.get("type", "chore")
            msg_scope = msg.get("scope", "")
            msg_message = msg.get("message", "")
            msg_body = msg.get("body", "")

            # Build display
            header = f"{msg_type}({msg_scope}): {msg_message}" if msg_scope else f"{msg_type}: {msg_message}"

            if self.commit_json_var.get():
                self.commit_output.delete("1.0", tk.END)
                self.commit_output.insert("1.0", json.dumps(msg, ensure_ascii=False, indent=2))
            else:
                lines = [f"📝 建议的 Commit Message (branch: {branch})\n", f"  {header}\n"]
                if msg_body:
                    lines.append(f"\n{msg_body}\n")
                lines.append(f"\n📁 涉及文件 ({len(files)}):")
                for f in files[:15]:
                    lines.append(f"  • {f}")
                lines.append("\n💡 如满意，点击下方按钮执行提交")
                self.commit_output.delete("1.0", tk.END)
                self.commit_output.insert("1.0", "\n".join(lines))

            # Store for commit/push actions
            self._last_commit_msg = header
            if msg_body:
                self._last_commit_msg += f"\n\n{msg_body}"

            self._set_status("✅ Commit message 已生成")
            self._show_actions(self.commit_actions)
        except Exception as e:
            self._show_error(self.commit_output, e)

    def _do_git_commit(self):
        """Execute git add + git commit with the generated message."""
        if not self._last_commit_msg:
            messagebox.showwarning("提示", "请先生成 Commit Message")
            return
        repo = self._check_repo()
        if not repo: return
        if not messagebox.askyesno("确认提交", f"将执行:\n\ngit add -A\ngit commit -m \"{self._last_commit_msg[:80]}...\"\n\n确认提交?"):
            return

        from tools.git_commit import git_add, git_commit_exec
        ok, out = git_add(repo)
        if not ok:
            messagebox.showerror("提交失败", f"git add 失败:\n{out}")
            return
        ok, out = git_commit_exec(str(repo), self._last_commit_msg)
        if ok:
            messagebox.showinfo("提交成功", f"✅ git commit 成功!\n\n{out}")
            self._set_status("✅ 已提交到本地仓库")
        else:
            messagebox.showerror("提交失败", out)

    def _do_commit_and_push(self):
        """Execute git add + git commit + git push to GitHub."""
        if not self._last_commit_msg:
            messagebox.showwarning("提示", "请先生成 Commit Message")
            return

        from tools.git_commit import git_add, git_commit_exec, git_push, git_get_remote

        repo = self._check_repo()
        if not repo: return
        remote = git_get_remote(repo)

        if not remote:
            messagebox.showerror("推送失败", "未找到 GitHub 远程仓库 (origin)。\n请先设置: git remote add origin <url>")
            return

        if not messagebox.askyesno("确认推送 GitHub",
            f"将执行以下操作:\n\n"
            f"  1. git add -A\n"
            f"  2. git commit -m \"{self._last_commit_msg[:100]}{'...' if len(self._last_commit_msg)>100 else ''}\"\n"
            f"  3. git push origin\n\n"
            f"远程仓库: {remote}\n\n"
            f"确认推送?"):
            return

        self._set_status("⏳ 正在提交并推送...")
        ok, out = git_add(str(repo))
        if not ok:
            messagebox.showerror("推送失败", f"git add 失败:\n{out}")
            self._set_status("❌ git add 失败")
            return

        ok, out = git_commit_exec(str(repo), self._last_commit_msg)
        if not ok:
            messagebox.showerror("推送失败", f"git commit 失败:\n{out}")
            self._set_status("❌ git commit 失败")
            return

        self._set_status("⏳ 正在推送到 GitHub...")
        ok, out = git_push(str(repo))
        if ok:
            messagebox.showinfo("推送成功", f"✅ 已推送到 GitHub!\n\n{remote}\n\n{out}")
            self._set_status("✅ 已提交并推送到 GitHub")
        else:
            messagebox.showerror("推送失败", f"git push 失败:\n{out}\n\n请检查网络或权限")
            self._set_status("❌ git push 失败 (本地已提交)")

    # ═══════════════════════════════════════════════
    # Workflow navigation (tab jumping)
    # ═══════════════════════════════════════════════
    def _show_actions(self, frame):
        self.root.after(0, lambda: frame.pack(fill=tk.X, pady=(5, 0)))

    def _hide_actions(self, frame):
        self.root.after(0, lambda: frame.pack_forget())

    def _jump_to_tab(self, tab_index: int):
        """Switch to a specific notebook tab."""
        self.root.after(0, lambda: self.notebook.select(tab_index))

    def _show_commit_text(self, text: str):
        """Show plain text in commit output (UI thread safe)."""
        def _do():
            self.commit_output.delete("1.0", tk.END)
            self.commit_output.insert("1.0", text)
        self.root.after(0, _do)

    def _save_generated_code(self):
        """Save the current editor code, using input text as filename."""
        code = self._get_code_from_editor()
        if not code:
            messagebox.showwarning("提示", "请先生成代码或编写代码")
            return
        # Generate filename from input description
        import re
        raw = self.code_input.get("1.0", tk.END).strip()
        # Clean: keep Chinese/English/digits/underscore, remove punctuation
        clean = re.sub(r'[^\w一-鿿]', '_', raw)
        clean = re.sub(r'_+', '_', clean).strip('_')  # collapse multiple underscores
        if clean:
            filename = clean[:40] + ".py"
        else:
            filename = "generated_code.py"

        from pathlib import Path
        default_dir = Path(self.repo_path_var.get()).resolve() / "generated"
        default_dir.mkdir(parents=True, exist_ok=True)
        path = filedialog.asksaveasfilename(
            defaultextension=".py",
            filetypes=[("Python files", "*.py"), ("All files", "*.*")],
            initialdir=str(default_dir),
            initialfile=filename,
        )
        if path:
            Path(path).write_text(code, encoding="utf-8")
            self._set_status(f"💾 代码已保存到: {path}")

    def _jump_gen_to_review(self):
        """Jump to review tab with the current editor code."""
        code = self._get_code_from_editor()
        if code:
            self.review_input.delete("1.0", tk.END)
            self.review_input.insert("1.0", code)
        self._jump_to_tab(1)  # review is tab index 1

    def _jump_gen_to_test(self):
        """Jump to test tab directly with generated code (skip review)."""
        code = self._get_code_from_editor()
        if code:
            self.test_input.delete("1.0", tk.END)
            self.test_input.insert("1.0", code)
        self._jump_to_tab(2)  # test is tab index 2

    def _jump_to_test_with_code(self):
        """Jump to test tab with review input as source."""
        code = self.review_input.get("1.0", tk.END).strip()
        if code:
            self.test_input.delete("1.0", tk.END)
            self.test_input.insert("1.0", code)
        self._jump_to_tab(2)  # test is tab index 2

    def _jump_to_commit(self):
        """Jump to commit tab."""
        self._jump_to_tab(3)  # commit is tab index 3

    # ═══════════════════════════════════════════════
    # Tab 5: 文本编辑器
    # ═══════════════════════════════════════════════
    def _build_editor_tab(self):
        tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(tab, text="  📄 文本编辑器  ")

        # Toolbar
        toolbar = ttk.Frame(tab)
        toolbar.pack(fill=tk.X, pady=(0, 5))
        ttk.Button(toolbar, text="📂 打开", command=self._editor_open).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="💾 保存", command=self._editor_save).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="📋 另存为", command=self._editor_save_as).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        ttk.Button(toolbar, text="🔍 审查", command=self._editor_to_review).pack(side=tk.LEFT, padx=2)
        ttk.Button(toolbar, text="🧪 测试", command=self._editor_to_test).pack(side=tk.LEFT, padx=2)
        ttk.Separator(toolbar, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=8)
        self._editor_path_var = tk.StringVar(value="未打开文件")
        self._editor_path_label = ttk.Label(toolbar, textvariable=self._editor_path_var,
                                             font=("Consolas", 9), foreground="#999")
        self._editor_path_label.pack(side=tk.LEFT, padx=5)
        self._editor_modified = tk.StringVar(value="")
        ttk.Label(toolbar, textvariable=self._editor_modified, foreground="#e0a000",
                  font=("Consolas", 8)).pack(side=tk.LEFT)

        # Line numbers + editor
        editor_frame = tk.Frame(tab)
        editor_frame.pack(fill=tk.BOTH, expand=True)

        self._editor_line_canvas = tk.Canvas(editor_frame, width=45, bg="#252526", highlightthickness=0)
        self._editor_line_canvas.pack(side=tk.LEFT, fill=tk.Y)

        self._editor_text = tk.Text(editor_frame, font=("Consolas", 11), relief=tk.FLAT,
                                     bg="#1e1e1e", fg="#d4d4d4", insertbackground="white",
                                     undo=True, wrap=tk.NONE)
        editor_scroll_y = ttk.Scrollbar(editor_frame, orient=tk.VERTICAL,
                                         command=self._editor_text.yview)
        editor_scroll_x = ttk.Scrollbar(tab, orient=tk.HORIZONTAL,
                                         command=self._editor_text.xview)
        self._editor_text.configure(yscrollcommand=editor_scroll_y.set,
                                     xscrollcommand=editor_scroll_x.set)
        editor_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        self._editor_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        editor_scroll_x.pack(fill=tk.X)

        self._editor_text.bind("<KeyRelease>", lambda e: self._editor_update_line_numbers())
        self._editor_text.bind("<MouseWheel>", lambda e: self._editor_update_line_numbers())
        self._editor_text.bind("<<Modified>>", self._editor_on_modify)
        self._editor_file_path = None

        # Keyboard shortcuts
        self.root.bind("<Control-o>", lambda e: self._editor_open())
        self.root.bind("<Control-s>", lambda e: self._editor_save())
        self.root.bind("<Control-Shift-S>", lambda e: self._editor_save_as())

        self._editor_update_line_numbers()

        # Status
        status = tk.Frame(tab, bg="#252526", height=22)
        status.pack(fill=tk.X, side=tk.BOTTOM, pady=(5, 0))
        self._editor_status = tk.Label(status, text="Ctrl+O 打开 | Ctrl+S 保存 | Ctrl+Shift+S 另存为",
                                        font=("Consolas", 8), bg="#252526", fg="#999", anchor=tk.W)
        self._editor_status.pack(side=tk.LEFT, padx=8, pady=2)
        self._editor_cursor = tk.Label(status, text="行: 1  列: 1", font=("Consolas", 8),
                                        bg="#252526", fg="#999", anchor=tk.E)
        self._editor_cursor.pack(side=tk.RIGHT, padx=8, pady=2)
        self._editor_text.bind("<KeyRelease>", self._editor_update_cursor, add="+")
        self._editor_text.bind("<Button-1>", lambda e: self.root.after(100, self._editor_update_cursor))

    def _editor_update_line_numbers(self):
        """Redraw line numbers for the text editor."""
        self._editor_line_canvas.delete("all")
        code = self._editor_text.get("1.0", tk.END)
        n = code.count("\n") + (0 if code.endswith("\n") else 1)
        lh = 17
        for i in range(1, n + 1):
            y0 = (i - 1) * lh + 2
            self._editor_line_canvas.create_text(33, y0 + lh/2, text=str(i), anchor=tk.E,
                                                  fill="#888", font=("Consolas", 7))

    def _editor_on_modify(self, event=None):
        """Track modification state."""
        if self._editor_text.edit_modified():
            self._editor_modified.set("● 已修改")
        self._editor_text.edit_modified(False)

    def _editor_update_cursor(self, event=None):
        """Update cursor position display."""
        pos = self._editor_text.index(tk.INSERT)
        line, col = pos.split(".")
        self._editor_cursor.config(text=f"行: {line}  列: {int(col)+1}")

    def _editor_open(self):
        """Open a file in the editor."""
        path = filedialog.askopenfilename(
            title="打开文件",
            filetypes=[("所有文件", "*.*"), ("文本文件", "*.txt"), ("Python", "*.py"),
                       ("Markdown", "*.md"), ("JSON", "*.json"), ("HTML", "*.html")])
        if not path: return
        try:
            from pathlib import Path
            content = Path(path).read_text(encoding="utf-8")
            self._editor_text.delete("1.0", tk.END)
            self._editor_text.insert("1.0", content)
            self._editor_file_path = path
            self._editor_path_var.set(path)
            self._editor_modified.set("")
            self._editor_text.edit_modified(False)
            self._editor_update_line_numbers()
            self._set_status(f"📂 已打开: {path}")
        except Exception as e:
            messagebox.showerror("打开失败", f"无法打开文件:\n{e}")

    def _editor_save(self):
        """Save current file (Ctrl+S)."""
        if self._editor_file_path:
            try:
                from pathlib import Path
                content = self._editor_text.get("1.0", tk.END)
                if content.endswith("\n"): content = content[:-1]
                Path(self._editor_file_path).write_text(content, encoding="utf-8")
                self._editor_modified.set("")
                self._editor_text.edit_modified(False)
                self._set_status(f"💾 已保存: {self._editor_file_path}")
            except Exception as e:
                messagebox.showerror("保存失败", f"无法保存文件:\n{e}")
        else:
            self._editor_save_as()

    def _editor_save_as(self):
        """Save as a new file."""
        path = filedialog.asksaveasfilename(
            title="另存为",
            defaultextension=".txt",
            filetypes=[("文本文件", "*.txt"), ("Python", "*.py"), ("Markdown", "*.md"),
                       ("JSON", "*.json"), ("HTML", "*.html"), ("所有文件", "*.*")])
        if not path: return
        try:
            from pathlib import Path
            content = self._editor_text.get("1.0", tk.END)
            if content.endswith("\n"): content = content[:-1]
            Path(path).write_text(content, encoding="utf-8")
            self._editor_file_path = path
            self._editor_path_var.set(path)
            self._editor_modified.set("")
            self._editor_text.edit_modified(False)
            self._set_status(f"💾 已保存: {path}")
        except Exception as e:
            messagebox.showerror("保存失败", f"无法保存文件:\n{e}")

    def _editor_to_review(self):
        """Send editor content to review tab."""
        code = self._editor_text.get("1.0", tk.END).strip()
        if code:
            self.review_input.delete("1.0", tk.END)
            self.review_input.insert("1.0", code)
        self._jump_to_tab(1)

    def _editor_to_test(self):
        """Send editor content to test tab."""
        code = self._editor_text.get("1.0", tk.END).strip()
        if code:
            self.test_input.delete("1.0", tk.END)
            self.test_input.insert("1.0", code)
        self._jump_to_tab(2)

    def _jump_to_review_with_test(self):
        """After test gen → jump to review the test code."""
        if self._last_test_code:
            self.review_input.delete("1.0", tk.END)
            self.review_input.insert("1.0", self._last_test_code)
        self._jump_to_tab(1)

    # ═══════════════════════════════════════════════
    # Helpers
    # ═══════════════════════════════════════════════
    def _run_async(self, task):
        def wrapper():
            try:
                task()
            except Exception as e:
                self.root.after(0, lambda: messagebox.showerror("错误", str(e)))
        threading.Thread(target=wrapper, daemon=True).start()

    def _show_result(self, widget, result, is_json=False):
        def _do():
            widget.delete("1.0", tk.END)
            if is_json:
                widget.insert("1.0", json.dumps(result, ensure_ascii=False, indent=2))
                return

            lines = []
            status = result.get("status", "?")

            # Header
            if status == "success":
                lines.append("✅ 成功\n" + "═" * 50)
            elif status == "error":
                lines.append("❌ 失败\n" + "═" * 50)
            else:
                lines.append(f"[{status.upper()}]")

            if "file" in result:
                lines.append(f"📁 文件: {result['file']}")

            # Metadata line
            meta = result.get("metadata", {})
            if "total_issues" in meta:
                lines.append(f"📊 问题: {meta['total_issues']}  "
                             f"❌{meta.get('errors',0)} ⚠{meta.get('warnings',0)} ℹ{meta.get('info',0)}")

            content = result.get("content", "")
            if isinstance(content, list):
                if not content:
                    lines.append("\n✅ 未发现任何问题")
                else:
                    sev_icon = {"ERROR": "❌", "WARNING": "⚠️", "INFO": "ℹ️"}
                    for sev, icon in sev_icon.items():
                        for issue in content:
                            if issue.get("severity") == sev:
                                lines.append(
                                    f"\n  {icon} 第{issue.get('line', '?')}行: {issue.get('issue', '?')}")
                                lines.append(f"      → {issue.get('suggestion', '')}")
            elif isinstance(content, str) and content:
                lines.append(f"\n{content}")

            # Extra details
            for key, label in [("stdout", "标准输出"), ("test_output", "测试结果"),
                               ("test_stderr", "测试错误"), ("exception", "异常信息")]:
                val = meta.get(key, "")
                if val:
                    lines.append(f"\n{'─' * 40}\n【{label}】\n{val}")

            widget.insert("1.0", "\n".join(lines))
        self.root.after(0, _do)

    def _show_error(self, widget, error):
        import traceback
        def _do():
            widget.delete("1.0", tk.END)
            widget.insert("1.0", f"❌ 发生异常\n{'═'*50}\n\n{error}\n\n{traceback.format_exc()}")
        self.root.after(0, _do)

    def _set_status(self, text: str):
        self.root.after(0, lambda: self.status_var.set(text))

    # ═══════════════════════════════════════════════
    # Help / About dialogs
    # ═══════════════════════════════════════════════
    def _show_help(self):
        help_text = """📖 使用指南

【代码生成】
  1. 切换到 "📝 代码生成" 标签页
  2. 用自然语言描述你要的功能
  3. 点击 "🚀 生成并执行"
  4. 代码会自动运行，出错自动修正（最多3轮）

【代码审查】
  1. 切换到 "🔍 代码审查" 标签页
  2. 粘贴代码或选择 .py 文件
  3. 点击 "🔍 开始审查"
  4. 报告包含 5 个维度：命名/复杂度/Bug模式/导入/格式

【测试生成】
  1. 切换到 "🧪 测试生成" 标签页
  2. 粘贴源代码或选择 .py 文件
  3. 点击 "🧪 生成测试"
  4. 自动生成 pytest 并执行验证，失败自动修正

【Commit 生成】
  1. 切换到 "📋 Commit 生成" 标签页
  2. 选择 Git 仓库路径
  3. 点击 "📊 查看变更" 预览 diff
  4. 点击 "📝 生成 Commit Message"

【模型设置】
  菜单栏 → 设置 → ⚙️ API 配置
  支持: DeepSeek / Anthropic Claude / Ollama 本地模型

提示：所有功能支持 JSON 输出格式（勾选对应复选框）"""
        dialog = tk.Toplevel(self.root)
        dialog.title("📖 使用指南")
        dialog.geometry("550x500")
        dialog.transient(self.root)
        dialog.grab_set()
        txt = scrolledtext.ScrolledText(dialog, font=("Microsoft YaHei UI", 10), wrap=tk.WORD, padx=10, pady=10)
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert("1.0", help_text)
        txt.config(state="disabled")
        ttk.Button(dialog, text="关闭", command=dialog.destroy).pack(pady=8)

    def _show_about(self):
        messagebox.showinfo(
            "关于",
            "🤖 AI 编程助手 Agent\n\n"
            "版本: 1.0\n"
            "基于: LangChain 1.x + 多模型支持\n"
            "功能: 代码生成 · 静态审查 · 测试生成 · Commit 生成\n\n"
            "技术栈: Python / tkinter / LangChain / LangGraph / AST\n"
            "模型: DeepSeek / Anthropic Claude / Ollama\n\n"
            "MIT License",
        )


def main():
    root = tk.Tk()
    AIAgentGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
