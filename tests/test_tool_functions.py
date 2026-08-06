"""tool.py 纯函数单元测试

覆盖 tool.py 中不依赖 cv2/paddleocr 真实功能的模块级纯函数：
- _get_filename(path)：从路径提取文件名，处理 / 和 \\
- error_record(e)：异常记录（log 已被 conftest mock，不产生真实副作用）

注：Tool.cosine_similarity 已在 test_tool.py 中覆盖，此处不重复。
依赖 cv2 真实功能的方法（cropping / match_template 等）不在本文件覆盖范围内。
"""
import pytest

from tool import _get_filename, error_record


# ==================== _get_filename ====================

class TestGetFilename:
    """_get_filename 函数测试"""

    def test_windows_path(self):
        """Windows 路径取最后一段"""
        assert _get_filename("a\\b\\c.txt") == "c.txt"

    def test_unix_path(self):
        """Unix 路径取最后一段"""
        assert _get_filename("a/b/c.txt") == "c.txt"

    def test_no_separator(self):
        """无分隔符返回整个路径"""
        assert _get_filename("file.txt") == "file.txt"

    def test_mixed_separators(self):
        """混合分隔符取最后一段"""
        assert _get_filename("a/b\\c.txt") == "c.txt"

    def test_empty_string(self):
        """空字符串返回空字符串"""
        assert _get_filename("") == ""

    def test_trailing_separator(self):
        """尾部分隔符返回空字符串"""
        assert _get_filename("a/b/") == ""

    def test_single_separator(self):
        """单个分隔符返回空字符串"""
        assert _get_filename("/") == ""

    def test_filename_with_dots(self):
        """文件名含多个点正常返回"""
        assert _get_filename("a/b/c.d.e.txt") == "c.d.e.txt"


# ==================== error_record ====================

class TestErrorRecord:
    """error_record 函数测试

    log 模块已被 conftest.py 整体 mock，error_record 内部调用 log.log
    不会产生真实副作用，仅验证不抛错。
    """

    def test_exception_without_traceback(self):
        """无 traceback 的异常（直接构造）不抛错"""
        e = Exception("test error")
        assert e.__traceback__ is None
        # 不抛错即通过
        error_record(e)

    def test_exception_with_traceback(self):
        """有 traceback 的异常（raise 后捕获）不抛错"""
        try:
            raise ValueError("raised error")
        except ValueError as e:
            assert e.__traceback__ is not None
            error_record(e)

    def test_returns_none(self):
        """error_record 无返回值（返回 None）"""
        e = Exception("test")
        assert error_record(e) is None

    def test_various_exception_types(self):
        """各类异常类型均可记录，不抛错"""
        for exc in [Exception("a"), RuntimeError("b"), TypeError("c"), KeyError("d")]:
            error_record(exc)  # 不抛错即通过
