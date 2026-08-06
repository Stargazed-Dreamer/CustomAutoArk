"""TagFinder 单元测试

覆盖 find_agents_by_tags 方法：输入 tag 列表，返回所有非空子集组合对应的干员列表。

注意：TagFinder 在初始化时过滤掉 obtain_method != 1 以及 star == '5' 的干员，
因此 5 星干员不会出现在任何查询结果中。
"""
from itertools import combinations


class TestFindAgentsByTags:
    """find_agents_by_tags 方法测试"""

    def test_empty_input(self, finder):
        """空输入返回空字典"""
        assert finder.find_agents_by_tags([]) == {}

    def test_single_tag(self, finder):
        """单个 tag 查询"""
        result = finder.find_agents_by_tags(['治疗'])
        assert ('治疗',) in result
        agents = result[('治疗',)]
        assert len(agents) > 0
        # 所有返回的干员都应包含 '治疗' tag
        for name in agents:
            assert '治疗' in finder.valid_agents[name]['tag']

    def test_combo_key_sorted(self, finder):
        """组合键应为排序后的元组"""
        result = finder.find_agents_by_tags(['群攻', '削弱'])
        assert ('削弱', '群攻') in result
        assert ('群攻', '削弱') not in result

    def test_excludes_five_star(self, finder):
        """5 星干员应被排除（STAR_EXCEPTION = ['5']）"""
        result = finder.find_agents_by_tags(['群攻', '削弱'])
        agents = result[('削弱', '群攻')]
        # 4 星且 obtain_method==1 的慑砂、陨星应出现
        assert '慑砂' in agents
        assert '陨星' in agents
        # 5 星干员伊芙利特虽拥有群攻+削弱，但应被排除
        assert '伊芙利特' not in agents

    def test_no_valid_agents(self, finder):
        """仅匹配到被排除干员的 tag 不应出现在结果中"""
        # '高空' 仅出现在 obtain_method==0 的干员上
        result = finder.find_agents_by_tags(['高空'])
        assert ('高空',) not in result

    def test_subset_invariant(self, finder):
        """不变量：返回的干员必须拥有该组合的全部 tag"""
        result = finder.find_agents_by_tags(['输出', '减速', '生存'])
        for combo, agents in result.items():
            combo_set = set(combo)
            for name in agents:
                assert combo_set.issubset(set(finder.valid_agents[name]['tag']))

    def test_all_results_are_nonempty_subsets(self, finder):
        """所有结果键都是输入 tag 的非空子集"""
        input_tags = ['治疗', '输出', '防护']
        result = finder.find_agents_by_tags(input_tags)
        all_subsets = set()
        for r in range(1, len(input_tags) + 1):
            for combo in combinations(input_tags, r):
                all_subsets.add(tuple(sorted(combo)))
        for key in result:
            assert key in all_subsets

    def test_result_agents_nonempty(self, finder):
        """结果中每个组合对应的干员列表均非空"""
        result = finder.find_agents_by_tags(['削弱', '位移'])
        for combo, agents in result.items():
            assert len(agents) > 0

    def test_only_valid_agents_returned(self, finder):
        """返回的干员均来自 valid_agents（已过滤 obtain_method 与星级）"""
        result = finder.find_agents_by_tags(['输出'])
        for combo, agents in result.items():
            for name in agents:
                assert name in finder.valid_agents
                assert finder.valid_agents[name]['star'] != '5'
