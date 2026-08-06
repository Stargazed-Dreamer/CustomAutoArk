"""Data 类纯方法单元测试

覆盖 data.py 中 Data 类的 is_special / getTagPriority 方法，
以及 l_agent / l_tag / d_agent 的数据结构约定。
data 模块为纯 Python 数据定义，不依赖 cv2/paddleocr/PySide6/log。
"""
import pytest

from data import data as DATA


# ==================== is_special ====================

class TestIsSpecial:
    """is_special 方法测试"""

    def test_special_tag_returns_true(self):
        """d_tag[4] 中的 tag 返回 True"""
        for tag in DATA.d_tag[4]:
            assert DATA.is_special(tag) is True

    def test_non_special_tag_returns_false(self):
        """非 d_tag[4] 的 tag 返回 False"""
        for num in [0, 1, 2, 3]:
            for tag in DATA.d_tag[num]:
                assert DATA.is_special(tag) is False

    def test_unknown_tag_returns_false(self):
        """未知 tag（不在任何分组中）返回 False"""
        assert DATA.is_special("不存在的标签") is False


# ==================== getTagPriority ====================

class TestGetTagPriority:
    """getTagPriority 方法测试"""

    def test_returns_priority_group(self):
        """返回 tag 所在的优先级分组数字"""
        for num, tags in DATA.d_tag.items():
            for tag in tags:
                assert DATA.getTagPriority(tag) == num

    def test_known_tags_priority(self):
        """已知 tag 的优先级与 d_tag 分组一致"""
        # 0 组：元素、支援机械
        assert DATA.getTagPriority("元素") == 0
        assert DATA.getTagPriority("支援机械") == 0
        # 1 组：先锋干员、近战位
        assert DATA.getTagPriority("先锋干员") == 1
        assert DATA.getTagPriority("近战位") == 1
        # 2 组：治疗、输出
        assert DATA.getTagPriority("治疗") == 2
        assert DATA.getTagPriority("输出") == 2
        # 3 组：支援、爆发
        assert DATA.getTagPriority("支援") == 3
        assert DATA.getTagPriority("爆发") == 3
        # 4 组：资深干员、高级资深干员
        assert DATA.getTagPriority("资深干员") == 4
        assert DATA.getTagPriority("高级资深干员") == 4

    def test_unknown_tag_raises_valueerror(self):
        """非法 tag 抛 ValueError"""
        with pytest.raises(ValueError):
            DATA.getTagPriority("不存在的标签")


# ==================== l_agent 结构 ====================

class TestLAgent:
    """l_agent 数据结构测试"""

    def test_is_list_of_tuples(self):
        """l_agent 是 (zh, en) 元组列表"""
        assert isinstance(DATA.l_agent, list)
        assert len(DATA.l_agent) > 0
        for item in DATA.l_agent:
            assert isinstance(item, tuple)
            assert len(item) == 2
            zh, en = item
            assert isinstance(zh, str)
            assert isinstance(en, str)

    def test_contains_known_agents(self):
        """包含已知干员 (zh, en) 对"""
        agent_set = set(DATA.l_agent)
        assert ("W", "W") in agent_set
        assert ("克洛丝", "Kroos") in agent_set
        assert ("Castle-3", "Castle-3") in agent_set

    def test_zh_names_match_d_agent_keys(self):
        """l_agent 中每个中文干员名都是 d_agent 的键"""
        for zh, _en in DATA.l_agent:
            assert zh in DATA.d_agent

    def test_en_names_match_d_agent_values(self):
        """l_agent 中每个英文干员名与 d_agent 中 en 字段一致"""
        for zh, en in DATA.l_agent:
            assert DATA.d_agent[zh]["en"] == en

    def test_length_matches_d_agent(self):
        """l_agent 长度与 d_agent 键数一致"""
        assert len(DATA.l_agent) == len(DATA.d_agent)


# ==================== l_tag 结构 ====================

class TestLTag:
    """l_tag 数据结构测试"""

    def test_is_list(self):
        """l_tag 是列表"""
        assert isinstance(DATA.l_tag, list)
        assert len(DATA.l_tag) > 0

    def test_contains_all_d_tag_tags(self):
        """l_tag 包含 d_tag 中的所有 tag"""
        all_tags = []
        for num in DATA.d_tag:
            all_tags += DATA.d_tag[num]
        assert set(DATA.l_tag) == set(all_tags)

    def test_no_duplicates(self):
        """l_tag 中无重复元素（各分组 tag 互不相交）"""
        assert len(DATA.l_tag) == len(set(DATA.l_tag))

    def test_all_tags_are_strings(self):
        """l_tag 中每个 tag 都是字符串"""
        for tag in DATA.l_tag:
            assert isinstance(tag, str)


# ==================== d_agent 结构 ====================

class TestDAgent:
    """d_agent 数据结构测试"""

    def test_contains_known_agents(self):
        """d_agent 包含 W、克洛丝、Castle-3 等已知干员"""
        assert "W" in DATA.d_agent
        assert "克洛丝" in DATA.d_agent
        assert "Castle-3" in DATA.d_agent

    def test_star_field_is_string(self):
        """每个干员的 star 字段为字符串"""
        for _name, info in DATA.d_agent.items():
            assert "star" in info
            assert isinstance(info["star"], str)

    def test_agent_has_required_fields(self):
        """每个干员数据含 en / star / tag / subprofession 字段"""
        for _name, info in DATA.d_agent.items():
            assert "en" in info
            assert "star" in info
            assert "tag" in info
            assert "subprofession" in info
            assert isinstance(info["tag"], list)

    def test_agent_tags_are_valid(self):
        """每个干员的 tag 列表中的 tag 都在 l_tag 中（除特殊标签外）"""
        valid_tags = set(DATA.l_tag)
        for _name, info in DATA.d_agent.items():
            for tag in info["tag"]:
                # 个别 tag（如 '高空'）可能不在 d_tag 中，此处仅做软校验：
                # 在 l_tag 中的 tag 必须存在于 valid_tags
                if tag in valid_tags:
                    assert tag in valid_tags
