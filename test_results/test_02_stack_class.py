import pytest
from stack import Stack


class TestStack:
    """Stack 单元测试套件，覆盖基础功能、边界条件和异常."""

    # ---- 初始化与新栈状态 ----
    def test_initial_stack_is_empty(self):
        s = Stack()
        assert s.is_empty()
        assert s.size() == 0

    # ---- 基础 push / peek / pop / size ----
    def test_push_increases_size_and_peek_returns_last(self):
        s = Stack()
        s.push(1)
        assert s.size() == 1
        assert not s.is_empty()
        assert s.peek() == 1

        s.push(2)
        assert s.size() == 2
        assert s.peek() == 2

    def test_pop_returns_and_removes_top(self):
        s = Stack()
        s.push("a")
        s.push("b")
        assert s.pop() == "b"
        assert s.size() == 1
        assert s.peek() == "a"
        assert s.pop() == "a"
        assert s.is_empty()

    @pytest.mark.parametrize("items", [
        [1],
        [1, 2, 3],
        list(range(100)),
        ["x", "y"],
        [None, False, 0],
    ])
    def test_filo_order(self, items):
        """验证后进先出顺序."""
        s = Stack()
        for item in items:
            s.push(item)
        assert s.size() == len(items)
        for expected in reversed(items):
            assert s.pop() == expected
        assert s.is_empty()

    def test_supports_mixed_types(self):
        s = Stack()
        s.push(42)
        s.push("hello")
        s.push([1, 2])
        s.push({"key": "val"})
        assert s.pop() == {"key": "val"}
        assert s.pop() == [1, 2]
        assert s.pop() == "hello"
        assert s.pop() == 42

    # ---- 边界条件 ----
    def test_single_element(self):
        s = Stack()
        s.push(99)
        assert s.peek() == 99
        assert s.pop() == 99
        assert s.is_empty()

    def test_large_push_and_pop(self):
        n = 10000
        s = Stack()
        for i in range(n):
            s.push(i)
        assert s.size() == n
        assert s.peek() == n - 1
        for i in range(n - 1, -1, -1):
            assert s.pop() == i
        assert s.is_empty()

    # ---- 异常情况 ----
    def test_pop_from_empty_raises_index_error(self):
        s = Stack()
        with pytest.raises(IndexError, match="pop from empty stack"):
            s.pop()

    def test_peek_from_empty_raises_index_error(self):
        s = Stack()
        with pytest.raises(IndexError, match="peek from empty stack"):
            s.peek()

    def test_pop_after_emptying_raises(self):
        s = Stack()
        s.push(1)
        s.pop()
        with pytest.raises(IndexError):
            s.pop()

    def test_peek_after_emptying_raises(self):
        s = Stack()
        s.push(1)
        s.pop()
        with pytest.raises(IndexError):
            s.peek()