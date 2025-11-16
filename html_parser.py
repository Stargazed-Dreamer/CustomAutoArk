_path = ".\\a.html"

import re

def extract_agents(html_content, d_transfer, d_func):
    # 正则表达式匹配干员信息div
    pattern = r'<div\b([^>]*?data-zh="[^"]*"[^>]*)>'
    matches = re.findall(pattern, html_content)
    
    agents_dict = {}
    key_field = d_transfer["__key__"]
    
    for attrs_str in matches:
        # 提取所有属性键值对
        attr_pattern = r'(\bdata-[\w-]+)\s*=\s*"([^"]*)"'
        attrs = dict(re.findall(attr_pattern, attrs_str))
        
        if not attrs:
            continue
            
        # 获取干员主键（中文名）
        agent_key = attrs.get(key_field)
        if not agent_key:
            continue
            
        agent_data = {}
        for new_key, transfer_rule in d_transfer.items():
            if new_key == "__key__":
                continue
                
            # 处理函数调用
            if transfer_rule.startswith('\\'):
                # 提取函数名和参数
                func_match = re.match(r'\\(\w+)\(([^)]*)\)', transfer_rule)
                if not func_match:
                    raise ValueError(f"Invalid function format: {transfer_rule}")
                    
                func_name = func_match.group(1)
                arg_names = [a.strip() for a in func_match.group(2).split(',')]
                
                # 获取参数值
                arg_values = []
                for arg in arg_names:
                    if arg not in attrs:
                        raise KeyError(f"Attribute {arg} not found for agent {agent_key}")
                    arg_values.append(attrs[arg])
                
                # 调用处理函数
                if func_name not in d_func:
                    raise KeyError(f"Function {func_name} not found in d_func")
                agent_data[new_key] = d_func[func_name](*arg_values)
                
            # 直接属性映射
            else:
                if transfer_rule not in attrs:
                    raise KeyError(f"Attribute {transfer_rule} not found for agent {agent_key}")
                agent_data[new_key] = attrs[transfer_rule]
                
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