import inspect
import os
import socket
import subprocess
import time
import threading
from enum import Enum
from typing import Optional, Tuple

import cv2
import numpy as np
from paddleocr import PaddleOCR
from PySide6.QtCore import QObject, Signal, Slot

from data_manager import data_manager
from log import log_manager
from data import data as DATA
#==============================
ADB_PATH = "D:\\YXArkNights-12.0\\shell\\adb.exe"
IMG_PATH = ".\\img"
region_tag = (0.30,0.47,0.66,0.70)
region_agent = (0.45, 0.67, 0.87, 0.85)
region_history = (0.44, 0.27, 0.71, 0.91)
#==============================
class CantFindNameError(Exception):
    pass

class MouseMoveError(Exception):
    pass

class OcrError(Exception):
    pass

class UserSuspendOperationError(InterruptedError):
    pass

class StopError(Exception):
    pass
#==============================
# 使用全局日志管理器
log = log_manager

LOCK = threading.Lock()
#======================================
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
        raise OcrError(f"ocr失败")

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
        #mode : result or name
        def returnResult(result, similarity = 1):
            if mode == "result":
                output = result
            else:
                output = returnItem
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
                    returnItem = t_name
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
            for tag in DATA.l_tag:
                t_result = self.find_nameOnResult(l_result, tag, sameOnly=False, includeSimilarity=True)
                log.debug(f"{tag}匹配ocr的结果: {t_result}")
                if t_result is not None:
                    l_tag.append(t_result)
        log.info(f"所有匹配的ocr结果: {l_tag}")
        #取相似度最高的5个
        return [t_result[0][1][0] for t_result in sorted(l_tag, key=lambda x: x[1], reverse=True)[:5]]

    def getAgent(self, img):
        img = self.cropping(img, region_agent, mode="percent")
        l_result = self.ocr(img)
        d_acceptName = {}
        for t_agent in DATA.l_agent:
            result = self.find_nameOnResult(l_result, t_agent)
            if result is not None:
                if result[1][0] not in d_acceptName:
                    d_acceptName[result[1][0]] = 1
                else:
                    d_acceptName[result[1][0]] += 1
        if d_acceptName == {}:
            return None
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
        
        processed_entries = []

        # 遍历OCR结果中的每个识别区域
        for line in l_result:
            for word_info in line:
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
                
                log.debug(f"处理文本: {text} -> {name}, y坐标: {y}, 星级: {star}")
                
                # 检查干员是否存在及星级匹配
                if name not in DATA.d_agent:
                    log.debug(f"干员不存在: {name}")
                    flag = False
                # 验证星级
                if star is not None and star != DATA.d_agent[name]["star"]:
                    log.debug(f"星级不匹配: {name} 标记为{star}星，实际为{DATA.d_agent[name]['star']}星")
                    flag = False
                
                # 记录处理后的条目
                processed_entries.append({'y': y, 'name': name})
        
        # 按y坐标排序条目（从上到下）
        sorted_entries = sorted(processed_entries, key=lambda a: a['y'])
        log.debug(f"排序后的条目: {sorted_entries}")
        
        # 检查垂直间距是否符合要求
        prev_rounded_y = None
        expected_delta = 60/1080*height
        log.debug(f"期望的垂直间距: {expected_delta:.2f}±10")
        
        for entry in sorted_entries:
            rounded_y = round(entry['y'] / 10) * 10  # 四舍五入到十位
            if prev_rounded_y is not None:
                delta = rounded_y - prev_rounded_y
                log.debug(f"检查间距: {entry['name']} 与上一个条目间距为 {delta:.2f}")
                if not ((60/1080*height - 10) <= delta <= (60/1080*height + 10)):
                    log.debug(f"间距不符合要求: {delta:.2f}")
                    flag = False
            prev_rounded_y = rounded_y
        
        # 生成结果列表（最多10个元素）
        result_list = [entry['name'] for entry in sorted_entries]
        if not (1 <= len(result_list) <= 10):
            log.debug(f"结果数量不符合要求: {len(result_list)}")
            flag = False
        
        log.debug(f"最终结果: {result_list}, 检查标志: {flag}")
        return result_list, flag

tool = Tool()
#==============================
class Simulator:
    def __init__(self, adb_path = ADB_PATH, type = "mumu", resource_dir = "."):
        self.adb_path = adb_path
        self.device_addr = None
        self.minitouch_proc = None
        self.minitouch_socket = None
        self.screen_size = None
        
        self.type = type

        # 设置资源目录
        self.resource_dir = resource_dir
        self._setup_resource_dir()

        # 连接
        self._connected = False
        if not self.ensure_connected():
            raise ConnectionError("无法连接到设备")
        
    def _setup_resource_dir(self):
        """设置资源目录结构"""
        # 创建minitouch目录
        minitouch_dir = os.path.join(self.resource_dir, "minitouch")
        os.makedirs(minitouch_dir, exist_ok=True)
        
        # 创建各架构目录
        archs = ["x86_64", "x86", "arm64-v8a", "armeabi-v7a", "armeabi"]
        for arch in archs:
            os.makedirs(os.path.join(minitouch_dir, arch), exist_ok=True)
        
    def find_adb_path(self):
        """
        查找adb路径
        :return: adb路径或None
        """
        """
        try:
            # 1. 首先尝试从MUMU模拟器注册表项查找
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\NetEase\\MuMuPlayer") as key:
                mumu_path = winreg.QueryValueEx(key, "InstallDir")[0]
                adb_path = os.path.join(mumu_path, "emulator", "nemu", "vmonitor", "bin", "adb.exe")
                if os.path.exists(adb_path):
                    log.info(f"在MUMU模拟器注册表中找到adb: {adb_path}")
                    return adb_path
        except WindowsError:
            log.debug("未在注册表中找到MUMU模拟器")
            
        try:
            # 2. 尝试从Android SDK注册表项查找
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, "SOFTWARE\\Android SDK Tools") as key:
                sdk_path = winreg.QueryValueEx(key, "Path")[0]
                adb_path = os.path.join(sdk_path, "platform-tools", "adb.exe")
                if os.path.exists(adb_path):
                    log.info(f"在Android SDK注册表中找到adb: {adb_path}")
                    return adb_path
        except WindowsError:
            log.debug("未在注册表中找到Android SDK")
            
        # 3. 尝试从环境变量查找
        for path in os.environ["PATH"].split(os.pathsep):
            adb_path = os.path.join(path, "adb.exe")
            if os.path.exists(adb_path):
                log.info(f"在环境变量中找到adb: {adb_path}")
                return adb_path
                
        # 4. 尝试常见安装路径
        common_paths = [
            "C:\\Program Files\\Microvirt\\MEmu\\adb.exe",  # MEmu
            "C:Program FilesNox\\bin\\nox_adb.exe",     # Nox
            "C:Program FilesBlueStacks_nxt\\HD-Adb.exe",  # BlueStacks
            "D:Program FilesMicrovirt\\MEmu\\adb.exe",
            "D:Program FilesNox\\bin\\nox_adb.exe",
            "D:Program FilesBlueStacks_nxt\\HD-Adb.exe",
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                log.info(f"在常见路径中找到adb: {path}")
                return path
        """
        log.error("未找到adb路径")
        return None
    
    def ensure_connected(self):
        """确保设备已连接"""
        if not self._connected:
            try:
                if not self.connect(adb_path=self.adb_path):
                    raise ConnectionError("无法连接到设备")
                self._connected = True
                return True
            except Exception as e:
                log.error(f"设备连接失败: {str(e)}")
                return False
        
        # 检查设备是否仍然连接
        try:
            result = subprocess.run(
                [self.adb_path, "-s", self.device_addr, "shell", "echo", "test"],
                capture_output=True,
                text=True,
                check=True
            )
            if result.stdout.strip() != "test":
                raise ConnectionError("设备连接异常")
            return True
        except Exception as e:
            log.error(f"设备连接丢失: {str(e)}")
            self._connected = False
            self.cleanup()
            return False
        
    def connect(self, adb_path: Optional[str] = None) -> bool:
        """
        连接设备
        :param adb_path: adb路径，如果为None则自动查找
        :return: 是否连接成功
        """
        try:
            # 获取adb路径
            self.adb_path = adb_path or self.find_adb_path()
            if not self.adb_path:
                log.error("未找到adb路径")
                return False
                
            # 启动adb server
            log.info("启动adb server")
            subprocess.run([self.adb_path, "start-server"], check=True)
            
            # 连接设备
            self.device_addr = "127.0.0.1:7555"  # MUMU模拟器默认端口
            log.info(f"连接设备: {self.device_addr}")
            subprocess.run([self.adb_path, "connect", self.device_addr], check=True)
            
            # 获取屏幕大小
            result = subprocess.run(
                [self.adb_path, "-s", self.device_addr, "shell", "wm size"],
                capture_output=True,
                text=True,
                check=True
            )
            size = result.stdout.strip().split()[-1].split("x")
            self.screen_size = (int(size[0]), int(size[1]))
            log.info(f"屏幕大小: {self.screen_size}")
            
            # 获取屏幕方向
            result = subprocess.run(
                [self.adb_path, "-s", self.device_addr, "shell", "dumpsys input | grep SurfaceOrientation"],
                capture_output=True,
                text=True,
                check=True
            )
            self.orientation = 0  # 默认为0度
            if "SurfaceOrientation" in result.stdout:
                self.orientation = int(result.stdout.strip().split()[-1])
            log.info(f"屏幕方向: {self.orientation}度")
            
            # 获取CPU架构
            result = subprocess.run(
                [self.adb_path, "-s", self.device_addr, "shell", "getprop ro.product.cpu.abi"],
                capture_output=True,
                text=True,
                check=True
            )
            cpu_abi = result.stdout.strip()
            log.info(f"设备CPU架构: {cpu_abi}")
            
            # 设置minitouch
            minitouch_dir = os.path.join(self.resource_dir, "minitouch")
            minitouch_path = os.path.join(minitouch_dir, cpu_abi, "minitouch")
            
            if not os.path.exists(minitouch_path):
                log.error(f"找不到minitouch文件: {minitouch_path}")
                return True  # 即使minitouch不存在也返回True，因为可以使用input命令
                
            try:
                # 推送minitouch到设备
                subprocess.run([
                    self.adb_path, "-s", self.device_addr, "push",
                    minitouch_path, "/data/local/tmp/"
                ], check=True)
                
                # 设置权限
                subprocess.run([
                    self.adb_path, "-s", self.device_addr, "shell",
                    "chmod 755 /data/local/tmp/minitouch"
                ], check=True)
                
                # 转发端口
                subprocess.run([
                    self.adb_path, "-s", self.device_addr,
                    "forward", "tcp:1111", "localabstract:minitouch"
                ], check=True)
                
                # 启动minitouch
                self.minitouch_proc = subprocess.Popen([
                    self.adb_path, "-s", self.device_addr, "shell",
                    "/data/local/tmp/minitouch"
                ])
                
                time.sleep(1)  # 等待minitouch启动
                
                if self.minitouch_proc.poll() is not None:
                    raise RuntimeError("minitouch启动失败")
                else:
                    log.info("minitouch启动成功")
                    
            except Exception as e:
                log.error(f"设置minitouch失败: {e}")
                # 清理minitouch相关资源
                self.cleanup()
                
            return True
            
        except Exception as e:
            log.error(f"连接失败: {e}")
            return False
            
    def _convert_coordinates(self, x: int, y: int) -> Tuple[int, int]:
        """
        转换坐标，处理屏幕方向问题
        :param x: 原始x坐标
        :param y: 原始y坐标
        :return: 转换后的坐标
        """
        if not hasattr(self, 'orientation'):
            return x, y
            
        if self.orientation == 0:  # 0度
            return x, y
        elif self.orientation == 1:  # 90度
            return self.screen_size[1] - y, x
        elif self.orientation == 2:  # 180度
            return self.screen_size[0] - x, self.screen_size[1] - y
        elif self.orientation == 3:  # 270度
            return y, self.screen_size[0] - x
        return x, y
            
    def click(self, x, y, press_time = 50):
        """
        点击指定坐标
        :param x: x坐标
        :param y: y坐标
        :param press_time: 按下时间(毫秒)，默认50ms
        :return: 是否点击成功
        """
        try:
            x, y, press_time = int(x), int(y), int(press_time)
        except Exception:
            raise ValueError(f"坐标{x}或{y}或按下时间{press_time}不是数字")
        try:
            # 转换坐标
            conv_x, conv_y = self._convert_coordinates(x, y)
            log.debug(f"点击坐标: ({x}, {y}) -> ({conv_x}, {conv_y}), 按下时间: {press_time}ms")
            
            if self.minitouch_proc and self.minitouch_proc.poll() is None:
                # 使用minitouch进行点击
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(('127.0.0.1', 1111))
                    # 按下
                    s.sendall(f"d 0 {conv_x} {conv_y} 50\nc\n".encode())
                    time.sleep(press_time / 1000)  # 转换为秒
                    # 抬起
                    s.sendall("u 0\nc\n".encode())
            else:
                # 回退到input命令
                log.debug("minitouch未启动，使用input命令")
                subprocess.run([
                    self.adb_path, "-s", self.device_addr, "shell",
                    f"input swipe {conv_x} {conv_y} {conv_x} {conv_y} {press_time}"  # 使用swipe模拟长按
                ], check=True)
        except Exception as e:
            log.error(f"点击失败: {e}")
            return False
        time.sleep(0.05)  # 额外延迟
        if self.ensure_connected():
            return True
        return False
            
    def swipe(self, start_x: int, start_y: int, end_x: int, end_y: int, duration: int = 500) -> bool:
        """
        滑动屏幕
        :param start_x: 起始x坐标
        :param start_y: 起始y坐标
        :param end_x: 结束x坐标
        :param end_y: 结束y坐标
        :param duration: 持续时间(毫秒)
        :return: 是否滑动成功
        """
        try:
            int(start_x)
            int(start_y)
            int(end_x)
            int(end_y)
            int(duration)
        except:
            raise ValueError(f"坐标{start_x}或{start_y}或{end_x}或{end_y}或持续时间{duration}不是数字")
        try:
            # 转换坐标
            conv_start_x, conv_start_y = self._convert_coordinates(start_x, start_y)
            conv_end_x, conv_end_y = self._convert_coordinates(end_x, end_y)
            log.debug(f"滑动: ({start_x}, {start_y}) -> ({end_x}, {end_y}) => ({conv_start_x}, {conv_start_y}) -> ({conv_end_x}, {conv_end_y}), 持续时间: {duration}ms")
            
            if self.minitouch_proc and self.minitouch_proc.poll() is None:
                # 使用minitouch进行滑动
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(('127.0.0.1', 1111))
                    # 计算滑动步骤
                    step_duration = 5  # 每5ms一步
                    steps = max(duration // step_duration, 1)  # 至少1步
                    
                    # 按下起点
                    s.sendall(f"d 0 {conv_start_x} {conv_start_y} 50\nc\n".encode())
                    time.sleep(0.05)  # 起点停留50ms
                    
                    # 使用三次样条插值实现平滑滑动
                    for i in range(steps):
                        progress = i / steps
                        # 三次样条插值：progress = t³(10-15t+6t²)
                        t = progress
                        spline = t * t * t * (10 - 15 * t + 6 * t * t)
                        
                        cur_x = int(conv_start_x + (conv_end_x - conv_start_x) * spline)
                        cur_y = int(conv_start_y + (conv_end_y - conv_start_y) * spline)
                        s.sendall(f"m 0 {cur_x} {cur_y} 50\nc\n".encode())
                        time.sleep(step_duration / 1000)  # 每步延迟
                    
                    # 移动到终点
                    s.sendall(f"m 0 {conv_end_x} {conv_end_y} 50\nc\n".encode())
                    time.sleep(0.05)  # 终点停留50ms
                    
                    # 抬起
                    s.sendall("u 0\nc\n".encode())
            else:
                # 回退到input命令
                log.debug("minitouch未启动，使用input命令")
                subprocess.run([
                    self.adb_path, "-s", self.device_addr, "shell",
                    f"input swipe {conv_start_x} {conv_start_y} {conv_end_x} {conv_end_y} {duration}"
                ], check=True)
        except Exception as e:
            log.error(f"滑动失败: {e}")
            return False
        time.sleep(0.05)  # 额外延迟
        if self.ensure_connected():
            return True
        return False
            
    def screenshot(self, retries: int = 3) -> Optional[np.ndarray]:
        """
        截图
        :param retries: 重试次数
        :return: 截图数据或None
        """
        log.debug("开始截图")
        
        for i in range(retries):
            try:
                # 使用adb截图
                result = subprocess.run(
                    [self.adb_path, "-s", self.device_addr, "shell", "screencap", "-p"],
                    capture_output=True,
                    check=True
                )
                
                # 转换截图数据
                screen_bytes = result.stdout.replace(b'\r\n', b'\n')
                img_array = np.frombuffer(screen_bytes, np.uint8)
                img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
                
                if img is not None:
                    log.debug("截图成功")
                    return img
                else:
                    log.warning(f"截图解码失败，重试 {i+1}/{retries}")
            except subprocess.CalledProcessError as e:
                log.error(f"截图失败: {e}")
                if i < retries - 1:
                    time.sleep(1)  # 等待1秒后重试
                continue
            except Exception as e:
                log.error(f"截图时发生未知错误: {e}")
                if i < retries - 1:
                    time.sleep(1)
                continue
        
        log.error("截图失败，已达到最大重试次数")
        return None

    def cleanup(self):
        """清理资源"""
        try:
            # 关闭socket连接
            if hasattr(self, "minitouch_socket") and self.minitouch_socket:
                self.minitouch_socket.close()
                log.info("minitouch_socket已关闭")
            
            # 终止子进程
            if hasattr(self, "minitouch_proc") and self.minitouch_proc:
                self.minitouch_proc.terminate()
                self.minitouch_proc.wait()
                log.info("minitouch_proc已终止")
            
            # 移除端口转发
            if hasattr(self, "device_addr") and self.device_addr:
                try:
                    subprocess.run(
                        [self.adb_path, "-s", self.device_addr, "forward", "--remove", "tcp:1111"],
                        capture_output=True,
                        check=True
                    )
                    log.info("端口转发已移除")
                except Exception as e:
                    log.error(f"移除端口转发时发生错误: {str(e)}")
                    
                # 删除推送的文件
                try:
                    subprocess.run(
                        [self.adb_path, "-s", self.device_addr, "shell", "rm", "/data/local/tmp/minitouch"],
                        capture_output=True,
                        check=True
                    )
                    log.info("推送的minitouch文件已删除")
                except Exception as e:
                    log.error(f"删除推送的minitouch文件时发生错误: {str(e)}")
        except Exception as e:
            log.error(f"清理时发生错误: {str(e)}")

    def __del__(self):
        """析构函数"""
        self.cleanup()
#======================================
class OperationMode(Enum):
    """操作模式"""
    GACHA = "干员寻访"
    RECRUIT = "公开招募"
    PLAN = "自动规划"

class GachaMode(Enum):
    """寻访模式"""
    SINGLE = "单抽"
    TEN = "十连"

class RecruitMode(Enum):
    """公招模式"""
    BREAK = "中止"
    ACCELERATE = "加速"

class TaskType(Enum):
    # 点击操作
    CLICK_TEXT = "点击文字"
    CLICK_IMG  = "点击图片"
    CLICK_BEST_TAGS = "点击五个tag中的最好的多个"
    # 记录操作
    RECORD_TAG            = "记录tag"
    RECORD_AGENT          = "记录干员"
    RECORD_HISTORY_PAGE   = "记录一面抽卡记录"
    RECORD_SCREEN         = "记录屏幕内容，可能是以上所有RECORD模式中的任意一个"
    RECORD_HISTORY_FLEX   = "记录指定数量抽卡记录"
    # 偏底层操作
    CLICK_COORDINATE = "点击指定坐标"
    CLICK_COORDINATE_RELATIVE = "点击相对位置"
    SWIPE_TO_RIGHT = "向左划动"
    SWIPE_TO_LEFT  = "向右划动"
    # 界面切换操作
    ENTER_SLOT    = "进入指定公招池"
    SWIPE_TO_PAGE = "划动到指定页面"
    #ENTER_GACHA_STATISTICS = "进入当前寻访界面的历史记录"
    # 流程控制任务
    NOP = "无"
    STEP_COMPLETED = "一个步骤已完成"
    IF = "条件任务组"
    END = "终止"

class Task:
    """任务类，定义单个任务的属性和行为"""
    aimRecruitSlot = 1
    aimGachaPage = 1
    currentPage = 0
    d_imgs = None
    d_reuseableCoordinate = {}

    @classmethod
    def init_img(cls, imgPath):
        """初始化"点击图片"功能用到的图片到内存"""
        d_imgs = {}
        for item in os.listdir(imgPath):
            path = os.path.join(imgPath, item)
            if os.path.isfile(path) and path[-4:] == ".png":
                name = item[:-1-(item[::-1].find("."))]
                d_imgs[name] = cv2.cvtColor(cv2.imread(path), cv2.COLOR_BGR2GRAY)
        cls.d_imgs = d_imgs

    def __init__(self,
        taskType,            # 任务类型（定义在枚举类中）
        param,              # 任务参数
        *args,
        timeout        = 4,    # 超时时间（秒）
        pre_wait       = 0,     # 前置等待时间（秒）
        post_wait      = 0,     # 后置等待时间（秒）
        description    = None,  # 任务描述（用于显示在步骤中）
        retry_count    = 50,    # 重试次数
        b_reuse        = False, # 坐标可复用（重名不可用！）
        b_recruitCheck = False, # 需要进行公招的点击位置筛选
        region         = None,  # 图像识寻找的区域，格式为(x1, x2, y1, y2)
        **kwargs
    ):
        if Task.d_imgs is None:
            raise AttributeError("使用Task实例前必须初始化所有用于识别的图片，请使用'Task.init_img(imgPath = xxx)'完成这件事")
        self.description = description
        if description is None:
            self.description = taskType.value
        #
        self.taskType = taskType
        self.param = param
        self.timeout = timeout
        self.pre_wait = pre_wait
        self.post_wait = post_wait
        self.retry_count = retry_count
        self.b_reuse = b_reuse
        self.region = region
        self.args = args
        self.kwargs = kwargs
        if b_recruitCheck:
            self.checkFunc = self.checkCoordinate_recruit
        else:
            self.checkFunc = None
        log.debug(f"创建任务: 类型={taskType}, 参数={param}, 描述={description}, 超时={timeout}秒, 重试={retry_count}次, 复用={b_reuse}, 公招检查={b_recruitCheck}, 区域={region}")

    def execute(self):
        # result = (success: bool, taskType: TaskType, item)  or  True
        log.debug(f"开始执行任务: {self.description}")
        try:
            if self.taskType == TaskType.CLICK_TEXT:
                log.debug(f"点击文字: {self.param}")
                self.click_item(self.find_nameOnScreen, self.param, self.b_reuse, self.checkFunc, region=self.region)
            elif self.taskType == TaskType.CLICK_IMG:
                log.debug(f"点击图片: {self.param}")
                self.click_item(self.find_imgOnScreen, self.param, self.b_reuse, self.checkFunc, region=self.region)
            elif self.taskType == TaskType.CLICK_BEST_TAGS:
                # 识别tag
                img = Task.simulator.screenshot()
                l_tag = tool.getTag(img)
                log.debug(f"识别到的tag: {l_tag}")
                if len(l_tag) != 5:
                    log.debug(f"tag数量不正确: {len(l_tag)}")
                    return (False, TaskType.CLICK_BEST_TAGS, l_tag)
                # 选择最好的tag（最多三个）
                # l_sorted: [("tag", priority), ("tag", priority), ("tag", priority), ...] 降序
                l_sorted = sorted([(tag, DATA.getTagPriority(tag)) for tag in l_tag], key=lambda t:t[1], reverse=True)
                log.debug(f"tag优先级排序: {l_sorted}")
                bestNum = l_sorted[0][1]
                l_chosen = []
                for i in range(3):
                    if l_sorted[i][1] == bestNum:
                        l_chosen.append(l_sorted[i][1])
                    else:
                        break
                log.debug(f"选择的tag: {l_chosen}")
                # 点击
                for tag in l_chosen:
                    self.click_item(self.find_nameOnScreen, tag)
            elif self.taskType == TaskType.RECORD_TAG:
                img = Task.simulator.screenshot()
                l_tag = tool.getTag(img)
                log.debug(f"识别到的tag: {l_tag}")
                if len(l_tag) == 5:
                    return (True, TaskType.RECORD_TAG, l_tag)
                else:
                    return (False, TaskType.RECORD_TAG, tool.cropping(img, region_tag, mode="percent"))
            elif self.taskType == TaskType.RECORD_AGENT:
                img = Task.simulator.screenshot()
                agent = tool.getAgent(img)
                log.debug(f"识别到的干员: {agent}")
                if agent is not None:
                    return (True, TaskType.RECORD_AGENT, tool.cropping(img, region_agent, mode="percent"))
                else:
                    return (False, TaskType.RECORD_AGENT, img)
            elif self.taskType == TaskType.RECORD_HISTORY_PAGE:
                img = Task.simulator.screenshot()
                l_history, b_flag = tool.getHistory(img)
                log.debug(f"识别到的历史记录: {l_history}, 标志: {b_flag}")
                if b_flag:
                    return (True, TaskType.RECORD_HISTORY_PAGE, l_history)
                else:
                    return (False, TaskType.RECORD_HISTORY_PAGE, (tool.cropping(img, region_history, mode="percent"), l_history))
            elif self.taskType == TaskType.RECORD_SCREEN:
                # 三种识别
                img = Task.simulator.screenshot()
                l_tag = tool.getTag(img)
                agent = tool.getAgent(img)
                l_history, b_flag = tool.getHistory(img)
                log.debug(f"屏幕识别结果: tag={l_tag}, 干员={agent}, 历史={l_history}, 标志={b_flag}")
                # 挨个判定正确的
                if len(l_tag) == 5:
                    return (True, TaskType.RECORD_TAG, l_tag)
                if b_flag:
                    return (True, TaskType.RECORD_HISTORY_PAGE, l_history)
                if agent is not None:
                    return (True, TaskType.RECORD_AGENT, agent)
                # 找不到
                return (False, TaskType.RECORD_SCREEN, img)
            elif self.taskType == TaskType.RECORD_HISTORY_FLEX:
                aim = self.param
                log.debug(f"开始记录历史记录，目标数量: {aim}")
                b_less = False
                while len(l_agent) < aim:
                    if b_less:
                        log.debug(f"记录数量不足: {l_history}")
                        return (False, TaskType.RECORD_HISTORY_FLEX, (img, f"识别数量少了：{l_history}"))
                    # 截图识别
                    img = Task.simulator.screenshot()
                    l_history, b_flag = tool.getHistory(img)
                    log.debug(f"当前页识别结果: {l_history}, 标志: {b_flag}")
                    if not b_flag:
                        return (False, TaskType.RECORD_HISTORY_FLEX, (img, f"识别有误：{l_history}"))
                    if len(l_history) != 10:
                        b_less = True
                    # 暂存
                    l_agent += l_history
                    log.debug(f"当前已记录: {len(l_agent)}/{aim}")
                    # 点击下一页
                    try:
                        self.click_item(self.find_nameOnScreen, "gachaHistoryButton_right", True)
                    except CantFindNameError as e:
                        # 抵达最后一页
                        if len(l_agent) < aim:
                            log.debug(f"已到最后一页但记录不足: {len(l_agent)}/{aim}")
                            return (False, TaskType.RECORD_HISTORY_FLEX, (img, f"已到最后一页但是记录数目不正确：{len(l_agent)} < {aim}\n{l_agent}"))
                        break
                l_agent = l_agent[:aim]
                # 借 TaskType.RECORD_HISTORY_PAGE 的处理方法一用
                return (True, TaskType.RECORD_HISTORY_PAGE, l_agent)
            elif self.taskType == TaskType.CLICK_COORDINATE:
                log.debug(f"点击坐标: {self.param}")
                Task.simulator.click(*self.param)
            elif self.taskType == TaskType.CLICK_COORDINATE_RELATIVE:
                rx, ry = self.param
                height, width = Task.simulator.screen_size
                log.debug(f"点击相对坐标: ({rx}, {ry}) -> ({rx*width}, {ry*height})")
                Task.simulator.click(rx*width, ry*height)
            elif self.taskType == TaskType.SWIPE_TO_RIGHT:
                log.debug("执行向右滑动")
                self.to_rightPage()
            elif self.taskType == TaskType.SWIPE_TO_LEFT:
                log.debug("执行向左滑动")
                self.to_leftPage()
            elif self.taskType == TaskType.ENTER_SLOT:
                log.debug(f"进入公招槽位: {Task.aimRecruitSlot}")
                # "开始招募干员"可能出bug，稳妥一点选"开始"二字
                self.click_item(self.find_nameOnScreen, "开始", False, self.checkCoordinate_recruit)
            elif self.taskType == TaskType.SWIPE_TO_PAGE:
                if not Task.aimGachaPage != Task.currentPage:
                    log.debug("已在目标页面，无需滑动")
                    return
                log.debug(f"滑动到页面: 当前={Task.currentPage}, 目标={Task.aimGachaPage}")
                if Task.aimGachaPage < Task.currentPage:
                    func_swide = self.to_leftPage
                else:
                    func_swide = self.to_rightPage
                for _ in range(abs(Task.aimGachaPage - Task.currentPage)):
                    func_swide()
                    time.sleep(0.5)
            elif self.taskType == TaskType.NOP:
                log.debug("执行空任务")
            elif self.taskType == TaskType.STEP_COMPLETED:
                raise RuntimeError("STEP_COMPLETED 任务不应在此处被捕获")
            elif self.taskType == TaskType.IF:
                log.debug(f"执行条件判断: {self.param}")
                if self.param is True:
                    return (True, TaskType.IF, True)
                elif self.param is False:
                    return (True, TaskType.IF, False)
                elif not isinstance(self.param, str):
                    raise TypeError(f"IF 任务的参数必须是True False str中的一种，'{self.param}'是'{type(self.param)}'")
                if callable(getattr(self, self.param)):
                    result = getattr(self, self.param)()
                    log.debug(f"条件判断结果: {result}")
                    return (True, TaskType.IF, result)
                else:
                    raise TypeError(f"IF 任务的str参数必须是可调用的，'{getattr(self, self.param)}'是'{type(self.param)}'")
            elif self.taskType == TaskType.END:
                raise RuntimeError("END 任务不应在此处被捕获")
            log.debug(f"任务执行完成: {self.description}")
            return True
        except Exception as e:
            # 获取调用栈信息
            frame = inspect.currentframe()
            caller_frame = frame.f_back
            while caller_frame:
                if caller_frame.f_code.co_filename != frame.f_code.co_filename:
                    break
                caller_frame = caller_frame.f_back
            
            if caller_frame:
                filename = os.path.basename(caller_frame.f_code.co_filename)
                lineno = caller_frame.f_lineno
                log_manager.log(str(e), "DEBUG", filename, lineno)
            else:
                log_manager.log(str(e), "DEBUG")
            raise

    def isOriginiteOnScreen(self):
        result = self.find_nameOnScreen("至纯源石")
        log.debug(f"检查源石: {'存在' if result else '不存在'}")
        if result is None:
            return False
        return True

    def checkCoordinate_recruit(self, result, screen_size, aim):
        if aim not in [1, 2, 3, 4]:
            raise ValueError("选择的公招池必须是1~4之一")

        height, width = screen_size
        half_x = width // 2
        half_y = height // 2
        y_threshold = height * 0.15
        x, y = result[0][0]

        is_left_half = x < half_x
        is_right_half = x > half_x
        is_near_center_y = abs(y - half_y) < y_threshold
        is_far_from_center_y = abs(y - half_y) > y_threshold

        conditions = {
            1: is_left_half and is_near_center_y,
            2: is_right_half and is_near_center_y,
            3: is_left_half and is_far_from_center_y,
            4: is_right_half and is_far_from_center_y,
        }
        log.debug(f"检查公招坐标: 目标={aim}, 坐标=({x}, {y}), 结果={conditions[aim]}")
        if conditions[aim]:
            return True
        return False

    def find_nameOnScreen(self, name, limit = 0.5, b_allGet = False, **kwargs):
        """
        在屏幕上查找指定文字
        :param name: 要查找的文字
        :return: OCR识别结果
        """
        Task.simulator.ensure_connected()
        log.debug(f"查找文字: {name}, 阈值={limit}, 全部获取={b_allGet}")
        img = Task.simulator.screenshot()
        if "region" in kwargs and kwargs["region"] is not None:
            img = tool.cropping(img, kwargs["region"], mode="percent")
            log.debug(f"在区域内查找: {kwargs['region']}")
        results = tool.ocr(img)
        l_output = []
        for result in results:
            l_position, t_text = result
            if name in t_text[0]:
                l_output.append(result)
        offset = 0
        for i in range(len(l_output)):
            if l_output[i-offset][1][1] < limit:
                l_output.pop(i-offset)
                offset += 1
        log.debug(f"找到结果: {l_output}")
        if len(l_output) == 0:
            return None
        if b_allGet:
            return l_output
        else:
            l_output.sort(key=lambda result: result[1][1])
            return l_output[-1]

    def find_imgOnScreen(self, name, limit=0.5, b_allGet=False, b_paddleOutput=True, b_counterexampleMode = True, **kwargs):
        if name not in Task.d_imgs:
            raise KeyError(f"'{name}'可能不存在于识别图片路径中")

        log.debug(f"查找图片: {name}, 阈值={limit}, 全部获取={b_allGet}, 反例模式={b_counterexampleMode}")
        screenshot = Task.simulator.screenshot()
        if "region" in kwargs and kwargs["region"] is not None:
            img = tool.cropping(img, kwargs["region"], mode="percent")
            log.debug(f"在区域内查找: {kwargs['region']}")
        template = Task.d_imgs[name]
        l_results = tool.find_imgOnImg(screenshot, template, match_threshold = limit, b_needTemplate2GRAY = False)
        if b_counterexampleMode and (name + "#") in Task.d_imgs:
            template = Task.d_imgs[name + "#"]
            l_results_c = tool.find_imgOnImg(screenshot, template, match_threshold = limit, b_needTemplate2GRAY = False)
            log.debug(f"反例匹配结果: {l_results_c}")
            if l_results_c[0][1] > l_results[0][1]:
                l_results = []
        log.debug(f"找到结果: {l_results}")
        if len(l_results) == 0:
            return None
        if b_paddleOutput:
            # 配合paddle的格式
            l_results = [ [[(result[0][0], result[0][1]), None, (result[0][2], result[0][3]), None], result[1]] for result in l_results]
        if b_allGet:
            return l_results
        return l_results[0]

    def click_item(self, func_findResult, name=None, b_reuse=False, checkFunc=None, **kwargs):
        """点击指定文字位置"""
        # 检查
        if b_reuse and checkFunc is not None:
            raise ValueError("b_reuse 和 checkFunc 模式不能同时使用")
        log.debug(f"点击项目: name={name}, 复用={b_reuse}, 检查函数={'有' if checkFunc else '无'}")
        # 核心功能，找到name的位置
        def findCoodinate():
            result = func_findResult(name, **kwargs)
            log.debug(f"寻找结果: {result}")
            if not result:
                raise CantFindNameError(f"找不到: {name}")
            return tool.find_centerOnResult(result, mode = "paddle")
        if name is None:
            #1.None的时候点中心
            height, width = Task.simulator.screen_size
            x, y = width//2, height//2
            log.debug(f"点击屏幕中心: ({x}, {y})")
        elif b_reuse:
            #2.复用坐标模式
            if name not in Task.d_reuseableCoordinate:
                # 需要寻找
                Task.d_reuseableCoordinate[name] = findCoodinate()
            x, y = Task.d_reuseableCoordinate[name]
            log.debug(f"使用复用坐标: ({x}, {y})")
        elif checkFunc is not None:
            #3.公招位置寻找模式
            l_results = func_findResult(name, b_allGet=True, **kwargs)
            if l_results is None:
                raise CantFindNameError(f"找不到: {name}")
            realResult = None
            for result in l_results:
                if checkFunc(result, Task.simulator.screen_size, Task.aimRecruitSlot):
                    realResult = result
            if realResult is None:
                raise CantFindNameError(f"找不到合适的: {name}")
            x, y = tool.find_centerOnResult(realResult, mode = "paddle")
            log.debug(f"使用公招位置: ({x}, {y})")
        else:
            #4.常规模式
            x, y = findCoodinate()
            log.debug(f"使用常规位置: ({x}, {y})")
        Task.simulator.click(x, y)
    
    def to_rightPage(self):
        """向右翻页"""
        log.debug("向右翻页")
        height, width = Task.simulator.screen_size
        x = width
        y = height
        x1 = x/3
        y_2 = y/2
        Task.simulator.swipe(x1*2, y_2, x1, y_2)
    
    def to_leftPage(self):
        """向左翻页"""
        log.debug("向左翻页")
        height, width = Task.simulator.screen_size
        x = width
        y = height
        x1 = x/3
        y_2 = y/2
        Task.simulator.swipe(x1, y_2, x1*2, y_2)

Task.init_img(IMG_PATH)

class TaskManager(QObject):
    """任务管理器，负责任务队列的管理和执行"""
    task_started = Signal(str)          # 任务开始信号
    task_completed = Signal(object)     # 任务完成信号，传递任务结果
    task_failed = Signal(str)           # 任务失败信号
    step_completed = Signal()           # 步骤完成信号，用于请求下一组任务
    task_terminated = Signal()          # 任务终止信号，遇见END任务时触发
    device_disconnected = Signal()      # 设备离线信号
    
    def __init__(self):
        super().__init__()
        self.tasks = []
        self.current_task = None
        self.is_running = False
        self.is_paused = False
        self.thread = None
        self.b_needJoin = False
    
    def add_task(self, task: Task):
        """添加任务到队列"""
        self.tasks.append(task)
    
    def clear_tasks(self):
        """清空任务队列"""
        self.tasks.clear()
    
    def get_next_task_description(self) -> Optional[str]:
        """获取下一个任务的描述"""
        if not self.tasks:
            return None
        return self.tasks[0].description if self.tasks else None
    
    def execute_tasks(self):
        """开始执行任务队列"""
        log.debug(f"线程执行标志：{self.is_running}")
        if self.is_running:
            return
        if self.b_needJoin:
            if self.thread.is_alive():
                raise RuntimeError("线程未结束")
            if self.thread != threading.current_thread():
                self.thread.join()
        self.is_running = True
        self.is_paused = False
        self.thread = threading.Thread(target=self._task_loop)
        self.thread.start()
    
    def stop_tasks(self):
        """停止任务执行"""
        self.clear_tasks()
        self.is_running = False
        self.is_paused = True
    
    @Slot()
    def pause_tasks(self):
        self.is_paused = True

    @Slot()
    def resume_tasks(self):
        self.is_paused = False

    def _task_loop(self):
        """任务执行循环"""
        while self.is_running:
            if self.tasks == [] or self.is_paused:
                time.sleep(0.1)
                continue
            try:
                self.current_task = self.tasks.pop(0)
                
                # 前置等待
                if self.current_task.pre_wait > 0:
                    time.sleep(self.current_task.pre_wait)

                while self.is_paused:
                    if not self.is_running:
                        raise StopError
                    time.sleep(0.1)

                # 发送任务开始信号
                self.task_started.emit(self.current_task.description)
                
                # 执行任务
                result = None
                error = None

                if self.current_task.taskType == TaskType.STEP_COMPLETED:
                    self.step_completed.emit()
                    continue
                elif self.current_task.taskType == TaskType.END:
                    self.task_terminated.emit()
                    break

                start_time = time.time()
                for _ in range(self.current_task.retry_count):
                    if not Task.simulator.ensure_connected():
                        self.device_disconnected.emit()
                        raise RuntimeError("模拟器离线")
                    try:
                        result = self.current_task.execute()
                        if result is True or (isinstance(result, tuple)):
                            break
                            
                    except Exception as e:
                        error = str(e)
                        # 获取调用栈信息
                        frame = inspect.currentframe()
                        caller_frame = frame.f_back
                        while caller_frame:
                            if caller_frame.f_code.co_filename != frame.f_code.co_filename:
                                break
                            caller_frame = caller_frame.f_back
                        
                        if caller_frame:
                            filename = os.path.basename(caller_frame.f_code.co_filename)
                            lineno = caller_frame.f_lineno
                            log_manager.log(str(e), "DEBUG", filename, lineno)
                        else:
                            log_manager.log(str(e), "DEBUG")
                        time.sleep(0.1)  # 重试前短暂等待

                
                    while self.is_paused:
                        if not self.is_running:
                            raise StopError
                        time.sleep(0.1)
                        start_time += 0.1


                    if time.time() - start_time > self.current_task.timeout:
                        error = "任务超时"
                        break

                while self.is_paused:
                    if not self.is_running:
                        raise StopError
                    time.sleep(0.1)

                # 后置等待
                if self.current_task.post_wait > 0:
                    time.sleep(self.current_task.post_wait)

                while self.is_paused:
                    if not self.is_running:
                        raise StopError
                    time.sleep(0.1)

                # 发送任务结果
                if self.current_task.taskType == TaskType.IF:
                    if not isinstance(self.tasks[0], list):
                        raise TypeError("IF 类型的任务后必须接一个任务列表")
                    if result[2] is True:
                        l = self.tasks.pop(0)
                        self.tasks = l + self.tasks
                    else:
                        self.tasks.pop(0)
                elif result:
                    self.task_completed.emit(result)
                    if isinstance(result, tuple) and result[0] is False:
                        self.is_paused = True
                elif error:
                    self.task_failed.emit(error)
                    break
                else:
                    raise RuntimeError("不可能运行到此处")
            except StopError:
                break
            except Exception as e:
                self.task_failed.emit(str(e))
                break
        self.is_running = False
        self.b_needJoin = True
#==============================================
def execute_tasks(func):
    def wrapper(self, *args, **kwargs):
        tasks = func(self, *args, **kwargs)
        for task in tasks:
            self.task_manager.add_task(task)
        self.task_manager.execute_tasks()
    return wrapper

class GameManager(QObject):
    # 信号定义
    device_connected = Signal(bool)  # 设备连接状态信号
    operation_started = Signal()     # 操作开始信号
    operation_stopped = Signal()     # 操作停止信号
    operation_paused = Signal()      # 操作暂停信号
    operation_resumed = Signal()     # 操作恢复信号
    step_updated = Signal(str, str)  # 步骤更新信号
    macro_step_updated = Signal(str, str)  # 宏观步骤更新信号
    log_message = Signal(str, str)   # 日志消息信号(消息, 级别)
    data_updated = Signal()          # 数据更新通知
    
    def __init__(self):
        super().__init__()
        self.is_running = False
        self.is_paused = False
        self.b_exist_rare_tag = False
        self.current_mode = None
        self.execution_limit = 0
        self.b_special_stop = False
        self.task_manager = None
        self.top_item_count = 0
        self.gacha_mode = GachaMode.SINGLE
        self.recruit_mode = RecruitMode.BREAK
        
        # 操作计数
        self.operation_count = 0
        self.recruit_count = 0
        self.gacha_count = 0

        self.set_use_originite(False)

    def record(self, item):
        """记录数据"""
        self.log_with_time("INFO", f"记录: {item}")
            
        if isinstance(item, list):
            s_record = "!".join(item)
        if isinstance(item, str):
            s_record = item
        
        data_manager.update_data(s_record)
        self.data_updated.emit()

    def update_step(self, current_step: str, next_step: Optional[str] = None):
        """更新步骤信息"""
        # 发送步骤更新信号
        self.step_updated.emit(current_step, next_step)
        log_manager.update_step(current_step, next_step)
    
    def update_macro_step(self, level = "INFO", macro_step = None):
        self.macro_step_updated.emit(macro_step, level)
        self.log_with_time(level, macro_step)

    def _log(self, level = "INFO", message = None):
        """记录日志消息"""
        if message is None:
            return
        # 获取调用栈信息
        frame = inspect.currentframe()
        caller_frame = frame.f_back
        while caller_frame:
            if caller_frame.f_code.co_filename != frame.f_code.co_filename:
                break
            caller_frame = caller_frame.f_back
        
        if caller_frame:
            filename = os.path.basename(caller_frame.f_code.co_filename)
            lineno = caller_frame.f_lineno
            log_manager.log(message, level, filename, lineno)
        else:
            log_manager.log(message, level)
    
    def log_with_time(self, level: str, message: str, filename: str = None, lineno: int = None):
        """带时间戳的日志记录"""
        if (filename is None) or (lineno is None):
            # 获取调用者信息
            frame = inspect.currentframe().f_back
            if frame:
                filename = os.path.basename(frame.f_code.co_filename)
                lineno = frame.f_lineno
        
        log_manager.log(message, level, filename, lineno)
    
    def connect_device(self, adb_path: str):
        """连接设备"""
        try:
            self.task_manager = TaskManager()
            Task.simulator = Simulator(adb_path = adb_path)
            
            # 连接任务管理器信号
            self.task_manager.task_started.connect(self._on_task_started)
            self.task_manager.task_completed.connect(self._on_task_completed)
            self.task_manager.task_failed.connect(self._on_task_failed)
            self.task_manager.task_terminated.connect(self.reset_operation)
            self.task_manager.step_completed.connect(self._arrange_next_task)
            self.task_manager.device_disconnected.connect(lambda:self.device_connected.emit(False))
            
            # 连接自身信号
            self.operation_paused.connect(self.task_manager.pause_tasks)
            self.operation_resumed.connect(self.task_manager.resume_tasks)

            self.update_macro_step("INFO", "设备连接成功")
            self.device_connected.emit(True)
        except Exception as e:
            self.update_macro_step("ERROR", f"设备连接失败: {str(e)}")
            self.device_connected.emit(False)
    
    def break_connection(self):
        try:
            if hasattr(Task, "simulator"):
                Task.simulator.cleanup()
            if hasattr(self, "task_manager"):
                del self.task_manager
        except Exception as e:
            self._log("ERROR", f"adb清理失败: {str(e)}")

    def set_gacha_mode(self, mode: GachaMode):
        """设置寻访模式"""
        self.gacha_mode = mode
        self.log_with_time("INFO", f"寻访模式已设置为：{mode.value}")
    
    def set_recruit_mode(self, mode: RecruitMode):
        """设置公招模式"""
        self.recruit_mode = mode
        self.log_with_time("INFO", f"公招模式已设置为：{mode.value}")
    
    def set_recruit_slot(self, slot: int):
        """设置公招栏位"""
        Task.aimRecruitSlot = slot
        self.log_with_time("INFO", f"公招栏位已设置为：{slot}")

    def set_gacha_pool(self, pool: int):
        """设置寻访池"""
        Task.aimGachaPage = pool
        self.log_with_time("INFO", f"寻访池已设置为：{pool}")

    def set_use_originite(self, use: bool):
        """设置是否使用源石"""
        if use:
            self.l_originiteCheckTask = []
        else:
            self.l_originiteCheckTask = [
                Task(TaskType.IF, "isOriginiteOnScreen", description="检查是否消耗源石"),
                [
                    Task(TaskType.CLICK_TEXT, "取消", description="取消操作"),
                    Task(TaskType.END, None),
                ]
            ]
        self.log_with_time("INFO", f"源石消耗已设置为：{'开启' if use else '关闭'}")

    def start_operation(self, mode: OperationMode, param: int):
        """开始操作"""
        if self.is_running:
            return
            
        self.is_running = True
        self.is_paused = False
        self.current_mode = mode
        if param >= 0:
            self.execution_limit = param
        elif param < 0:
            self.b_special_stop = True
        if mode == OperationMode.GACHA:
            self.update_macro_step("INFO", f"开始寻访, 次数:{'循环直到遇见好东西' if self.b_special_stop else ('无限循环' if self.execution_limit == 0 else self.execution_limit)}, 模式:{self.gacha_mode.value}, 源石消耗:{'开启' if not self.l_originiteCheckTask else '关闭'}, 寻访池:{Task.aimGachaPage}")
        elif mode == OperationMode.RECRUIT:
            self.update_macro_step("INFO", f"开始公招, 次数:{'循环直到遇见好东西' if self.b_special_stop else ('无限循环' if self.execution_limit == 0 else self.execution_limit)}, 模式:{self.recruit_mode.value}, 公招栏:{Task.aimRecruitSlot}")
        elif mode == OperationMode.PLAN:
            self.update_macro_step("ERROR", "自动规划未实现")
            self.reset_operation()
            return
            #self.update_macro_step(f"开始自动规划, 次数:{'循环直到遇见好东西' if self.b_special_stop else ('无限循环' if self.execution_limit == 0 else self.execution_limit)}, 公招模式:{self.recruit_mode.value}, 源石消耗:{'开启' if not self.l_originiteCheckTask else '关闭'}, 寻访池:{Task.aimGachaPage}")
        self.operation_started.emit()

        self._arrange_next_task()
    
    def pause_operation(self):
        """暂停操作"""
        if not self.is_running or self.is_paused:
            return
            
        self.is_paused = True
        self.update_macro_step("INFO", "操作已暂停")
        self.operation_paused.emit()
    
    def resume_operation(self):
        """恢复操作"""
        if not self.is_running or not self.is_paused:
            return
            
        self.is_paused = False

        self.update_macro_step("INFO", "操作已恢复")
        self.operation_resumed.emit()
    
    @Slot()
    def reset_operation(self):
        """重置操作状态"""
        self.is_running = False
        self.is_paused = False
        self.b_exist_rare_tag = False
        self.b_special_stop = False
        self.top_item_count = 0
        self.operation_count = 0
        self.recruit_count = 0
        self.gacha_count = 0
        if self.task_manager:
            self.task_manager.stop_tasks()
        self.operation_stopped.emit()
        self.update_step("", "")
        self.update_macro_step("INFO", "操作已重置")
    
    @Slot()
    def _arrange_next_task(self):
        if not self.is_running or self.is_paused:
            return

        try:
            if self.current_mode == OperationMode.GACHA:
                if self.gacha_mode == GachaMode.SINGLE:
                    self.update_macro_step("INFO", f"开始第{self.gacha_count+1}次寻访")
                    self.taskAdd_gacha_once()
                    self.gacha_count += 1
                    self.operation_count += 1
                elif self.gacha_mode == GachaMode.TEN:
                    if self.execution_limit > 0 and self.execution_limit - self.operation_count < 10:
                        self.gacha_mode = GachaMode.SINGLE
                        self._arrange_next_task()
                    self.update_macro_step("INFO", f"开始第{self.gacha_count+1}~{self.gacha_count+10}次寻访")
                    self.taskAdd_gacha_ten()
                    self.gacha_count += 10
                    self.operation_count += 10
            
            elif self.current_mode == OperationMode.RECRUIT:
                self.operation_count += 1
                self.recruit_count += 1
                self.update_macro_step("INFO", f"开始第{self.recruit_count}次公招")
                self.taskAdd_recruit_enter()
                if self.recruit_mode == RecruitMode.BREAK:
                    self.taskAdd_recruit_break()
                elif self.recruit_mode == RecruitMode.ACCELERATE:
                    self.taskAdd_recruit_accelerate()
            
            elif self.current_mode == OperationMode.PLAN:
                # self.log_with_time("INFO", f"开始第{self.operation_count}次规划")
                # TODO: 实现自动规划功能
                # (!！AI！!)
                pass
            
            # 检查是否达到目标（为0的时候无限制）
            if  (
                (self.b_special_stop and
                    (self.b_exist_rare_tag or (self.top_item_count > 0))
                )
                or
                ((not self.b_special_stop) and
                    self.execution_limit > 0 and self.operation_count >= self.execution_limit
                )
                ):
                self.update_macro_step("INFO", "已达到目标，操作结束")
                if self.current_mode == OperationMode.GACHA and self.gacha_mode == GachaMode.TEN:
                    self.taskAdd_tenModeEndUp()
                else:
                    self.taskAdd_endUp()
                self.is_running = False
        except Exception as e:
            self.log_with_time("ERROR", f"任务分配过程中发生错误：{str(e)}")
            self.reset_operation()

    @Slot()
    def _on_task_started(self, description: str):
        """任务开始处理，更新步骤"""
        next_task = self.task_manager.get_next_task_description()
        self.update_step(description, next_task)
    
    @Slot()
    def _on_task_completed(self, result):
        """任务完成处理"""
        if result is True:
            return
        try:
            # result = (success: bool, taskType: TaskType, result)
            b_success, taskType, result = result

            if taskType == TaskType.RECORD_TAG:
                if not b_success:
                    self.pause_operation()
                    self.log_with_time("WARNING", f"tag无法识别")
                    result = self.parent().handle_missing_tag(result) # result: img
                    if result is None:
                        self.log_with_time("ERROR", "用户取消输入tag")
                        raise UserSuspendOperationError("用户取消操作")
                    self.resume_operation()
                self.log_with_time("INFO", f"获得tag：{', '.join(result)}")
                self.record(result)
                # 检查是否有罕见tag
                rare_tags = [tag for tag in result if DATA.is_special(tag)]
                if rare_tags:
                    self.log_with_time("INFO", f"出现罕见tag:{', '.join(rare_tags)}！")
                    self.b_exist_rare_tag = True

            elif taskType == TaskType.RECORD_AGENT:
                if not b_success:
                    self.pause_operation()
                    self.log_with_time("WARNING", f"干员无法识别")
                    result = self.parent().handle_missing_agent(result) # result: img
                    if result is None:
                        self.log_with_time("ERROR", "用户取消输入干员")
                        raise UserSuspendOperationError("用户取消操作")
                    self.resume_operation()
                self.log_with_time("INFO", f"获得干员：{result}")
                self.record(result)
                # 检查是否为六星干员
                if result in DATA.d_agent and DATA.d_agent[result]["star"] == 6:
                    self.log_with_time("INFO", f"获得六星干员{result}！")
                    self.top_item_count += 1

            elif taskType == TaskType.RECORD_HISTORY_PAGE:
                if not b_success:
                    self.pause_operation()
                    self.log_with_time("WARNING", f"记录无法识别")
                    result = self.parent().handle_missing_record(result) # result: (img, l_agent)
                    if result is None:
                        self.log_with_time("ERROR", "用户取消输入记录")
                        raise UserSuspendOperationError("用户取消操作")
                    self.resume_operation()
                self.log_with_time("INFO", f"获得记录：{result}")
                for agent in result:
                    self.record(agent)
                    # 检查是否为六星干员
                    if result in DATA.d_agent and DATA.d_agent[result]["star"] == 6:
                        self.log_with_time("INFO", f"获得六星干员{result}！")
                        self.top_item_count += 1

            elif taskType == TaskType.RECORD_SCREEN and not b_success:
                self.log_with_time("ERROR", f"屏幕识别失败，正在保存截图")
                log.img(result)
                raise ValueError(f"屏幕识别失败，截图已保存")

            elif taskType == TaskType.RECORD_HISTORY_FLEX and not b_success:
                self.log_with_time("ERROR", f"历史记录识别失败，正在保存截图")
                log.img(result)
                raise ValueError(f"历史记录识别失败，截图已保存")

            elif taskType == TaskType.CLICK_BEST_TAGS and not b_success:
                self.log_with_time("ERROR", f"tag点击识别结果：{result}，数量不正确，失败")
                raise ValueError(f"tag点击识别结果：{result}，数量不正确，失败")

        except Exception as e:
            log.error(str(e))
            self.reset_operation()

    @Slot()
    def _on_task_failed(self, error: str):
        """任务失败处理"""
        self.log_with_time("ERROR", f"出现错误：{error}")
        self.reset_operation()

    @execute_tasks
    def taskAdd_tenModeEndUp(self):
        return [
            Task(TaskType.CLICK_TEXT, "查看详情", b_reuseable = True, description="点击查看详情"),
            Task(TaskType.CLICK_TEXT, "查询记录", b_reuseable = True, pre_wait=0.4, description="点击查询记录"),
            Task(TaskType.RECORD_HISTORY_FLEX, self.gacha_count, pre_wait=0.4, description="记录招募历史"),
            Task(TaskType.CLICK_IMG, "gachaHistoryButton_exit", b_reuseable = True, description="点击×退出"),
            Task(TaskType.CLICK_COORDINATE_RELATIVE, (0.5, 0.05), pre_wait=0.4, description="点击屏幕上方退出"),
            Task(TaskType.END, None),
        ]
    @execute_tasks
    def taskAdd_endUp(self):
        return [
            Task(TaskType.END, None),
        ]
    @execute_tasks
    def taskAdd_recordScreen(self):
        return [
            Task(TaskType.RECORD_SCREEN, None),
            Task(TaskType.END, None),
        ]
    @execute_tasks
    def taskAdd_recruit_enter(self):
        return [
            Task(TaskType.ENTER_SLOT, None, description="进入公招池"),
            Task(TaskType.RECORD_TAG, None, pre_wait=0.5),
        ]
    @execute_tasks
    def taskAdd_recruit_break(self):
        return [
            Task(TaskType.CLICK_IMG, "RecruitConfirm", b_reuseable = True, description="点击对勾开始招募"),
            Task(TaskType.CLICK_TEXT, "停止招募", pre_wait=0.4, b_recruitCheck=True, description="点击停止招募"),
            Task(TaskType.CLICK_TEXT, "停止招募", pre_wait=0.4, b_recruitCheck=True, description="点击停止招募"),
            Task(TaskType.STEP_COMPLETED, None),
        ]
    @execute_tasks
    def taskAdd_recruit_accelerate(self):
        return [
            Task(TaskType.CLICK_IMG, "RecruitTimerDecrement", b_reuseable = True, description="点击向下箭头增加时间"),
            Task(TaskType.CLICK_BEST_TAGS, None, description="选好tag"),
            Task(TaskType.CLICK_IMG, "RecruitConfirm", b_reuseable = True, description="点击对勾开始招募"),
            Task(TaskType.CLICK_TEXT, "立即招募", pre_wait=0.2, b_recruitCheck=True, description="点击立即招募"),
            Task(TaskType.CLICK_IMG, "RecruitNowConfirm", pre_wait=0.2, b_reuseable = True, description="确认使用公招券"),
            Task(TaskType.CLICK_TEXT, "聘用候选人", pre_wait=0.2, b_recruitCheck=True, description="点击聘用候选人"),
            Task(TaskType.CLICK_TEXT, "SKIP", pre_wait=1, b_reuseable = True, description="点击SKIP"),
            Task(TaskType.CLICK_TEXT, "凭证", pre_wait=0.5, b_reuseable = True, description="点击凭证"),
            Task(TaskType.STEP_COMPLETED, None),
        ]
    @execute_tasks
    def taskAdd_gacha_once(self):
        return ([
            Task(TaskType.CLICK_TEXT, "寻访一次", b_reuseable = True, description="点击寻访一次"),
            ] + 
            self.l_originiteCheckTask + 
            [
            Task(TaskType.CLICK_TEXT, "确认", pre_wait=0.6, b_reuseable = True, description="点击确认寻访"),
            Task(TaskType.CLICK_TEXT, "SKIP", pre_wait=1.2, b_reuseable = True, description="点击SKIP"),
            Task(TaskType.RECORD_AGENT, None, pre_wait=1.0),
            Task(TaskType.CLICK_TEXT, "凭证", pre_wait=1.0, b_reuseable = True, description="点击凭证"),
            Task(TaskType.STEP_COMPLETED, None),
        ])
    @execute_tasks
    def taskAdd_gacha_ten(self):
        return ([
            Task(TaskType.CLICK_TEXT, "寻访十次", b_reuseable = True, description="点击寻访十次"),
            ] + 
            self.l_originiteCheckTask + 
            [
            Task(TaskType.CLICK_TEXT, "确认", pre_wait=0.6, b_reuseable = True, description="点击确认寻访"),
            Task(TaskType.CLICK_TEXT, "SKIP", pre_wait=1.2, b_reuseable = True, description="点击SKIP"),
            Task(TaskType.CLICK_TEXT, None, pre_wait=0.8, description="点击任意位置跳过干员"),
            Task(TaskType.CLICK_TEXT, None, pre_wait=0.3, description="点击任意位置跳过信物"),
            Task(TaskType.CLICK_COORDINATE_RELATIVE, (0.5, 0.9), description="点击屏幕下方"),
            Task(TaskType.STEP_COMPLETED, None),
        ])
    @execute_tasks
    def taskAdd_gacha_tenWithRecord(self):
        return ([
            Task(TaskType.CLICK_TEXT, "寻访十次", b_reuseable = True, description="点击寻访十次"),
            ] + 
            self.l_originiteCheckTask + 
            [
            Task(TaskType.CLICK_TEXT, "确认", pre_wait=0.6, b_reuseable = True, description="点击确认寻访"),
            Task(TaskType.CLICK_TEXT, "SKIP", pre_wait=1.2, b_reuseable = True, description="点击SKIP"),
            Task(TaskType.CLICK_TEXT, None, pre_wait=0.8, description="点击任意位置跳过干员"),
            Task(TaskType.CLICK_TEXT, None, pre_wait=0.3, description="点击任意位置跳过信物"),
            Task(TaskType.CLICK_COORDINATE_RELATIVE, (0.5, 0.9), description="点击屏幕下方"),
            Task(TaskType.CLICK_TEXT, "查看详情", b_reuseable = True, pre_wait=0.5, description="点击查看详情"),
            Task(TaskType.CLICK_TEXT, "查询记录", b_reuseable = True, pre_wait=0.4, description="点击查询记录"),
            Task(TaskType.RECORD_HISTORY_PAGE, None, pre_wait=0.4, description="记录一页招募历史"),
            Task(TaskType.CLICK_IMG, "gachaHistoryButton_exit", b_reuseable = True, description="点击×退出"),
            Task(TaskType.CLICK_COORDINATE_RELATIVE, (0.5, 0.05), pre_wait=0.4, description="点击屏幕上方退出"),
            Task(TaskType.STEP_COMPLETED, None),
        ])