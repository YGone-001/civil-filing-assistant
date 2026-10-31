# 民事立案文书助手（离线版）

离线填写案情，一次生成民事起诉状、证据清单与送达地址确认书。

民事立案文书助手是一款基于 Python 与 PySide6 的桌面向导工具，面向需要整理常见民事立案材料的个人与基层法律服务场景。应用在本机收集当事人和案情信息，按案由生成结构化诉讼请求、事实与理由以及配套 Word 文书，不依赖在线服务，也不会主动上传案件数据。

> **重要说明：** 本项目用于辅助整理文书，不构成法律意见，也不能替代律师、仲裁机构或人民法院的专业判断。正式提交前，请核对事实、金额、证据、管辖法院、程序前置条件及当地最新要求。

## 目录

- [核心能力](#核心能力)
- [支持的案件类型](#支持的案件类型)
- [工作流程](#工作流程)
- [本地草稿（保存与继续填写）](#本地草稿保存与继续填写)
- [架构](#架构)
- [技术栈](#技术栈)
- [快速开始](#快速开始)
- [构建与验证](#构建与验证)
- [输出与隐私](#输出与隐私)
- [项目结构](#项目结构)
- [当前边界](#当前边界)

## 核心能力

- **向导式信息采集：** 按案件类型依次填写当事人、事实、金额、证据和管辖法院等信息。
- **多案由文书生成：** 通过独立案件模型生成诉讼请求与事实理由，而不是只替换一份固定模板。
- **配套材料批量导出：** 一次生成民事起诉状、证据清单和送达地址确认书三份 `.docx` 文件。
- **常见证据建议：** 针对不同案由预置证据名称和证明目的，支持在界面中修改、增加或删除。
- **本地加密草稿：** 可随时把未填完的案件保存为本地 `.cfdraft` 草稿，稍后重新打开继续填写；草稿使用 Windows 当前用户加密，磁盘上不出现明文。
- **辅助计算与提示：** 支持借款利息暂计、物业费计算、欠薪金额计算，以及劳动争议仲裁前置提示。
- **本地隐私设计：** 启动时检查默认网络路由并提示离线使用，生成完成后对案件模型中的敏感字段执行尽力清理。

## 支持的案件类型

| 案件类型 | 结构化内容 | 已实现的辅助能力 |
| --- | --- | --- |
| 民间借贷纠纷 | 借款时间、用途、本金、交付方式、利率、催收情况 | 利息暂计、借条状态、证据建议 |
| 买卖合同纠纷 | 合同、标的、交付签收、欠款、违约金 | 逾期付款表述、交付状态、证据建议 |
| 物业服务合同纠纷 | 房屋、面积、单价、欠费期间、催缴记录 | 欠费月份与金额计算、金额偏差提示 |
| 劳动报酬／工资追索 | 入离职、岗位、工资、欠薪期间、加班、合同与社保 | 欠薪计算、未签合同请求、仲裁前置提示 |
| 离婚、析产与抚养费纠纷 | 婚姻、子女、抚养诉求、财产与离婚原因 | 抚养及财产诉求组织、证据建议 |

## 工作流程

1. 应用启动并检查当前设备是否存在默认网络路由；联网时提示用户切换到离线环境。
2. 用户选择案由，填写原被告、案件事实、金额和管辖法院。
3. 可随时点击“保存草稿”把当前进度加密保存到本地文件；下次启动后用“打开草稿”还原并继续填写。
4. 系统按案由载入常见证据，用户可根据实际材料调整清单。
5. 案件模型生成诉讼请求和事实理由，文档生成器套用 Word 排版。
6. 系统在桌面创建案件文件夹，输出三份立案材料，并对内存模型中的敏感字段执行尽力清理。

```mermaid
flowchart LR
    User["用户"] --> Entry["main.py<br/>应用入口"]
    Entry --> Guard["SecurityGuard<br/>网络状态提示"]
    Entry --> View["LawsuitWizard<br/>向导界面"]
    View --> Presenter["MainPresenter<br/>收集并编排数据"]
    Presenter --> Models["CaseModel<br/>五类案件模型"]
    View --> Evidence["EvidenceLibrary<br/>案由证据建议"]
    Evidence --> Presenter
    Models --> Generator["DocumentGenerator<br/>Word 文书生成"]
    Presenter --> Batch["BatchExportManager<br/>命名与批量导出"]
    Batch --> Generator
    Generator --> Output["桌面案件目录<br/>起诉状 / 证据清单 / 送达确认书"]
    Presenter --> Guard
    View --> DraftPresenter["DraftPresenter<br/>草稿保存与还原"]
    DraftPresenter --> Drafts["drafts<br/>严格校验 + DPAPI 加密"]
    Drafts --> DraftFile["本地 .cfdraft 草稿"]
```

## 本地草稿（保存与继续填写）

向导按钮栏中的 **保存草稿** 与 **打开草稿** 让用户在任何一步把未填完的案件保存到本地文件，下次启动后继续填写，而不必一次完成。

- **保存位置由用户决定：** 每次保存都会弹出文件对话框，默认建议一个不含当事人姓名的文件名（`案件草稿_YYYYMMDD_HHMM.cfdraft`）。
- **写入前加密：** 草稿在落盘前使用 Windows 数据保护 API（DPAPI）以**当前 Windows 用户**作用域加密；磁盘上只有密文，不会产生明文临时文件，加密失败时也不会退回明文保存。
- **保存的是输入，不是文书：** 草稿记录当事人卡片、案情字段、金额原文、三态确认项、证据行及其状态、当前步骤；不包含已生成的 Word 文件、渲染后的诉状正文、计算结果或辅助计算记录。
- **任何步骤都可以保存：** 当事人未填完、必填项为空、条件字段尚未确定、证据尚未填写时都能保存，保存动作不会触发导出前的完整性校验。
- **打开失败不会破坏当前内容：** 草稿会先在独立的向导中完整还原并校验，成功后才替换当前窗口；损坏、被篡改或版本不受支持的草稿会被拒绝，当前填写内容保持不变。
- **不自动保存：** 程序不会后台写盘、不会在退出时自动保存，也不会创建隐藏的恢复文件。

### 可移植性限制

DPAPI 的密钥来自当前 Windows 用户的配置文件，因此：

- 草稿**不保证**在另一个 Windows 账户、另一台电脑、重装系统或用户配置文件与密钥丢失后仍能打开；
- 草稿**不是**通用备份，请勿作为案件材料的唯一留存方式；
- 加密只保护文件内容，不能阻止使用同一 Windows 账户的其他程序读取，也不能防范恶意软件。

草稿扩展名为 `.cfdraft`，已被 `.gitignore` 排除；不要把它提交到仓库或放在共享目录中。

## 架构

项目采用轻量的 Model–View–Presenter 组织方式：

| 层次 | 位置 | 职责 |
| --- | --- | --- |
| 入口 | [`main.py`](main.py) | 创建 Qt 应用、执行网络状态提示、组装界面与 Presenter |
| View | [`views/`](views) | 向导页面、字段校验、案由分支和预览界面 |
| Presenter | [`presenters/main_presenter.py`](presenters/main_presenter.py) | 将界面字段转换为案件模型并触发批量导出 |
| 草稿 | [`presenters/draft_presenter.py`](presenters/draft_presenter.py)、[`drafts/`](drafts) | 显式保存/打开草稿：严格校验、DPAPI 加密、原子写入与整窗还原 |
| Model | [`models/case_model.py`](models/case_model.py) | 当事人、证据和五类案件的请求／事实生成逻辑 |
| 文书与规则工具 | [`utils/`](utils) | Word 排版、证据建议、批量命名、程序提示与隐私清理 |

应用当前没有数据库、服务端接口或云端依赖。案件数据只在当前进程、用户主动保存的本地草稿和生成的本地 Word 文件中流转。

草稿相关代码分为四层，且依赖方向单向向下：向导（[`views/draft_io.py`](views/draft_io.py)）→ 快照编排（[`presenters/draft_presenter.py`](presenters/draft_presenter.py)）→ 校验格式（[`drafts/schema.py`](drafts/schema.py)）→ 加密存储（[`drafts/storage.py`](drafts/storage.py)）→ Windows DPAPI（[`drafts/windows_protection.py`](drafts/windows_protection.py)）。存储层不导入 PySide6，业务计算仍留在 [`models/calculations.py`](models/calculations.py)。

## 技术栈

| 组件 | 用途 | 项目约束 |
| --- | --- | --- |
| Python | 应用运行时 | 项目尚未固定 Python 次版本；当前仓库已用 Python 3.12.10 完成语法检查 |
| PySide6 | Qt 桌面界面 | `>=6.5.0` |
| python-docx | Word 文书生成 | `>=0.8.11` |
| PyInstaller | Windows 可执行程序打包 | `>=6.0.0` |

当前主要面向 Windows 桌面环境。源码包含其他桌面系统的网络路由检测分支，但仓库只提供了 Windows 构建脚本，其他平台尚未完成打包验证。

## 快速开始

### 1. 克隆项目

```powershell
git clone https://github.com/YGone-001/civil-filing-assistant.git
Set-Location civil-filing-assistant
```

### 2. 创建虚拟环境并安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. 启动应用

```powershell
python main.py
```

如果 PowerShell 阻止当前会话加载激活脚本，可以仅为当前进程调整执行策略：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 构建与验证

### 构建 Windows 应用

依赖安装完成后运行：

```powershell
.\build.bat
```

PyInstaller 会将结果写入 `dist/民事立案文书助手/`。`build/`、`dist/` 和生成的 `.spec` 文件均为本地产物，不纳入版本控制。

### 基础验证

执行 Python 语法检查：

```powershell
python -m compileall -q main.py models presenters utils views drafts test_generator.py tools tests
```

执行文书生成冒烟测试：

```powershell
python test_generator.py
```

运行自动化测试套件：

```powershell
python -m pytest -q
```

冒烟测试会在项目根目录生成 `测试_起诉状.docx`。该文件包含模拟案件信息，仅供本地检查，已被 `.gitignore` 排除。项目已建立自动化测试与 CI：`tests/` 目录下为 pytest 测试套件，GitHub Actions 工作流 `.github/workflows/ci.yml` 在 Windows 上执行编译检查、提交信息校验、重复测试检查、完整 pytest 套件与文档冒烟测试；法律模板治理元数据由 `tools/check_template_governance.py` 校验。

## 输出与隐私

应用默认在当前用户桌面创建以下目录：

```text
原告名_vs_被告名_YYYYMMDD/
├── 原告名_vs_被告名_YYYYMMDD_HHMMSS_民事起诉状.docx
├── 原告名_vs_被告名_YYYYMMDD_HHMMSS_证据清单.docx
└── 原告名_vs_被告名_YYYYMMDD_HHMMSS_送达地址确认书.docx
```

请注意以下隐私边界：

- 网络状态检查只判断设备是否存在默认路由，不等同于操作系统级网络隔离。
- 敏感字段清理是 Python 进程内的尽力处理，不能保证不可恢复或替代磁盘加密、安全擦除等措施。
- 生成的 Word 文件包含姓名、证件号码、地址、电话和案件事实，应由使用者自行安全保存和销毁。
- 草稿文件同样包含上述信息，仅以当前 Windows 用户的 DPAPI 密钥加密；删除草稿请自行在文件管理器中处理，程序不会代为擦除磁盘。
- 不要将真实案件文书、草稿文件、身份信息、凭据、日志或本地输出目录提交到公开仓库。

## 项目结构

```text
civil-filing-assistant/
├── main.py                    # 桌面应用入口
├── drafts/
│   ├── schema.py              # 草稿字段注册表与严格校验（无 Qt）
│   ├── storage.py             # 版本化加密信封与原子写入
│   └── windows_protection.py  # Windows DPAPI（当前用户）绑定
├── models/
│   └── case_model.py          # 当事人、证据和案件模型
├── presenters/
│   ├── main_presenter.py      # 界面与模型/导出流程的协调层
│   └── draft_presenter.py     # 保存/打开草稿的编排与确认流程
├── views/
│   ├── main_window.py         # 主向导、页面路由和测试填充
│   ├── draft_io.py            # 草稿与向导控件之间的唯一适配层
│   └── wizard_pages.py        # 各向导页面与表单字段
├── utils/
│   ├── batch_manager.py       # 批量导出目录与文件命名
│   ├── doc_generator.py       # Word 文书排版与保存
│   ├── evidence_library.py    # 各案由常见证据建议
│   ├── family_calc.py         # 抚养费估算辅助函数
│   ├── labor_security.py      # 劳动争议程序提示
│   └── security_check.py      # 网络提示与敏感字段清理
├── test_generator.py          # 文书生成冒烟测试
├── requirements.txt           # Python 依赖下限
├── build.bat                  # Windows PyInstaller 构建入口
└── AGENTS.md                  # 项目约定与维护规则
```

## 当前边界

- 生成结果是可编辑初稿，未接入法院、仲裁机构或任何电子诉讼平台。
- 法律规则、利率、程序期限和当地文书要求可能变化，项目不会自动联网更新。
- 输入校验和金额计算只覆盖当前源码中实现的规则，不能替代人工复核。
- 草稿为单文件、手工保存：没有自动保存、草稿数据库、最近案件检索、云端同步或多用户协作，也不提供密码加密的可移植草稿格式。
- 当前没有用户系统、自动更新、数字签名或电子送达能力。
- 仓库暂不附带许可证；在明确许可证前，不应推定项目已授予复制、修改或再分发许可。
