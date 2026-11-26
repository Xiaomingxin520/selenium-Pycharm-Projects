# 项目概述
基于 **Playwright + Pytest** 的 Web UI 自动化测试框架，经典 PO 三层架构 +
CSV 数据驱动 + 业务流封装。Selenium 存量用例同仓共存（`test_case/` 冻结维护），
双引擎零冲突。支持多环境切换、登录态双粒度复用、
失败自动 Trace 回放与 Jenkins 无头持续集成。

# 目录结构与框架设计思路
```text
Python Projects/
├── page/               # 页面对象层 (PO模式)：元素定位与基础操作
│   ├── xxx1_page.py
│   ├── xxx2_page.py
│   └── xxx3_page.py
│   └── ....py
├── business/           # 业务层：串联多页面，封装核心业务流程
│   ├── test1_business.py
│   ├── test2_business.py
│   └── test3_business.py
│   └── ....py
├── test_case/          # 测试用例层：Pytest参数化，专注断言逻辑
│   ├── test_xxx1.py
│   ├── test_xxx2.py
│   └── test_xxx3.py
│   └── ....py
├── data/               # 数据驱动层：CSV管理测试数据，实现脚本与数据解耦
│   └── xxx1.csv
│   └── xxx2.csv
│   └── xxx3.csv
│   └── ....csv
├── reports/            # 测试报告与日志输出
├── conftest.py         # Pytest全局夹具 (Fixture)，管理浏览器生命周期
├── pytest.ini          # Pytest运行配置（标记、插件等）
├── operateElement.py   # 基础元素操作封装（显式等待、点击输入等）
├── Jenkinsfile         # CI/CD流水线定义（无头模式+Allure报告）
├── .venv/              # 虚拟环境
├── .gitignore          # Git忽略配置（已优化IDE缓存与日志）
└── README.md
```

# 分层架构思想
- **页面层 (page)**：只存 **Locator 字符串**（每次求值 = 天然防 Stale），零 `WebElement`
  缓存、零 `time.sleep`。彈窗類同構組件必須 **結構契約 + 內容消歧**：
  `div[role='dialog']:visible` 定位，再用標題關鍵詞區分出發/到達——**不猜 testid**。
- **业务层 (business)**：組合頁面動作成業務流，`print` 即日誌契約（CI 只看輸出就定位）。
  方法名 / 參數 / 返回值視為對外 API，用例層不感知頁面結構變化。
- **用例层 (test_case_pw)**：**不出現任何選擇器**，只調 business + 斷言。
  fixture 粒度按「數據潔淨度」選，不按「跑得快」選（見下表）。
- **配置层 (conftest)**：瀏覽器生命週期、登錄態雙通道、失敗自動截圖 / Trace、
  Selenium↔Playwright Cookie 橋接，全部收口在一個文件。

# Fixture 粒度速查（選錯 = 假綠，本框架最重要的一張表）
| Fixture | 粒度 | Context | 適用場景 |
|---|---|---|---|
| `pw_page` | function | 全新 | **登錄 CSV 負向用例必須用這個**；獨立用例默認 |
| `pw_logged_in_page` | function | Cookie 注入 | 單條登錄態用例 |
| `pw_module_page` | module | 全新（遊客態） | 流程型分步：船票 test_01 選線 → test_02 查日期 |
| `pw_module_page_logged_in` | module | **真登一次** | 大巴 22 條乘客組合 / 4 支付渠道 |
> ⚠️ 把登錄 CSV 掛到 module 級 → 第 2 條起帶登錄態，彈窗都不開，**負向用例全部假綠**。
> module 級**不走 Cookie 橋接**（過期會整 module 靜默變遊客態），改真登 + 當場自證。

# 登录态管理（雙通道，同倉共存）
- **通道 A（Selenium 存量）**：session 級 `_login_driver` 登一次 →
  `login_cookies` → function 級 `logged_in_driver` 注入，舊用例零改動。

- **通道 B（Playwright 主路徑）**：`_ensure_login_cookies`（session 級）**三級回落**
  ① 讀 cache → ② 自開一次性 context 真登一次並寫 cache → ③ 都失敗 **`pytest.fail`**。
  修掉原「第 1 條 `@use_login` 用例永遠拿不到 Cookie」的時序死鎖。

- **半截 Cookie 攔截**：登錄後雙通道自證——會話 Cookie 名（`session*`/`token`/`auth`）
  **或** `[data-testid='header-user-trigger']` 用戶區，任一不成立直接 fail，
  **絕不靜默以遊客態跑完 22 條全綠**。

- 賬號切換：`LOGIN_EMAIL` / `LOGIN_PHONE` + `LOGIN_PWD`（環境變量，倉庫零明文）。

# 防 Stale 策略（Playwright 原生優勢，20+ 處 `time.sleep` 已清除）
- **Locator 惰性求值**：每次操作重新解析 DOM，不緩存句柄 → `StaleElementReference`
  這一類問題從根上消失，無需重試裝飾器。

- **Auto-wait 五連檢**：click 前自動等 Visible / Stable / Receives Events / Enabled /
  Not Inert；`expect(locator).to_be_visible()` 自帶重試斷言，替代 `WebDriverWait`。

- **點擊統一兩級降級**：`真點擊 → force=True`，**全局零 `dispatch_event`**
  （它會跳過命中測試，測不出「用戶真的點不到」這類前端缺陷）。
  唯一 JS 兜底 `check_agreement(force_js=True)` 留作逃生艙並在日誌標紅。

- **時序判據（排查 CI 必備）**：
  - `waiting for locator(...)` → **attached 階段就沒命中** → 選擇器 / testid 寫錯或不存在
  - `element is not visible` → 節點在但 `display:none` / 零尺寸 → 時序或沒觸發打開
  > Playwright 的 visible = 非空 box + 非 `visibility:hidden`，**`opacity:0` 算可見**；
  > antd Modal 關閉時默認不銷毀 DOM 只掛 `display:none`。故卡在 `waiting`
  > 只有一種解釋：**這個 testid 前端壓根沒加**。
- **Toast 搶窗口**：AntD Toast 只活 3s，登錄返回後**立刻**在 3s 內抓，
  絕不「先 sleep 1.5 再 Wait 6」——那樣最壞 7.5s 必然錯過，紅得莫名其妙。

# 斷言哲學（寬斷言 + 窄日誌）
- 文本一律 **包含匹配**（`expect_text in actual`），防後端文案微調炸全量；
  核心負向用例可選 `expect_text_strict` 走 `==`。
- **每個斷言失敗都附上下文**：預期 / 實際原文 + `case_id` + 入參快照 + 全頁截圖，
  Allure 裏直接讀文本，不用放大截圖數像素。
- **`expect_text` 空值 → 收集期 `pytest.fail`**：`'' in '任意串'` 恆 True 是數據驅動
  最經典的假綠，必須在第一時間炸。
- **支付 QR 碼**：`strict_qrcode=False`（默認）放行但**日誌明寫「未 strict 校驗」**；
  開 `True` 才真斷言 —— 技術債自曝，不裝作測過了。

# 技术栈
- **Python 3.12** / **Playwright 1.64.1**（sync API）/ Selenium 4 共存
- **Pytest 8.x** + `pytest-order` / `pytest-playwright` / `pytest-metadata`
- **Allure 2.16**（報告 + 附件：截圖 / Trace / 上下文文本）
- **CSV** 輕量數據驅動（`utf-8-sig`，髒值詞典 `<null>/NULL/None/nan` 統一歸空）
- **Git**（多遠程備份）/ **Jenkins**（無頭流水線 + Webhook）

# 框架特性
- **PO + Locator 惰性**：UI 變更只改 page 層，且選擇器字符串與舊版逐字對齊可回溯。
- **測試隔離優先於速度**：function 級全新 context = 全新 cookie jar；
  慢 4~6s/條，換「用例順序不影響結果」。
- **可觀測性內建**：`LoginBusiness` 輸出 `Toast(success/error): <後端原文>`、
  彈窗串臺報錯附「頁面上所有 bus-* testid 清單」、日期斷言附 URL + body 前 300 字。
- **失敗即 Trace**：`--pw-trace` 開啓後 `playwright show-trace xxx.zip` 逐幀回放。
- **雙引擎零衝突**：`pytest test_case_pw/`（主）/ `pytest test_case/ -m selenium`（存量回歸）。
- **技術債可追溯**：11 個文件尾 TODO 共 19 條，標 P0/P1/P2 + 能消掉哪幾個 XPath，
  本次提交**只含引擎替換**，`git bisect` 能一刀切到根因。

# 持续集成（Jenkins）
根目錄 `Jenkinsfile`（聲明式流水線）：
- **無頭**：CI 自動 `HEADLESS=true`；module 級 fixture 亦透傳 `request`，
  `--headless` CLI 與環境變量雙通道生效。
- **依賴**：`pip install -r requirements.txt` + `playwright install chromium --with-deps`
- **執行**：`pytest test_case_pw/ -m "(smoke or playwright) and not slow" --pw-trace=retain-on-failure`
- **報告**：`reports/allure-results/` → Allure 插件渲染；Trace / 截圖作附件掛載。
- **分層調度**：日常跳過 `-m slow`（22 條乘客組合）；夜間全量含 slow。
- **觸發**：推送 GitLab/GitHub → Webhook 自動觸發。

# 快速开始
1. **环境安装**：`pip install -r requirements.txt`
2. **执行测试**：`pytest test_case/ -v`
3. **数据配置**：修改 `data/` 目录下对应 CSV 文件（如登录账号、车票查询条件）。
4. **CI执行**：推送代码至远程仓库，Jenkins 自动拉取并以无头模式运行。

# 注意事项
- 僅跑**測試環境**  **禁止對生產執行下單類用例**。
- 新增頁面嚴格 **page → business → test_case_pw** 順序；**用例層出現選擇器 = Code Review 打回**。
- 定位器變化只改 page 層；**彈窗/抽屜類同構組件用「結構 + 標題消歧」，不要靠複製 testid 猜名字**。
- fixture 粒度別爲了提速往上升級；**假綠比紅貴一百倍**——紅當天就修，假綠能在 CI 躺三個月。
- 密碼、Cookie、token 一律走環境變量或 Jenkins Credentials，**倉庫零明文**。
- 新增 CSV 列**只允許追加到末尾並給默認值**，保證舊行不報 `KeyError`。