_path = ".\\a.html"

import re

def extract_agents(html_content, d_transfer, d_func):
    """
    从HTML内容中提取干员信息，并根据转换规则进行映射，返回包含干员数据的字典。

    参数:
        html_content (str): 包含干员信息的HTML内容。
        d_transfer (dict): 转换规则字典，其中包含一个特殊的键'__key__'用于指定主键字段，
            其他键为目标字段名，值为属性名或以反斜杠开头的函数调用字符串。
        d_func (dict): 可用的函数字典，键为函数名，值为函数对象。

    返回:
        dict: 以干员主键（中文名）为键，干员数据字典为值的字典。
    """
    # 使用正则表达式匹配HTML中包含干员信息的div标签，要求div标签中包含data-zh属性
    pattern = r'<div\b([^>]*?data-zh="[^"]*"[^>]*)>'
    matches = re.findall(pattern, html_content)
    
    agents_dict = {}
    # 从转换规则中获取主键字段名
    key_field = d_transfer["__key__"]
    
    # 遍历所有匹配到的div标签属性字符串
    for attrs_str in matches:
        # 使用正则表达式提取所有data-开头的属性键值对
        attr_pattern = r'(\bdata-[\w-]+)\s*=\s*"([^"]*)"'
        attrs = dict(re.findall(attr_pattern, attrs_str))
        
        # 如果没有提取到任何属性，则跳过当前div
        if not attrs:
            continue
            
        # 获取干员的主键值（即中文名）
        agent_key = attrs.get(key_field)
        # 如果没有找到主键，则跳过当前干员
        if not agent_key:
            continue
            
        agent_data = {}
        # 根据转换规则映射属性到新的字段
        for new_key, transfer_rule in d_transfer.items():
            # 跳过主键字段的规则，因为主键已经单独处理
            if new_key == "__key__":
                continue
                
            # 如果转换规则以反斜杠开头，则表示需要调用函数进行处理
            if transfer_rule.startswith('\\'):
                # 提取函数名和参数列表
                func_match = re.match(r'\\(\w+)\(([^)]*)\)', transfer_rule)
                if not func_match:
                    raise ValueError(f"Invalid function format: {transfer_rule}")
                    
                func_name = func_match.group(1)
                # 将参数字符串按逗号分割并去除空格
                arg_names = [a.strip() for a in func_match.group(2).split(',')]
                
                # 根据参数名从属性中获取参数值
                arg_values = []
                for arg in arg_names:
                    if arg not in attrs:
                        raise KeyError(f"Attribute {arg} not found for agent {agent_key}")
                    arg_values.append(attrs[arg])
                
                # 在函数字典中查找并调用对应的处理函数
                if func_name not in d_func:
                    raise KeyError(f"Function {func_name} not found in d_func")
                agent_data[new_key] = d_func[func_name](*arg_values)
                
            # 如果转换规则不是函数调用，则直接进行属性映射
            else:
                if transfer_rule not in attrs:
                    raise KeyError(f"Attribute {transfer_rule} not found for agent {agent_key}")
                agent_data[new_key] = attrs[transfer_rule]
                
        # 将当前干员的数据字典添加到结果字典中
        agents_dict[agent_key] = agent_data
        
    return agents_dict

# 示例使用方式
if __name__ == "__main__":
    # 示例处理函数
    def add_3(a, b, c):
        return [a + "干员", b] + c.split(" ")

    def check(method):
        if "公开招募" in method:
            return 1
        return 0
    
    # 示例转换规则
    d_func = {"add_3": add_3, "check": check}
    d_transfer = {
        "__key__": "data-zh",
        "en": "data-en",
        "star": "data-rarity",
        "tag": '\\add_3(data-profession, data-position, data-tag)',
        "subprofession": "data-subprofession",
    }

    d_transfer = {
        "__key__": "data-zh",
        "obtain_method": '\\check(data-obtain_method)',
        "star": "data-rarity",
        "tag": '\\add_3(data-profession, data-position, data-tag)',
    }
    
    # 加载HTML内容
    with open(_path, "r", encoding="utf-8") as f:
        html_content = f.read()
    
    # 提取干员信息
    agents_data = extract_agents(html_content, d_transfer, d_func)
    from pprint import pprint as print
    print(agents_data, width = 150)
    print(len(agents_data))