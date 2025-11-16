from data import data as DATA

class Test:
    def cosine_similarity(self, s1, s2):
        if s1 == "" or s2 == "":
            return 0
        s1 = s1.lower()
        s2 = s2.lower()
        if s1 == s2:
            return 1
        if s1[:3] == "new":
            s1 = s1[3:]
        if s2[:3] == "new":
            s2 = s2[3:]
        # 创建字符频率向量
        chars = list(set(s1 + s2))
        v1 = [s1.count(c) for c in chars]
        v2 = [s2.count(c) for c in chars]
        
        # 计算点积和向量长度
        dot_product = sum(a * b for a, b in zip(v1, v2))
        norm1 = sum(a * a for a in v1) ** 0.5
        norm2 = sum(b * b for b in v2) ** 0.5
        result = dot_product / (norm1 * norm2) if norm1 * norm2 > 0 else 0.0
        #print(f"余弦相似度: {s1}, {s2}, {result}")
        return result

    def getHistory(self):
        """识别历史记录中的干员，返回列表及检查标志。"""
        """
        识别结果中的'NEW!'和' (6★)'内容需要及时去除
        主要输出应当是一个列表，按图片从上到下的顺序排列所有干员
        检查顺序排列后所有结果的垂直间距
        在高度为1080 px的图片中（输入图片尺寸可能不同，但比例一致），上下两行的正常间距是60 px，由于识别误差，在处理时需要将纵坐标四舍五入到十位取整计算，并且允许多或者少10 px
        有' (6★)'内容的干员应当在self.l_agents中检查名字和星级是否一致（DATA.l_agent[name]["star"]）
        每个干员应当在self.l_agents中检查是否存在
        以上所有检查只要有错误，输出标志就应当为False
        结果列表元素最多十个，最少一个
        输出示例：return ['芙蓉', '泡泡 ', '桃金娘', '米格鲁'], False
        """
        # 获取OCR结果
        l_result = [[[[236.0, 39.0], [303.0, 39.0], [303.0, 78.0], [236.0, 78.0]], ('地灵', 0.9998143911361694)], [[[239.0, 101.0], [302.0, 101.0], [302.0, 135.0], [239.0, 135.0]], ('寒檀', 0.9998079538345337)], [[[252.0, 160.0], [290.0, 160.0], [290.0, 196.0], [252.0, 196.0]], ('砾', 0.99907386302948)], [[[122.0, 221.0], [337.0, 224.0], [336.0, 257.0], [121.0, 254.0]], ('NEW!左乐 (6★)', 0.9443714618682861)], [[[237.0, 280.0], [304.0, 280.0], [304.0, 314.0], [237.0, 314.0]], ('维荻', 0.9854839444160461)], [[[238.0, 342.0], [303.0, 342.0], [303.0, 376.0], [238.0, 376.0]], ('慕斯', 0.9991408586502075)], [[[238.0, 402.0], [303.0, 402.0], [303.0, 437.0], [238.0, 437.0]], ('暗索', 0.9996955394744873)], [[[252.0, 460.0], [290.0, 460.0], [290.0, 497.0], [252.0, 497.0]], ('砾', 0.9989297986030579)], [[[237.0, 520.0], [303.0, 520.0], [303.0, 558.0], [237.0, 558.0]], ('泡泡', 0.9993722438812256)], [[[225.0, 584.0], [317.0, 584.0], [317.0, 616.0], [225.0, 616.0]], ('安赛尔', 0.9984970092773438)]]
        processed_entries = []
        flag = True
        height = 1080

        # 遍历OCR结果中的每个识别区域
        for word_info in l_result:
            # 解析坐标和文本
            box = word_info[0]
            text = word_info[1][0]
            # 提取左上角的y坐标作为垂直位置
            y = box[0][1]
            
            # 去除'NEW!'和星级标记
            name = text
            for x in ["NEW!", " (6★)"]:
                name = name.strip(x)
            if " (6★)" == text[-5:]:
                star = 6
            else:
                star = None

            possibleName = name
            maxSimilarity = 0
            for t_agent in DATA.l_agent:
                for name in t_agent:
                    similarity = self.cosine_similarity(possibleName, name)
                    if similarity > maxSimilarity:
                        maxSimilarity = similarity
                        bestResult = t_agent
            if maxSimilarity > 0.9:
                name = bestResult[0]
            else:
                name = possibleName
            print(f"处理文本: {text} -> {name}, y坐标: {y}, 星级: {star}")
            
            # 检查干员是否存在及星级匹配
            if name not in DATA.d_agent:
                print(f"干员不存在: {name}")
                flag = False
            # 验证星级
            if star is not None and star != int(DATA.d_agent[name]["star"])+1:
                print(f"星级不匹配: {name} 标记为{star}星，实际为{int(DATA.d_agent[name]['star'])+1}星")
                flag = False
            
            # 记录处理后的条目
            processed_entries.append({'y': y, 'name': name})
        
        # 按y坐标排序条目（从上到下）
        sorted_entries = sorted(processed_entries, key=lambda a: a['y'])
        print(f"排序后的条目: {sorted_entries}")
        
        # 检查垂直间距是否符合要求
        prev_rounded_y = None
        expected_delta = 60/1080*height
        print(f"期望的垂直间距: {expected_delta:.2f}±10")
        
        for entry in sorted_entries:
            rounded_y = round(entry['y'] / 10) * 10  # 四舍五入到十位
            if prev_rounded_y is not None:
                delta = rounded_y - prev_rounded_y
                print(f"检查间距: {entry['name']} 与上一个条目间距为 {delta:.2f}")
                if not ((60/1080*height - 10) <= delta <= (60/1080*height + 10)):
                    print(f"间距不符合要求: {delta:.2f}")
                    flag = False
            prev_rounded_y = rounded_y
        
        # 生成结果列表（最多10个元素）
        result_list = [entry['name'] for entry in sorted_entries]
        if not (1 <= len(result_list) <= 10):
            print(f"结果数量不符合要求: {len(result_list)}")
            flag = False
        
        print(f"最终结果: {result_list}, 检查标志: {flag}")
        return result_list, flag

test = Test()
print(test.getHistory())