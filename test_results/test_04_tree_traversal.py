import pytest
from typing import List, Optional
from tree_traversal import TreeNode, preorder, inorder, postorder


# ---------------------------------------------------------------------------
# Helper trees for parametrised tests
# ---------------------------------------------------------------------------

EMPTY: Optional[TreeNode] = None

SINGLE_ZERO = TreeNode(0)
SINGLE_ONE = TreeNode(1)
SINGLE_NEGATIVE = TreeNode(-42)

# Left-skewed tree: 1 -> 2 -> 3
LEFT_SKEW = TreeNode(1)
LEFT_SKEW.left = TreeNode(2)
LEFT_SKEW.left.left = TreeNode(3)

# Right-skewed tree: 1 -> 2 -> 3
RIGHT_SKEW = TreeNode(1)
RIGHT_SKEW.right = TreeNode(2)
RIGHT_SKEW.right.right = TreeNode(3)

# Example tree:       1
#                    / \\
#                   2   3
#                  / \\
#                 4   5
EXAMPLE = TreeNode(1)
EXAMPLE.left = TreeNode(2)
EXAMPLE.right = TreeNode(3)
EXAMPLE.left.left = TreeNode(4)
EXAMPLE.left.right = TreeNode(5)

# Full binary tree of height 2 (values 1..7)
FULL = TreeNode(1)
FULL.left = TreeNode(2)
FULL.right = TreeNode(3)
FULL.left.left = TreeNode(4)
FULL.left.right = TreeNode(5)
FULL.right.left = TreeNode(6)
FULL.right.right = TreeNode(7)

# Tree with large / extreme values
LARGE = TreeNode(10**9)
LARGE.left = TreeNode(-(10**9))
LARGE.right = TreeNode(0)


# ---------------------------------------------------------------------------
# Preorder tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "tree, expected",
    [
        (EMPTY, []),
        (SINGLE_ZERO, [0]),
        (SINGLE_ONE, [1]),
        (SINGLE_NEGATIVE, [-42]),
        (LEFT_SKEW, [1, 2, 3]),
        (RIGHT_SKEW, [1, 2, 3]),
        (EXAMPLE, [1, 2, 4, 5, 3]),
        (FULL, [1, 2, 4, 5, 3, 6, 7]),
        (LARGE, [10**9, -(10**9), 0]),
    ],
)
def test_preorder(tree: Optional[TreeNode], expected: List[int]):
    assert preorder(tree) == expected


def test_preorder_invalid_input():
    """Non-TreeNode inputs should raise AttributeError."""
    for bad in [1, "hello", 3.14, [1, 2], {"a": 1}]:
        with pytest.raises(AttributeError):
            preorder(bad)


# ---------------------------------------------------------------------------
# Inorder tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "tree, expected",
    [
        (EMPTY, []),
        (SINGLE_ZERO, [0]),
        (SINGLE_ONE, [1]),
        (SINGLE_NEGATIVE, [-42]),
        (LEFT_SKEW, [3, 2, 1]),
        (RIGHT_SKEW, [1, 2, 3]),
        (EXAMPLE, [4, 2, 5, 1, 3]),
        (FULL, [4, 2, 5, 1, 6, 3, 7]),
        (LARGE, [-(10**9), 10**9, 0]),
    ],
)
def test_inorder(tree: Optional[TreeNode], expected: List[int]):
    assert inorder(tree) == expected


def test_inorder_invalid_input():
    for bad in [1, "hello", 3.14, [1, 2], {"a": 1}]:
        with pytest.raises(AttributeError):
            inorder(bad)


# ---------------------------------------------------------------------------
# Postorder tests
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "tree, expected",
    [
        (EMPTY, []),
        (SINGLE_ZERO, [0]),
        (SINGLE_ONE, [1]),
        (SINGLE_NEGATIVE, [-42]),
        (LEFT_SKEW, [3, 2, 1]),
        (RIGHT_SKEW, [3, 2, 1]),
        (EXAMPLE, [4, 5, 2, 3, 1]),
        (FULL, [4, 5, 2, 6, 7, 3, 1]),
        (LARGE, [-(10**9), 0, 10**9]),
    ],
)
def test_postorder(tree: Optional[TreeNode], expected: List[int]):
    assert postorder(tree) == expected


def test_postorder_invalid_input():
    for bad in [1, "hello", 3.14, [1, 2], {"a": 1}]:
        with pytest.raises(AttributeError):
            postorder(bad)


# ---------------------------------------------------------------------------
# Deep recursion boundary test (depth = 500)
# ---------------------------------------------------------------------------

def test_deep_tree_all_orders():
    """All three traversals should handle a deep right-skewed tree."""
    depth = 500
    root = TreeNode(0)
    cur = root
    for i in range(1, depth):
        cur.right = TreeNode(i)
        cur = cur.right

    expected_pre = list(range(depth))
    assert preorder(root) == expected_pre

    expected_in = list(range(depth))
    assert inorder(root) == expected_in

    expected_post = list(reversed(range(depth)))
    assert postorder(root) == expected_post


# ---------------------------------------------------------------------------
# Additional edge case: single node with value 0 == 0 (not False)
# ---------------------------------------------------------------------------

def test_zero_node_not_false():
    """Node with value 0 should be treated as 0, not boolean False."""
    zero = TreeNode(0)
    assert preorder(zero) == [0]
    assert inorder(zero) == [0]
    assert postorder(zero) == [0]