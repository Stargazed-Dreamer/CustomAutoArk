import traceback

import cv2
import numpy as np
from paddleocr import PaddleOCR

from data import data as DATA
from log import log_manager as log



region_tag = (0.30,0.47,0.66,0.70)
#急招数据临时处理↓
#region_tag = (0,0,1,1)
region_agent = (0.45, 0.67, 0.87, 0.85)
#急招数据临时处理↓
#region_agent = (0.255, 0.45,1,1)
region_history = (0.44, 0.27, 0.71, 0.91)

def _get_filename(path):
    # 找到最后一个 '/' 或 '\' 的位置
    last_slash_pos = -1
    for i in range(len(path)):
        if path[i] == '/' or path[i] == '\\':
            last_slash_pos = i
    
    # 如果没有找到分隔符，返回整个路径
    if last_slash_pos == -1:
        return path
    
    # 返回分隔符后面的部分
    return path[last_slash_pos + 1:]
#========================================
def error_record(e):
    tb = e.__traceback__
    if tb:
        # extract_tb 列表的最后一个元素就是错误发生的源头
        error_frame_summary = traceback.extract_tb(tb)[-1]
        filename = error_frame_summary.filename
        lineno = error_frame_summary.lineno
        
        log.log(str(e), "ERROR", filename, lineno)
    else:
        log.log(str(e), "ERROR")

class Tool:
    def __init__(self):
        """
        初始化工具类
        """
        self.ocrUseable = False

    def init_ocr(self):
        self.ocr_ch = PaddleOCR()
        """
        try:
            # 首先尝试使用GPU
            self.ocr_ch = PaddleOCR(use_gpu=True)
            log.debug("使用GPU模式初始化OCR")
        except RuntimeError as e:
            if "cudnn64_8.dll" in str(e):
                # CUDA/CUDNN加载失败，切换到CPU模式
                log.warning("GPU初始化失败，切换到CPU模式")
                self.ocr_ch = PaddleOCR(use_gpu=False)
            else:
                # 其他RuntimeError，继续抛出
                raise
        except Exception as e:
            # 其他异常，继续抛出
            raise
        """
        self.ocrUseable = True

    def ocr(self, cvImg):
        """
        调用百度OCR接口进行文字识别
        Args:
            cvImg: OpenCV格式的图片
        Returns:
            #[[[[[764.0, 179.0], [1708.0, 179.0], [1708.0, 355.0], [764.0, 355.0]], ('ERATOR', 0.981677234172821)], [[[344.0, 216.0], [534.0, 216.0], [534.0, 250.0], [344.0, 250.0]], ('重复任命转化', 0.9992479681968689)], [[[324.0, 878.0], [566.0, 878.0], [566.0, 939.0], [324.0, 939.0]], ('任命完成', 0.9980717897415161)], [[[1572.0, 893.0], [1686.0, 893.0], [1686.0, 955.0], [1572.0, 955.0]], ('确认', 0.9997517466545105)], [[[324.0, 947.0], [1062.0, 947.0], [1062.0, 975.0], [324.0, 975.0]], ('*任命到的干员若为未持有干员，将只能作为助战干员加入战备', 0.9936957955360413)]]]
            
            [  #总结果
                [ #第一组结果
                    [ #第一个结果
                        [764.0, 179.0], [1708.0, 179.0], [1708.0, 355.0], [764.0, 355.0],  # 矩形顶点
                        ('ERATOR', 0.981677234172821) # 文字识别结果
                    ],
                    [ #第二个结果
                        [344.0, 216.0], [534.0, 216.0], [534.0, 250.0], [344.0, 250.0],
                        ('重复任命转化', 0.9992479681968689)
                    ],
                    ……
                ]
            ]
        """

        if not self.ocrUseable:
            self.init_ocr()
        retry = 3
        b_ocrSuccess = False
        while retry >= 0:
            result = self.ocr_ch.ocr(cvImg, cls=True)
            """
            log.debug(f"ocr结果: {result}")
            for l in result:
                if l is None:
                    continue
                for x in l:
                    log.debug(f"ocr结果: {x}")
            #"""
            if result[0] is not None:
                b_ocrSuccess = True
                break
            log.debug(f"ocr失败, 剩余重试次数: {retry}")
            retry -= 1
        if b_ocrSuccess:
            return result[0]
        #raise OcrError(f"ocr失败")
        return []

    def find_smallRegionsOnImg(self, image):
        """
        找出并裁剪UI图片中的按钮区域，结合颜色识别和边缘检测
        Args:
            image: OpenCV格式的图片(BGR)
        Returns:
            list of dict: 包含裁剪图像和位置信息的字典列表
        """
        # 保存原始图像副本用于最终裁剪
        # original = image.copy()
        
        # 1. 颜色识别部分
        # 转换到HSV空间
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        
        # 定义目标颜色 #313131 的HSV范围
        # 增大颜色容差范围
        lower = np.array([0, 0, 30])  # 更宽松的下限
        upper = np.array([180, 30, 80])  # 更宽松的上限
        
        # 创建颜色掩码
        color_mask = cv2.inRange(hsv, lower, upper)
        
        # 2. 边缘检测部分
        # 转换为灰度图
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # 高斯模糊减少噪声
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Canny边缘检测（调整阈值）
        edges = cv2.Canny(blurred, 30, 100)  # 降低阈值使边缘更容易被检测
        
        # 3. 组合颜色掩码和边缘
        # 膨胀边缘使其更容易形成闭合区域
        dilated_edges = cv2.dilate(edges, None, iterations=3)  # 增加膨胀次数
        
        # 合并颜色掩码和边缘
        combined_mask = cv2.bitwise_or(color_mask, dilated_edges)  # 使用or而不是and
        
        # 4. 形态学处理
        kernel = np.ones((3,3), np.uint8)  # 减小核的大小
        mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
        
        # 5. 查找轮廓
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        # 存储裁剪后的图像信息
        #cropped_regions = []
        # 存储裁剪后的图像
        l_output = []
        
        # 6. 处理每个轮廓
        for contour in contours:
            # 计算轮廓面积
            area = cv2.contourArea(contour)
            
            # 获取最小外接矩形
            rect = cv2.minAreaRect(contour)
            box = cv2.boxPoints(rect)
            box = np.intp(box)
            
            # 计算矩形的宽高比
            width = rect[1][0]
            height = rect[1][1]
            aspect_ratio = max(width, height) / min(width, height)
            
            # 根据面积和宽高比筛选
            #if area > 100 and aspect_ratio < 5:  # 根据实际情况调整阈值
            if area > 0.05*image.shape[0]*image.shape[1]:  # 暂时只用面积过滤
                x, y, w, h = cv2.boundingRect(contour)
                
                # 稍微扩大裁剪区域，确保不会裁掉边缘
                padding = 2
                x = max(0, x - padding)
                y = max(0, y - padding)
                w = min(image.shape[1] - x, w + 2*padding)
                h = min(image.shape[0] - y, h + 2*padding)
                
                # 裁剪图像
                l_output.append(self.cropping(image, (x,y,w,h), format="x, y, w, h"))
                """
                # 存储结果
                cropped_regions.append({
                    'image': cropped,
                    'position': (x, y, w, h),
                    'area': area,
                    'aspect_ratio': aspect_ratio
                })
                """
        return l_output

    def find_imgOnImg(self, mainImg, template, match_threshold=0.7, scales=np.linspace(0.8, 1.2, 5), nms_threshold=0.4, b_needTemplate2GRAY = True):
        """
        图片匹配函数，支持多尺度和非极大值抑制
        
        参数:
        mainImg: numpy.ndarray - BGR格式的屏幕截图（h, w, 3）
        template: numpy.ndarray - BGR格式的模板图片（h, w, 3）
        match_threshold: float - 匹配置信度阈值（默认0.7）
        scales: list - 缩放比例列表（默认[0.8, 0.9, 1.0, 1.1, 1.2]）
        nms_threshold: float - NMS重叠阈值（默认0.4）
        
        返回:
        list - [([x1,y1,x2,y2], confidence), ...]
        """
        
        # 转换为灰度图
        mainImg_gray = cv2.cvtColor(mainImg, cv2.COLOR_BGR2GRAY)
        if b_needTemplate2GRAY:
            template_gray = cv2.cvtColor(template, cv2.COLOR_BGR2GRAY)
        else:
            template_gray = template
        
        t_h, t_w = template_gray.shape
        s_h, s_w = mainImg_gray.shape
        
        matches = []
        
        # 多尺度匹配
        for scale in scales:
            # 计算缩放后模板尺寸
            scaled_w = int(t_w * scale)
            scaled_h = int(t_h * scale)
            
            # 跳过无效尺寸
            if scaled_w < 5 or scaled_h < 5 or scaled_w > s_w or scaled_h > s_h:
                continue
                
            # 调整模板尺寸
            resized = cv2.resize(template_gray, (scaled_w, scaled_h), 
                               interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_CUBIC)
            
            # 模板匹配
            result = cv2.matchTemplate(mainImg_gray, resized, cv2.TM_CCOEFF_NORMED)
            
            # 获取匹配结果
            loc = np.where(result >= match_threshold)
            for pt in zip(*loc[::-1]):  # 交换x,y坐标
                x1, y1 = pt
                x2, y2 = x1 + scaled_w, y1 + scaled_h
                confidence = result[y1, x1]  # 注意numpy数组的行列顺序
                matches.append(([x1, y1, x2, y2], float(confidence)))
        
        # 非极大值抑制
        if not matches:
            return []
        
        boxes = np.array([m[0] for m in matches])
        confidences = np.array([m[1] for m in matches])
        
        # 使用OpenCV的NMS实现
        indices = cv2.dnn.NMSBoxes(
            boxes.reshape(-1, 4).tolist(),
            confidences.tolist(),
            score_threshold=match_threshold,
            nms_threshold=nms_threshold
        )
        
        # 处理OpenCV版本差异
        if len(indices) > 0:
            indices = indices.flatten() if hasattr(indices, 'flatten') else indices[:, 0]
        else:
            return []
        
        final_matches = [matches[i] for i in indices]
        # 返回排序后的结果（按置信度降序）
        final_matches.sort(key=lambda x: -x[1])
        
        return final_matches

    def cropping(self, cvImg, region, mode="pixel", format = "x1, y1, x2, y2"):
        """
        裁剪图片大小到指定区域，支持显示缩放
        Args:
            cvImg:  图片数组
            region: 一个四元数组，内容取决于format参数，如：x, y, w, h -> (x, y, width【图片相对大小】, height【图片相对大小】) 相对于窗口的坐标和大小
            mode: "pixel" 表示以像素为单位，"percent" 表示以百分比为单位
            format: "x, y, w, h" | 1   或者   "x1, y1, x2, y2" | 2
        """
        a, b, c, d = region
        if format == 1 or format == "x, y, w, h":
            x1, y1, x2, y2 = a, b, a+c, b+d
        elif format == 2 or format == "x1, y1, x2, y2":
            x1, y1, x2, y2 = a, b, c, d
        else:
            ValueError(f"'{format}'格式不是合法的值")
        if mode == "percent":
            shape = cvImg.shape #(height, width, channels)
            x1, y1, x2, y2 = shape[1]*a, shape[0]*b, shape[1]*c, shape[0]*d
        elif mode == "pixel":
            "Good"
        else:
            ValueError(f"'{mode}'处理模式不是合法的值")
        x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)
        # 确保裁剪区域有效
        if x1 >= x2 or y1 >= y2:
            raise ValueError(f"裁剪区域无效，起始坐标 {(x1, y1)} 必须小于结束坐标 {(x2, y2)}")
        if x1 < 0 or x2 < 0 or y1 < 0 or y2 < 0:
            raise ValueError(f"裁剪区域无效，坐标 {(x1, y1)} 或坐标 {(x2, y2)} 中有负数")
        log.img(cvImg[y1:y2, x1:x2])
        return cvImg[y1:y2, x1:x2]

    def showImg(self, img):
        cv2.imshow("picture", img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

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
        #log.debug(f"余弦相似度: {s1}, {s2}, {result}")
        return result

    def find_centerOnResult(self, result, mode=None):
        """
        mode 是输入坐标的表示方法
        1: x1, x2, y1, y2
        2: x1, y1, x2, y2
        3: paddle [[左上, 右上, 右下, 左下], (name, threshold)]
        4: x, y, w, h
        """
        if mode is None:
            raise ValueError("必须填入mode！")
        log.debug(f"找中心: {result}")
        if result is None:
            raise CantFindNameError(f"找不到None的中心!")
        l_coordinate = result[0]

        if mode == 1 or mode == "x1, x2, y1, y2":
            x1, x2, y1, y2 = l_coordinate
        elif mode == 2 or mode == "x1, y1, x2, y2":
            x1, y1, x2, y2 = l_coordinate
        elif mode == 3 or mode == "paddle":
            x1, y1 = l_coordinate[0]
            x2, y2 = l_coordinate[2]
        elif mode == 4 or mode == "x, y, w, h":
            x, y, w, h = l_coordinate
            x1, y1 = x, y
            x2, y2 = x + w, y + h
        else:
            raise ValueError("无效的mode值！")

        # 计算中心点
        center_x = (x1 + x2) // 2
        center_y = (y1 + y2) // 2

        return (center_x, center_y)

    def find_nameOnResult(self, l_result, t_name, mode="result", sameOnly=False, includeSimilarity=False):
        #mode : result or src
        def returnResult(result, similarity = 1):
            if mode == "result":
                output = result
            elif mode == "src":
                output = returnItem
            else:
                raise NameError(f"mode 必须是 result 或者 src, 而不是'{mode}'")
            if includeSimilarity:
                output = (output, similarity)
            log.debug(f"返回结果：{output}，相似度：{similarity}")
            return output
        returnItem = t_name
        if isinstance(t_name, str):
            t_name = (t_name,)
        elif not isinstance(t_name, tuple):
            raise ValueError(f"t_name必须是字符串或元组，当前类型为{type(t_name)}")
        
        #log.debug(f"开始查找名称：{t_name}，模式：{mode}，是否仅完全匹配：{sameOnly}")
        
        #全字匹配
        #log.debug("开始进行全字匹配...")
        for result in l_result:
            for name in t_name:
                if result[1][0] == name:
                    #log.debug(f"找到完全匹配：{result} -> {name}")
                    return returnResult(result)
        
        if sameOnly:
            log.debug("仅完全匹配模式，未找到匹配项，返回None")
            return None
            
        #余弦相似匹配
        #log.debug("开始进行余弦相似度匹配...")
        maxCosine = -1
        bestResult = None
        for result in l_result:
            for name in t_name:
                similarity = self.cosine_similarity(name, result[1][0])
                #log.debug(f"计算余弦相似度：{name} 与 {result[1][0]} 的相似度为 {similarity}")
                if similarity > maxCosine and similarity > 0.5:
                    #log.debug(f"找到更好的匹配：{result[1][0]}，相似度：{similarity}")
                    maxCosine = similarity
                    bestResult = result
        if maxCosine > 0.5 and bestResult is not None:
            #log.debug(f"使用余弦相似度匹配结果：{bestResult[1][0]}，最终相似度：{maxCosine}")
            return returnResult(bestResult, maxCosine)
            
        #不完全匹配
        #log.debug("开始进行不完全匹配...")
        for result in l_result:
            for name in t_name:
                if name in result[1][0]:
                    #log.debug(f"找到子串匹配：{name} 在 {result[1][0]} 中")
                    return returnResult(result, 0.01)
                        
        #log.debug(f"未找到任何匹配项：{t_name}")
        return None

    def getTag(self, img):
        img = self.cropping(img, region_tag, mode="percent")
        l_buttons = self.find_smallRegionsOnImg(img)
        log.debug(f"找到的按钮: {len(l_buttons)}个")
        l_tag = []
        for img in l_buttons:
            l_result = self.ocr(img)
            if l_result is None:
                continue
            for tag in DATA.l_tag:
                t_result = self.find_nameOnResult(l_result, tag, mode="src", sameOnly=False, includeSimilarity=True)
                if t_result is not None:
                    log.debug(f"{tag}匹配ocr的结果: {l_result} -> {t_result}")
                    l_tag.append(t_result)
        log.info(f"所有匹配的ocr结果: {l_tag}")
        #取相似度最高的5个
        return [t_result[0] for t_result in sorted(l_tag, key=lambda x: x[1], reverse=True)[:5]]

    def getAgent(self, img):
        img = self.cropping(img, region_agent, mode="percent")
        l_result = self.ocr(img)
        if not l_result:
            return None
        # 0.结果预处理
        limit = 10
        # 0.0.检测是否是矩形
        tL = []
        for result in l_result:
            # left, right, top, bottom 排列组合：[左上,右上,右下,左下]
            lt, rt, rb, lb = result[0]
            # 四个角都要对上
            if  (   abs(int(lt[0]) - int(lb[0])) <= limit
                and abs(int(rt[0]) - int(rb[0])) <= limit
                and abs(int(lt[1]) - int(rt[1])) <= limit
                and abs(int(lb[1]) - int(rb[1])) <= limit
            ):
                tL.append(result)
        l_result = tL
        # 0.1.连接断开的字段
        # 0.1.0.分组
        l_group = []
        offset = 0
        for i in range(len(l_result)):
            # 这个识别结果的坐标
            i = i - offset
            coor = l_result[i][0]
            new_top = coor[0][1]
            new_bottom = coor[2][1]
            b_managed = False
            for group in l_group:
                # 组的第一个组员的坐标
                coor = group[0][0]
                top = coor[0][1]
                bottom = coor[2][1]
                # 二者坐标是否接近
                if (top-limit < new_top < top+limit) and (bottom-limit < new_bottom < bottom+limit):
                    group.append(l_result.pop(i))
                    offset += 1
                    b_managed = True
                    break
            # 找不到相似的组，则创建新组
            if not b_managed:
                l_group.append([l_result[i]])
        # 0.1.1.合并
        for group in l_group:
            if len(group) == 1:
                l_result.append(group[0])
                continue
            group = group.sort(key=lambda x: x[0][0][0])
            # 计算坐标
            top = min([x[0][0][1] for x in group])
            bottom = max([x[0][2][1] for x in group])
            left = group[0][0][0][0]
            right = group[-1][0][0][0]
            coor = [
                [left, top],
                [right, top],
                [right, bottom],
                [left, bottom]
            ]
            # 合并字段
            s = "".join([x[1][0] for x in group])
            # 平均置信度
            confidence = sum([x[1][1] for x in group]) / len(group)
            # 添加合并结果
            l_result.append([coor, (s, confidence)])
        # 1.先对所有OCR结果进行计数，看看谁匹配上的干员名称多
        d_acceptName = {}
        for t_agent in DATA.l_agent:
            # result是一个(OCR结果, 匹配度)的元组 或者 None
            result = self.find_nameOnResult(l_result, t_agent, includeSimilarity=True)
            if result is None:
                continue
            result, similarity = result
            if similarity == 1:
                d_acceptName = {result[1][0]: 1}
                break
            # result是一个OCR结果，格式是[ [左上,右上,右下,左下], (识别的文字, 置信度) ]
            if similarity > 0.7:
                # result[1][0]是最匹配当前干员的OCR文字段
                if result[1][0] not in d_acceptName:
                    d_acceptName[result[1][0]] = 1
                else:
                    d_acceptName[result[1][0]] += 1
        if d_acceptName == {}:
            return None
        # 2.再看匹配最多的那个结果和哪个干员最匹配
        possibleName = max(d_acceptName, key=d_acceptName.get)
        maxSimilarity = -1
        bestResult = None
        for t_agent in DATA.l_agent:
            for name in t_agent:
                similarity = self.cosine_similarity(possibleName, name)
                if similarity > maxSimilarity:
                    maxSimilarity = similarity
                    bestResult = t_agent
        log.info(f"最大相似度: {maxSimilarity}, 最佳结果: {bestResult}")
        # 结果处理并返回
        if maxSimilarity > 0.5 and bestResult is not None:
            l_zh = [t_name[0] for t_name in DATA.l_agent]
            l_en = [t_name[1] for t_name in DATA.l_agent]
            name = bestResult[0]
            if name in l_en:
                return l_zh[l_en.index(name)]
            return name
        return None

    def getHistory(self, img):
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
        flag = True
        height = img.shape[0]
        log.debug(f"开始处理历史记录图片，图片高度: {height}")
        
        img = self.cropping(img, region_history, mode="percent")
        # 获取OCR结果
        l_result = self.ocr(img)
        log.debug(f"OCR识别结果: {l_result}")
        if l_result is None:
            return [], False
        
        # 第一次识别
        processed_entries = []
        for word_info in l_result:
            entry = self.process_ocr_entry(word_info)
            if entry is None:
                continue
            processed_entries.append(entry)
        
        # 按y坐标排序条目（从上到下）
        sorted_entries = sorted(processed_entries, key=lambda a: a['y'])
        log.debug(f"排序后的条目: {sorted_entries}")
        
        #####
        # 检查垂直间距是否符合要求
        expected_delta = 60/1080*height
        prev_rounded_y = None
        log.debug(f"期望的垂直间距: {expected_delta:.2f}±10")

        for entry in sorted_entries:
            rounded_y = round(entry['y'] / 10) * 10
            if prev_rounded_y is not None:
                delta = rounded_y - prev_rounded_y
                log.debug(f"检查间距: {entry['name']} 与上一个条目间距为 {delta:.2f}")
                if not ((expected_delta - 10) <= delta <= (expected_delta + 10)):
                    log.debug(f"间距不符合要求: {delta:.2f}")
            prev_rounded_y = rounded_y
        #####
        
        # 第二次识别：间距重新切割处理
        h, w = img.shape[:2]
        
        # 计算平均间距（排除异常值）
        deltas = []
        legalIndex = [0]
        for i in range(1, len(sorted_entries)):
            delta = sorted_entries[i]['y'] - sorted_entries[i-1]['y']
            if (expected_delta - 10) <= delta <= (expected_delta + 10):
                deltas.append(delta)
                legalIndex.append(i-1)
        avg_delta = int(sum(deltas)/len(deltas) if deltas else expected_delta)
        log.debug(f"平均间距为 {avg_delta}")

        # 求出某个符合条件的中间位置
        middle_x = (sorted_entries[legalIndex[0]]['y2'] + sorted_entries[legalIndex[0]+1]['y']) // 2
        # 据此定位第一行起始
        y_start = middle_x - (legalIndex[0]+1) * avg_delta

        # 切割并处理每个行块
        new_processed_entries = []
        for i in range(10):
            current_y_start = y_start + avg_delta*i
            if current_y_start < 11:
                current_y_start = 11
            # +10和-10是保护性的
            row_img = self.cropping(img, (0, current_y_start-10, w, current_y_start + avg_delta+10), mode="pixel")
            l_result_row = self.ocr(row_img)
            if l_result_row is None:
                continue
            for word_info in l_result_row:
                entry = self.process_ocr_entry(word_info, y_offset = current_y_start)
                if entry is None:
                    continue
                new_processed_entries.append(entry)

        # 更新排序后的条目
        sorted_entries = sorted(new_processed_entries, key=lambda a: a['y'])
                
        # 检查干员存在性和星级
        for entry in sorted_entries:
            name = entry['name']
            star = entry.get('star')
            if name not in DATA.d_agent:
                log.debug(f"干员不存在: {name}")
                flag = False
            if star is not None and star != int(DATA.d_agent[name]["star"])+1:
                log.debug(f"星级不匹配: {name} 标记为{star}星，实际为{DATA.d_agent[name]['star']+1}星")
                flag = False
        
        # 生成结果列表并检查数量
        result_list = [entry['name'] for entry in sorted_entries]
        if not (1 <= len(result_list) <= 10):
            log.debug(f"结果数量不符合要求: {len(result_list)}")
            flag = False
        
        log.debug(f"最终结果: {result_list}, 检查标志: {flag}")
        return result_list, flag

    def process_ocr_entry(self, word_info, y_offset=0):
        """处理单个OCR结果，返回干员信息"""
        box = word_info[0]
        text = word_info[1][0]
        # 根据裁剪位置调整起始y坐标，因为y坐标应当是原始图片的y坐标而不是已裁剪图片的y坐标
        # 顶部y坐标
        y = box[0][1] + y_offset
        # 底部y坐标
        y2 = box[3][1] + y_offset
        
        # 去除'NEW!'和星级标记
        name = text
        for x in ["NEW!", " (6★)"]:
            name = name.strip(x)
        star = 6 if " (6★)" in text else None
        
        # OCR稳定识别错误校正
        d_ocrERROR = {
            "子": "孑",
            "罗比塔": "罗比菈塔",
            "深定": "深靛"
        }
        if name in d_ocrERROR:
            name = d_ocrERROR[name]

        if name == "":
            return None
        
        # 名称相似度匹配
        possibleName = name
        max_similarity = 0
        best_match = None
        for agent in DATA.l_agent:
            for alias in agent:
                similarity = self.cosine_similarity(possibleName, alias)
                if similarity > max_similarity:
                    max_similarity = similarity
                    best_match = agent[0]  # 标准名称在首位
        if max_similarity > 0.9:
            name = best_match
        
        log.debug(f"处理文本: {text} -> {name}, y坐标: {y}, 星级: {star}")
        return {'y': y, 'name': name, 'star': star, 'y2': y2}

tool = Tool()