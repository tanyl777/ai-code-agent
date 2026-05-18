"""Few-shot examples for each task type — 3 difficulty levels each."""

# ============================================================
# Code Generation Examples
# ============================================================

CODE_GEN_EASY = {
    "user_request": "写一个函数，判断一个字符串是否是回文",
    "output": {
        "type": "code",
        "status": "success",
        "content": '''def is_palindrome(s: str) -> bool:
    """Return True if s is a palindrome, ignoring case and non-alphanumeric chars."""
    cleaned = "".join(c.lower() for c in s if c.isalnum())
    return cleaned == cleaned[::-1]


if __name__ == "__main__":
    assert is_palindrome("A man, a plan, a canal: Panama")
    assert not is_palindrome("hello")
    print("All tests passed")''',
        "metadata": {"task": "palindrome_check", "complexity": "O(n)"},
    },
}

CODE_GEN_MEDIUM = {
    "user_request": "实现一个 LRU 缓存类，支持 get 和 put 操作，容量为 capacity",
    "output": {
        "type": "code",
        "status": "success",
        "content": '''from collections import OrderedDict


class LRUCache:
    """Least Recently Used cache with O(1) get and put."""

    def __init__(self, capacity: int):
        if capacity <= 0:
            raise ValueError("capacity must be positive")
        self.capacity = capacity
        self.cache: OrderedDict[int, int] = OrderedDict()

    def get(self, key: int) -> int:
        if key not in self.cache:
            return -1
        self.cache.move_to_end(key)
        return self.cache[key]

    def put(self, key: int, value: int) -> None:
        if key in self.cache:
            self.cache.move_to_end(key)
        self.cache[key] = value
        if len(self.cache) > self.capacity:
            self.cache.popitem(last=False)


if __name__ == "__main__":
    cache = LRUCache(2)
    cache.put(1, 1)
    cache.put(2, 2)
    assert cache.get(1) == 1
    cache.put(3, 3)
    assert cache.get(2) == -1
    print("All tests passed")''',
        "metadata": {"task": "lru_cache", "complexity": "O(1) per operation"},
    },
}

CODE_GEN_HARD = {
    "user_request": "实现一个函数，解析嵌套的 JSON 字符串中的整数并求和，支持嵌套列表和字典",
    "output": {
        "type": "code",
        "status": "success",
        "content": '''from typing import Any, Union


def sum_nested_integers(data: Any) -> int:
    """Recursively sum all integers in a nested structure of lists and dicts.

    Non-integer values and dict keys are ignored.
    """
    total = 0
    if isinstance(data, int) and not isinstance(data, bool):
        total += data
    elif isinstance(data, list):
        for item in data:
            total += sum_nested_integers(item)
    elif isinstance(data, dict):
        for value in data.values():
            total += sum_nested_integers(value)
    return total


if __name__ == "__main__":
    nested = {"a": [1, 2, {"b": 3}], "c": [4, [5, 6]]}
    assert sum_nested_integers(nested) == 21
    assert sum_nested_integers([1, "hello", 2.5, True]) == 1
    assert sum_nested_integers({}) == 0
    print("All tests passed")''',
        "metadata": {"task": "nested_sum", "complexity": "O(n)", "technique": "recursion"},
    },
}

# ============================================================
# Code Review Examples
# ============================================================

CODE_REVIEW_EASY = {
    "code": '''def calc(a,b):
    return a+b''',
    "output": {
        "type": "review",
        "status": "success",
        "content": [
            {
                "severity": "ERROR",
                "line": 1,
                "issue": "函数名不规范",
                "suggestion": "使用 snake_case 命名，如 calculate_sum",
            },
            {
                "severity": "WARNING",
                "line": 1,
                "issue": "缺少类型标注",
                "suggestion": "添加参数和返回值类型: def calc(a: int, b: int) -> int:",
            },
            {
                "severity": "WARNING",
                "line": 1,
                "issue": "缺少文档字符串",
                "suggestion": "添加一行 docstring 描述函数功能",
            },
            {
                "severity": "WARNING",
                "line": 1,
                "issue": "运算符两侧缺少空格",
                "suggestion": "a + b，PEP 8 要求运算符两侧各一个空格",
            },
        ],
        "metadata": {"total_issues": 4, "errors": 1, "warnings": 3},
    },
}

CODE_REVIEW_MEDIUM = {
    "code": '''def process_data(items=[]):
    try:
        result = []
        for i in range(len(items)):
            result.append(items[i] * 2)
        return result
    except:
        pass''',
    "output": {
        "type": "review",
        "status": "success",
        "content": [
            {
                "severity": "ERROR",
                "line": 1,
                "issue": "可变默认参数（mutable default argument）",
                "suggestion": '使用 None 作为默认值: def process_data(items=None): 然后在函数内处理: items = items or []',
            },
            {
                "severity": "ERROR",
                "line": 8,
                "issue": "裸 except 语句（bare except）",
                "suggestion": "捕获具体异常类型，至少使用 except Exception: 且不要 pass 吞掉错误",
            },
            {
                "severity": "WARNING",
                "line": 3,
                "issue": "使用 range(len(...)) 遍历不够 Pythonic",
                "suggestion": "使用列表推导式或直接迭代: return [item * 2 for item in items]",
            },
            {
                "severity": "WARNING",
                "line": 1,
                "issue": "缺少类型标注和文档字符串",
                "suggestion": "添加: def process_data(items: list[int] | None = None) -> list[int]:",
            },
        ],
        "metadata": {"total_issues": 4, "errors": 2, "warnings": 2},
    },
}

CODE_REVIEW_HARD = {
    "code": '''from os import *
import sys, json, re

class myclass:
    def __init__(self,val):
        self.val=val
    def GET_DATA(self):
        x=self.val+1
        if x>10:
            if x>20:
                if x>30:
                    if x>40:
                        if x>50:
                            return "large"
        return "small"''',
    "output": {
        "type": "review",
        "status": "success",
        "content": [
            {
                "severity": "ERROR",
                "line": 1,
                "issue": "使用 from os import * 会污染命名空间",
                "suggestion": "仅导入需要的符号: from os import getenv, path，或使用 import os",
            },
            {
                "severity": "ERROR",
                "line": 6,
                "issue": "类名不符合 PascalCase 规范",
                "suggestion": "改为 class MyClass:",
            },
            {
                "severity": "ERROR",
                "line": 9,
                "issue": "方法名 GET_DATA 不符合 snake_case 规范",
                "suggestion": "改为 def get_data(self):",
            },
            {
                "severity": "WARNING",
                "line": 10,
                "issue": "变量 x 仅递增，命名不够描述性",
                "suggestion": "使用更有意义的变量名，如 threshold",
            },
            {
                "severity": "WARNING",
                "line": 4,
                "issue": "嵌套 if 层级过深（5层），圈复杂度偏高",
                "suggestion": "使用早返回或查表法简化逻辑：thresholds = [(50, 'large')]; for t, label in thresholds: if x > t: return label",
            },
            {
                "severity": "WARNING",
                "line": 7,
                "issue": "构造函数参数和属性间缺少空格",
                "suggestion": "self.val = val (PEP 8 冒号/等号左右空格规范)",
            },
            {
                "severity": "INFO",
                "line": 2,
                "issue": "导入不使用的模块 json",
                "suggestion": "移除未使用的导入",
            },
        ],
        "metadata": {"total_issues": 7, "errors": 3, "warnings": 3, "info": 1},
    },
}

# ============================================================
# Commit Message Examples
# ============================================================

COMMIT_EASY = {
    "staged_diff": """diff --git a/README.md b/README.md
+## 安装说明
+pip install -r requirements.txt""",
    "unstaged_diff": "",
    "output": {
        "type": "commit",
        "status": "success",
        "content": {
            "type": "docs",
            "scope": "readme",
            "message": "docs(readme): 添加安装说明章节",
        },
        "metadata": {"files_changed": 1, "lines_added": 2, "lines_deleted": 0},
    },
}

COMMIT_MEDIUM = {
    "staged_diff": """diff --git a/src/auth.py b/src/auth.py
+def validate_token(token: str) -> bool:
+    return len(token) > 0 and token.startswith("Bearer ")
diff --git a/src/handler.py b/src/handler.py
-    if not token:
-        raise ValueError("missing token")
+    if not validate_token(token):
+        raise ValueError("invalid token format")
diff --git a/tests/test_auth.py b/tests/test_auth.py
+def test_validate_token():
+    assert validate_token("Bearer xyz")
+    assert not validate_token("invalid")""",
    "unstaged_diff": "",
    "output": {
        "type": "commit",
        "status": "success",
        "content": {
            "type": "feat",
            "scope": "auth",
            "message": "feat(auth): 添加 token 格式验证函数",
            "body": "- 新增 validate_token 验证 Bearer token 格式\n- 更新 handler 使用新的验证函数\n- 添加对应单元测试",
        },
        "metadata": {"files_changed": 3, "new_file": 1},
    },
}

COMMIT_HARD = {
    "staged_diff": """diff --git a/src/api/users.py b/src/api/users.py
+async def delete_user(user_id: int) -> None:
+    await db.users.delete(id=user_id)
+    await cache.invalidate(f"user:{user_id}")
+
+async def batch_delete(user_ids: list[int]) -> dict[str, int]:
+    deleted = 0
+    failed = 0
+    for uid in user_ids:
+        try:
+            await delete_user(uid)
+            deleted += 1
+        except NotFoundError:
+            failed += 1
+    return {"deleted": deleted, "failed": failed}
diff --git a/src/db/models.py b/src/db/models.py
+class NotFoundError(Exception):
+    pass
diff --git a/src/api/__init__.py b/src/api/__init__.py
-from .users import get_user, update_user
+from .users import batch_delete, delete_user, get_user, update_user
diff --git a/tests/api/test_users.py b/tests/api/test_users.py
+async def test_delete_user():
+    ...
+async def test_batch_delete_mixed_results():
+    ...""",
    "unstaged_diff": "",
    "output": {
        "type": "commit",
        "status": "success",
        "content": {
            "type": "feat",
            "scope": "api",
            "message": "feat(api): 实现用户删除及批量删除功能",
            "body": "- 新增 delete_user 异步函数，删除用户并清理缓存\n- 新增 batch_delete 支持批量删除及部分失败容忍\n- 新增 NotFoundError 异常类型\n- 添加删除功能的单元测试",
        },
        "metadata": {"files_changed": 4, "breaking": False},
    },
}

# ============================================================
# Aggregated Example Sets for Easy Import
# ============================================================

CODE_GEN_EXAMPLES = [CODE_GEN_EASY, CODE_GEN_MEDIUM, CODE_GEN_HARD]
CODE_REVIEW_EXAMPLES = [CODE_REVIEW_EASY, CODE_REVIEW_MEDIUM, CODE_REVIEW_HARD]
COMMIT_EXAMPLES = [COMMIT_EASY, COMMIT_MEDIUM, COMMIT_HARD]

ALL_EXAMPLES = {
    "code_generation": CODE_GEN_EXAMPLES,
    "code_review": CODE_REVIEW_EXAMPLES,
    "commit_message": COMMIT_EXAMPLES,
}
