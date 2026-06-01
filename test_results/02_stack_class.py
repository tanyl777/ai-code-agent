from typing import Any


class Stack:
    """A simple stack data structure with standard operations."""

    def __init__(self) -> None:
        self._items: list[Any] = []

    def push(self, item: Any) -> None:
        """Push an item onto the top of the stack."""
        self._items.append(item)

    def pop(self) -> Any:
        """Remove and return the top item of the stack.

        Raises IndexError if the stack is empty.
        """
        if self.is_empty():
            raise IndexError("pop from empty stack")
        return self._items.pop()

    def peek(self) -> Any:
        """Return the top item of the stack without removing it.

        Raises IndexError if the stack is empty.
        """
        if self.is_empty():
            raise IndexError("peek from empty stack")
        return self._items[-1]

    def is_empty(self) -> bool:
        """Return True if the stack contains no items."""
        return len(self._items) == 0

    def size(self) -> int:
        """Return the number of items in the stack."""
        return len(self._items)


if __name__ == "__main__":
    s = Stack()
    assert s.is_empty()
    assert s.size() == 0

    s.push(1)
    s.push(2)
    s.push(3)
    assert s.size() == 3
    assert not s.is_empty()
    assert s.peek() == 3
    assert s.pop() == 3
    assert s.peek() == 2
    assert s.pop() == 2
    assert s.pop() == 1
    assert s.is_empty()

    try:
        s.pop()
    except IndexError as e:
        assert str(e) == "pop from empty stack"

    try:
        s.peek()
    except IndexError as e:
        assert str(e) == "peek from empty stack"

    print("All tests passed")