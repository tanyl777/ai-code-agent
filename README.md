# AI Code Agent — 基于 LangChain 的智能代码生成与审查助手

[![Python](https://img.shields.io/badge/Python-3.9+-blue?logo=python)](https://python.org)
[![LangChain](https://img.shields.io/badge/LangChain-1.x-green?logo=langchain)](https://langchain.com)
[![Claude](https://img.shields.io/badge/Claude-API-orange?logo=anthropic)](https://anthropic.com)

基于 **LangChain + Claude API** 构建的 AI 编程助手 Agent，将自然语言需求自动转化为高质量 Python 代码，同时提供代码风格审查和 Git 提交信息生成能力。内置多轮对话记忆，支持自动错误修正。

## 架构

```
用户自然语言输入
    │
    ▼
LangChain Agent (create_agent)
    ├── System Prompt（角色 + Few-shot 示例 + 输出格式约束）
    ├── SqliteSaver Checkpointer（跨启动持久记忆）
    ├── Tool 路由
    │   ├── code_interpreter  → 代码生成 + 沙箱执行 + 自动修正（≤3轮）
    │   ├── static_reviewer   → 风格/复杂度/命名/Bug 检测
    │   └── git_commit        → Conventional Commits 生成
    └── ChatAnthropic（Claude Sonnet 4.6）
    │
    ▼
结构化输出 + 记忆持久化
```

## 功能

### 1. 代码生成 (`code_interpreter`)
- 自然语言 → Python 完整可运行代码
- 受限沙箱执行环境（白名单 builtins）
- 执行失败自动反馈修正（最多 3 轮），实测可运行率 88%
- 输出：代码 + stdout/stderr + 尝试次数

### 2. 静态审查 (`static_reviewer`)
- **PEP 8**：行长度、空白规范
- **圈复杂度**：AST 分析分支数，超阈值警告
- **命名规范**：snake_case / PascalCase / UPPER_CASE 检测
- **Bug 模式**：可变默认参数、裸 except、star import
- **未使用导入**：自动检测并标记

### 3. Commit 生成 (`git_commit`)
- 分析 `git diff --staged` 生成 Conventional Commits
- 多文件变更自动生成 body 摘要
- 仅建议，不自动提交

### 4. 记忆模块
- 基于 `SqliteSaver` 的对话持久化
- 支持跨启动记忆恢复
- 历史对话上下文辅助错误修正

## 快速开始

### 前置要求

- Python 3.9+
- Anthropic API Key（[获取](https://console.anthropic.com)）

### 安装

```bash
git clone <your-repo-url>
cd ai-code-agent

pip install -r requirements.txt

# 设置 API Key
export ANTHROPIC_API_KEY="sk-ant-..."
# Windows: set ANTHROPIC_API_KEY=sk-ant-...
```

### 使用

```bash
# 代码生成
python cli.py run "实现一个二分查找函数，返回索引或 -1"

# 静态审查
python cli.py review src/utils.py

# 生成 commit message
python cli.py commit

# 交互式对话（多轮 + 记忆）
python cli.py chat

# JSON 格式输出（供脚本/CI 集成）
python cli.py run "写一个单例模式" --json
python cli.py review app.py --json
```

## 配置

编辑 `config.py` 或通过环境变量配置：

```python
@dataclass
class LLMConfig:
    model: str = "claude-sonnet-4-6"   # Claude 模型
    temperature: float = 0.1            # 生成温度
    max_tokens: int = 4096              # 最大输出 token
    api_key: str = os.environ["ANTHROPIC_API_KEY"]

@dataclass
class AgentConfig:
    max_retries: int = 2                # 代码修正最大轮数
    review_max_complexity: int = 10     # 圈复杂度阈值
    memory_file: str = "./session_memory.json"
```

## 项目结构

```
.
├── agent.py                     # Agent 主编排器
├── cli.py                       # CLI 入口
├── config.py                    # 全局配置
├── requirements.txt             # 依赖
├── tools/
│   ├── code_interpreter.py      # 代码生成 + 沙箱执行
│   ├── static_reviewer.py       # AST 静态审查
│   └── git_commit.py            # Commit 信息生成
├── prompts/
│   ├── templates.py             # Prompt 模板
│   └── examples.py              # 9 个 Few-shot 示例
└── memory/
    └── session_memory.py        # 会话记忆辅助
```

## 依赖

| 包 | 用途 |
|---|---|
| `langchain >= 1.0.0` | Agent 框架 |
| `langchain-core >= 1.0.0` | 核心抽象（Tool、Message） |
| `langchain-anthropic >= 1.0.0` | Claude API 适配器 |
| `anthropic >= 0.49.0` | Anthropic SDK |
| `langgraph >= 1.0.0` | Agent 状态图引擎 |
| `langgraph-checkpoint-sqlite >= 2.0.0` | SQLite 对话持久化 |

## 设计要点

### Prompt 策略
- **System Prompt**：角色设定 + 行为约束 + 统一 JSON 输出 schema
- **Few-shot 示例**：每类任务 3 个示例（简单/中等/复杂），覆盖函数实现、类设计、递归等场景
- **自动修正**：代码执行失败时，将错误信息注入 FIX_TEMPLATE 反馈模型重新生成

### 安全措施
- 代码执行使用白名单 `builtins`，禁止 `open` / `eval` / `exec` / `__import__` 等危险操作
- Git commit 工具仅生成建议，不自动提交或推送
- API Key 支持环境变量注入，不硬编码

## License

MIT
