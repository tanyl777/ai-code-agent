from typing import List, Optional


class TreeNode:
    """Binary tree node."""

    def __init__(
        self,
        val: int = 0,
        left: Optional["TreeNode"] = None,
        right: Optional["TreeNode"] = None,
    ):
        self.val = val
        self.left = left
        self.right = right


def preorder(root: Optional[TreeNode]) -> List[int]:
    """Return node values in pre-order traversal (root, left, right)."""
    if root is None:
        return []
    return [root.val] + preorder(root.left) + preorder(root.right)


def inorder(root: Optional[TreeNode]) -> List[int]:
    """Return node values in in-order traversal (left, root, right)."""
    if root is None:
        return []
    return inorder(root.left) + [root.val] + inorder(root.right)


def postorder(root: Optional[TreeNode]) -> List[int]:
    """Return node values in post-order traversal (left, right, root)."""
    if root is None:
        return []
    return postorder(root.left) + postorder(root.right) + [root.val]


if __name__ == "__main__":
    # Build a simple binary tree:
    #       1
    #      / \
    #     2   3
    #    / \
    #   4   5
    root = TreeNode(1)
    root.left = TreeNode(2)
    root.right = TreeNode(3)
    root.left.left = TreeNode(4)
    root.left.right = TreeNode(5)

    print("Preorder:", preorder(root))   # [1, 2, 4, 5, 3]
    print("Inorder:", inorder(root))     # [4, 2, 5, 1, 3]
    print("Postorder:", postorder(root)) # [4, 5, 2, 3, 1]

    # Boundary: empty tree
    assert preorder(None) == []
    assert inorder(None) == []
    assert postorder(None) == []
    print("All tests passed")