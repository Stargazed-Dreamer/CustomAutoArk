"""extract_agents 单元测试

覆盖 html_parser.py 中 extract_agents 函数。该函数为纯函数，仅依赖 re 模块，
从 HTML 字符串中提取含 data-zh 属性的 div，并按 d_transfer 转换规则映射字段。

测试用构造的小段 HTML 字符串，不依赖真实 a.html 文件。
"""
import pytest

from html_parser import extract_agents


# ==================== 基本提取 ====================

class TestExtractAgentsBasic:
    """基本提取行为测试"""

    def test_empty_html_returns_empty_dict(self):
        """空 HTML 返回空字典"""
        d_transfer = {"__key__": "data-zh"}
        assert extract_agents("", d_transfer, {}) == {}

    def test_no_matching_div_returns_empty(self):
        """没有 data-zh 属性的 div 不被匹配，返回空字典"""
        html = '<div data-en="W"></div>'
        d_transfer = {"__key__": "data-zh"}
        assert extract_agents(html, d_transfer, {}) == {}

    def test_basic_extraction(self):
        """基本提取：返回字典键为中文干员名（data-zh 的值）"""
        html = '<div data-zh="W" data-en="W" data-rarity="5"></div>'
        d_transfer = {
            "__key__": "data-zh",
            "en": "data-en",
            "star": "data-rarity",
        }
        result = extract_agents(html, d_transfer, {})
        assert "W" in result
        assert result["W"]["en"] == "W"
        assert result["W"]["star"] == "5"

    def test_multiple_divs_extracted(self):
        """多个 div 都被提取"""
        html = (
            '<div data-zh="W" data-en="W"></div>'
            '<div data-zh="克洛丝" data-en="Kroos"></div>'
        )
        d_transfer = {
            "__key__": "data-zh",
            "en": "data-en",
        }
        result = extract_agents(html, d_transfer, {})
        assert len(result) == 2
        assert "W" in result
        assert "克洛丝" in result
        assert result["W"]["en"] == "W"
        assert result["克洛丝"]["en"] == "Kroos"

    def test_div_without_data_zh_skipped(self):
        """没有 data-zh 的 div 被跳过（正则不匹配）"""
        html = (
            '<div data-en="W"></div>'            # 无 data-zh，跳过
            '<div data-zh="W" data-en="W"></div>'  # 有 data-zh，提取
        )
        d_transfer = {"__key__": "data-zh", "en": "data-en"}
        result = extract_agents(html, d_transfer, {})
        assert len(result) == 1
        assert "W" in result


# ==================== 直接属性映射 ====================

class TestDirectAttributeMapping:
    """直接属性映射（transfer_rule 不以反斜杠开头）测试"""

    def test_direct_mapping(self):
        """transfer_rule 为属性名时直接取该属性值"""
        html = '<div data-zh="W" data-rarity="5"></div>'
        d_transfer = {
            "__key__": "data-zh",
            "star": "data-rarity",
        }
        result = extract_agents(html, d_transfer, {})
        assert result["W"]["star"] == "5"

    def test_missing_attribute_raises_keyerror(self):
        """直接映射时缺失属性抛 KeyError"""
        html = '<div data-zh="W"></div>'  # 没有 data-rarity
        d_transfer = {
            "__key__": "data-zh",
            "star": "data-rarity",
        }
        with pytest.raises(KeyError):
            extract_agents(html, d_transfer, {})


# ==================== 函数调用规则 ====================

class TestFunctionCall:
    """函数调用规则（transfer_rule 以反斜杠开头）测试"""

    def test_function_call(self):
        """以反斜杠开头的规则调用 d_func 中对应函数"""
        html = (
            '<div data-zh="W" data-profession="狙击"'
            ' data-position="远程位" data-tag="输出 控场"></div>'
        )

        def add_3(a, b, c):
            return [a + "干员", b] + c.split(" ")

        d_func = {"add_3": add_3}
        d_transfer = {
            "__key__": "data-zh",
            "tag": '\\add_3(data-profession, data-position, data-tag)',
        }
        result = extract_agents(html, d_transfer, d_func)
        assert result["W"]["tag"] == ["狙击干员", "远程位", "输出", "控场"]

    def test_invalid_function_format_raises_valueerror(self):
        """非法函数格式（无括号）抛 ValueError"""
        html = '<div data-zh="W"></div>'
        d_transfer = {
            "__key__": "data-zh",
            "tag": '\\add_3',  # 缺少括号，无法匹配函数格式
        }
        with pytest.raises(ValueError):
            extract_agents(html, d_transfer, {})

    def test_missing_attribute_in_function_raises_keyerror(self):
        """函数参数对应的属性缺失抛 KeyError"""
        html = '<div data-zh="W"></div>'  # 没有 data-profession 等属性
        d_func = {"add_3": lambda a, b, c: None}
        d_transfer = {
            "__key__": "data-zh",
            "tag": '\\add_3(data-profession, data-position, data-tag)',
        }
        with pytest.raises(KeyError):
            extract_agents(html, d_transfer, d_func)

    def test_missing_function_raises_keyerror(self):
        """d_func 中缺失对应函数抛 KeyError"""
        html = '<div data-zh="W" data-profession="狙击"></div>'
        d_transfer = {
            "__key__": "data-zh",
            "tag": '\\nonexistent(data-profession)',
        }
        with pytest.raises(KeyError):
            extract_agents(html, d_transfer, {})


# ==================== 主键字段 ====================

class TestKeyField:
    """主键字段（__key__）行为测试"""

    def test_key_field_as_data_zh(self):
        """__key__ 为 data-zh 时，以中文干员名为键"""
        html = '<div data-zh="阿米娅" data-en="Amiya"></div>'
        d_transfer = {"__key__": "data-zh", "en": "data-en"}
        result = extract_agents(html, d_transfer, {})
        assert "阿米娅" in result
        assert result["阿米娅"]["en"] == "Amiya"

    def test_div_without_key_field_value_skipped(self):
        """div 有 data-zh（满足正则）但 __key__ 指定字段缺失时跳过"""
        # __key__ 设为 data-en，但 div 没有 data-en
        html = '<div data-zh="W"></div>'
        d_transfer = {"__key__": "data-en"}
        result = extract_agents(html, d_transfer, {})
        assert result == {}
