"""100 benchmark cases for code generation evaluation.

Organized into 4 categories × ~25 cases each:
- basic:    基础功能 (simple functions, data operations)
- recursion: 递归算法 (tree, graph, divide & conquer)
- exception: 异常处理 (input validation, error handling)
- boundary:  边界条件 (empty input, extremes, edge cases)

Core metric: "首次生成可运行率" (first-attempt runnable rate)
"""

from typing import Any

# ═══════════════════════════════════════════════════════════════
# Category 1: 基础功能 (25 cases)
# ═══════════════════════════════════════════════════════════════

BASIC_CASES: list[dict[str, Any]] = [
    # --- 字符串操作 ---
    {
        "id": "basic_str_001",
        "category": "basic",
        "subcategory": "字符串操作",
        "user_request": "写一个函数，计算字符串中每个字符出现的次数，返回字典",
        "expected_patterns": ["def ", "count", "dict", "for", "return"],
    },
    {
        "id": "basic_str_002",
        "category": "basic",
        "subcategory": "字符串操作",
        "user_request": "写一个函数，将字符串中的单词顺序反转，保持单词内字符顺序不变",
        "expected_patterns": ["def ", "split", "reverse", "join", "return"],
    },
    {
        "id": "basic_str_003",
        "category": "basic",
        "subcategory": "字符串操作",
        "user_request": "写一个函数，判断两个字符串是否是字母异位词（anagram）",
        "expected_patterns": ["def ", "sorted", "return"],
    },
    {
        "id": "basic_str_004",
        "category": "basic",
        "subcategory": "字符串操作",
        "user_request": "写一个函数，找出字符串中第一个不重复的字符并返回其索引",
        "expected_patterns": ["def ", "for", "count", "return"],
    },
    {
        "id": "basic_str_005",
        "category": "basic",
        "subcategory": "字符串操作",
        "user_request": "写一个函数，将驼峰命名转换为蛇形命名（camelCase → snake_case）",
        "expected_patterns": ["def ", "re", "sub", "return"],
    },
    # --- 列表/数组操作 ---
    {
        "id": "basic_list_006",
        "category": "basic",
        "subcategory": "列表操作",
        "user_request": "写一个函数，找出列表中第 k 大的元素",
        "expected_patterns": ["def ", "sorted", "return", "k"],
    },
    {
        "id": "basic_list_007",
        "category": "basic",
        "subcategory": "列表操作",
        "user_request": "写一个函数，将两个有序数组合并为一个有序数组",
        "expected_patterns": ["def ", "while", "append", "return"],
    },
    {
        "id": "basic_list_008",
        "category": "basic",
        "subcategory": "列表操作",
        "user_request": "写一个函数，移除列表中的所有重复元素并保持原始顺序",
        "expected_patterns": ["def ", "set", "for", "return"],
    },
    {
        "id": "basic_list_009",
        "category": "basic",
        "subcategory": "列表操作",
        "user_request": "写一个函数，将列表中的所有零移动到末尾，保持非零元素的相对顺序",
        "expected_patterns": ["def ", "for", "append", "0", "return"],
    },
    {
        "id": "basic_list_010",
        "category": "basic",
        "subcategory": "列表操作",
        "user_request": "写一个函数，找到列表中连续子数组的最大和（Kadane 算法）",
        "expected_patterns": ["def ", "max", "for", "return"],
    },
    # --- 字典/哈希表 ---
    {
        "id": "basic_dict_011",
        "category": "basic",
        "subcategory": "字典操作",
        "user_request": "写一个函数，合并两个字典，如果键冲突则对值求和",
        "expected_patterns": ["def ", "for", "dict", "return"],
    },
    {
        "id": "basic_dict_012",
        "category": "basic",
        "subcategory": "字典操作",
        "user_request": "写一个函数，按键的字母顺序排序字典并返回新的 OrderedDict",
        "expected_patterns": ["def ", "sorted", "OrderedDict", "return"],
    },
    {
        "id": "basic_dict_013",
        "category": "basic",
        "subcategory": "字典操作",
        "user_request": "写一个函数，将嵌套字典扁平化为单层字典，键用点号连接",
        "expected_patterns": ["def ", "isinstance", "dict", "recursion", "return"],
    },
    # --- 数学计算 ---
    {
        "id": "basic_math_014",
        "category": "basic",
        "subcategory": "数学计算",
        "user_request": "写一个函数，判断一个整数是否为质数",
        "expected_patterns": ["def ", "range", "%", "return", "bool"],
    },
    {
        "id": "basic_math_015",
        "category": "basic",
        "subcategory": "数学计算",
        "user_request": "写一个函数，计算两个整数的最大公约数（欧几里得算法）",
        "expected_patterns": ["def ", "while", "%", "return"],
    },
    {
        "id": "basic_math_016",
        "category": "basic",
        "subcategory": "数学计算",
        "user_request": "写一个函数，计算整数的阶乘",
        "expected_patterns": ["def ", "factorial", "return"],
    },
    {
        "id": "basic_math_017",
        "category": "basic",
        "subcategory": "数学计算",
        "user_request": "写一个函数，生成斐波那契数列的前 n 项",
        "expected_patterns": ["def ", "fibonacci", "for", "append", "return"],
    },
    {
        "id": "basic_math_018",
        "category": "basic",
        "subcategory": "数学计算",
        "user_request": "写一个函数，将罗马数字转换为整数",
        "expected_patterns": ["def ", "dict", "for", "return", "roman"],
    },
    # --- 排序与搜索 ---
    {
        "id": "basic_sort_019",
        "category": "basic",
        "subcategory": "排序与搜索",
        "user_request": "实现冒泡排序算法",
        "expected_patterns": ["def ", "bubble", "for", "swap", "return"],
    },
    {
        "id": "basic_sort_020",
        "category": "basic",
        "subcategory": "排序与搜索",
        "user_request": "实现二分查找，在有序数组中查找目标值，返回索引或 -1",
        "expected_patterns": ["def ", "binary_search", "while", "mid", "return"],
    },
    {
        "id": "basic_sort_021",
        "category": "basic",
        "subcategory": "排序与搜索",
        "user_request": "实现快速排序算法",
        "expected_patterns": ["def ", "quick_sort", "pivot", "return"],
    },
    # --- 数据结构 ---
    {
        "id": "basic_ds_022",
        "category": "basic",
        "subcategory": "数据结构",
        "user_request": "用两个栈实现一个队列，支持 push 和 pop 操作",
        "expected_patterns": ["class ", "stack", "push", "pop", "return"],
    },
    {
        "id": "basic_ds_023",
        "category": "basic",
        "subcategory": "数据结构",
        "user_request": "实现一个简单的链表节点类 ListNode 和打印链表的函数",
        "expected_patterns": ["class ListNode", "next", "val", "def "],
    },
    {
        "id": "basic_ds_024",
        "category": "basic",
        "subcategory": "数据结构",
        "user_request": "实现一个最小堆类，支持 push、pop 和 peek 操作",
        "expected_patterns": ["class ", "heap", "push", "pop", "peek"],
    },
    {
        "id": "basic_ds_025",
        "category": "basic",
        "subcategory": "数据结构",
        "user_request": "实现一个循环队列（Circular Queue），支持 enqueue 和 dequeue",
        "expected_patterns": ["class ", "CircularQueue", "enqueue", "dequeue"],
    },
]

# ═══════════════════════════════════════════════════════════════
# Category 2: 递归算法 (25 cases)
# ═══════════════════════════════════════════════════════════════

RECURSION_CASES: list[dict[str, Any]] = [
    # --- 树遍历 ---
    {
        "id": "rec_tree_001",
        "category": "recursion",
        "subcategory": "树遍历",
        "user_request": "实现二叉树的前序遍历（递归版本），返回节点值列表",
        "expected_patterns": ["def ", "preorder", "recursive", "return", "list"],
    },
    {
        "id": "rec_tree_002",
        "category": "recursion",
        "subcategory": "树遍历",
        "user_request": "实现二叉树的中序遍历（递归版本），返回节点值列表",
        "expected_patterns": ["def ", "inorder", "return", "list"],
    },
    {
        "id": "rec_tree_003",
        "category": "recursion",
        "subcategory": "树遍历",
        "user_request": "实现二叉树的后序遍历（递归版本），返回节点值列表",
        "expected_patterns": ["def ", "postorder", "return", "list"],
    },
    {
        "id": "rec_tree_004",
        "category": "recursion",
        "subcategory": "树遍历",
        "user_request": "实现二叉树的层序遍历，返回按层分组的节点值列表",
        "expected_patterns": ["def ", "level_order", "queue", "return"],
    },
    {
        "id": "rec_tree_005",
        "category": "recursion",
        "subcategory": "树属性",
        "user_request": "计算二叉树的最大深度",
        "expected_patterns": ["def ", "max_depth", "return", "1 + max"],
    },
    {
        "id": "rec_tree_006",
        "category": "recursion",
        "subcategory": "树属性",
        "user_request": "判断一棵二叉树是否是对称的（镜像对称）",
        "expected_patterns": ["def ", "symmetric", "mirror", "return"],
    },
    {
        "id": "rec_tree_007",
        "category": "recursion",
        "subcategory": "树属性",
        "user_request": "判断一棵二叉树是否是平衡二叉树",
        "expected_patterns": ["def ", "balanced", "height", "abs", "return"],
    },
    {
        "id": "rec_tree_008",
        "category": "recursion",
        "subcategory": "树操作",
        "user_request": "翻转（镜像）一棵二叉树",
        "expected_patterns": ["def ", "invert", "left", "right", "return"],
    },
    {
        "id": "rec_tree_009",
        "category": "recursion",
        "subcategory": "树路径",
        "user_request": "找出二叉树中从根到叶子的所有路径",
        "expected_patterns": ["def ", "paths", "root", "leaf", "return"],
    },
    {
        "id": "rec_tree_010",
        "category": "recursion",
        "subcategory": "树路径",
        "user_request": "判断二叉树中是否存在一条根到叶子的路径，其节点值之和等于目标值",
        "expected_patterns": ["def ", "has_path_sum", "target", "return"],
    },
    # --- 分治与回溯 ---
    {
        "id": "rec_dc_011",
        "category": "recursion",
        "subcategory": "分治算法",
        "user_request": "实现归并排序算法",
        "expected_patterns": ["def ", "merge_sort", "mid", "merge", "return"],
    },
    {
        "id": "rec_dc_012",
        "category": "recursion",
        "subcategory": "回溯算法",
        "user_request": "生成 n 对括号的所有合法组合",
        "expected_patterns": ["def ", "generate_parentheses", "backtrack", "return"],
    },
    {
        "id": "rec_dc_013",
        "category": "recursion",
        "subcategory": "回溯算法",
        "user_request": "给定一个不含重复数字的数组，返回其所有可能的子集（幂集）",
        "expected_patterns": ["def ", "subsets", "backtrack", "return"],
    },
    {
        "id": "rec_dc_014",
        "category": "recursion",
        "subcategory": "回溯算法",
        "user_request": "实现全排列算法，给定一个不含重复数字的数组，返回所有可能的排列",
        "expected_patterns": ["def ", "permute", "backtrack", "return"],
    },
    {
        "id": "rec_dc_015",
        "category": "recursion",
        "subcategory": "分治算法",
        "user_request": "实现汉诺塔问题，打印移动步骤",
        "expected_patterns": ["def ", "hanoi", "move", "recursive", "print"],
    },
    # --- 递归数据结构 ---
    {
        "id": "rec_ds_016",
        "category": "recursion",
        "subcategory": "递归数据结构",
        "user_request": "实现递归函数，计算嵌套列表的深度（最深嵌套层数）",
        "expected_patterns": ["def ", "depth", "isinstance", "list", "return"],
    },
    {
        "id": "rec_ds_017",
        "category": "recursion",
        "subcategory": "递归数据结构",
        "user_request": "实现递归函数，将嵌套列表中的所有元素扁平化为一维列表",
        "expected_patterns": ["def ", "flatten", "isinstance", "list", "yield", "return"],
    },
    {
        "id": "rec_ds_018",
        "category": "recursion",
        "subcategory": "递归数据结构",
        "user_request": "实现递归函数，在嵌套字典中按点号分隔的路径查找值，如 get_nested(d, 'a.b.c')",
        "expected_patterns": ["def ", "get_nested", "split", "return"],
    },
    {
        "id": "rec_ds_019",
        "category": "recursion",
        "subcategory": "递归数据结构",
        "user_request": "实现递归函数，比较两个嵌套结构（列表/字典）是否完全相等",
        "expected_patterns": ["def ", "deep_equal", "isinstance", "return"],
    },
    {
        "id": "rec_ds_020",
        "category": "recursion",
        "subcategory": "递归数据结构",
        "user_request": "实现一个递归函数，克隆嵌套的列表/字典结构（深拷贝）",
        "expected_patterns": ["def ", "deep_clone", "isinstance", "return"],
    },
    # --- 图算法 ---
    {
        "id": "rec_graph_021",
        "category": "recursion",
        "subcategory": "图算法",
        "user_request": "实现深度优先搜索（DFS）遍历图，图用邻接表表示",
        "expected_patterns": ["def ", "dfs", "visited", "for", "return"],
    },
    {
        "id": "rec_graph_022",
        "category": "recursion",
        "subcategory": "图算法",
        "user_request": "判断无向图中两个节点是否连通",
        "expected_patterns": ["def ", "connected", "visited", "dfs", "return"],
    },
    {
        "id": "rec_graph_023",
        "category": "recursion",
        "subcategory": "图算法",
        "user_request": "找出无向图中的所有连通分量",
        "expected_patterns": ["def ", "components", "dfs", "visited", "return"],
    },
    {
        "id": "rec_graph_024",
        "category": "recursion",
        "subcategory": "图算法",
        "user_request": "判断有向图是否有环",
        "expected_patterns": ["def ", "has_cycle", "visited", "rec_stack", "return"],
    },
    {
        "id": "rec_graph_025",
        "category": "recursion",
        "subcategory": "图算法",
        "user_request": "实现拓扑排序（Kahn 算法 或 DFS 版本）",
        "expected_patterns": ["def ", "topological_sort", "indegree", "return"],
    },
]

# ═══════════════════════════════════════════════════════════════
# Category 3: 异常处理 (25 cases)
# ═══════════════════════════════════════════════════════════════

EXCEPTION_CASES: list[dict[str, Any]] = [
    # --- 输入验证 ---
    {
        "id": "exc_input_001",
        "category": "exception",
        "subcategory": "输入验证",
        "user_request": "写一个除法函数，处理除数为零的情况，抛出有意义的异常信息",
        "expected_patterns": ["def ", "ZeroDivisionError", "raise", "return"],
    },
    {
        "id": "exc_input_002",
        "category": "exception",
        "subcategory": "输入验证",
        "user_request": "写一个函数，从列表中按索引取元素，处理索引越界并给出提示",
        "expected_patterns": ["def ", "IndexError", "try", "except", "return"],
    },
    {
        "id": "exc_input_003",
        "category": "exception",
        "subcategory": "输入验证",
        "user_request": "写一个函数，将字符串转换为整数，处理无效输入并返回 None",
        "expected_patterns": ["def ", "ValueError", "try", "except", "return"],
    },
    {
        "id": "exc_input_004",
        "category": "exception",
        "subcategory": "输入验证",
        "user_request": "写一个函数，打开并读取文件内容，处理文件不存在和权限错误",
        "expected_patterns": ["def ", "FileNotFoundError", "PermissionError", "try", "except"],
    },
    {
        "id": "exc_input_005",
        "category": "exception",
        "subcategory": "输入验证",
        "user_request": "写一个函数，从字典中获取指定键的值，键不存在时返回默认值并记录警告",
        "expected_patterns": ["def ", "get", "default", "KeyError", "return"],
    },
    # --- 类型检查 ---
    {
        "id": "exc_type_006",
        "category": "exception",
        "subcategory": "类型检查",
        "user_request": "写一个函数，计算两个数的和，但参数必须为 int 或 float，否则抛 TypeError",
        "expected_patterns": ["def ", "isinstance", "TypeError", "raise", "return"],
    },
    {
        "id": "exc_type_007",
        "category": "exception",
        "subcategory": "类型检查",
        "user_request": "写一个函数，接收列表参数，验证所有元素都是同一类型，否则抛出 TypeError",
        "expected_patterns": ["def ", "isinstance", "TypeError", "all", "raise"],
    },
    {
        "id": "exc_type_008",
        "category": "exception",
        "subcategory": "类型检查",
        "user_request": "写一个函数，验证输入是正整数的列表，每个元素 > 0 且为 int",
        "expected_patterns": ["def ", "isinstance", "ValueError", "> 0", "raise"],
    },
    {
        "id": "exc_type_009",
        "category": "exception",
        "subcategory": "类型检查",
        "user_request": "写一个装饰器，验证被装饰函数的每个参数都不为 None",
        "expected_patterns": ["def ", "decorator", "None", "ValueError", "raise"],
    },
    {
        "id": "exc_type_010",
        "category": "exception",
        "subcategory": "类型检查",
        "user_request": "写一个函数，安全地将值转换为指定类型（int/float/str/bool），转换失败返回原值",
        "expected_patterns": ["def ", "safe_convert", "try", "except", "return"],
    },
    # --- 自定义异常 ---
    {
        "id": "exc_custom_011",
        "category": "exception",
        "subcategory": "自定义异常",
        "user_request": "定义一个自定义异常类 InvalidAgeError，并在年龄设置函数中使用",
        "expected_patterns": ["class ", "Error", "Exception", "raise", "def "],
    },
    {
        "id": "exc_custom_012",
        "category": "exception",
        "subcategory": "自定义异常",
        "user_request": "实现一个银行账户类，取款时余额不足抛 InsufficientFundsError 自定义异常",
        "expected_patterns": ["class ", "Error", "balance", "raise", "Insufficient"],
    },
    {
        "id": "exc_custom_013",
        "category": "exception",
        "subcategory": "自定义异常",
        "user_request": "实现一个配置验证器，验证必填字段，缺失时抛 MissingConfigError 并列出缺失字段",
        "expected_patterns": ["class ", "Error", "MissingConfig", "raise", "for"],
    },
    # --- 异常链与上下文 ---
    {
        "id": "exc_chain_014",
        "category": "exception",
        "subcategory": "异常链",
        "user_request": "写一个函数，读取 JSON 文件并解析，将底层异常包装为业务异常并保留原始异常链",
        "expected_patterns": ["def ", "json", "raise", "from", "try", "except"],
    },
    {
        "id": "exc_chain_015",
        "category": "exception",
        "subcategory": "异常链",
        "user_request": "写一个数据库查询函数，捕获连接超时和查询错误，分别包装为不同的业务异常",
        "expected_patterns": ["def ", "DatabaseError", "raise", "from", "try"],
    },
    # --- 资源管理 ---
    {
        "id": "exc_res_016",
        "category": "exception",
        "subcategory": "资源管理",
        "user_request": "写一个上下文管理器类，进入时打印 'start'，退出时打印 'end'，即使异常也要执行退出",
        "expected_patterns": ["class ", "__enter__", "__exit__", "print", "return"],
    },
    {
        "id": "exc_res_017",
        "category": "exception",
        "subcategory": "资源管理",
        "user_request": "用 contextlib.contextmanager 装饰器实现一个计时上下文管理器",
        "expected_patterns": ["contextmanager", "yield", "try", "finally", "time"],
    },
    {
        "id": "exc_res_018",
        "category": "exception",
        "subcategory": "资源管理",
        "user_request": "写一个函数，使用 try-finally 确保文件句柄一定被关闭",
        "expected_patterns": ["def ", "open", "try", "finally", "close"],
    },
    # --- 重试机制 ---
    {
        "id": "exc_retry_019",
        "category": "exception",
        "subcategory": "重试机制",
        "user_request": "写一个装饰器，让函数在抛出指定异常时自动重试最多 3 次，每次间隔递增",
        "expected_patterns": ["def ", "decorator", "retry", "time.sleep", "for"],
    },
    {
        "id": "exc_retry_020",
        "category": "exception",
        "subcategory": "重试机制",
        "user_request": "写一个函数，模拟调用不稳定的外部 API，最多重试 5 次，使用指数退避策略",
        "expected_patterns": ["def ", "api_call", "retry", "sleep", "for", "try"],
    },
    # --- 防御性编程 ---
    {
        "id": "exc_def_021",
        "category": "exception",
        "subcategory": "防御性编程",
        "user_request": "写一个函数，安全地执行数学表达式字符串（仅支持 +-*/），捕获所有可能的错误",
        "expected_patterns": ["def ", "eval", "safe", "try", "except", "return"],
    },
    {
        "id": "exc_def_022",
        "category": "exception",
        "subcategory": "防御性编程",
        "user_request": "写一个函数，批量处理列表中的元素，单个元素失败不影响其他元素的处理",
        "expected_patterns": ["def ", "for", "try", "except", "continue", "return"],
    },
    {
        "id": "exc_def_023",
        "category": "exception",
        "subcategory": "防御性编程",
        "user_request": "写一个函数，使用 assert 语句对输入参数进行前置条件检查",
        "expected_patterns": ["def ", "assert", "isinstance", ">=", "return"],
    },
    {
        "id": "exc_def_024",
        "category": "exception",
        "subcategory": "日志记录",
        "user_request": "写一个函数，捕获异常时不仅处理还要用 logging 模块记录完整的 traceback",
        "expected_patterns": ["def ", "logging", "exception", "try", "except"],
    },
    {
        "id": "exc_def_025",
        "category": "exception",
        "subcategory": "异常聚合",
        "user_request": "写一个函数，收集多个验证错误后一次性抛出（异常组或错误列表）",
        "expected_patterns": ["def ", "errors", "append", "raise", "Exception"],
    },
]

# ═══════════════════════════════════════════════════════════════
# Category 4: 边界条件 (25 cases)
# ═══════════════════════════════════════════════════════════════

BOUNDARY_CASES: list[dict[str, Any]] = [
    # --- 空值/零值 ---
    {
        "id": "bnd_empty_001",
        "category": "boundary",
        "subcategory": "空值处理",
        "user_request": "写一个函数，计算整数列表的平均值，空列表返回 None 而不是报错",
        "expected_patterns": ["def ", "if not", "return None", "sum", "len"],
    },
    {
        "id": "bnd_empty_002",
        "category": "boundary",
        "subcategory": "空值处理",
        "user_request": "写一个函数，查找字符串中最长的单词，空字符串返回空字符串",
        "expected_patterns": ["def ", "if not", "split", "max", "return"],
    },
    {
        "id": "bnd_empty_003",
        "category": "boundary",
        "subcategory": "空值处理",
        "user_request": "写一个函数，合并多个列表，处理 None 和空列表输入",
        "expected_patterns": ["def ", "for", "extend", "if", "None", "return"],
    },
    {
        "id": "bnd_empty_004",
        "category": "boundary",
        "subcategory": "空值处理",
        "user_request": "写一个函数，递归遍历目录结构，处理空目录和权限拒绝的目录",
        "expected_patterns": ["def ", "os.walk", "try", "except", "return"],
    },
    {
        "id": "bnd_empty_005",
        "category": "boundary",
        "subcategory": "空值处理",
        "user_request": "写一个函数，安全地将任意值转换为布尔值，None/空/零 为 False，其余为 True",
        "expected_patterns": ["def ", "bool", "return", "None", "not"],
    },
    # --- 极值 ---
    {
        "id": "bnd_extreme_006",
        "category": "boundary",
        "subcategory": "极值处理",
        "user_request": "写一个函数，计算整数的绝对值，正确处理 INT_MIN（Python 中为 -2**31）",
        "expected_patterns": ["def ", "abs", "return", "int"],
    },
    {
        "id": "bnd_extreme_007",
        "category": "boundary",
        "subcategory": "极值处理",
        "user_request": "写一个函数，反转 32 位有符号整数，处理溢出时返回 0",
        "expected_patterns": ["def ", "reverse", "2**31", "overflow", "return"],
    },
    {
        "id": "bnd_extreme_008",
        "category": "boundary",
        "subcategory": "极值处理",
        "user_request": "写一个函数，计算 x 的 n 次幂，n 可能为负数或极大值，考虑溢出",
        "expected_patterns": ["def ", "pow", "n < 0", "return", "**"],
    },
    {
        "id": "bnd_extreme_009",
        "category": "boundary",
        "subcategory": "极值处理",
        "user_request": "写一个函数，将秒数转换为 HH:MM:SS 格式，支持超过 86400 的秒数",
        "expected_patterns": ["def ", "divmod", "%", "format", "return"],
    },
    {
        "id": "bnd_extreme_010",
        "category": "boundary",
        "subcategory": "极值处理",
        "user_request": "写一个函数，解析超大 JSON 字符串中的整数，正确处理超过 64 位的数值",
        "expected_patterns": ["def ", "json", "int", "Decimal", "return"],
    },
    # --- 单元素/单次 ---
    {
        "id": "bnd_single_011",
        "category": "boundary",
        "subcategory": "单元素",
        "user_request": "写一个函数，对列表进行二分查找，正确处理单元素列表",
        "expected_patterns": ["def ", "binary_search", "while", "mid", "return"],
    },
    {
        "id": "bnd_single_012",
        "category": "boundary",
        "subcategory": "单元素",
        "user_request": "写一个函数，找到二叉搜索树中的最小值，正确处理只有根节点的树",
        "expected_patterns": ["def ", "min", "left", "while", "return"],
    },
    {
        "id": "bnd_single_013",
        "category": "boundary",
        "subcategory": "单元素",
        "user_request": "写一个函数，将嵌套列表扁平化，正确处理深度只有 1 层的列表和空列表",
        "expected_patterns": ["def ", "flatten", "isinstance", "yield", "return"],
    },
    # --- Unicode 与编码 ---
    {
        "id": "bnd_enc_014",
        "category": "boundary",
        "subcategory": "编码边界",
        "user_request": "写一个函数，检查字符串是否包含中文字符",
        "expected_patterns": ["def ", "unicode", "range", "return", "bool"],
    },
    {
        "id": "bnd_enc_015",
        "category": "boundary",
        "subcategory": "编码边界",
        "user_request": "写一个函数，安全地将字符串截断到指定字符数，不在 emoji 或中文字符中间截断",
        "expected_patterns": ["def ", "encode", "truncate", "return"],
    },
    {
        "id": "bnd_enc_016",
        "category": "boundary",
        "subcategory": "编码边界",
        "user_request": "写一个函数，统计字符串中 Unicode 字符数（而非字节数）",
        "expected_patterns": ["def ", "len", "return"],
    },
    # --- 并发边界 ---
    {
        "id": "bnd_concur_017",
        "category": "boundary",
        "subcategory": "并发边界",
        "user_request": "写一个线程安全的计数器类，支持 increment、decrement 和 get_value",
        "expected_patterns": ["class ", "Counter", "threading.Lock", "with"],
    },
    {
        "id": "bnd_concur_018",
        "category": "boundary",
        "subcategory": "并发边界",
        "user_request": "实现一个简单的线程池，限制最大并发数，支持 submit 和 shutdown",
        "expected_patterns": ["class ", "ThreadPool", "Queue", "Thread", "submit"],
    },
    # --- 时间/日期边界 ---
    {
        "id": "bnd_time_019",
        "category": "boundary",
        "subcategory": "时间边界",
        "user_request": "写一个函数，判断一个年份是否为闰年，正确处理公元前的年份",
        "expected_patterns": ["def ", "leap_year", "%", "return", "bool"],
    },
    {
        "id": "bnd_time_020",
        "category": "boundary",
        "subcategory": "时间边界",
        "user_request": "写一个函数，计算两个日期之间的天数差，正确处理跨月和跨年",
        "expected_patterns": ["def ", "date", "days", "abs", "return"],
    },
    # --- 浮点精度 ---
    {
        "id": "bnd_float_021",
        "category": "boundary",
        "subcategory": "浮点精度",
        "user_request": "写一个函数，比较两个浮点数是否近似相等（相对误差 < 1e-9）",
        "expected_patterns": ["def ", "abs", "epsilon", "1e-9", "return"],
    },
    {
        "id": "bnd_float_022",
        "category": "boundary",
        "subcategory": "浮点精度",
        "user_request": "写一个函数，安全地对浮点数列表求和，使用 math.fsum 避免精度损失",
        "expected_patterns": ["def ", "math.fsum", "return"],
    },
    {
        "id": "bnd_float_023",
        "category": "boundary",
        "subcategory": "浮点精度",
        "user_request": "写一个函数，将浮点数四舍五入到指定小数位，正确处理 .5 边界情况",
        "expected_patterns": ["def ", "round", "Decimal", "return"],
    },
    # --- 递归深度 ---
    {
        "id": "bnd_depth_024",
        "category": "boundary",
        "subcategory": "递归深度",
        "user_request": "写一个函数，用迭代而非递归的方式实现树遍历，避免爆栈（处理深度 > 1000 的树）",
        "expected_patterns": ["def ", "stack", "while", "tuple", "iterative"],
    },
    {
        "id": "bnd_depth_025",
        "category": "boundary",
        "subcategory": "递归深度",
        "user_request": "写一个函数，计算列表的最大嵌套深度，使用迭代 + 栈而不是递归",
        "expected_patterns": ["def ", "stack", "while", "max", "iterative"],
    },
]

# ═══════════════════════════════════════════════════════════════
# Aggregated benchmark set
# ═══════════════════════════════════════════════════════════════

BENCHMARK_CASES: list[dict[str, Any]] = (
    BASIC_CASES + RECURSION_CASES + EXCEPTION_CASES + BOUNDARY_CASES
)

CATEGORY_STATS = {
    "basic": {"count": len(BASIC_CASES), "label": "基础功能"},
    "recursion": {"count": len(RECURSION_CASES), "label": "递归算法"},
    "exception": {"count": len(EXCEPTION_CASES), "label": "异常处理"},
    "boundary": {"count": len(BOUNDARY_CASES), "label": "边界条件"},
}
