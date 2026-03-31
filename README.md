# TranslateX — 翻譯工具

支援多種翻譯 API、可處理 CSV / Excel / TXT 檔案的桌面翻譯工具，介面完全繁體中文化。

---

##  功能特色

| 功能             | 說明                                               |
|------------------|----------------------------------------------------|
| 多 API 支援      | Google（免費）、DeepL、Microsoft Azure、OpenAI GPT |
| 自訂 API         | 填入任意 REST API 端點，支援 JSON 模板             |
| 文字即時翻譯     | 介面直接輸入翻譯，支援複製結果                     |
| 檔案翻譯         | 支援 .csv、.xlsx、.xls、.txt                       |
| 批次翻譯         | 一次選取多個檔案依序翻譯                           |
| 欄位選擇         | 指定 CSV/Excel 中要翻譯的欄位（A, B, C 或 1, 2, 3）|
| 進度顯示         | 即時進度條 + 環形動畫 + 翻譯日誌                   |
| 繁體中文 UI      | 全介面繁體中文，深色主題設計                       |
| 設定持久化       | API 金鑰儲存於本機 `~/.translatex/config.json`    |

---

##  快速開始

### 1. 安裝相依套件

```bash
pip install -r requirements.txt
```

### 2. 在 VSCode 中開啟

```bash
code translator_app/
```

按 `F5` 或點選 **Run → Start Debugging** 啟動。

### 3. 直接執行

```bash
python main.py
```

---

##  專案結構

```
translator_app/
├── main.py              # 主程式（GUI 介面）
├── translator_engine.py # 翻譯引擎（各 API 實作）
├── file_handler.py      # 檔案讀寫處理
├── config_manager.py    # 設定管理
├── requirements.txt     # 相依套件
└── .vscode/
    ├── launch.json      # 除錯設定
    └── settings.json    # 編輯器設定
```

---

##  翻譯 API 設定

### Google 翻譯（免費，無需金鑰）
- 預設即可使用，呼叫非官方 API
- 有請求頻率限制，建議設定請求間隔 ≥ 0.5 秒

### DeepL
1. 前往 [deepl.com/pro-api](https://www.deepl.com/pro-api) 申請
2. 免費方案金鑰結尾為 `:fx`
3. 在「設定」頁填入 API 金鑰

### Microsoft Azure 翻譯
1. 在 Azure 建立「翻譯工具」資源
2. 複製「訂閱金鑰」和「區域」
3. 在「設定」頁填入

### OpenAI GPT
1. 前往 [platform.openai.com](https://platform.openai.com) 取得 API Key
2. 在「設定」頁填入
3. 可選擇模型：`gpt-4o-mini`（便宜）或 `gpt-4o`（高品質）

### 自訂 API
填入以下資訊：
- **端點 URL**：REST API 的完整 URL
- **API 金鑰**：若需要驗證（Bearer Token）
- **請求模板**：JSON 格式，使用以下佔位符：
  - `{text}` — 待翻譯文字
  - `{src}`  — 來源語言代碼
  - `{tgt}`  — 目標語言代碼

範例模板：
```json
{"q": "{text}", "source": "{src}", "target": "{tgt}"}
```

---

##  檔案格式說明

### CSV
- 支援 UTF-8、Big5、GBK 等編碼（自動偵測）
- 輸出為 UTF-8（含 BOM），相容 Excel 開啟
- 可勾選「跳過標題列」保留欄位名稱

### Excel (.xlsx / .xls)
- 保留原始格式、樣式、公式
- 支援多個工作表（Sheet）
- 輸出為同格式的新檔案

### TXT
- 逐行翻譯，保留空行結構
- 支援 UTF-8 編碼

---

## ⚙️ 欄位選擇格式

在「選擇特定欄位」輸入框中輸入：

| 格式           | 說明                        |
|----------------|-----------------------------|
| `A, C, E`      | 英文字母欄位（Excel 標記法）|
| `1, 3, 5`      | 數字欄位編號（從 1 開始）   |
| `姓名, 描述`   | 欄位標題名稱（需有標題列）  |

---

##  常見問題

**Q：tkinter 找不到？**
- macOS：`brew install python-tk`
- Ubuntu：`sudo apt install python3-tk`
- Windows：重新安裝 Python，勾選「tcl/tk」選項

**Q：Excel 檔案無法開啟？**
- 執行：`pip install openpyxl`

**Q：Google 翻譯失敗？**
- 調高「請求間隔」至 1 秒以上
- 確認網路連線正常

**Q：設定儲存在哪裡？**
- `~/.translatex/config.json`（Windows：`C:\Users\你的名字\.translatex\config.json`）

---
