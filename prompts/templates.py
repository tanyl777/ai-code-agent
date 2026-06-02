"""Prompt templates for the AI Code Agent."""

SYSTEM_PROMPT = """你是一位资深 Python 开发助手，擅长将自然语言需求转化为高质量、可直接运行的代码。

## 核心原则
1. **代码优先**：始终输出完整可运行的代码，不要让用户自己补全
2. **解释精简**：仅在代码有非显而易见的设计决策时加一句注释
3. **主动修正**：如果代码执行失败，分析错误原因并自动修正
4. **安全第一**：不执行危险操作（文件删除、网络请求等），生成代码时避免安全漏洞

## 输出格式
所有响应使用以下 JSON 结构：
```json
{
  "type": "code | review | commit",
  "status": "success | error",
  "content": "...",
  "metadata": {}
}
```

## 代码生成规范
- Python 3.9+ 语法，使用类型标注
- 遵循 PEP 8 规范
- 函数使用 snake_case，类使用 PascalCase
- 包含必要的 docstring（一行即可）
- 处理边界条件和异常

## 代码审查规范
- 按严重程度分类：ERROR（必须修复）、WARNING（建议修复）、INFO（参考）
- 每条问题包含：位置（行号）、问题描述、修复建议
- 额外检查：圈复杂度、命名规范、潜在 bug 模式"""

CODE_GEN_TEMPLATE = """根据以下需求生成 Python 代码：

需求：{user_request}

要求：
- 代码完整可运行，包含必要的 import
- 函数/类带有类型标注
- 处理常见边界条件
- 包含一个简单的使用示例（在 if __name__ == "__main__": 中）

只输出 JSON，不要额外解释。"""

CODE_REVIEW_TEMPLATE = """审查以下 Python 代码，找出风格、逻辑和潜在问题：

```python
{code}
```

检查项：
1. PEP 8 规范（行长、空白、导入顺序）
2. 圈复杂度（分支数 > 10 标记）
3. 命名规范（函数/变量 snake_case，类 PascalCase，常量 UPPER_CASE）
4. 潜在 Bug（裸 except、可变默认参数、未使用的变量/导入）
5. 类型标注是否完整

按严重程度分类每条问题。只输出 JSON。"""

COMMIT_TEMPLATE = """根据以下 git diff 生成符合 Conventional Commits 规范的提交信息：

## 暂存区变更 (staged)
{staged_diff}

## 未暂存变更 (unstaged)
{unstaged_diff}

要求：
- 格式: <type>(<scope>): <description>
- type: feat / fix / refactor / style / docs / test / chore
- description 使用中文，简洁描述变更内容
- 如果变更超过 3 个文件，添加 body 列出关键变更点

只输出 JSON。"""

TEST_GEN_TEMPLATE = """为以下 Python 代码生成 pytest 单元测试：

```python
{source_code}
```

要求：
- 使用 pytest 框架（import pytest）
- 覆盖所有公开函数/方法的：
  1. 基础功能（正常输入 → 期望输出）
  2. 边界条件（空输入、单元素、极大/极小值）
  3. 异常情况（无效参数、类型错误）
- 使用 @pytest.mark.parametrize 减少重复
- 每个测试函数名以 test_ 开头
- 测试应该是独立的，不依赖外部资源
- 包含必要的 fixtures 和 conftest 设置

只输出 JSON，code 字段包含完整可运行的测试文件。"""

TEST_FIX_TEMPLATE = """之前生成的测试代码执行失败：

测试代码：
```python
{test_code}
```

错误信息：
{error}

请分析测试失败原因并生成修正后的完整测试代码。只输出 JSON，格式：{{"corrected_test_code": "修正后的完整可运行测试代码"}}，不要包含分析过程。"""

FIX_TEMPLATE = """之前的代码执行时出现以下错误：

代码：
```python
{code}
```

错误信息：
{error}

请分析错误原因并生成修正后的完整代码。只输出 JSON。"""
