#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TranslateX - 多功能翻譯工具
支援 CSV / Excel / TXT 檔案，整合多種翻譯 API
"""

import sys
import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import json
from pathlib import Path
from datetime import datetime

# 確保模組路徑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from translator_engine import TranslatorEngine
from file_handler import FileHandler
from config_manager import ConfigManager

# ─── 色彩系統 ───────────────────────────────────────────────────────────────
COLORS = {
    "bg_dark":      "#0F1117",
    "bg_panel":     "#1A1D27",
    "bg_card":      "#232738",
    "bg_hover":     "#2D3148",
    "accent":       "#6C63FF",
    "accent_light": "#8B85FF",
    "accent_dark":  "#4A44CC",
    "success":      "#00D9A3",
    "warning":      "#FFB547",
    "error":        "#FF5C5C",
    "text_primary": "#EAEAF0",
    "text_secondary":"#8B8FA8",
    "text_dim":     "#5A5E73",
    "border":       "#2D3148",
    "border_light": "#3D4166",
}

FONTS = {
    "title":   ("Microsoft JhengHei UI", 22, "bold"),
    "heading": ("Microsoft JhengHei UI", 13, "bold"),
    "body":    ("Microsoft JhengHei UI", 11),
    "small":   ("Microsoft JhengHei UI", 9),
    "mono":    ("Consolas", 10),
    "badge":   ("Microsoft JhengHei UI", 9, "bold"),
}


# ─── 自訂元件 ──────────────────────────────────────────────────────────────
class ModernButton(tk.Canvas):
    def __init__(self, parent, text="", command=None, style="primary",
                 width=120, height=36, **kwargs):
        super().__init__(parent, width=width, height=height,
                         bg=COLORS["bg_panel"], highlightthickness=0, **kwargs)
        self.command = command
        self.style = style
        self.text = text
        self.width = width
        self.height = height
        self._hover = False

        colors = {
            "primary":  (COLORS["accent"],   COLORS["accent_light"]),
            "success":  (COLORS["success"],   "#00F0B5"),
            "danger":   (COLORS["error"],     "#FF7A7A"),
            "ghost":    (COLORS["bg_card"],   COLORS["bg_hover"]),
            "outline":  ("",                  COLORS["bg_hover"]),
        }
        self.base_color, self.hover_color = colors.get(style, colors["primary"])

        self._draw()
        self.bind("<Enter>",    self._on_enter)
        self.bind("<Leave>",    self._on_leave)
        self.bind("<Button-1>", self._on_click)

    def _draw(self, hover=False):
        self.delete("all")
        c = self.hover_color if hover else self.base_color
        r = self.height // 2

        if self.style == "outline":
            self.create_rounded_rect(2, 2, self.width-2, self.height-2, r,
                                     fill=c if hover else COLORS["bg_panel"],
                                     outline=COLORS["accent"], width=1)
            text_color = COLORS["accent_light"] if hover else COLORS["accent"]
        else:
            self.create_rounded_rect(0, 0, self.width, self.height, r,
                                     fill=c, outline="")
            text_color = "#FFFFFF" if self.style != "ghost" else COLORS["text_primary"]

        self.create_text(self.width // 2, self.height // 2,
                         text=self.text, fill=text_color,
                         font=("Microsoft JhengHei UI", 10, "bold"))

    def create_rounded_rect(self, x1, y1, x2, y2, radius, **kwargs):
        pts = [
            x1+radius, y1, x2-radius, y1,
            x2, y1, x2, y1+radius,
            x2, y2-radius, x2, y2,
            x2-radius, y2, x1+radius, y2,
            x1, y2, x1, y2-radius,
            x1, y1+radius, x1, y1,
        ]
        return self.create_polygon(pts, smooth=True, **kwargs)

    def _on_enter(self, e):
        self._draw(hover=True)
        self.config(cursor="hand2")

    def _on_leave(self, e):
        self._draw(hover=False)

    def _on_click(self, e):
        if self.command:
            self.command()


class StatusBar(tk.Frame):
    def __init__(self, parent, **kwargs):
        super().__init__(parent, bg=COLORS["bg_dark"], height=28, **kwargs)
        self.pack_propagate(False)

        self._dot = tk.Label(self, text="●", bg=COLORS["bg_dark"],
                             fg=COLORS["success"], font=("Consolas", 9))
        self._dot.pack(side="left", padx=(12, 4))

        self._msg = tk.Label(self, text="就緒", bg=COLORS["bg_dark"],
                             fg=COLORS["text_secondary"],
                             font=FONTS["small"])
        self._msg.pack(side="left")

        self._time = tk.Label(self, bg=COLORS["bg_dark"],
                              fg=COLORS["text_dim"], font=FONTS["small"])
        self._time.pack(side="right", padx=12)
        self._tick()

    def _tick(self):
        self._time.config(text=datetime.now().strftime("%H:%M:%S"))
        self.after(1000, self._tick)

    def set(self, msg, level="info"):
        colors = {"info": COLORS["text_secondary"],
                  "success": COLORS["success"],
                  "error": COLORS["error"],
                  "warning": COLORS["warning"]}
        dots   = {"info": COLORS["accent"],
                  "success": COLORS["success"],
                  "error": COLORS["error"],
                  "warning": COLORS["warning"]}
        self._msg.config(text=msg, fg=colors.get(level, COLORS["text_secondary"]))
        self._dot.config(fg=dots.get(level, COLORS["accent"]))


class ProgressRing(tk.Canvas):
    """圓形進度指示器"""
    def __init__(self, parent, size=40, **kwargs):
        super().__init__(parent, width=size, height=size,
                         bg=COLORS["bg_panel"], highlightthickness=0, **kwargs)
        self.size = size
        self._angle = 0
        self._running = False

    def start(self):
        self._running = True
        self._spin()

    def stop(self):
        self._running = False
        self.delete("all")

    def _spin(self):
        if not self._running:
            return
        self.delete("all")
        s = self.size
        pad = 5
        self.create_arc(pad, pad, s-pad, s-pad,
                        start=self._angle, extent=270,
                        outline=COLORS["accent"], width=3, style="arc")
        self._angle = (self._angle + 12) % 360
        self.after(30, self._spin)


# ─── 主視窗 ────────────────────────────────────────────────────────────────
class TranslateXApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TranslateX — 多功能翻譯工具")
        self.geometry("1100x750")
        self.minsize(900, 620)
        self.configure(bg=COLORS["bg_dark"])

        # 設定 DPI
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        self.config_mgr = ConfigManager()
        self.engine     = TranslatorEngine(self.config_mgr)
        self.file_handler = FileHandler()
        self._file_path  = None
        self._is_running = False

        self._build_ui()
        self._load_settings()

    # ── 建構 UI ──────────────────────────────────────────────────────────
    def _build_ui(self):
        # 頂部標題列
        self._build_header()

        # 主體：左側邊欄 + 右側工作區
        body = tk.Frame(self, bg=COLORS["bg_dark"])
        body.pack(fill="both", expand=True, padx=0, pady=0)

        self._build_sidebar(body)
        self._build_workspace(body)

        # 底部狀態列
        self.status = StatusBar(self)
        self.status.pack(fill="x", side="bottom")

    def _build_header(self):
        hdr = tk.Frame(self, bg=COLORS["bg_panel"], height=60)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        # 左側 logo
        logo_frame = tk.Frame(hdr, bg=COLORS["bg_panel"])
        logo_frame.pack(side="left", padx=20)

        tk.Label(logo_frame, text="⬡", bg=COLORS["bg_panel"],
                 fg=COLORS["accent"], font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(logo_frame, text=" TranslateX",
                 bg=COLORS["bg_panel"], fg=COLORS["text_primary"],
                 font=("Microsoft JhengHei UI", 15, "bold")).pack(side="left")

        tk.Label(hdr, text="多功能翻譯工具 v1.0",
                 bg=COLORS["bg_panel"], fg=COLORS["text_dim"],
                 font=FONTS["small"]).pack(side="left", padx=(0, 0))

        # 右側頁籤
        tab_frame = tk.Frame(hdr, bg=COLORS["bg_panel"])
        tab_frame.pack(side="right", padx=20)

        self._tabs = {}
        for name, label in [("translate", "📄  翻譯"), ("batch", "📦  批次"), ("settings", "⚙  設定")]:
            btn = tk.Label(tab_frame, text=label, bg=COLORS["bg_panel"],
                           fg=COLORS["text_secondary"],
                           font=("Microsoft JhengHei UI", 10),
                           padx=14, pady=4, cursor="hand2")
            btn.pack(side="left", padx=4)
            btn.bind("<Button-1>", lambda e, n=name: self._switch_tab(n))
            btn.bind("<Enter>", lambda e, b=btn: b.config(fg=COLORS["text_primary"]))
            btn.bind("<Leave>", lambda e, b=btn, n=name: b.config(
                fg=COLORS["accent"] if self._current_tab == n else COLORS["text_secondary"]))
            self._tabs[name] = btn

        self._current_tab = "translate"

    def _build_sidebar(self, parent):
        side = tk.Frame(parent, bg=COLORS["bg_panel"], width=260)
        side.pack(side="left", fill="y", padx=0, pady=0)
        side.pack_propagate(False)

        # ── API 選擇 ──
        self._section(side, "翻譯引擎")

        self.api_var = tk.StringVar(value="google")
        apis = [
            ("google",    "Google 翻譯",    "免費"),
            ("deepl",     "DeepL",          "付費"),
            ("microsoft", "Microsoft Azure","付費"),
            ("openai",    "OpenAI GPT",     "付費"),
            ("custom",    "自訂 API",       "客製"),
        ]
        for val, label, badge in apis:
            self._api_radio(side, val, label, badge)

        tk.Frame(side, bg=COLORS["border"], height=1).pack(fill="x", padx=16, pady=8)

        # ── 語言選擇 ──
        self._section(side, "語言設定")

        tk.Label(side, text="來源語言", bg=COLORS["bg_panel"],
                 fg=COLORS["text_secondary"], font=FONTS["small"]).pack(anchor="w", padx=16)

        self.src_lang = ttk.Combobox(side, font=FONTS["body"], state="readonly")
        self.src_lang.pack(fill="x", padx=16, pady=(2, 8))

        tk.Label(side, text="目標語言", bg=COLORS["bg_panel"],
                 fg=COLORS["text_secondary"], font=FONTS["small"]).pack(anchor="w", padx=16)

        self.tgt_lang = ttk.Combobox(side, font=FONTS["body"], state="readonly")
        self.tgt_lang.pack(fill="x", padx=16, pady=(2, 8))

        self._populate_languages()

        tk.Frame(side, bg=COLORS["border"], height=1).pack(fill="x", padx=16, pady=8)

        # ── 進階選項 ──
        self._section(side, "進階選項")

        self.skip_header_var = tk.BooleanVar(value=True)
        self._checkbox(side, "跳過標題列 (CSV/Excel)", self.skip_header_var)

        self.col_select_var  = tk.BooleanVar(value=False)
        self._checkbox(side, "選擇特定欄位", self.col_select_var,
                       command=self._toggle_col_entry)

        self.col_entry = tk.Entry(side, bg=COLORS["bg_card"],
                                  fg=COLORS["text_primary"],
                                  insertbackground=COLORS["accent"],
                                  relief="flat", font=FONTS["small"],
                                  disabledbackground=COLORS["bg_card"],
                                  disabledforeground=COLORS["text_dim"])
        self.col_entry.pack(fill="x", padx=16, pady=(0, 6))
        self.col_entry.insert(0, "例：A, C, E 或 1, 3, 5")
        self.col_entry.config(state="disabled")

        self.delay_var = tk.DoubleVar(value=0.3)
        tk.Label(side, text="請求間隔 (秒)", bg=COLORS["bg_panel"],
                 fg=COLORS["text_secondary"], font=FONTS["small"]).pack(anchor="w", padx=16)
        delay_scale = tk.Scale(side, variable=self.delay_var,
                               from_=0, to=3, resolution=0.1,
                               orient="horizontal",
                               bg=COLORS["bg_panel"], fg=COLORS["text_primary"],
                               highlightthickness=0, troughcolor=COLORS["bg_card"],
                               activebackground=COLORS["accent"],
                               sliderrelief="flat")
        delay_scale.pack(fill="x", padx=16, pady=(0, 8))

    def _build_workspace(self, parent):
        work = tk.Frame(parent, bg=COLORS["bg_dark"])
        work.pack(side="left", fill="both", expand=True, padx=16, pady=16)

        # ── 頁籤內容框架 ──
        self.tab_frames = {}

        # 翻譯頁籤
        f = tk.Frame(work, bg=COLORS["bg_dark"])
        self.tab_frames["translate"] = f
        self._build_translate_tab(f)

        # 批次頁籤
        f2 = tk.Frame(work, bg=COLORS["bg_dark"])
        self.tab_frames["batch"] = f2
        self._build_batch_tab(f2)

        # 設定頁籤
        f3 = tk.Frame(work, bg=COLORS["bg_dark"])
        self.tab_frames["settings"] = f3
        self._build_settings_tab(f3)

        self._switch_tab("translate")

    def _build_translate_tab(self, parent):
        # ── 上方：文字翻譯 ──
        card = self._card(parent, "文字即時翻譯")
        card.pack(fill="x", pady=(0, 12))

        text_row = tk.Frame(card, bg=COLORS["bg_card"])
        text_row.pack(fill="both", expand=True, padx=12, pady=8)

        # 輸入
        src_col = tk.Frame(text_row, bg=COLORS["bg_card"])
        src_col.pack(side="left", fill="both", expand=True)
        tk.Label(src_col, text="原文", bg=COLORS["bg_card"],
                 fg=COLORS["text_dim"], font=FONTS["small"]).pack(anchor="w")
        self.src_text = scrolledtext.ScrolledText(
            src_col, height=6, font=FONTS["body"],
            bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
            insertbackground=COLORS["accent"], relief="flat",
            wrap="word", padx=8, pady=8)
        self.src_text.pack(fill="both", expand=True)

        # 箭頭
        arrow = tk.Label(text_row, text="→", bg=COLORS["bg_card"],
                         fg=COLORS["accent"], font=("Consolas", 20))
        arrow.pack(side="left", padx=12, pady=30)

        # 輸出
        tgt_col = tk.Frame(text_row, bg=COLORS["bg_card"])
        tgt_col.pack(side="left", fill="both", expand=True)
        tk.Label(tgt_col, text="譯文", bg=COLORS["bg_card"],
                 fg=COLORS["text_dim"], font=FONTS["small"]).pack(anchor="w")
        self.tgt_text = scrolledtext.ScrolledText(
            tgt_col, height=6, font=FONTS["body"],
            bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
            insertbackground=COLORS["accent"], relief="flat",
            wrap="word", padx=8, pady=8, state="disabled")
        self.tgt_text.pack(fill="both", expand=True)

        btn_row = tk.Frame(card, bg=COLORS["bg_card"])
        btn_row.pack(fill="x", padx=12, pady=(0, 12))

        ModernButton(btn_row, "翻譯", self._translate_text,
                     "primary", 100, 34).pack(side="left", padx=(0, 8))
        ModernButton(btn_row, "清除", self._clear_text,
                     "ghost", 80, 34).pack(side="left")
        ModernButton(btn_row, "複製譯文", self._copy_result,
                     "outline", 100, 34).pack(side="right")

        # ── 下方：檔案翻譯 ──
        card2 = self._card(parent, "檔案翻譯")
        card2.pack(fill="both", expand=True)

        # 拖放區
        drop_zone = tk.Frame(card2, bg=COLORS["bg_dark"],
                             highlightthickness=2,
                             highlightbackground=COLORS["border"])
        drop_zone.pack(fill="x", padx=12, pady=8)

        self.drop_label = tk.Label(
            drop_zone,
            text="📂  點擊選擇檔案\n支援 .csv  .xlsx  .xls  .txt",
            bg=COLORS["bg_dark"], fg=COLORS["text_dim"],
            font=("Microsoft JhengHei UI", 11),
            pady=20, cursor="hand2")
        self.drop_label.pack(fill="x")
        drop_zone.bind("<Button-1>", lambda e: self._open_file())
        self.drop_label.bind("<Button-1>", lambda e: self._open_file())
        self._add_hover(drop_zone, COLORS["bg_dark"], COLORS["bg_hover"])
        self._add_hover(self.drop_label, COLORS["bg_dark"], COLORS["bg_hover"])

        # 進度列
        prog_frame = tk.Frame(card2, bg=COLORS["bg_card"])
        prog_frame.pack(fill="x", padx=12, pady=(0, 4))

        self.ring = ProgressRing(prog_frame, size=28)
        self.ring.pack(side="left", padx=(0, 8))

        prog_right = tk.Frame(prog_frame, bg=COLORS["bg_card"])
        prog_right.pack(side="left", fill="x", expand=True)

        self.prog_label = tk.Label(prog_right, text="等待檔案...",
                                   bg=COLORS["bg_card"], fg=COLORS["text_secondary"],
                                   font=FONTS["small"])
        self.prog_label.pack(anchor="w")

        self.progress = ttk.Progressbar(prog_right, mode="determinate",
                                        style="Accent.Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(2, 0))

        # 動作按鈕
        action_row = tk.Frame(card2, bg=COLORS["bg_card"])
        action_row.pack(fill="x", padx=12, pady=(4, 12))

        self.translate_btn = ModernButton(action_row, "▶  開始翻譯",
                                          self._start_translation, "primary", 130, 36)
        self.translate_btn.pack(side="left", padx=(0, 8))

        self.stop_btn = ModernButton(action_row, "⬛  停止",
                                     self._stop_translation, "danger", 90, 36)
        self.stop_btn.pack(side="left")

        ModernButton(action_row, "另存輸出", self._save_output,
                     "outline", 100, 36).pack(side="right")

        # 日誌
        log_frame = self._card(parent, "翻譯日誌")
        log_frame.pack(fill="both", expand=True, pady=(12, 0))

        self.log_box = scrolledtext.ScrolledText(
            log_frame, height=5, font=FONTS["mono"],
            bg=COLORS["bg_dark"], fg=COLORS["text_primary"],
            insertbackground=COLORS["accent"], relief="flat",
            state="disabled", padx=8, pady=8)
        self.log_box.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.log_box.tag_config("success", foreground=COLORS["success"])
        self.log_box.tag_config("error",   foreground=COLORS["error"])
        self.log_box.tag_config("info",    foreground=COLORS["accent"])
        self.log_box.tag_config("warn",    foreground=COLORS["warning"])

    def _build_batch_tab(self, parent):
        card = self._card(parent, "批次檔案管理")
        card.pack(fill="both", expand=True)

        toolbar = tk.Frame(card, bg=COLORS["bg_card"])
        toolbar.pack(fill="x", padx=12, pady=8)

        ModernButton(toolbar, "+ 新增檔案", self._batch_add, "primary", 110, 32).pack(side="left", padx=(0, 6))
        ModernButton(toolbar, "清除全部", self._batch_clear, "ghost", 90, 32).pack(side="left")
        ModernButton(toolbar, "▶ 全部翻譯", self._batch_run, "success", 110, 32).pack(side="right")

        # 檔案列表
        list_frame = tk.Frame(card, bg=COLORS["bg_dark"])
        list_frame.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        columns = ("file", "size", "status", "progress")
        self.batch_tree = ttk.Treeview(list_frame, columns=columns,
                                        show="headings", height=12)

        for col, label, w in [
            ("file", "檔案路徑", 380),
            ("size", "大小", 80),
            ("status", "狀態", 90),
            ("progress", "進度", 100),
        ]:
            self.batch_tree.heading(col, text=label)
            self.batch_tree.column(col, width=w)

        scroll = ttk.Scrollbar(list_frame, orient="vertical",
                               command=self.batch_tree.yview)
        self.batch_tree.configure(yscrollcommand=scroll.set)
        self.batch_tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        self._batch_files = []

    def _build_settings_tab(self, parent):
        # DeepL
        card = self._card(parent, "DeepL API")
        card.pack(fill="x", pady=(0, 10))
        self._api_key_row(card, "API 金鑰", "deepl_key")

        # Microsoft
        card2 = self._card(parent, "Microsoft Azure 翻譯")
        card2.pack(fill="x", pady=(0, 10))
        self._api_key_row(card2, "訂閱金鑰", "ms_key")
        self._api_key_row(card2, "區域",     "ms_region", secret=False)

        # OpenAI
        card3 = self._card(parent, "OpenAI GPT 翻譯")
        card3.pack(fill="x", pady=(0, 10))
        self._api_key_row(card3, "API Key", "openai_key")

        frame3 = tk.Frame(card3, bg=COLORS["bg_card"])
        frame3.pack(fill="x", padx=12, pady=(0, 8))
        tk.Label(frame3, text="模型", bg=COLORS["bg_card"],
                 fg=COLORS["text_secondary"], font=FONTS["small"],
                 width=14, anchor="w").pack(side="left")
        self.openai_model = ttk.Combobox(frame3, font=FONTS["body"],
                                          values=["gpt-4o-mini", "gpt-4o", "gpt-3.5-turbo"])
        self.openai_model.set("gpt-4o-mini")
        self.openai_model.pack(side="left", fill="x", expand=True)

        # 自訂 API
        card4 = self._card(parent, "自訂翻譯 API")
        card4.pack(fill="x", pady=(0, 10))

        for label, key, secret in [
            ("端點 URL",    "custom_url",    False),
            ("API 金鑰",    "custom_key",    True),
            ("請求模板 (JSON)", "custom_body", False),
        ]:
            self._api_key_row(card4, label, key, secret=secret)

        tk.Label(card4, text="• 模板中使用 {text}、{src}、{tgt} 作為佔位符",
                 bg=COLORS["bg_card"], fg=COLORS["text_dim"],
                 font=FONTS["small"]).pack(anchor="w", padx=12, pady=(0, 4))

        # 儲存
        save_row = tk.Frame(parent, bg=COLORS["bg_dark"])
        save_row.pack(fill="x", pady=8)
        ModernButton(save_row, "儲存設定", self._save_settings, "primary", 120, 36).pack(side="left")
        ModernButton(save_row, "測試連線", self._test_api, "outline", 110, 36).pack(side="left", padx=8)

        self._setting_entries = {}

    # ── 輔助 UI 方法 ────────────────────────────────────────────────────────
    def _section(self, parent, title):
        tk.Label(parent, text=title.upper(), bg=COLORS["bg_panel"],
                 fg=COLORS["text_dim"],
                 font=("Microsoft JhengHei UI", 8, "bold"),
                 padx=16).pack(anchor="w", pady=(12, 4))

    def _card(self, parent, title=""):
        outer = tk.Frame(parent, bg=COLORS["bg_card"],
                         highlightthickness=1,
                         highlightbackground=COLORS["border"])
        if title:
            hdr = tk.Frame(outer, bg=COLORS["bg_card"])
            hdr.pack(fill="x", padx=12, pady=(10, 4))
            tk.Frame(hdr, bg=COLORS["accent"], width=3, height=14).pack(side="left")
            tk.Label(hdr, text=f"  {title}", bg=COLORS["bg_card"],
                     fg=COLORS["text_primary"], font=FONTS["heading"]).pack(side="left")
        return outer

    def _api_radio(self, parent, val, label, badge):
        frame = tk.Frame(parent, bg=COLORS["bg_panel"], cursor="hand2")
        frame.pack(fill="x", padx=12, pady=2)

        rb = tk.Radiobutton(frame, variable=self.api_var, value=val,
                            bg=COLORS["bg_panel"],
                            activebackground=COLORS["bg_panel"],
                            selectcolor=COLORS["accent"],
                            fg=COLORS["text_primary"],
                            font=FONTS["body"], text=label,
                            command=self._on_api_change)
        rb.pack(side="left")

        badge_colors = {"免費": COLORS["success"], "付費": COLORS["warning"],
                        "客製": COLORS["accent"]}
        tk.Label(frame, text=badge, bg=badge_colors.get(badge, COLORS["accent"]),
                 fg="#000000" if badge != "客製" else "#FFFFFF",
                 font=FONTS["badge"], padx=5, pady=1).pack(side="right")

    def _checkbox(self, parent, label, var, command=None):
        cb = tk.Checkbutton(parent, text=label, variable=var,
                            bg=COLORS["bg_panel"], fg=COLORS["text_primary"],
                            activebackground=COLORS["bg_panel"],
                            selectcolor=COLORS["accent"],
                            font=FONTS["body"], cursor="hand2",
                            command=command)
        cb.pack(anchor="w", padx=16, pady=2)

    def _add_hover(self, widget, normal, hover):
        widget.bind("<Enter>", lambda e: widget.config(bg=hover))
        widget.bind("<Leave>", lambda e: widget.config(bg=normal))

    def _api_key_row(self, parent, label, key, secret=True):
        frame = tk.Frame(parent, bg=COLORS["bg_card"])
        frame.pack(fill="x", padx=12, pady=4)
        tk.Label(frame, text=label, bg=COLORS["bg_card"],
                 fg=COLORS["text_secondary"], font=FONTS["small"],
                 width=14, anchor="w").pack(side="left")
        entry = tk.Entry(frame, bg=COLORS["bg_dark"],
                         fg=COLORS["text_primary"],
                         insertbackground=COLORS["accent"],
                         relief="flat", font=FONTS["body"],
                         show="●" if secret else "")
        entry.pack(side="left", fill="x", expand=True, ipady=4, padx=(0, 4))

        if not hasattr(self, '_setting_entries'):
            self._setting_entries = {}
        self._setting_entries[key] = entry

        saved = self.config_mgr.get(key, "")
        if saved:
            entry.insert(0, saved)

    def _populate_languages(self):
        langs = [
            ("auto",  "自動偵測"),
            ("zh-TW", "繁體中文"),
            ("zh-CN", "簡體中文"),
            ("en",    "英文"),
            ("ja",    "日文"),
            ("ko",    "韓文"),
            ("fr",    "法文"),
            ("de",    "德文"),
            ("es",    "西班牙文"),
            ("it",    "義大利文"),
            ("pt",    "葡萄牙文"),
            ("ru",    "俄文"),
            ("ar",    "阿拉伯文"),
            ("th",    "泰文"),
            ("vi",    "越南文"),
        ]
        display = [f"{code}  {name}" for code, name in langs]
        src_langs = display
        tgt_langs = display[1:]  # 去掉 auto

        self.src_lang["values"] = src_langs
        self.tgt_lang["values"] = tgt_langs
        self.src_lang.set("auto  自動偵測")
        self.tgt_lang.set("zh-TW  繁體中文")

        self._lang_map = {f"{code}  {name}": code for code, name in langs}

    def _switch_tab(self, name):
        self._current_tab = name
        for n, frame in self.tab_frames.items():
            if n == name:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

        for n, btn in self._tabs.items():
            btn.config(fg=COLORS["accent"] if n == name else COLORS["text_secondary"])

    def _toggle_col_entry(self):
        state = "normal" if self.col_select_var.get() else "disabled"
        self.col_entry.config(state=state)
        if state == "normal":
            self.col_entry.delete(0, "end")

    # ── 翻譯邏輯 ────────────────────────────────────────────────────────────
    def _get_lang_code(self, display):
        return self._lang_map.get(display, display.split()[0])

    def _translate_text(self):
        text = self.src_text.get("1.0", "end").strip()
        if not text:
            return

        src = self._get_lang_code(self.src_lang.get())
        tgt = self._get_lang_code(self.tgt_lang.get())
        api = self.api_var.get()

        self.status.set("翻譯中...", "info")

        def run():
            result = self.engine.translate(text, src, tgt, api)
            self.after(0, lambda: self._show_text_result(result))

        threading.Thread(target=run, daemon=True).start()

    def _show_text_result(self, result):
        self.tgt_text.config(state="normal")
        self.tgt_text.delete("1.0", "end")
        self.tgt_text.insert("1.0", result)
        self.tgt_text.config(state="disabled")
        self.status.set("翻譯完成", "success")

    def _clear_text(self):
        self.src_text.delete("1.0", "end")
        self.tgt_text.config(state="normal")
        self.tgt_text.delete("1.0", "end")
        self.tgt_text.config(state="disabled")

    def _copy_result(self):
        result = self.tgt_text.get("1.0", "end").strip()
        if result:
            self.clipboard_clear()
            self.clipboard_append(result)
            self.status.set("已複製到剪貼簿", "success")

    def _open_file(self):
        path = filedialog.askopenfilename(
            title="選擇檔案",
            filetypes=[
                ("所有支援格式", "*.csv *.xlsx *.xls *.txt"),
                ("CSV 檔案",    "*.csv"),
                ("Excel 檔案",  "*.xlsx *.xls"),
                ("文字檔案",    "*.txt"),
            ])
        if path:
            self._file_path = path
            name = Path(path).name
            size = Path(path).stat().st_size
            size_str = f"{size/1024:.1f} KB" if size < 1024*1024 else f"{size/1024/1024:.1f} MB"
            self.drop_label.config(
                text=f"✅  {name}\n{size_str} · 點擊重新選擇",
                fg=COLORS["text_primary"])
            self.status.set(f"已選擇：{name}", "info")
            self._log(f"開啟檔案：{path}", "info")

    def _start_translation(self):
        if not self._file_path:
            messagebox.showwarning("提示", "請先選擇要翻譯的檔案。")
            return
        if self._is_running:
            return

        self._is_running = True
        self._stop_flag  = False
        self.ring.start()
        self.progress["value"] = 0
        self.status.set("翻譯中...", "info")

        src = self._get_lang_code(self.src_lang.get())
        tgt = self._get_lang_code(self.tgt_lang.get())
        api = self.api_var.get()
        skip_header = self.skip_header_var.get()
        delay = self.delay_var.get()
        cols = None
        if self.col_select_var.get():
            raw = self.col_entry.get().strip()
            cols = [c.strip() for c in raw.split(",") if c.strip()]

        def run():
            try:
                result_path = self.file_handler.translate_file(
                    self._file_path, src, tgt, api,
                    self.engine, skip_header, cols, delay,
                    progress_cb=self._update_progress,
                    log_cb=self._log,
                    stop_flag=lambda: self._stop_flag,
                )
                self.after(0, lambda: self._on_done(result_path))
            except Exception as e:
                self.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=run, daemon=True).start()

    def _stop_translation(self):
        self._stop_flag = True
        self.status.set("正在停止...", "warning")

    def _update_progress(self, current, total, msg=""):
        pct = int(current / total * 100) if total > 0 else 0
        self.after(0, lambda: [
            self.progress.configure(value=pct),
            self.prog_label.config(text=f"{msg}  ({current}/{total})  {pct}%"),
        ])

    def _on_done(self, result_path):
        self._is_running = False
        self.ring.stop()
        self.progress["value"] = 100
        self._result_path = result_path
        self.status.set(f"完成！輸出：{Path(result_path).name}", "success")
        self._log(f"翻譯完成 → {result_path}", "success")
        messagebox.showinfo("完成", f"翻譯完成！\n\n輸出檔案：\n{result_path}")

    def _on_error(self, msg):
        self._is_running = False
        self.ring.stop()
        self.status.set("發生錯誤", "error")
        self._log(f"錯誤：{msg}", "error")
        messagebox.showerror("錯誤", msg)

    def _save_output(self):
        if not hasattr(self, "_result_path") or not self._result_path:
            messagebox.showinfo("提示", "尚無輸出檔案。")
            return
        dest = filedialog.asksaveasfilename(
            defaultextension=Path(self._result_path).suffix,
            initialfile=Path(self._result_path).name)
        if dest:
            import shutil
            shutil.copy2(self._result_path, dest)
            self.status.set(f"已另存：{Path(dest).name}", "success")

    # ── 日誌 ────────────────────────────────────────────────────────────────
    def _log(self, msg, level="info"):
        def _write():
            ts = datetime.now().strftime("%H:%M:%S")
            self.log_box.config(state="normal")
            self.log_box.insert("end", f"[{ts}] {msg}\n", level)
            self.log_box.see("end")
            self.log_box.config(state="disabled")
        self.after(0, _write)

    # ── 批次 ────────────────────────────────────────────────────────────────
    def _batch_add(self):
        paths = filedialog.askopenfilenames(
            filetypes=[("支援格式", "*.csv *.xlsx *.xls *.txt")])
        for p in paths:
            if p not in self._batch_files:
                self._batch_files.append(p)
                size = Path(p).stat().st_size
                size_str = f"{size/1024:.1f} KB"
                self.batch_tree.insert("", "end",
                                       values=(p, size_str, "等待", "0%"))

    def _batch_clear(self):
        self._batch_files.clear()
        for item in self.batch_tree.get_children():
            self.batch_tree.delete(item)

    def _batch_run(self):
        if not self._batch_files:
            messagebox.showwarning("提示", "請先新增檔案。")
            return
        src = self._get_lang_code(self.src_lang.get())
        tgt = self._get_lang_code(self.tgt_lang.get())
        api = self.api_var.get()

        def run():
            items = self.batch_tree.get_children()
            for i, (path, item) in enumerate(zip(self._batch_files, items)):
                self.after(0, lambda it=item: self.batch_tree.set(it, "status", "翻譯中"))
                try:
                    result = self.file_handler.translate_file(
                        path, src, tgt, api, self.engine,
                        self.skip_header_var.get(), None,
                        self.delay_var.get(),
                        progress_cb=None, log_cb=self._log,
                        stop_flag=lambda: False)
                    self.after(0, lambda it=item: [
                        self.batch_tree.set(it, "status", "完成"),
                        self.batch_tree.set(it, "progress", "100%")])
                except Exception as e:
                    self.after(0, lambda it=item, err=str(e): [
                        self.batch_tree.set(it, "status", "錯誤"),
                        self.batch_tree.set(it, "progress", err[:20])])

        threading.Thread(target=run, daemon=True).start()

    # ── 設定 ────────────────────────────────────────────────────────────────
    def _save_settings(self):
        for key, entry in self._setting_entries.items():
            self.config_mgr.set(key, entry.get())
        self.config_mgr.save()
        self.engine.reload_config(self.config_mgr)
        messagebox.showinfo("設定", "設定已儲存。")
        self.status.set("設定已儲存", "success")

    def _test_api(self):
        api = self.api_var.get()
        self.status.set("測試連線中...", "info")

        def run():
            result = self.engine.translate("Hello", "en", "zh-TW", api)
            ok = bool(result) and result != "Hello"
            self.after(0, lambda: [
                self.status.set(
                    f"✅ 連線成功（測試：{result}）" if ok else "❌ 連線失敗",
                    "success" if ok else "error"),
                messagebox.showinfo("測試結果",
                    f"API：{api}\n結果：{result}" if ok
                    else f"API：{api}\n連線失敗，請確認設定。")
            ])

        threading.Thread(target=run, daemon=True).start()

    def _on_api_change(self):
        api = self.api_var.get()
        if api == "settings":
            self._switch_tab("settings")

    def _load_settings(self):
        for key, entry in self._setting_entries.items():
            val = self.config_mgr.get(key, "")
            if val:
                entry.delete(0, "end")
                entry.insert(0, val)

    def _apply_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Accent.Horizontal.TProgressbar",
                         background=COLORS["accent"],
                         troughcolor=COLORS["bg_dark"],
                         borderwidth=0, lightcolor=COLORS["accent"],
                         darkcolor=COLORS["accent"])
        style.configure("TCombobox",
                         fieldbackground=COLORS["bg_dark"],
                         background=COLORS["bg_dark"],
                         foreground=COLORS["text_primary"],
                         selectbackground=COLORS["accent"],
                         arrowcolor=COLORS["accent"])
        style.configure("Treeview",
                         background=COLORS["bg_dark"],
                         foreground=COLORS["text_primary"],
                         fieldbackground=COLORS["bg_dark"],
                         rowheight=26)
        style.configure("Treeview.Heading",
                         background=COLORS["bg_card"],
                         foreground=COLORS["text_secondary"],
                         relief="flat")
        style.map("Treeview", background=[("selected", COLORS["accent"])])


def main():
    app = TranslateXApp()
    app._apply_styles()
    app.mainloop()


if __name__ == "__main__":
    main()
