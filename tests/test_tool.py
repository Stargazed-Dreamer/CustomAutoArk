"""Tool.cosine_similarity 单元测试

cosine_similarity 为静态行为方法，计算两个字符串的余弦相似度，
仅依赖 Python 内建操作，不涉及 cv2/paddleocr。
"""
import pytest


class TestCosineSimilarity:
    """cosine_similarity 方法测试"""

    def test_identical_string(self, tool_obj):
        """完全相同的字符串相似度为 1.0"""
        assert tool_obj.cosine_similarity("abc", "abc") == 1.0

    def test_empty_string(self, tool_obj):
        """任一字符串为空时相似度为 0"""
        assert tool_obj.cosine_similarity("", "abc") == 0
        assert tool_obj.cosine_similarity("abc", "") == 0
        assert tool_obj.cosine_similarity("", "") == 0

    def test_case_insensitive(self, tool_obj):
        """忽略大小写后相同的字符串相似度为 1.0"""
        assert tool_obj.cosine_similarity("AbC", "aBc") == 1.0

    def test_new_prefix_stripped(self, tool_obj):
        """以 new 开头的字符串去除前缀后再比较"""
        # "newABC" 去除 "new" → "abc"，与 "ABC"(→"abc") 完全相同
        # 用 approx 容忍浮点误差
        assert tool_obj.cosine_similarity("newABC", "ABC") == pytest.approx(1.0)

    def test_high_similarity(self, tool_obj):
        """'NEW!地灵' 与 '地灵' 应高度相似但不完全相同"""
        sim = tool_obj.cosine_similarity("NEW!地灵", "地灵")
        assert sim > 0.7
        assert sim < 1.0  # 多出一个 "!" 字符，不完全相同

    def test_no_common_chars(self, tool_obj):
        """无公共字符时相似度为 0"""
        assert tool_obj.cosine_similarity("abc", "xyz") == 0.0

    def test_result_in_range(self, tool_obj):
        """相似度结果始终在 [0, 1] 区间内"""
        sim = tool_obj.cosine_similarity("hello", "hallo")
        assert 0.0 <= sim <= 1.0

    def test_partial_overlap(self, tool_obj):
        """部分重叠的字符串相似度介于 0 和 1 之间"""
        sim = tool_obj.cosine_similarity("abcd", "ab")
        assert 0.0 < sim < 1.0
