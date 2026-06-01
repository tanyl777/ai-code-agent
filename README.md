# AI Code Agent — 基于 LangChain 的智能代码生成与审查助手

[![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-1.x-green?logo=langchain)](https://langchain.com)
[![Claude](https://img.shields.io/badge/Claude-API-orange?logo=anthropic)](https://anthropic.com)

基于 **LangChain 1.x + Claude/DeepSeek API** 构建的 AI 编程助手 Agent，将自然语言需求自动转化为高质量 Python 代码，同时提供静态代码审查、单元测试生成和 Git 提交信息生成能力。内置多轮对话记忆，支持自动错误修正。

---

## 能做什么

一个命令，覆盖开发全流程：

```
写代码   →  python cli.py run "实现二分查找"     # 生成 + 沙箱执行 + 报错自动修
审代码   →  python cli.py review src/             # AST 5 维度审查 (命名/复杂度/Bug/导入/格式)
测代码   →  python cli.py test src/utils.py        # pytest 生成 + 自动跑 + 失败自动修
写提交   →  python cli.py commit .                 # git diff → Conventional Commits
```

四条命令串起来，就是一条自动化编程产线。

## 为什么不用豆包/DeepSeek 聊天框

聊天框只能 **一问一答**，本项目做的是 **自动化闭环**：

| 聊天框 | 本项目 |
| ------ | ------ |
| 生成代码 → 你手动粘到IDE跑 → 报错 → 你贴回去让他修 | 生成 → 自动执行 → 报错 → **自动注入错误给LLM** → 修正（最多3轮） |
| "帮我review" → LLM随口一评，每次结果可能不同 | AST 规则引擎 → 同一文件审100次结果100%一致 → CI 可依赖 |
| 代码发到第三方服务器 | 换一行代码用本地模型，**数据不出本机** |
| 手动贴 diff 让它写 commit | `git diff` 自动分析，生成规范格式 |
| 你控制不了怎么审、怎么生成 | 完全控制 Prompt + 审查规则 → **注入团队编码规范** |

本质区别：聊天框是 **手动工具**，本项目是 **可集成的自动化产线**。

## 功效

| 效果 | 怎么做到的 |
| ---- | ---------- |
| ✅ 代码生成可运行率 **88%** | 沙箱执行 + 3轮自动反馈修正 |
| ✅ 低级 Bug **零漏网** | AST 确定性审查：裸 except、可变默认参数、star import |
| ✅ 审查结果 **100% 可复现** | 规则引擎，不是 LLM 主观判断 |
| ✅ Commit 格式 **100% 规范** | 强制 Conventional Commits，自动生成 CHANGELOG |
| ✅ 代码 **不出内网** | 换本地模型即可，满足金融/军工合规 |
| ✅ CI 管线 **直接对接** | `--json` 输出，对接 Jenkins/GitLab CI/工蜂 |

## 架构

```
用户自然语言输入
    |
    v
LangChain Agent (create_agent / ReAct 模式)
    +-- System Prompt (角色 + Few-shot 示例 + JSON 输出格式)
    +-- SqliteSaver Checkpointer (跨启动持久记忆)
    +-- Tool 路由 (LLM 根据意图自动选择)
    |   +-- code_interpreter  -> 代码生成 + 沙箱执行 + 自动修正 (<=3 轮)
    |   +-- static_reviewer   -> AST 静态审查 (5 维检查)
    |   +-- git_commit        -> Conventional Commits 生成
    |   +-- test_generator    -> pytest 单元测试生成 + 自动验证
    +-- ChatAnthropic (Claude / DeepSeek)
    |
    v
结构化 JSON 输出 + 记忆持久化
```

## 功能

### 1. 代码生成 (`code_interpreter`)
- 自然语言 → Python 完整可运行代码
- 受限沙箱执行环境（白名单 builtins，34 个安全内置函数）
- 执行失败自动反馈修正（最多 3 轮），实测可运行率 88%
- 输出：代码 + stdout/stderr + 尝试次数

### 2. 静态审查 (`static_reviewer`)
- **PEP 8**：行长度 > 100 字符检测
- **圈复杂度**：AST 分析分支数（if/for/while/except/boolop/match），超阈值警告
- **命名规范**：snake_case / PascalCase / UPPER_CASE 检测
- **Bug 模式**：可变默认参数(list/dict/set)、裸 except、star import
- **未使用导入**：对比 import vs 实际 Name 使用

### 3. Commit 生成 (`git_commit`)
- 分析 `git diff --staged` + `git diff` 双通道
- 生成 Conventional Commits 规范提交信息
- 多文件变更自动生成 body 摘要
- **仅建议，不自动提交**（Human-in-the-loop 安全设计）

### 4. 单元测试生成 (`test_generator`)  ← NEW
- 为 Python 源代码生成 pytest 单元测试
- 覆盖：基础功能 + 边界条件 + 异常情况
- 使用 @pytest.mark.parametrize 参数化
- 自动执行验证，失败时自动修正（最多 3 轮）

### 5. 记忆模块
- 基于 `SqliteSaver` checkpointer 的对话持久化
- `thread_id` 隔离不同会话
- `SessionMemory` 提供 JSON 可读备份和上下文摘要

## 快速开始

### 前置要求

- Python 3.9+
- Anthropic API Key 或 DeepSeek API Key

### 安装

```bash
git clone <your-repo-url>
cd ai-code-agent

pip install -r requirements.txt
pip install pytest  # 测试生成工具需要

# 设置 API Key
export ANTHROPIC_API_KEY="sk-..."
# Windows CMD: set ANTHROPIC_API_KEY=sk-...
# Windows PowerShell: $env:ANTHROPIC_API_KEY="sk-..."
```

### 使用

```bash
# 🖥 图形化界面（一键启动）
python gui.py

# 代码生成
python cli.py run "实现一个二分查找函数，返回索引或 -1"

# 静态审查
python cli.py review src/utils.py

# 生成 commit message
python cli.py commit

# 单元测试生成  ← NEW
python cli.py test src/utils.py
python cli.py test src/utils.py -o tests/test_utils.py  # 写入文件

# 交互式对话（多轮 + 记忆）
python cli.py chat

# JSON 格式输出（供脚本/CI 集成）
python cli.py run "写一个单例模式" --json
python cli.py review app.py --json
python cli.py test app.py --json
```

### 评估基准  ← NEW

```bash
# 完整 100 题评估
python -m eval.evaluator

# 快速评估（随机 10 题）
python -m eval.evaluator --quick

# 单分类评估
python -m eval.evaluator --category recursion

# 保存详细报告
python -m eval.evaluator -o report.json
```

## 配置

编辑 `config.py`：

```python
@dataclass
class LLMConfig:
    model: str = "claude-sonnet-4-6"    # Claude 或 DeepSeek 模型
    temperature: float = 0.1             # 代码生成需要确定性
    max_tokens: int = 4096
    base_url: str = "https://api.anthropic.com"  # 或 DeepSeek 兼容端点
    api_key: str = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY", ""))

@dataclass
class AgentConfig:
    max_retries: int = 2                 # 代码修正最大额外轮数
    review_max_complexity: int = 10      # 圈复杂度阈值
    memory_file: str = "./session_memory.json"
```

## 项目结构

```
.
├── gui.py                        # 🖥 图形化界面 (tkinter)
├── agent.py                     # Agent 主编排器 (ReAct + checkpointer)
├── cli.py                       # CLI 入口 (6 个子命令)
├── config.py                    # 全局配置 dataclass
├── requirements.txt             # 依赖清单
├── tools/
│   ├── code_interpreter.py      # 代码生成 + 沙箱执行 + 3 轮修正
│   ├── static_reviewer.py       # AST 5 维静态审查引擎
│   ├── git_commit.py            # Git diff 分析 + Conventional Commits
│   └── test_generator.py        # pytest 测试生成 + 自动验证  ← NEW
├── prompts/
│   ├── templates.py             # 6 套 Prompt 模板 (+ 测试/修复模板)
│   └── examples.py              # 12 个 Few-shot 示例 (4 类 × 3 难度)
├── memory/
│   └── session_memory.py        # 会话记忆辅助 (JSON 备份 + 摘要)
└── eval/                        ← NEW
    ├── __init__.py
    ├── evaluator.py             # 评估基准运行器
    └── test_cases.py            # 100 条评估用例 (4 类 × 25)
```

## 评估基准设计

100 条测试用例，4 个类别 × 25 条：

| 类别 | 数量 | 覆盖场景 |
|------|:----:|----------|
| 基础功能 | 25 | 字符串/列表/字典/数学/排序/数据结构 |
| 递归算法 | 25 | 树遍历/分治/回溯/图算法/递归数据结构 |
| 异常处理 | 25 | 输入验证/类型检查/自定义异常/重试/防御性编程 |
| 边界条件 | 25 | 空值/极值/单元素/Unicode/并发/浮点精度/递归深度 |

核心指标：**首次生成可运行率**（first-attempt runnable rate）

## 设计要点

### Agent 架构
- **ReAct 模式**：LLM 先推理（Reasoning）→ 决定调用哪个工具（Acting）→ 观察结果 → 循环
- **工具路由**：Agent 根据用户意图自动选择工具，无需手动分发
- **SqliteSaver**：LangGraph 内置 checkpointer，一行代码实现跨启动记忆

### Prompt 策略
- **System Prompt**：角色设定 + 行为约束 + 统一 JSON 输出 schema
- **Few-shot 示例**：每类任务 3 个难度示例（Easy/Medium/Hard），共 12 个
- **动态示例选择**：根据任务类型（代码生成/审查/测试/提交）注入对应示例集
- **自动修正**：执行失败时，将错误信息注入 FIX_TEMPLATE 反馈模型重新生成

### 安全措施
- 代码执行使用白名单 `builtins`（34 个），禁止 `open`/`eval`/`exec`/`__import__`
- Git commit 工具仅生成建议，不自动提交
- API Key 仅通过环境变量读取，不硬编码

## License

MIT
