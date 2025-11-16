from itertools import combinations
from newData import data

# 定义星级优先级顺序
STAR_PRIORITY = ['5', '4', '0', '3', '2', '1']
STAR_EXCEPTION = ["5"]

class TagFinder:
    def __init__(self):
        # 过滤出obtain_method为1的干员
        self.valid_agents = {
            name: info 
            for name, info in data.d_agent.items() 
            if info['obtain_method'] == 1
            if info['star'] not in STAR_EXCEPTION
        }
        # 预计算每个tag的最低出现星级
        self.tag_min_star = self._calculate_tag_min_star()
    
    def _calculate_tag_min_star(self):
        """计算每个tag在有效干员中的最低出现星级"""
        tag_stars = {}
        
        # 收集每个tag出现的所有星级
        for agent_info in self.valid_agents.values():
            star = agent_info['star']
            for tag in agent_info['tag']:
                if tag not in tag_stars:
                    tag_stars[tag] = []
                tag_stars[tag].append(star)
        
        # 确定每个tag的最低出现星级（在优先级顺序中最靠后的）
        tag_min_star = {}
        for tag, stars in tag_stars.items():
            # 根据优先级排序，优先级最低的（在STAR_PRIORITY中索引最大的）即为最低出现星级
            min_star = max(stars, key=lambda s: STAR_PRIORITY.index(s))
            tag_min_star[tag] = min_star
        
        return tag_min_star

    def get_tag_levels(self):
        """
        功能函数二：返回所有tag应该属于的等级
        格式: {等级: [tag1, tag2, ...]}
        """
        level_dict = {}
        
        for tag, min_star in self.tag_min_star.items():
            level = min_star
            if level not in level_dict:
                level_dict[level] = []
            level_dict[level].append(tag)
        
        # 添加特殊tag（资深干员和高级资深干员）到-1等级
        special_tags = ['资深干员', '高级资深干员']
        level_dict['-1'] = special_tags
        
        return level_dict

    def find_agents_with_low_level_tags(self):
        """
        功能函数一：找出仅通过低等级tag组合就能锁定的干员
        返回: {干员名: 干员信息}
        """
        result = {}
        
        for name, agent_info in self.valid_agents.items():
            agent_star = agent_info['star']
            agent_tags = set(agent_info['tag'])
            
            # 找出干员中所有"低等级"的tag（星级低于干员自身星级）
            low_level_tags = [
                tag for tag in agent_tags
                if STAR_PRIORITY.index(self.tag_min_star[tag]) > STAR_PRIORITY.index(agent_star)
            ]
            
            # 检查所有可能的低等级tag组合
            found = False
            agent_info["tag_combo"] = []
            for r in range(1, len(low_level_tags) + 1):
                for combo in combinations(low_level_tags, r):
                    combo_set = set(combo)
                    
                    # 检查是否只有当前干员拥有这个组合
                    match_count = 0
                    for other_name, other_info in self.valid_agents.items():
                        other_tags = set(other_info['tag'])
                        if combo_set.issubset(other_tags):
                            match_count += 1
                            if match_count > 1:
                                break
                    
                    # 如果只有当前干员匹配，则添加到结果
                    if match_count == 1:
                        agent_info["tag_combo"].append(tuple(combo_set))
                        result[name] = agent_info
                        found = True
                        break
                if found:
                    break
                    
        return result

    def find_agents_by_tags(self, input_tags):
        """
        功能函数三：输入tag列表，返回所有组合对应的干员
        返回: {组合元组: [干员名1, 干员名2, ...]}
        """
        # 生成所有非空子集组合
        all_combos = []
        for r in range(1, len(input_tags) + 1):
            for combo in combinations(input_tags, r):
                all_combos.append(tuple(sorted(combo)))
        
        # 为每个组合查找匹配的干员
        result = {}
        for combo in all_combos:
            combo_set = set(combo)
            matched_agents = []
            
            for name, agent_info in self.valid_agents.items():
                agent_tags = set(agent_info['tag'])
                if combo_set.issubset(agent_tags):
                    matched_agents.append(name)
            
            if matched_agents:
                result[combo] = matched_agents
        
        return result

finder = TagFinder()

# 使用示例
if __name__ == "__main__":
    from pprint import pprint

    
    # 功能函数一示例
    low_level_agents = finder.find_agents_with_low_level_tags()
    print("仅用低等级tag锁定的干员:", list(low_level_agents.keys()))
    #pprint(low_level_agents, width = 160)
    _low_level_agents = sorted(low_level_agents, key = lambda a:int(low_level_agents[a]['star']))
    for name in _low_level_agents:
        #a = " ".join(list(low_level_agents[name]['tag_combo'][0]))
        a = low_level_agents[name]['tag_combo'][0]
        len_a = len(str(a))//6 if len(str(a)) % 6 != 0 else len(str(a))//6-1
        b = (5-len_a)*'\t'
        print(f"{a}{b}{name}")
    
    # 功能函数二示例
    tag_levels = finder.get_tag_levels()
    print("\nTag等级分布:")
    for level, tags in tag_levels.items():
        print(f"等级 {level}: {tags}")
    
    # 功能函数三示例
    input_tags = ['群攻', '削弱']
    agents_by_tags = finder.find_agents_by_tags(input_tags)
    print("\nTag组合查询结果:")
    for combo, agents in agents_by_tags.items():
        print(f"{combo}: {agents}")