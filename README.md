# 项目概述
基于 Selenium WebDriver与Pytest搭建的 Web UI 自动化测试框架。项目采用经典的 PO (Page Object) 分层设计模式，结合数据驱动（CSV）与业务流封装，
具备高可维护性与易扩展性。目前已覆盖登录及大巴票核心业务（搜索/下单骨架），支持多环境配置与持续集成。

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
├── Jenkinsfile            # CI/CD流水线定义（无头模式+Allure报告）
├── .venv/              # 虚拟环境
├── .gitignore          # Git忽略配置（已优化IDE缓存与日志）
└── README.md
```

# 分层架构思想
- **页面层 (page)**：封装UI元素与基础动作，屏蔽底层定位器变化。
- **业务层 (business)**：组合页面动作，形成可复用的业务流（如：登录→搜索→下单）。
- **用例层 (test_case)**：调用业务层，结合 CSV 数据驱动，执行多场景断言。
- **配置层 (conftest等)**：统一驱动管理、前置后置处理，提升代码整洁度。

# 技术栈
- **Python 3.8+** / **Selenium WebDriver**（UI自动化核心）
- **Pytest**（测试框架与参数化）
- **Allure / HTML报告**（测试报告生成，可扩展）
- **CSV**（轻量级数据驱动）
- **Git**（版本控制，支持多远程仓库备份）
- **Jenkins**（持续集成，流水线自动触发）

# 框架特性
- **PO模式**：降低代码冗余，UI变更只需修改页面层。
- **数据驱动**：业务数据与脚本分离，快速覆盖正向/异常场景。
- **显式等待**：封装健壮的元素交互，应对动态渲染页面（如跨月日历、弹窗）。
- **多端兼容**：基础架构支持登录、票务等复杂业务扩展。
- **工程化规范**：已清理IDE缓存（pycache、idea），保持仓库整洁。
- **CI/CD 预留**：conftest 支持 HEADLESS 环境变量切换，Jenkinsfile 定义完整流水线，本地调试与服务器无头执行无缝切换。

# 持续集成（Jenkins）
项目根目录包含 `Jenkinsfile`（无后缀），定义声明式流水线：
- **无头模式**：CI 环境自动设置 `HEADLESS=true`，无需修改业务代码。
- **依赖安装**：自动执行 `pip install -r requirements.txt`。
- **测试执行**：运行 `pytest`，结果写入 `reports/allure-results/`。
- **报告收集**：流水线结束后自动生成 Allure 报告并清理工作空间。
- **触发方式**：代码推送至 GitLab/GitHub 后，通过 Webhook 自动触发（需 Jenkins 安装 Allure 插件）。

# 快速开始
1. **环境安装**：`pip install -r requirements.txt`
2. **执行测试**：`pytest test_case/ -v`
3. **数据配置**：修改 `data/` 目录下对应 CSV 文件（如登录账号、车票查询条件）。
4. **CI执行**：推送代码至远程仓库，Jenkins 自动拉取并以无头模式运行。