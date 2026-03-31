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
            "google":      self._google,
            "deepl":       self._deepl,
            "microsoft":   self._microsoft,
            "openai":      self._openai,
            "cloudflare":  self._cloudflare,
            "custom":      self._custom,
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

    # ── Cloudflare Workers AI ─────────────────────────────────────────────
    # 支援模型：
    #   @cf/meta/m2m100-1.2b              — 100 種語言直接互譯
    #   @cf/facebook/nllb-200-distilled-600M — 200 種語言
    # 若設定了 AI Gateway ID，則透過 Cloudflare AI Gateway 路由請求

    # m2m100 / NLLB 語言代碼對照表（部分）
    _CF_LANG = {
        "zh-TW": "zho",   # m2m100 使用 ISO 639-2
        "zh-CN": "zho",
        "en":    "eng",
        "ja":    "jpn",
        "ko":    "kor",
        "fr":    "fra",
        "de":    "deu",
        "es":    "spa",
        "it":    "ita",
        "pt":    "por",
        "ru":    "rus",
        "ar":    "ara",
        "th":    "tha",
        "vi":    "vie",
        "auto":  "eng",   # 自動偵測不支援時預設英文
    }

    # NLLB 使用不同格式的代碼
    _NLLB_LANG = {
        "zh-TW": "zho_Hant",
        "zh-CN": "zho_Hans",
        "en":    "eng_Latn",
        "ja":    "jpn_Jpan",
        "ko":    "kor_Hang",
        "fr":    "fra_Latn",
        "de":    "deu_Latn",
        "es":    "spa_Latn",
        "it":    "ita_Latn",
        "pt":    "por_Latn",
        "ru":    "rus_Cyrl",
        "ar":    "arb_Arab",
        "th":    "tha_Thai",
        "vi":    "vie_Latn",
        "auto":  "eng_Latn",
    }

    def _cloudflare(self, text: str, src: str, tgt: str) -> str:
        account_id = self.cfg.get("cf_account_id", "").strip()
        api_token  = self.cfg.get("cf_api_token",  "").strip()
        model      = self.cfg.get("cf_model", "@cf/meta/m2m100-1.2b").strip()
        gateway_id = self.cfg.get("cf_gateway_id", "").strip()

        if not account_id:
            raise ValueError("請在設定中填入 Cloudflare Account ID")
        if not api_token:
            raise ValueError("請在設定中填入 Cloudflare API Token")

        is_nllb = "nllb" in model.lower()

        if is_nllb:
            lang_map = self._NLLB_LANG
        else:
            lang_map = self._CF_LANG

        src_code = lang_map.get(src, src)
        tgt_code = lang_map.get(tgt, tgt)

        payload = json.dumps({
            "text": text,
            "source_lang": src_code,
            "target_lang": tgt_code,
        }).encode("utf-8")

        # 決定端點：使用 AI Gateway 或直接呼叫 Workers AI
        if gateway_id:
            url = (
                f"https://gateway.ai.cloudflare.com/v1/{account_id}"
                f"/{gateway_id}/workers-ai/{model}"
            )
        else:
            url = (
                f"https://api.cloudflare.com/client/v4/accounts"
                f"/{account_id}/ai/run/{model}"
            )

        req = urllib.request.Request(
            url, data=payload, method="POST",
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type":  "application/json",
            })

        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = json.loads(resp.read().decode("utf-8"))

        # 解析回應
        # Workers AI 回傳格式：{"result": {"translated_text": "..."}, "success": true}
        if isinstance(raw, dict):
            result = raw.get("result", raw)
            if isinstance(result, dict):
                for key in ("translated_text", "translation", "text", "result"):
                    val = result.get(key)
                    if isinstance(val, str) and val:
                        return val
            if isinstance(result, str):
                return result

        raise RuntimeError(f"Cloudflare 回應格式異常：{str(raw)[:200]}")

    # ── Cloudflare AI ────────────────────────────────────────────────────
    # 支援模型：
    #   @cf/meta/m2m100-1.2b          — Meta M2M100，100 種語言互譯
    #   @cf/facebook/nllb-200-distilled-600m — NLLB-200，200 種語言
    #
    # 語言代碼對照（Cloudflare 使用 FLORES-200 格式）
    _CF_LANG = {
        "zh-TW": "zho_Hant",   # 繁體中文
        "zh-CN": "zho_Hans",   # 簡體中文
        "en":    "eng_Latn",   # 英文
        "ja":    "jpn_Jpan",   # 日文
        "ko":    "kor_Hang",   # 韓文
        "fr":    "fra_Latn",   # 法文
        "de":    "deu_Latn",   # 德文
        "es":    "spa_Latn",   # 西班牙文
        "it":    "ita_Latn",   # 義大利文
        "pt":    "por_Latn",   # 葡萄牙文
        "ru":    "rus_Cyrl",   # 俄文
        "ar":    "arb_Arab",   # 阿拉伯文
        "th":    "tha_Thai",   # 泰文
        "vi":    "vie_Latn",   # 越南文
    }
    # m2m100 使用較簡短的代碼
    _CF_LANG_M2M = {
        "zh-TW": "zh",
        "zh-CN": "zh",
        "en":    "en",
        "ja":    "ja",
        "ko":    "ko",
        "fr":    "fr",
        "de":    "de",
        "es":    "es",
        "it":    "it",
        "pt":    "pt",
        "ru":    "ru",
        "ar":    "ar",
        "th":    "th",
        "vi":    "vi",
    }

    def _cloudflare(self, text: str, src: str, tgt: str) -> str:
        account_id = self.cfg.get("cf_account_id", "").strip()
        api_token  = self.cfg.get("cf_api_token",  "").strip()
        model      = self.cfg.get("cf_model", "@cf/meta/m2m100-1.2b").strip()

        if not account_id:
            raise ValueError("請在設定中填入 Cloudflare Account ID")
        if not api_token:
            raise ValueError("請在設定中填入 Cloudflare API Token")

        # 根據模型選擇語言代碼格式
        if "nllb" in model:
            lang_map = self._CF_LANG
            src_code = lang_map.get(src, "eng_Latn") if src != "auto" else None
            tgt_code = lang_map.get(tgt, "zho_Hant")
        else:
            # m2m100 及其他模型使用簡短代碼
            lang_map = self._CF_LANG_M2M
            src_code = lang_map.get(src, "en") if src != "auto" else None
            tgt_code = lang_map.get(tgt, "zh")

        payload = {"text": text, "target_lang": tgt_code}
        if src_code:
            payload["source_lang"] = src_code

        url = (f"https://api.cloudflare.com/client/v4/accounts/"
               f"{account_id}/ai/run/{model}")

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data, method="POST", headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type":  "application/json",
        })
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))

        # Cloudflare 回應格式：{"result": {"translated_text": "..."}, "success": true}
        if not result.get("success", False):
            errors = result.get("errors", [])
            raise RuntimeError(f"Cloudflare API 錯誤：{errors}")

        return result["result"]["translated_text"]

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
