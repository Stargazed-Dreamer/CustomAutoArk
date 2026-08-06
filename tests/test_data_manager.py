"""DataManager 单元测试

覆盖以下纯算法方法（均不依赖 cv2/paddleocr/PySide6）：
- data_convert：原始数据转数值
- find_peaks：查找波峰波谷
- dtw_distance：动态时间规整距离
- find_patterns：DTW 相似模式查找
- get_statistics：统计信息
- normalize：Z-score 归一化
"""
import numpy as np
import pytest


# ==================== data_convert ====================

class TestDataConvert:
    """data_convert 方法测试"""

    def test_tag_combo(self, dm):
        """含 ! 的 tag 组合 → 各 tag 优先级之和"""
        # 近战位 优先级 1，输出 优先级 2 → 3
        assert dm.data_convert(["近战位!输出"]) == [3]
        # 元素 优先级 0，高级资深干员 优先级 4 → 4
        assert dm.data_convert(["元素!高级资深干员"]) == [4]

    def test_agent_name(self, dm):
        """干员名 → 星级数字"""
        assert dm.data_convert(["W"]) == [5]
        assert dm.data_convert(["克洛丝"]) == [2]
        assert dm.data_convert(["Castle-3"]) == [0]

    def test_prefixed_number(self, dm):
        """#/ ?/ ？ 前缀数字 → 去前缀转 int"""
        assert dm.data_convert(["#6"]) == [6]
        assert dm.data_convert(["?3"]) == [3]
        assert dm.data_convert(["？4"]) == [4]
        # 无前缀纯数字也合法
        assert dm.data_convert(["7"]) == [7]

    def test_empty_string_skipped(self, dm):
        """空字符串被跳过"""
        assert dm.data_convert(["", ""]) == []

    def test_mixed_formats(self, dm):
        """混合多种格式"""
        result = dm.data_convert(["W", "#6", "近战位!输出"])
        assert result == [5, 6, 3]

    def test_invalid_raises(self, dm):
        """无效数据抛出 ValueError"""
        with pytest.raises(ValueError):
            dm.data_convert(["不存在的数据xyz"])


# ==================== find_peaks ====================

class TestFindPeaks:
    """find_peaks 方法测试"""

    def test_basic(self, dm):
        """基本波峰波谷识别"""
        dm.data = [1, 3, 2, 4, 1]
        peaks, valleys = dm.find_peaks()
        assert peaks == [1, 3]
        assert valleys == [2]

    def test_too_short(self, dm):
        """数据少于 3 个点时返回空列表"""
        dm.data = [1, 2]
        assert dm.find_peaks() == ([], [])

    def test_monotonic(self, dm):
        """单调序列无波峰波谷"""
        dm.data = [1, 2, 3, 4]
        peaks, valleys = dm.find_peaks()
        assert peaks == []
        assert valleys == []

    def test_plateau_not_extreme(self, dm):
        """相邻相等不算波峰/波谷（严格大于/小于）"""
        dm.data = [1, 2, 2, 1]
        peaks, valleys = dm.find_peaks()
        assert peaks == []
        assert valleys == []


# ==================== dtw_distance ====================

class TestDtwDistance:
    """dtw_distance 方法测试"""

    def test_identical_series(self, dm):
        """完全相同的序列距离为 0"""
        assert dm.dtw_distance([1, 2, 3], [1, 2, 3]) == pytest.approx(0.0)

    def test_positive_distance(self, dm):
        """不同序列距离为正"""
        assert dm.dtw_distance([1, 2, 3], [3, 2, 1]) > 0

    def test_symmetric(self, dm):
        """DTW 距离具有对称性"""
        a = [1, 2, 3, 4]
        b = [1, 3, 2, 4]
        assert dm.dtw_distance(a, b) == pytest.approx(dm.dtw_distance(b, a))

    def test_different_lengths(self, dm):
        """支持不等长序列比较"""
        d = dm.dtw_distance([1, 2], [1, 2, 3])
        assert d >= 0


# ==================== find_patterns ====================

class TestFindPatterns:
    """find_patterns 方法测试"""

    def test_short_data(self, dm):
        """数据长度不足时返回空"""
        dm.data = [1, 2, 3]
        assert dm.find_patterns(pattern_length=2) == []

    def test_repeating_pattern(self, dm):
        """重复模式应被识别

        注：命中一个模式后 j 会按 pattern_length 跳过相邻片段以避免重复，
        故 (0,2) 命中后 (0,4) 被跳过；[2,1] 与 [2,1] 形成 (1,3)。
        """
        dm.data = [1, 2, 1, 2, 1, 2]
        patterns = dm.find_patterns(pattern_length=2, threshold=0.8)
        assert (0, 2) in patterns
        assert (1, 3) in patterns

    def test_threshold_too_high(self, dm):
        """相似度上限为 1.0，阈值超过 1.0 时无匹配"""
        dm.data = [1, 2, 1, 2, 1, 2]
        assert dm.find_patterns(pattern_length=2, threshold=1.5) == []

    def test_returns_list_of_tuples(self, dm):
        """返回值为 (start1, start2) 元组列表"""
        dm.data = [1, 2, 1, 2, 1, 2]
        patterns = dm.find_patterns(pattern_length=2, threshold=0.8)
        for pair in patterns:
            assert isinstance(pair, tuple)
            assert len(pair) == 2


# ==================== get_statistics ====================

class TestGetStatistics:
    """get_statistics 方法测试"""

    def test_full_data(self, dm):
        """统计全部数据"""
        dm.data = [6, 5, 6, 3]
        stats = dm.get_statistics()
        assert stats["数据点数"] == 4
        assert stats["平均值"] == 5.0
        assert stats["六星数量"] == 2
        assert stats["五星数量"] == 1

    def test_slice(self, dm):
        """统计指定切片"""
        dm.data = [6, 5, 6, 3]
        stats = dm.get_statistics(0, 2)
        assert stats["数据点数"] == 2
        assert stats["平均值"] == 5.5
        assert stats["六星数量"] == 1
        assert stats["五星数量"] == 1

    def test_empty_data(self, dm):
        """空数据返回空字典"""
        dm.data = []
        assert dm.get_statistics() == {}

    def test_partial_args_uses_full(self, dm):
        """仅传 start 不传 end 时使用全部数据"""
        dm.data = [6, 5, 6]
        stats = dm.get_statistics(0, None)
        assert stats["数据点数"] == 3


# ==================== normalize ====================

class TestNormalize:
    """normalize 方法测试"""

    def test_zero_std(self, dm):
        """标准差为 0 时返回全 0 列表"""
        assert dm.normalize([5, 5, 5]) == [0, 0, 0]

    def test_zscore_properties(self, dm):
        """Z-score 归一化后均值为 0"""
        result = dm.normalize([1, 2, 3])
        assert sum(result) == pytest.approx(0, abs=1e-9)

    def test_zscore_values(self, dm):
        """归一化值与手算一致"""
        series = [1, 2, 3]
        mean = np.mean(series)
        std = np.std(series)
        expected = [(x - mean) / std for x in series]
        result = dm.normalize(series)
        for r, e in zip(result, expected):
            assert r == pytest.approx(e)

    def test_length_preserved(self, dm):
        """归一化不改变序列长度"""
        series = [1, 2, 3, 4, 5]
        assert len(dm.normalize(series)) == len(series)
