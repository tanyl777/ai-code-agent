import sys
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open

from safe_reader import safe_read_file


class TestSafeReadFile:
    """safe_read_file 单元测试套件，覆盖正常读取、边界条件、重试逻辑与异常。"""

    # ------------------------------------------------------------------
    # 基础功能：正常读取
    # ------------------------------------------------------------------
    @pytest.mark.parametrize(
        "content,encoding,file_factory",
        [
            ("Hello, World!", "utf-8", lambda p: p),
            ("café", "latin-1", lambda p: p),
            ("multiple\
lines", "ascii", lambda p: p),
            ("", "utf-8", lambda p: p),
            # 也接受 Path 对象
            ("Path as argument", "utf-8", lambda p: p),
        ],
    )
    def test_read_file_success(self, tmp_path, content, encoding, file_factory):
        """正常读取不同内容和编码，接受 str 或 Path 参数。"""
        file = tmp_path / "test.txt"
        file.write_text(content, encoding=encoding)
        result = safe_read_file(file_factory(file), encoding=encoding)
        assert result == content

    def test_read_file_returns_str(self, tmp_path):
        """返回值类型为 str。"""
        file = tmp_path / "test.txt"
        file.write_text("data", encoding="utf-8")
        result = safe_read_file(str(file))
        assert isinstance(result, str)

    # ------------------------------------------------------------------
    # 边界条件
    # ------------------------------------------------------------------
    def test_read_empty_file(self, tmp_path):
        """空文件返回空字符串。"""
        file = tmp_path / "empty.txt"
        file.write_text("", encoding="utf-8")
        result = safe_read_file(file)
        assert result == ""

    def test_read_file_default_encoding(self, tmp_path):
        """未指定编码时使用默认 utf-8 正确读取。"""
        content = "默认编码测试"
        file = tmp_path / "default.txt"
        file.write_text(content, encoding="utf-8")
        result = safe_read_file(str(file))
        assert result == content

    # ------------------------------------------------------------------
    # 重试逻辑
    # ------------------------------------------------------------------
    @patch("safe_reader.time.sleep", return_value=None)  # 避免测试真实等待
    @pytest.mark.skipif(sys.platform=="win32",reason="Windows permission model differs")
    def test_retry_on_permission_error(self, mock_sleep, tmp_path):
        """当发生 PermissionError 时应重试，最终成功。"""
        file = tmp_path / "retry.txt"
        file.write_text("retry success", encoding="utf-8")
        mock = mock_open(read_data="retry success")

        # 前两次调用抛出 PermissionError，第三次正常返回
        mock.side_effect = [PermissionError("denied"), PermissionError("denied"), mock.return_value]

        with patch("builtins.open", mock):
            result = safe_read_file(str(file))

        assert result == "retry success"
        assert mock.call_count == 4
        assert mock_sleep.call_count == 2

    @patch("safe_reader.time.sleep", return_value=None)
    def test_retry_exhausted_raises(self, mock_sleep, tmp_path):
        """重试次数用尽后应抛出最后的异常。"""
        file = tmp_path / "fail.txt"
        file.write_text("fail", encoding="utf-8")
        mock = mock_open(read_data="fail")
        # 始终抛出异常
        mock.side_effect = PermissionError("Access denied")

        with patch("builtins.open", mock):
            with pytest.raises(PermissionError, match="Access denied"):
                safe_read_file(str(file))

        # 应重试指定次数，假设为3次
        assert mock.call_count == 4
        assert mock_sleep.call_count == 3

    # ------------------------------------------------------------------
    # 异常处理：文件不存在
    # ------------------------------------------------------------------
    def test_file_not_found_raises(self, tmp_path):
        """文件不存在时直接抛出 FileNotFoundError，不重试。"""
        non_existent = tmp_path / "ghost.txt"
        with pytest.raises(FileNotFoundError):
            safe_read_file(non_existent)

    # ------------------------------------------------------------------
    # 编码错误处理
    # ------------------------------------------------------------------
    def test_encoding_error_raises(self, tmp_path):
        """指定错误编码时应抛出 UnicodeDecodeError。"""
        file = tmp_path / "encoded.txt"
        # 写入非 UTF-8 内容，然后以错误的编码读取
        file.write_bytes("café".encode("latin-1"))
        with pytest.raises(UnicodeDecodeError):
            safe_read_file(file, encoding="ascii")