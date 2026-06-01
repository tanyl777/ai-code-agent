import pytest
from binary_search import binary_search


class TestBinarySearch:
    """binary_search 单元测试套件 — 基础功能、边界条件、类型错误."""

    @pytest.mark.parametrize(
        "arr, target, expected",
        [
            # 基础功能：目标存在
            ([1, 2, 3, 4, 5], 3, 2),
            ([1, 2, 3, 4, 5], 1, 0),
            ([1, 2, 3, 4, 5], 5, 4),
            ([1, 2, 3, 4, 5, 6], 4, 3),   # 偶数长度
            # 基础功能：目标不存在
            ([1, 2, 3, 4, 5], 0, -1),
            ([1, 2, 3, 4, 5], 6, -1),
            ([1, 3, 5, 7], 2, -1),
            ([1, 3, 5, 7], 4, -1),
            ([1, 3, 5, 7], 8, -1),
            # 边界：空数组
            ([], 1, -1),
            ([], 0, -1),
            # 边界：单元素
            ([1], 1, 0),
            ([1], 2, -1),
            # 边界：两个元素
            ([1, 2], 1, 0),
            ([1, 2], 2, 1),
            ([1, 2], 0, -1),
            ([1, 2], 3, -1),
            # 负数
            ([-5, -3, 0, 2, 4], -5, 0),
            ([-5, -3, 0, 2, 4], -3, 1),
            ([-5, -3, 0, 2, 4], 4, 4),
            ([-5, -3, 0, 2, 4], -1, -1),
            # 较大整数
            ([0, 10**9, 2 * 10**9], 10**9, 1),
            ([0, 10**9, 2 * 10**9], 10**9 + 1, -1),
        ],
    )
    def test_search(self, arr, target, expected):
        assert binary_search(arr, target) == expected

    def test_duplicate_elements(self):
        """重复元素时返回任一匹配索引."""
        arr = [1, 1, 2, 2, 3]
        assert binary_search(arr, 1) in (0, 1)
        assert binary_search(arr, 2) in (2, 3)
        assert binary_search(arr, 3) == 4
        assert binary_search(arr, 4) == -1

    def test_none_array_raises(self):
        """传入 None 引发 TypeError."""
        with pytest.raises(TypeError):
            binary_search(None, 1)

    def test_type_mismatch_raises(self):
        """target 或数组元素类型不匹配引发 TypeError."""
        # 目标为字符串
        with pytest.raises(TypeError):
            binary_search([1, 2, 3], "a")
        # 数组元素为字符串
        with pytest.raises(TypeError):
            binary_search(["a", "b", "c"], 1)

    def test_large_array_smoke(self):
        """大型有序数组冒烟测试."""
        arr = list(range(0, 1000000, 2))   # 50万个偶数
        assert binary_search(arr, 500000) == 250000
        assert binary_search(arr, 500001) == -1