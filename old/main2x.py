#pip install paddlepaddle paddleocr opencv-python numpy pywin32
# 会在需要时导入  from paddleocr import PaddleOCR
#==============================
import time
from pathlib import Path as CreatPath
import json
import logging
import subprocess
from typing import Optional, Tuple
from datetime import datetime
import socket
import winreg
#==============================
import cv2
import numpy as np
import os
#from paddleocr import PaddleOCR
#==============================
ADB_PATH = "D:\\YXArkNights-12.0\\shell\\adb.exe"
region_tag = (0.30,0.47,0.66,0.70)
region_agent = (0.45, 0.67, 0.87, 0.85)
#==============================
#from data import l_tag1, l_tag2, l_tag3, l_tagSpecial, d_agents
#==============================
class CantFindNameError(Exception):
    pass

class MouseMoveError(Exception):
    pass
#==============================
class Log:
    def __init__(self, dir="log", file="info.log"):
        """
        定义两种handler，一个用来控制台debug，一个打算用来作日志级文件存储
        """
        self.dir = dir
        self.file = file
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.DEBUG)
        #
        fh = logging.FileHandler(f"{dir}/{file}")
        fh.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)
        f_formatter = logging.Formatter("[%(levelname)s][%(asctime)s][line %(lineno)d]\n%(message)s\n", datefmt = "%Y.%m.%d %H:%M:%S")
        c_formatter = logging.Formatter("[%(levelname)s][line %(lineno)d]\n%(message)s\n")
        fh.setFormatter(f_formatter)
        ch.setFormatter(c_formatter)
        self.logger.addHandler(fh)
        self.logger.addHandler(ch)
        """
        self.logger.debug("debug message")
        self.logger.info("info message")
        self.logger.warning("warn message")
        self.logger.error("error message")
        self.logger.critical("critical message")
        """
    def img(self, img):
        """
        cv2.imshow("img", img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        """
        #时间命名精确到毫秒
        formatted_time = f"{time.strftime('%Y%m%d%H%M%S')}{int((time.time() % 1) * 1000):03d}"
        cv2.imwrite(f"{self.dir}\\{formatted_time}.png", img)

    def debug(self, log):
        self.logger.debug(log)

    def info(self, log):
        self.logger.info(log)

    def warning(self, log):
        self.logger.warning(log)
    
    def error(self, log):
        self.logger.error(log)

    def critical(self, log):
        self.logger.critical(log)

#log = Log()
#==============================
class Tool:
    def __init__(self):
        """
        初始化工具类
        """
        self.l_agents = None
        self.init_data()
        self.ocrUseable = False

    def init_ocr(self):
        self.ocr_ch = PaddleOCR()
        """
        try:
            # 首先尝试使用GPU
            self.ocr_ch = PaddleOCR(use_gpu=True)
            print("使用GPU模式初始化OCR")
        except RuntimeError as e:
            if "cudnn64_8.dll" in str(e):
                # CUDA/CUDNN加载失败，切换到CPU模式
                log.warning("GPU初始化失败，切换到CPU模式")
                self.ocr_ch = PaddleOCR(use_gpu=False)
            else:
                # 其他RuntimeError，继续抛出
                raise e
        except Exception as e:
            # 其他异常，继续抛出
            raise e
        """
        self.ocrUseable = True

    def init_data(self):
        pass
        # l_agents -> [(zh, en), (zh, en), ...]
        #self.l_agents = [(zh, d_agents[zh]["en"]) for zh in d_agents]
        # l_tags -> ["支援", "辅助干员", ...]
        #self.l_tags = l_tag1 + l_tag2 + l_tag3 + l_tagSpecial

    def ocr(self, cvImg):
        if not self.ocrUseable:
            self.init_ocr()
        result = self.ocr_ch.ocr(cvImg, cls=True)
        #"""
        for l in result:
            if l is None:
                continue
            for x in l:
                print(f"ocr结果: {x}")
        #"""
        return result

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
                l_output.append(self.cropping(image, (x,y,w,h)))
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

    def cropping(self, cvImg, region, mode="pixel"):
        """
        裁剪图片大小到指定区域，支持显示缩放
        Args:
            cvImg:  图片数组
            region: (x, y, width【图片相对大小】, height【图片相对大小】) 相对于窗口的坐标和大小
            mode: "pixel" 表示以像素为单位，"percent" 表示以百分比为单位
        """
        x, y, w, h = region
        if mode == "percent":
            shape = cvImg.shape #(height, width, channels)
            x, y, w, h = shape[1]*x, shape[0]*y, shape[1]*w, shape[0]*h
        elif mode == "pixel":
            w, h = w+x, h+y
        x, y, w, h = int(x), int(y), int(w), int(h)
        """
        # 考虑缩放因素调整区域大小
        scaled_x = int(x * self.scaling_factor)
        scaled_y = int(y * self.scaling_factor)
        scaled_w = int(w * self.scaling_factor)
        scaled_h = int(h * self.scaling_factor)
        """
        print(f"裁剪区域: {x}, {y}, {w}, {h}")
        log.img(cvImg[y:h, x:w])
        return cvImg[y:h, x:w]

    def showImg(self, img):
        cv2.imshow("picture", img)
        cv2.waitKey(0)
        cv2.destroyAllWindows()

    def cosine_similarity(self, s1, s2):
        """计算两个字符串之间的余弦相似度。

        该方法通过构建字符频率向量并计算余弦相似度来衡量两个字符串的相似程度。
        在处理前会先进行标准化（转为小写），并去除字符串开头的"new"前缀。

        参数:
            self: 对象实例
            s1 (str): 第一个输入字符串
            s2 (str): 第二个输入字符串

        返回值:
            float: 两个字符串的余弦相似度，取值范围在0.0到1.0之间。
                   返回0.0的情况包括：任一字符串为空；计算时出现除零错误。
                   返回1.0的情况包括：标准化且去除前缀后两个字符串完全相同。
        """
        # 检查输入字符串是否为空，如果任一为空则直接返回0
        if s1 == "" or s2 == "":
            return 0
        # 将字符串转为小写以进行大小写不敏感的比较
        s1 = s1.lower()
        s2 = s2.lower()
        # 如果标准化后两个字符串完全相同，直接返回1
        if s1 == s2:
            return 1
        # 去除字符串开头的"new"前缀（如果存在）
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
        # 计算余弦相似度，避免除零错误
        result = dot_product / (norm1 * norm2) if norm1 * norm2 > 0 else 0.0
        #print(f"余弦相似度: {s1}, {s2}, {result}")
        return result

    def find_centerOnResult(self, result):
        print(f"找中心: {result}")
        if result is None:
            raise CantFindNameError(f"找不到None的中心!")
        l_coordinate = result[0]
        #通过计算四个顶点的x和y坐标的平均值来计算四边形的中心点
        l_x = [vertex[0] for vertex in l_coordinate]
        l_y = [vertex[1] for vertex in l_coordinate]
        center_x = sum(l_x) // 4
        center_y = sum(l_y) // 4
        return (center_x, center_y)
    
    def find_nameOnResult(self, l_result, t_name, mode="result", sameOnly=False, includeSimilarity=False):
        """
        在结果列表中查找与目标名称匹配的结果。
    
        功能说明：
        1. 支持精确匹配和余弦相似度匹配两种模式
        2. 可返回匹配结果、相似度分数或两者组合
        3. 支持单个字符串或多个名称（元组）的匹配
    
        参数说明：
        - self: 实例对象自身
        - l_result: 嵌套的结果列表，每个元素是一个结果子列表
        - t_name: 要查找的目标名称，可以是字符串或字符串元组
        - mode: 返回模式，"result"返回结果对象，"name"返回原始目标名称
        - sameOnly: 是否只进行精确匹配，默认为False
        - includeSimilarity: 是否在返回结果中包含相似度分数，默认为False
    
        返回值：
        - 匹配的结果对象（根据mode参数）
        - 如果includeSimilarity为True，返回(结果对象, 相似度)元组
        - 如果没有匹配结果，返回None
        """
        def returnResult(result, similarity = 1):
            """内部函数：根据模式构造返回结果"""
            if mode == "result":
                output = result  # 返回匹配的结果对象
            else:
                output = returnItem  # 返回原始目标名称
            if includeSimilarity:
                output = (output, similarity)  # 包含相似度时打包成元组
            return output
    
        # 处理目标名称参数，统一转换为元组格式以便后续处理
        returnItem = t_name  # 保存原始目标名称
        if isinstance(t_name, str):
            t_name = (t_name,)  # 将单个字符串转换为元组
        elif not isinstance(t_name, tuple):
            raise ValueError(f"t_name必须是字符串或元组，当前类型为{type(t_name)}")
    
        # 第一阶段：精确匹配（全字匹配）
        # 遍历结果列表，查找与目标名称完全相同的结果
        for l in l_result:
            if l is None:
                continue  # 跳过空的子列表
            for result in l:
                for name in t_name:
                    # 检查结果名称与目标名称是否完全相等
                    if result[1][0] == name:
                        return returnResult(result)
    
        # 如果只允许精确匹配，则在此时返回None
        if sameOnly:
            return None
    
        # 第二阶段：余弦相似度匹配
        # 使用余弦相似度算法寻找最相似的结果（相似度阈值0.5）
        maxCosine = -1  # 初始化最大相似度为-1
        bestResult = None  # 初始化最佳匹配结果
        for l in l_result:
            if l is None:
                continue
            for result in l:
                for name in t_name:
                    # 计算名称之间的余弦相似度
                    similarity = self.cosine_similarity(name, result[1][0])
                    # 更新最佳匹配结果（相似度需大于当前最大值且超过阈值0.5）
                    if similarity > maxCosine and similarity > 0.5:
                        maxCosine = similarity
                        bestResult = result
                        returnItem = t_name  # 记录原始目标名称
        # 如果找到满足条件的相似结果，返回最佳匹配
        if maxCosine > 0.5 and bestResult is not None:
            return returnResult(bestResult, maxCosine)
    
        # 第三阶段：不完全匹配（包含匹配）
        # 查找目标名称是否是结果名称的子字符串
        for l in l_result:
            if l is None:
                continue
            for result in l:
                for name in t_name:
                    # 检查目标名称是否包含在结果名称中
                    if name in result[1][0]:
                        return returnResult(result, 0.01)  # 返回很低的相似度分数
    
        # 所有匹配尝试均失败，返回None
        #raise CantFindNameError(f"找不到{name}")
        return None

    def getTag(self, img):
        """本来想做位置记录裁剪优化，但是裁的话很容易因为tag字数不一而裁不对
        if self.l_tagCoordinates is None:
            l_result = ocr_ch.ocr(img)
            l_correctResult = []
            for tag in self.l_tags:
                result = self._findOnResult(l_result, tag)
                if result is not None:
                    l_correctResult.append(result)
            self.l_tagCoordinates = [(result[0][0] + [result[0][2][0] - result[0][0][0], result[0][2][1] - result[0][0][1]]) for result in l_correctResult]
        l_tags = []
        for region in self.l_tagCoordinates:
            imgPart = self.cropping(img, region, mode="pixel")
            l_result = self.ocr(imgPart)
            for l in l_result:
                for result in l:
                    if result[1][0] in self.l_tags:
                        l_tags.append(result[1][0])
        #"""
        #"""不优化的版本
        img = self.cropping(img, region_tag, mode="percent")
        l_buttons = self.find_smallRegionsOnImg(img)
        #print(f"找到的按钮: {len(l_buttons)}个")
        l_tags = []
        for img in l_buttons:
            l_result = self.ocr(img)
            for tag in self.l_tags:
                t_result = self.find_nameOnResult(l_result, tag, sameOnly=False, includeSimilarity=True)
                log.logger.debug(f"{tag}匹配ocr的结果: {t_result}")
                if t_result is not None:
                    l_tags.append(t_result)
        #"""
        log.logger.info(f"所有匹配的ocr结果: {l_tags}")
        #取相似度最高的5个
        return [t_result[0][1][0] for t_result in sorted(l_tags, key=lambda x: x[1], reverse=True)[:5]]

    def getAgent(self, img):
        """
        从图像中识别并返回最可能的智能体名称。

        功能：对输入的图像进行区域裁剪和OCR识别，通过与候选智能体列表进行匹配和相似度计算，
             返回最可能的智能体名称（中文优先）。
        参数：
            img: 待处理的图像数据。
        返回值：
            str: 识别到的智能体名称（可能是中文或英文），如果未找到符合条件的智能体则返回 None。
        """
        # 对图像进行裁剪，只保留智能体区域（使用百分比模式）
        img = self.cropping(img, region_agent, mode="percent")
        # 对裁剪后的图像执行OCR识别
        l_result = self.ocr(img)
        d_acceptName = {}
        # 遍历所有候选智能体
        for t_agent in self.l_agents:
            # 在OCR结果中查找当前智能体的名称
            result = self.find_nameOnResult(l_result, t_agent)
            # 如果找到匹配项，则在字典中记录该名称出现的次数
            if result is not None:
                if result[1][0] not in d_acceptName:
                    d_acceptName[result[1][0]] = 1
                else:
                    d_acceptName[result[1][0]] += 1
        # 如果没有找到任何匹配的智能体名称，则返回None
        if d_acceptName == {}:
            return None
        # 获取出现次数最多的名字作为最可能的识别结果
        possibleName = max(d_acceptName, key=d_acceptName.get)
        maxSimilarity = -1
        bestResult = None
        # 再次遍历所有候选智能体，计算余弦相似度以找到最匹配的智能体
        for t_agent in self.l_agents:
            # 遍历当前智能体的所有可能名称（可能是中英文名列表）
            for name in t_agent:
                # 计算可能的名字与当前名字之间的余弦相似度
                similarity = self.cosine_similarity(possibleName, name)
                # 记录最大相似度及其对应的智能体
                if similarity > maxSimilarity:
                    maxSimilarity = similarity
                    bestResult = t_agent
        # 打印调试信息：最大相似度和最佳结果
        print(f"最大相似度: {maxSimilarity}, 最佳结果: {bestResult}")
        # 如果最大相似度超过阈值且找到了最佳结果，则进行名称转换和返回
        if maxSimilarity > 0.5 and bestResult is not None:
            # 构建中文名列表和英文名列表，以便进行名称转换
            l_zh = [t_name[0] for t_name in self.l_agents]
            l_en = [t_name[1] for t_name in self.l_agents]
            name = bestResult[0]
            # 如果最佳结果中的名字在英文名列表中，则返回对应的中文名；否则直接返回该名字
            if name in l_en:
                return l_zh[l_en.index(name)]
            return name
        # 如果相似度不足或未找到有效结果，则返回None
        return None
#==============================
class Simulator:
    def __init__(self, log_dir: str = "log", resource_dir: str = "."):
        """
        初始化
        :param log_dir: 日志目录
        :param resource_dir: 资源目录
        """
        self.adb_path = None
        self.device_addr = None
        self.minitouch_proc = None
        self.minitouch_socket = None
        self.screen_size = None
        
        # 设置资源目录
        self.resource_dir = resource_dir
        self._setup_resource_dir()
        
        # 设置日志
        self.log_dir = log_dir
        os.makedirs(log_dir, exist_ok=True)
        
        # 设置日志格式
        log_file = os.path.join(log_dir, f"core_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        
    def _setup_resource_dir(self):
        """设置资源目录结构"""
        # 创建minitouch目录
        minitouch_dir = os.path.join(self.resource_dir, "minitouch")
        os.makedirs(minitouch_dir, exist_ok=True)
        
        # 创建各架构目录
        archs = ["x86_64", "x86", "arm64-v8a", "armeabi-v7a", "armeabi"]
        for arch in archs:
            os.makedirs(os.path.join(minitouch_dir, arch), exist_ok=True)
        
    def find_adb_path(self) -> Optional[str]:
        """
        查找adb路径
        :return: adb路径或None
        """
        """
        try:
            # 1. 首先尝试从MUMU模拟器注册表项查找
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\NetEase\\MuMuPlayer") as key:
                mumu_path = winreg.QueryValueEx(key, "InstallDir")[0]
                adb_path = os.path.join(mumu_path, "emulator", "nemu", "vmonitor", "bin", "adb.exe")
                if os.path.exists(adb_path):
                    self.logger.info(f"在MUMU模拟器注册表中找到adb: {adb_path}")
                    return adb_path
        except WindowsError:
            self.logger.debug("未在注册表中找到MUMU模拟器")
            
        try:
            # 2. 尝试从Android SDK注册表项查找
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\\Android SDK Tools") as key:
                sdk_path = winreg.QueryValueEx(key, "Path")[0]
                adb_path = os.path.join(sdk_path, "platform-tools", "adb.exe")
                if os.path.exists(adb_path):
                    self.logger.info(f"在Android SDK注册表中找到adb: {adb_path}")
                    return adb_path
        except WindowsError:
            self.logger.debug("未在注册表中找到Android SDK")
            
        # 3. 尝试从环境变量查找
        for path in os.environ["PATH"].split(os.pathsep):
            adb_path = os.path.join(path, "adb.exe")
            if os.path.exists(adb_path):
                self.logger.info(f"在环境变量中找到adb: {adb_path}")
                return adb_path
                
        # 4. 尝试常见安装路径
        common_paths = [
            r"C:\\Program Files\\Microvirt\\MEmu\\adb.exe",  # MEmu
            r"C:\\Program Files\\Nox\\bin\\nox_adb.exe",     # Nox
            r"C:\\Program Files\\BlueStacks_nxt\\HD-Adb.exe",  # BlueStacks
            r"D:\\Program Files\\Microvirt\\MEmu\\adb.exe",
            r"D:\\Program Files\\Nox\\bin\\nox_adb.exe",
            r"D:\\Program Files\\BlueStacks_nxt\\HD-Adb.exe",
        ]
        
        for path in common_paths:
            if os.path.exists(path):
                self.logger.info(f"在常见路径中找到adb: {path}")
                return path
        """
        self.logger.error("未找到adb路径")
        return None
        
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
                self.logger.error("未找到adb路径")
                return False
                
            # 启动adb server
            self.logger.info("启动adb server")
            #subprocess.run([self.adb_path, "kill-server"], check=True)
            subprocess.run([self.adb_path, "start-server"], check=True)
            
            # 连接设备
            self.device_addr = "127.0.0.1:7555"  # MUMU模拟器默认端口
            self.logger.info(f"连接设备: {self.device_addr}")
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
            self.logger.info(f"屏幕大小: {self.screen_size}")
            
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
            self.logger.info(f"屏幕方向: {self.orientation*90}度")
            
            # 获取CPU架构
            result = subprocess.run(
                [self.adb_path, "-s", self.device_addr, "shell", "getprop ro.product.cpu.abi"],
                capture_output=True,
                text=True,
                check=True
            )
            cpu_abi = result.stdout.strip()
            self.logger.info(f"设备CPU架构: {cpu_abi}")
            
            # 设置minitouch
            minitouch_dir = os.path.join(self.resource_dir, "minitouch")
            minitouch_path = os.path.join(minitouch_dir, cpu_abi, "minitouch")
            
            if not os.path.exists(minitouch_path):
                self.logger.error(f"找不到minitouch文件: {minitouch_path}")
                return True  # 即使minitouch不存在也返回True，因为可以使用input命令
                
            try:
                # 推送minitouch到设备
                #"""
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
                
                #"""
                # 启动minitouch
                self.minitouch_proc = subprocess.Popen([
                    self.adb_path, "-s", self.device_addr, "shell",
                    "/data/local/tmp/minitouch"
                ])
                
                #time.sleep(1)  # 等待minitouch启动
                
                if self.minitouch_proc.poll() is not None:
                    self.logger.error("minitouch启动失败")
                else:
                    self.logger.info("minitouch启动成功")
                    
            except Exception as e:
                self.logger.error(f"设置minitouch失败: {e}")
                # 清理minitouch相关资源
                self.cleanup()
                
            return True
            
        except Exception as e:
            self.logger.error(f"连接失败: {e}")
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
            a, b = x, y
        elif self.orientation == 1:  # 90度
            a, b = self.screen_size[0] - y, x
        elif self.orientation == 2:  # 180度
            a, b = self.screen_size[1] - x, self.screen_size[0] - y
        elif self.orientation == 3:  # 270度
            a, b = y, self.screen_size[1] - x
        return int(a), int(b)
            
    def click(self, x: int, y: int, press_time: int = 50) -> bool:
        """
        点击指定坐标
        :param x: x坐标
        :param y: y坐标
        :param press_time: 按下时间(毫秒)，默认50ms
        :return: 是否点击成功
        """
        try:
            # 转换坐标
            conv_x, conv_y = self._convert_coordinates(x, y)
            self.logger.debug(f"点击坐标: ({x}, {y}) -> ({conv_x}, {conv_y}), 按下时间: {press_time}ms")
            
            if self.minitouch_proc and self.minitouch_proc.poll() is None and True:
                # 使用minitouch进行点击
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(('127.0.0.1', 1111))
                    # 按下
                    s.sendall(f"d 0 {conv_x} {conv_y} 50\nw {press_time}\nu 0\nc\n".encode())
                    # 额外延迟
                    #time.sleep(0.5)  # 额外延迟
                    return True
            else:
                # 回退到input命令
                self.logger.debug("minitouch未启动，使用input命令")
                subprocess.run([
                    self.adb_path, "-s", self.device_addr, "shell",
                    f"input swipe {conv_x} {conv_y} {conv_x} {conv_y} {press_time}"  # 使用swipe模拟长按
                ], check=True)
                time.sleep(0.05)  # 额外延迟
                return True
        except Exception as e:
            self.logger.error(f"点击失败: {e}")
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
            # 转换坐标
            conv_start_x, conv_start_y = self._convert_coordinates(start_x, start_y)
            conv_end_x, conv_end_y = self._convert_coordinates(end_x, end_y)
            self.logger.debug(f"滑动: ({start_x}, {start_y}) -> ({end_x}, {end_y}) => ({conv_start_x}, {conv_start_y}) -> ({conv_end_x}, {conv_end_y}), 持续时间: {duration}ms")
            
            if self.minitouch_proc and self.minitouch_proc.poll() is None and True:
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
                    #s.sendall(f"m 0 {conv_end_x} {conv_end_y} 50\nc\n".encode())
                    #time.sleep(0.05)  # 终点停留50ms
                    
                    # 抬起
                    s.sendall("u 0\nc\n".encode())
                    time.sleep(0.05)  # 额外延迟
                    return True
            else:
                # 回退到input命令
                self.logger.debug("minitouch未启动，使用input命令")
                subprocess.run([
                    self.adb_path, "-s", self.device_addr, "shell",
                    f"input swipe {conv_start_x} {conv_start_y} {conv_end_x} {conv_end_y} {duration}"
                ], check=True)
                time.sleep(0.05)  # 额外延迟
                return True
        except Exception as e:
            self.logger.error(f"滑动失败: {e}")
            return False
            
    def screenshot(self, retries: int = 3) -> Optional[np.ndarray]:
        """
        截图
        :param retries: 重试次数
        :return: 截图数据或None
        """
        self.logger.debug("开始截图")
        
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
                    self.logger.debug("截图成功")
                    return img
                else:
                    self.logger.warning(f"截图解码失败，重试 {i+1}/{retries}")
            except subprocess.CalledProcessError as e:
                self.logger.error(f"截图失败: {e}")
                if i < retries - 1:
                    time.sleep(1)  # 等待1秒后重试
                continue
            except Exception as e:
                self.logger.error(f"截图时发生未知错误: {e}")
                if i < retries - 1:
                    time.sleep(1)
                continue
        
        self.logger.error("截图失败，已达到最大重试次数")
        return None

    def cleanup(self):
        """清理资源"""
        try:
            # 关闭socket连接
            if hasattr(self, "minitouch_socket") and self.minitouch_socket:
                self.minitouch_socket.close()
                print("minitouch_socket已关闭")
            
            # 终止子进程
            if hasattr(self, "minitouch_proc") and self.minitouch_proc:
                self.minitouch_proc.terminate()
                self.minitouch_proc.wait()
                print("minitouch_proc已终止")
            
            # 移除端口转发
            if hasattr(self, "device_addr") and self.device_addr:
                try:
                    subprocess.run(
                        [self.adb_path, "-s", self.device_addr, "forward", "--remove", "tcp:1111"],
                        capture_output=True,
                        check=True
                    )
                    print("端口转发已移除")
                except Exception as e:
                    print(f"移除端口转发时发生错误: {str(e)}")
                    
                # 删除推送的文件
                try:
                    subprocess.run(
                        [self.adb_path, "-s", self.device_addr, "shell", "rm", "/data/local/tmp/minitouch"],
                        capture_output=True,
                        check=True
                    )
                    print("推送的minitouch文件已删除")
                except Exception as e:
                    print(f"删除推送的minitouch文件时发生错误: {str(e)}")
        except Exception as e:
            print(f"清理时发生错误: {str(e)}")

    def __del__(self):
        """析构函数"""
        self.cleanup() 
#==============================
class MUMU(Simulator):
    def __init__(self):
        """初始化MUMU模拟器操作类"""
        super().__init__(log_dir="log", resource_dir=".")
        
        # 连接设备
        if not self.connect(adb_path=ADB_PATH):
            raise ConnectionError("无法连接到设备")

    def find_nameOnScreen(self, name):
        """
        在屏幕上查找指定文字
        :param name: 要查找的文字
        :return: OCR识别结果
        """
        print(f"在窗口内查找: {name}")
        img = self.screenshot()
        # 使用MAA的OCR功能
        results = tool.ocr(img)
        # 过滤并格式化结果
        filtered_results = []
        for text, score, rect in results:
            if name in text:
                x, y, w, h = rect
                filtered_results.append(((y, y+h), (x, x+w), text, score))
        return filtered_results
    
    def click_text(self, name=None, retry=3):
        """
        点击指定文字位置
        :param name: 要点击的文字
        :param retry: 重试次数
        """
        print(f"点击: {name}, 剩余重试次数: {retry}")
        try:
            if name == "开始招募":
                r1 = self.find_nameOnScreen("可获得的干员")
                r2 = self.find_nameOnScreen("招募预算")
                if not r1 or not r2:
                    raise Exception("找不到目标文字")
                x = r1[0][1][0]  # 第一个匹配结果的x坐标
                y = r2[0][0][1]  # 第二个匹配结果的y坐标
                self.click(x, y)
                return
            
            if name is None:
                # 点击屏幕中心
                left, top, right, bottom = self.screen_size
                self.click((left+right)//2, (top+bottom)//2)
                return
            
            # 查找文字位置
            results = self.find_nameOnScreen(name)
            if not results:
                raise Exception(f"找不到文字: {name}")
            
            # 计算中心点坐标
            center = tool.find_centerOnResult(results)
            self.click(*center)
            
        except Exception as e:
            if retry <= 0:
                raise e
            retry -= 1
            self.click(name, retry)
    
    def to_rightPage(self):
        """向右翻页"""
        print(f"向右翻页")
        y, x = self.screen_size
        x1 = x/7
        y_2 = y/2
        self.swipe(x1*6, y_2, x1, y_2)
    
    def to_leftPage(self):
        """向左翻页"""
        print(f"向左翻页")
        y, x = self.screen_size
        x1 = x/7
        y_2 = y/2
        self.swipe(x1, y_2, x1*6, y_2)

    def getTag(self):
        #截屏
        img = self.screenshot()
        l_tags = tool.getTag(img)
        if len(l_tags) == 5:
            return l_tags
        #找不到Tag
        while True:
            name = input(f"找不到tag,需要人工协助,请输入tag,逗号分隔:")
            l_tags = name.split(",")
            admit = input(f"请确认:{l_tags} 任意输入取消,Enter确认:")
            if admit == "":
                break
        print(f"找到的tag: {l_tags}")
        return l_tags

    def getAgent(self):
        #截屏
        img = self.screenshot()
        agent = tool.getAgent(img)
        if agent is not None:
            return agent
        #找不到干员
        while True:
            name = input(f"找不到干员,需要人工协助,请输入干员中文名称:")
            admit = input(f"请确认:{name} 任意输入取消,Enter确认:")
            if admit == "":
                break
        print(f"找到的干员: {name}")
        return name
#==============================
class Main:
    def __init__(self):
        self.mumu = MUMU()

    def record(self, item, file=None):
        """将项目记录到指定文件中。

        功能：打印录入信息，确保文件存在，将项目转换为字符串后追加到文件。
        参数：
            self: 类实例
            item: 要记录的项目，可以是列表或字符串
            file: 文件路径，默认为"#record.txt"
        返回值：无
        """
        print(f"录入: {item}")  # 打印录入信息
        if file is None:  # 如果文件路径未指定
            file = "#record.txt"  # 使用默认文件"#record.txt"
        if not CreatPath(file).exists():  # 检查文件是否存在
            open(file, "w").close()  # 如果不存在，创建空文件
        if isinstance(item, list):  # 如果item是列表
            s_record = "!".join(item)  # 用"!"连接列表元素成字符串
        if isinstance(item, str):  # 如果item是字符串
            s_record = item  # 直接使用item作为记录字符串
        with open(file, 'a', encoding='utf-8') as f:  # 以追加模式打开文件，指定UTF-8编码
            f.write(s_record + "\n")  # 写入记录并添加换行符
    
    def load(self, file=None):
        """加载记录文件并解析其内容。
        参数:
            file (str, optional): 要加载的文件路径。如果未提供，则默认使用"#record.txt"。
        返回:
            list: 解析后的记录列表。每条记录根据是否包含"!"会被拆分为列表元素，否则作为一个字符串元素。
        """
        if file is None:
            file = "#record.txt"  # 如果未指定文件路径，则使用默认文件名
        with open(file, 'r', encoding='utf-8') as f:  # 以读取模式打开文件，指定UTF-8编码
            record = f.read()  # 读取文件全部内容到字符串
        l_record = record.split("\n")  # 按换行符分割成记录列表
        l_output = []  # 初始化用于存储最终结果的列表
        for record in l_record:  # 遍历每条记录
            if "!" in record:  # 如果记录中包含感叹号"!"
                l_output.append(record.split("!"))  # 按"!"分割，并将结果列表添加到输出中
            else:
                l_output.append(record)  # 否则，将整条记录作为一个字符串元素添加
        print(f"加载结果: {l_output}")  # 打印加载结果用于调试
        return l_output  # 返回解析后的列表

    #招募
    def recruit(self):
        """
        执行一次公开招募操作，获取招募标签并返回。

        该方法模拟游戏中的公开招募流程，包括点击相关按钮、等待页面响应、收集标签数据。
        所有参数通过实例变量传入（无显式参数）。

        Returns:
            list: 本次招募获得的干员标签列表。
        """
        print(f"招募一次开始")
        # 点击加号按钮，进入招募界面
        self.mumu.click("开始招募干员")
        # 等待界面加载完成
        time.sleep(0.5)
        # 获取当前页面的干员标签列表
        l_tag = self.mumu.getTag()
        # 点击开始公招按钮，启动倒计时
        self.mumu.click("开始招募")
        time.sleep(0.5)
        # 点击停止招募按钮，取消本次招募
        self.mumu.click("停止招募")
        time.sleep(0.5)
        # 再次点击停止招募以确认取消（可能为二次确认弹窗）
        self.mumu.click("停止招募")
        time.sleep(0.5)
        print(f"招募一次结束")
        return l_tag

    #寻访
    def draw(self):
        print(f"寻访一次开始")
        # 点击单抽
        time.sleep(0.7)
        self.mumu.click("寻访一次")
        time.sleep(0.6)
        # 点击确认
        self.mumu.click("确认")
        time.sleep(1.2)
        # 点击skip
        self.mumu.click("SKIP")
        time.sleep(1)
        # 收集数据
        agent = self.mumu.getAgent()
        time.sleep(1)
        # 点击任意位置回到抽卡界面
        self.mumu.click("凭证")
        print(f"寻访一次结束")
        return agent

    #垫卡模式
    def mode_pad(self):
        """该方法用于执行卡池翻页操作。通过用户输入确定卡池位置，循环执行招募、翻页和抽取。

        参数:
            self: 当前对象实例

        返回值:
            无
        """
        pass  # 占位符，由于代码逻辑在字符串中，此方法实际上不执行操作
        """
        print('请输入目标卡池为第几个卡池（如：1，2等）并划至公招界面')
        num = int(input('输入：'))
        try:
            while True:
                self.recruit()
                for i in range(num):
                    self.mumu.to_rightPage()
                self.draw()
                for i in range(num):
                    self.mumu.to_leftPage()
        """

    def mode_recruit(self):
        """开启招募模式，持续进行招募并记录。

        该方法打印开始消息，然后进入无限循环，不断调用招募方法并记录结果。

        参数:
            self: 类的实例，用于访问其他方法。

        返回:
            无返回值。
        """
        print(f"招募模式开始")  # 打印招募模式开始的消息
        while True:  # 进入无限循环，持续执行招募和记录操作
            l_tag = self.recruit()  # 调用招募方法，获取标签
            self.record(l_tag)  # 记录获取到的标签

    def mode_draw(self):
        """
        功能：启动抽卡模式，持续执行抽卡并记录过程。
        参数：无（除self外）
        返回值：无
        """
        print(f"抽卡模式开始")  # 打印抽卡模式开始的提示信息
        while True:  # 创建无限循环，持续执行抽卡流程
            agent = self.draw()  # 调用draw方法进行一次抽卡，获取抽到的代理人对象
            self.record(agent)  # 调用record方法记录本次抽到的代理人

    def record_fromDir(self, dir, func_sortKey=None):
        """
        从指定目录中批量读取JSON文件和图片文件，并依次录入记录。
    
        功能：
            遍历给定目录下的所有文件，根据文件类型分别调用相应的录入方法。
            对于JSON文件调用record_fromJson方法，对于图片文件调用record_fromImage方法。
            默认会根据文件名中的数字部分进行排序。
        
        参数：
            dir (str): 需要读取的目录路径。
            func_sortKey (callable, optional): 用于对文件列表排序的函数。默认根据文件名中的数字部分排序。
        
        返回值：
            None: 该方法没有返回值，但会执行录入操作并打印相关信息。
        """
        print(f"从目录{dir}中录入")
    
        # 如果没有提供排序函数，则使用默认的基于文件名数字部分的排序函数
        if func_sortKey is None:
            def func_sortKey(x):
                # 提取文件名中所有数字字符并组合成字符串
                s_output = "".join([char for char in x.stem if char.isdigit()])
                # 将提取的数字字符串转换为整数用于排序
                return int(s_output)
    
        # 获取目录下所有文件，并过滤掉目录只保留文件
        l_file = [file for file in CreatPath(dir).iterdir() if file.is_file()]
    
        # 使用指定的排序函数对文件列表进行排序
        l_file.sort(key=func_sortKey)
    
        # 遍历排序后的每个文件
        for file in l_file:
            # 如果是JSON文件，则使用JSON录入方法
            if file.suffix == "json":
                self.record_fromJson(str(file))
            else:
                try:
                    # 尝试将文件作为图片读取
                    img = cv2.imread(str(file))
                except Exception as e:
                    # 如果读取失败，打印错误信息并跳过当前文件
                    print(f"文件{file}既不是json也不是图片！")
                    print(e)
                    continue
            
                # 使用图片录入方法处理读取到的图片
                self.record_fromImage(img, str(file))

    def record_fromImage(self, img, file):
        print(f"从图片{file}中录入")
        #log.img(img)
        l_tags = tool.getTag(img)
        agent = tool.getAgent(img)
        if agent is not None:
            self.record(agent)
        elif len(l_tags) == 5:
            self.record(l_tags)
        else:
            print(f"图片{file}无法匹配！")

    def record_fromJson(self, jsonFile):
        """从指定的JSON文件中读取数据，并提取所有代理人（agent）的名字，然后以逆序调用record方法。
    
        Args:
            jsonFile (str): 要读取的JSON文件路径。
    
        Returns:
            None: 该方法不返回任何值，但会调用record方法。
        """
        print(f"从json文件{jsonFile}中录入")  # 打印开始从JSON文件录入的信息
        with open(jsonFile, 'r', encoding='utf-8') as f:  # 以UTF-8编码打开JSON文件
            data = json.load(f)  # 解析JSON文件内容为Python字典
        l_agents = []  # 初始化一个空列表，用于存储代理人名称
        for entry in data['data']['list']:  # 遍历数据中的列表条目
            for char in entry['chars']:  # 遍历每个条目中的字符（代理人）列表
                l_agents.append(char['name'])  # 将代理人的名称添加到l_agents列表中
        for agent in l_agents[::-1]:  # 以逆序遍历代理人名称列表
            self.record(agent)  # 对每个代理人调用record方法

    def main(self):
        print('''请选择模式并输入相应的选项:
        1.公招模式
        2.抽卡模式
        3.垫卡模式（暂未开放）
        ''')

        option = int(input('输入：'))
        if option == 1:
            self.mode_recruit()

        elif option == 2:
            self.mode_draw()

        elif option == 3:
            self.mode_pad()


tool = Tool()
#tool = Tool(b_ocr=False)

#main = Main()
#main.record_fromDir("0")
print("到底了")
#main.main()


"""
#main.mumu.getAgent(cv2.imread("a.png"))
img = cv2.imread("v.png")
cropedImg = tool.cropping(img, (0.47, 0.67, 0.87, 0.85), mode="percent")
#"""
mumu = MUMU()
time.sleep(1)
mumu.click(1767, 603)
'''
time.sleep(1)
mumu.click(1450,975)
time.sleep(1)
mumu.to_rightPage()
time.sleep(1)
mumu.to_rightPage()
time.sleep(1)
mumu.to_leftPage()
time.sleep(1)
mumu.to_leftPage()
#'''