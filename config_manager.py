#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ConfigManager — 管理 API 金鑰與應用程式設定
設定儲存於使用者目錄下的 .translatex/config.json
"""

import json
import os
from pathlib import Path


CONFIG_DIR  = Path.home() / ".translatex"
CONFIG_FILE = CONFIG_DIR / "config.json"


class ConfigManager:
    def __init__(self):
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        self._data: dict = {}
        self._load()

    def _load(self):
        if CONFIG_FILE.exists():
            try:
                self._data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
            except Exception:
                self._data = {}

    def save(self):
        CONFIG_FILE.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding="utf-8")

    def get(self, key: str, default=None):
        return self._data.get(key, default)

    def set(self, key: str, value):
        self._data[key] = value

    def all(self) -> dict:
        return dict(self._data)
