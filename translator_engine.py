#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
TranslatorEngine — 多 API 翻譯引擎
支援：Google、DeepL、Microsoft Azure、OpenAI、自訂 API
"""

import json
import time
import urllib.parse
import urllib.request
import urllib.error
import http.client


LANG_MAP_GOOGLE = {
    "zh-TW": "zh-TW",
    "zh-CN": "zh-CN",
    "auto":  "auto",
}

LANG_MAP_MS = {
    "zh-TW": "zh-Hant",
    "zh-CN": "zh-Hans",
    "auto":  None,
}


class TranslatorEngine:
    def __init__(self, config_mgr):
        self.cfg = config_mgr
        self._retry = 3

    def reload_config(self, config_mgr):
        self.cfg = config_mgr

    def translate(self, text: str, src: str, tgt: str, api: str) -> str:
        if not text or not text.strip():
            return ""

        methods = {
            "google":    self._google,
            "deepl":     self._deepl,
            "microsoft": self._microsoft,
            "openai":    self._openai,
            "custom":    self._custom,
        }
        fn = methods.get(api, self._google)

        for attempt in range(self._retry):
            try:
                result = fn(text.strip(), src, tgt)
                return result or text
            except Exception as e:
                if attempt == self._retry - 1:
                    raise RuntimeError(f"[{api}] 翻譯失敗：{e}")
                time.sleep(1.5 ** attempt)
        return text

    # ── Google 翻譯（免費非官方） ─────────────────────────────────────────
    def _google(self, text: str, src: str, tgt: str) -> str:
        src_code = src if src != "auto" else "auto"
        tgt_code = tgt

        url = (
            "https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl={src_code}&tl={tgt_code}&dt=t"
            f"&q={urllib.parse.quote(text)}"
        )
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        parts = []
        for block in data[0]:
            if block and block[0]:
                parts.append(block[0])
        return "".join(parts)

    # ── DeepL ────────────────────────────────────────────────────────────
    def _deepl(self, text: str, src: str, tgt: str) -> str:
        key = self.cfg.get("deepl_key", "")
        if not key:
            raise ValueError("請在設定中填入 DeepL API 金鑰")

        # 語言代碼轉換
        tgt_code = "ZH" if tgt.startswith("zh") else tgt.upper()
        src_code = None if src == "auto" else src.upper()

        payload = {"text": [text], "target_lang": tgt_code}
        if src_code:
            payload["source_lang"] = src_code

        data = json.dumps(payload).encode("utf-8")

        # 偵測是否為免費 API (含 :fx)
        base = "api-free.deepl.com" if key.endswith(":fx") else "api.deepl.com"
        conn = http.client.HTTPSConnection(base, timeout=15)
        conn.request("POST", "/v2/translate",
                     body=data,
                     headers={
                         "Authorization": f"DeepL-Auth-Key {key}",
                         "Content-Type": "application/json",
                     })
        resp = conn.getresponse()
        result = json.loads(resp.read().decode("utf-8"))
        return result["translations"][0]["text"]

    # ── Microsoft Azure ───────────────────────────────────────────────────
    def _microsoft(self, text: str, src: str, tgt: str) -> str:
        key    = self.cfg.get("ms_key", "")
        region = self.cfg.get("ms_region", "eastus")
        if not key:
            raise ValueError("請在設定中填入 Microsoft Azure 訂閱金鑰")

        tgt_code = LANG_MAP_MS.get(tgt, tgt)
        src_code = LANG_MAP_MS.get(src, src) if src != "auto" else None

        url = "https://api.cognitive.microsofttranslator.com/translate?api-version=3.0"
        url += f"&to={tgt_code}"
        if src_code:
            url += f"&from={src_code}"

        payload = json.dumps([{"text": text}]).encode("utf-8")
        req = urllib.request.Request(url, data=payload, method="POST", headers={
            "Ocp-Apim-Subscription-Key": key,
            "Ocp-Apim-Subscription-Region": region,
            "Content-Type": "application/json; charset=UTF-8",
        })
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        return result[0]["translations"][0]["text"]

    # ── OpenAI GPT ───────────────────────────────────────────────────────
    def _openai(self, text: str, src: str, tgt: str) -> str:
        key   = self.cfg.get("openai_key", "")
        model = self.cfg.get("openai_model", "gpt-4o-mini")
        if not key:
            raise ValueError("請在設定中填入 OpenAI API Key")

        lang_names = {
            "zh-TW": "繁體中文",
            "zh-CN": "簡體中文",
            "en":    "英文",
            "ja":    "日文",
            "ko":    "韓文",
            "fr":    "法文",
            "de":    "德文",
            "es":    "西班牙文",
        }
        tgt_name = lang_names.get(tgt, tgt)
        src_name = lang_names.get(src, src) if src != "auto" else "原始語言"

        payload = {
            "model": model,
            "messages": [
                {"role": "system",
                 "content": (
                     f"你是一位專業翻譯員。請將以下{src_name}文字翻譯成{tgt_name}。"
                     "只需輸出譯文，不要添加任何說明或標注。"
                 )},
                {"role": "user", "content": text},
            ],
            "temperature": 0.2,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=data, method="POST",
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            })
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        return result["choices"][0]["message"]["content"].strip()

    # ── 自訂 API ─────────────────────────────────────────────────────────
    def _custom(self, text: str, src: str, tgt: str) -> str:
        url  = self.cfg.get("custom_url", "")
        key  = self.cfg.get("custom_key", "")
        body = self.cfg.get("custom_body", "")

        if not url:
            raise ValueError("請在設定中填入自訂 API 端點 URL")

        # 替換佔位符
        body_str = body.replace("{text}", text).replace("{src}", src).replace("{tgt}", tgt)

        headers = {"Content-Type": "application/json"}
        if key:
            headers["Authorization"] = f"Bearer {key}"

        req = urllib.request.Request(
            url, data=body_str.encode("utf-8") if body_str else None,
            method="POST", headers=headers)

        with urllib.request.urlopen(req, timeout=15) as resp:
            raw = resp.read().decode("utf-8")

        # 嘗試解析 JSON，取第一個字串值
        try:
            parsed = json.loads(raw)
            if isinstance(parsed, str):
                return parsed
            if isinstance(parsed, dict):
                for v in parsed.values():
                    if isinstance(v, str) and v:
                        return v
            if isinstance(parsed, list) and parsed:
                first = parsed[0]
                if isinstance(first, str):
                    return first
                if isinstance(first, dict):
                    for v in first.values():
                        if isinstance(v, str) and v:
                            return v
        except Exception:
            pass

        return raw.strip()
