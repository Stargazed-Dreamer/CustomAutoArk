#pip install paddlepaddle paddleocr opencv-python numpy pywin32
# 会在需要时导入  from paddleocr import PaddleOCR
#==============================
from typing import Optional, List, Tuple, Union
import cv2
import numpy as np
import os
import time
import subprocess
import socket
from dataclasses import dataclass
#==============================
from paddleocr import PaddleOCR
#==============================
ADB_PATH = "D:\\YXArkNights-12.0\\shell\\adb.exe"
region_tag = (0.30,0.47,0.66,0.70)
region_agent = (0.45, 0.67, 0.87, 0.85)
#==============================
from data import l_tag0, l_tag1, l_tag2, l_tag3, l_tag4, d_agents
#==============================
class CantFindNameError(Exception):
    pass

class MouseMoveError(Exception):
    pass
#==============================
from log import log_manager

# 使用全局日志管理器
log = log_manager
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
            log.debug("使用GPU模式初始化OCR")
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
        # l_agents -> [(zh, en), (zh, en), ...]
        self.l_agents = [(zh, d_agents[zh]["en"]) for zh in d_agents]
        # l_tags -> ["支援", "辅助干员", ...]
        self.l_tags = l_tag0 + l_tag1 + l_tag2 + l_tag3 + l_tag4

    def ocr(self, cvImg):
        if not self.ocrUseable:
            self.init_ocr()
        result = self.ocr_ch.ocr(cvImg, cls=True)
        """
        for l in result:
            if l is None:
                continue
            for x in l:
                log.debug(f"ocr结果: {x}")
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
        #log.debug(f"裁剪区域: {x}, {y}, {w}, {h}")
        log.img(cvImg[y:h, x:w])
        return cvImg[y:h, x:w]

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

    def find_centerOnResult(self, result):
        log.debug(f"找中心: {result}")
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
        def returnResult(result, similarity = 1):
            if mode == "result":
                output = result
            else:
                output = returnItem
            if includeSimilarity:
                output = (output, similarity)
            return output
        #mode : result or name
        returnItem = t_name
        if isinstance(t_name, str):
            t_name = (t_name,)
        elif not isinstance(t_name, tuple):
            raise ValueError(f"t_name必须是字符串或元组，当前类型为{type(t_name)}")
        #全字匹配
        for l in l_result:
            if l is None:
                continue
            for result in l:
                for name in t_name:
                    if result[1][0] == name:
                        return returnResult(result)
        if sameOnly:
            return None
        #余弦相似匹配
        maxCosine = -1
        bestResult = None
        for l in l_result:
            if l is None:
                continue
            for result in l:
                for name in t_name:
                    similarity = self.cosine_similarity(name, result[1][0])
                    if similarity > maxCosine and similarity > 0.5:
                        maxCosine = similarity
                        bestResult = result
                        returnItem = t_name
        if maxCosine > 0.5 and bestResult is not None:
            return returnResult(bestResult, maxCosine)
        #不完全匹配
        for l in l_result:
            if l is None:
                continue
            for result in l:
                for name in t_name:
                    if name in result[1][0]:
                        return returnResult(result, 0.01)
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
        #log.debug(f"找到的按钮: {len(l_buttons)}个")
        l_tags = []
        for img in l_buttons:
            l_result = self.ocr(img)
            for tag in self.l_tags:
                t_result = self.find_nameOnResult(l_result, tag, sameOnly=False, includeSimilarity=True)
                #log.debug(f"{tag}匹配ocr的结果: {t_result}")
                if t_result is not None:
                    l_tags.append(t_result)
        #"""
        log.info(f"所有匹配的ocr结果: {l_tags}")
        #取相似度最高的5个
        return [t_result[0][1][0] for t_result in sorted(l_tags, key=lambda x: x[1], reverse=True)[:5]]

    def getAgent(self, img):
        img = self.cropping(img, region_agent, mode="percent")
        l_result = self.ocr(img)
        d_acceptName = {}
        for t_agent in self.l_agents:
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
        for t_agent in self.l_agents:
            for name in t_agent:
                similarity = self.cosine_similarity(possibleName, name)
                if similarity > maxSimilarity:
                    maxSimilarity = similarity
                    bestResult = t_agent
        log.info(f"最大相似度: {maxSimilarity}, 最佳结果: {bestResult}")
        if maxSimilarity > 0.5 and bestResult is not None:
            l_zh = [t_name[0] for t_name in self.l_agents]
            l_en = [t_name[1] for t_name in self.l_agents]
            name = bestResult[0]
            if name in l_en:
                return l_zh[l_en.index(name)]
            return name
        return None
#==============================
class Simulator:
    def __init__(self, resource_dir: str = "resource"):
        """
        初始化
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
                    log.error("minitouch启动失败")
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
                    # 额外延迟
                    time.sleep(0.05)  # 50ms额外延迟
                    return True
            else:
                # 回退到input命令
                log.debug("minitouch未启动，使用input命令")
                subprocess.run([
                    self.adb_path, "-s", self.device_addr, "shell",
                    f"input swipe {conv_x} {conv_y} {conv_x} {conv_y} {press_time}"  # 使用swipe模拟长按
                ], check=True)
                time.sleep(0.05)  # 额外延迟
                return True
        except Exception as e:
            log.error(f"点击失败: {e}")
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
                    time.sleep(0.05)  # 额外延迟
                    return True
            else:
                # 回退到input命令
                log.debug("minitouch未启动，使用input命令")
                subprocess.run([
                    self.adb_path, "-s", self.device_addr, "shell",
                    f"input swipe {conv_start_x} {conv_start_y} {conv_end_x} {conv_end_y} {duration}"
                ], check=True)
                time.sleep(0.05)  # 额外延迟
                return True
        except Exception as e:
            log.error(f"滑动失败: {e}")
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
            if hasattr(self, "minitouch_socket") and self.minitouch_socket:
                self.minitouch_socket.close()
                self.minitouch_socket = None
            
            if hasattr(self, "minitouch_proc") and self.minitouch_proc:
                self.minitouch_proc.terminate()
                self.minitouch_proc = None
            
            if hasattr(self, "device_addr") and self.device_addr:
                subprocess.run(
                    [self.adb_path, "-s", self.device_addr, "forward", "--remove", "tcp:1111"],
                    capture_output=True
                )
                subprocess.run(
                    [self.adb_path, "-s", self.device_addr, "shell", "rm", "/data/local/tmp/minitouch"],
                    capture_output=True
                )
        except Exception as e:
            log.debug(f"清理时发生错误: {e}")

    def __del__(self):
        """析构函数"""
        self.cleanup() 
#==============================
@dataclass
class PredictionResult:
    """AI预测结果"""
    recommended_action: str  # 'recruit' 或 'draw'
    confidence_score: float  # 0-1之间的置信度
    expected_value: float    # 预期收益
    reasoning: str          # 预测理由

class AIPredictor:
    """AI预测器接口"""
    def __init__(self, model_path: str = None):
        self.model_path = model_path
        self._model = None
    
    @property
    def model(self):
        """懒加载模型"""
        if self._model is None and self.model_path:
            # TODO: 实现LSTM模型加载
            pass
        return self._model
    
    def predict(self, history_data: List[dict]) -> PredictionResult:
        """
        根据历史数据预测下一步操作
        :param history_data: 历史操作数据
        :return: 预测结果
        """
        if not self.model:
            return PredictionResult(
                recommended_action="recruit",
                confidence_score=0.0,
                expected_value=0.0,
                reasoning="AI模型未加载"
            )
        # TODO: 实现预测逻辑
        pass

class MUMU(Simulator):
    def __init__(self, adb_path = ADB_PATH):
        """初始化MUMU模拟器操作类"""
        super().__init__(resource_dir=".")
        self._connected = False
        self._ai_predictor = None
        self.adb_path = adb_path

        if not self.ensure_connected():
            raise ConnectionError("无法连接到设备")
    
    @property
    def ai_predictor(self):
        """懒加载AI预测器"""
        if self._ai_predictor is None:
            self._ai_predictor = AIPredictor()
        return self._ai_predictor
    
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
    
    def find_nameOnScreen(self, name: str) -> List[Tuple]:
        """
        在屏幕上查找指定文字
        :param name: 要查找的文字
        :return: OCR识别结果
        """
        self.ensure_connected()
        log.info(f"在窗口内查找: {name}")
        img = self.screenshot()
        results = tool.ocr(img)
        filtered_results = []
        for text, score, rect in results:
            if name in text:
                x, y, w, h = rect
                filtered_results.append(((y, y+h), (x, x+w), text, score))
        return filtered_results
    
    def click_text(self, name: Optional[str] = None, retry: int = 3):
        """
        点击指定文字位置
        :param name: 要点击的文字
        :param retry: 重试次数
        """
        self.ensure_connected()
        log.debug(f"点击: {name}, 剩余重试次数: {retry}")
        try:
            if name == "开始招募":
                r1 = self.find_nameOnScreen("可获得的干员")
                r2 = self.find_nameOnScreen("招募预算")
                if not r1 or not r2:
                    raise Exception("找不到目标文字")
                x = r1[0][1][0]
                y = r2[0][0][1]
                self.click(x, y)
                return
            
            if name is None:
                left, top, right, bottom = self.screen_size
                self.click((left+right)//2, (top+bottom)//2)
                return
            
            results = self.find_nameOnScreen(name)
            if not results:
                raise Exception(f"找不到文字: {name}")
            
            center = tool.find_centerOnResult(results)
            self.click(*center)
            
        except Exception as e:
            if retry <= 0:
                raise e
            retry -= 1
            self.click(name, retry)
    
    def to_rightPage(self):
        """向右翻页"""
        self.ensure_connected()
        log.debug("向右翻页")
        left, top, right, bottom = self.screen_size
        x = right - left
        y = bottom - top
        x1 = x/3
        y_2 = y/2
        self.swipe(x1*2, y_2, x1, y_2)
    
    def to_leftPage(self):
        """向左翻页"""
        self.ensure_connected()
        log.debug("向左翻页")
        left, top, right, bottom = self.screen_size
        x = right - left
        y = bottom - top
        x1 = x/3
        y_2 = y/2
        self.swipe(x1, y_2, x1*2, y_2)

    def getTag(self) -> List[str]:
        """获取标签"""
        self.ensure_connected()
        img = self.screenshot()
        l_tags = tool.getTag(img)
        if len(l_tags) == 5:
            return l_tags
            
        while True:
            name = input("找不到tag,需要人工协助,请输入tag,逗号分隔:")
            l_tags = name.split(",")
            admit = input(f"请确认:{l_tags} 任意输入取消,Enter确认:")
            if admit == "":
                break
        log.info(f"找到的tag: {l_tags}")
        return l_tags

    def getAgent(self) -> Optional[str]:
        """获取干员"""
        self.ensure_connected()
        img = self.screenshot()
        agent = tool.getAgent(img)
        if agent is not None:
            return agent
            
        while True:
            name = input("找不到干员,需要人工协助,请输入干员中文名称:")
            admit = input(f"请确认:{name} 任意输入取消,Enter确认:")
            if admit == "":
                break
        log.info(f"找到的干员: {name}")
        return name
    
    def recruit(self) -> List[str]:
        """执行一次公开招募"""
        log.debug("招募一次开始")
        try:
            # 点击加号
            self.click_text("开始招募干员")
            # 收集数据
            time.sleep(0.5)
            l_tag = self.getTag()
            # 点击开始公招
            self.click_text("开始招募")
            time.sleep(0.5)
            # 点击停止招募
            self.click_text("停止招募")
            time.sleep(0.5)
            # 再次点击停止招募
            self.click_text("停止招募")
            time.sleep(0.5)
            
            log.debug("招募一次结束")
            return l_tag
        except Exception as e:
            log.error(f"招募失败: {str(e)}")
            raise
    
    def draw(self) -> Optional[str]:
        """执行一次寻访"""
        log.debug("寻访一次开始")
        try:
            # 点击单抽
            time.sleep(0.7)
            self.click_text("寻访一次")
            time.sleep(0.6)
            # 点击确认
            self.click_text("确认")
            time.sleep(1.2)
            # 点击skip
            self.click_text("SKIP")
            time.sleep(1)
            # 收集数据
            agent = self.getAgent()
            time.sleep(1)
            # 点击任意位置回到抽卡界面
            self.click_text("凭证")
            
            log.debug("寻访一次结束")
            return agent
        except Exception as e:
            log.error(f"寻访失败: {str(e)}")
            raise

    def get_ai_recommendation(self, history_data: List[dict]) -> PredictionResult:
        """
        获取AI推荐的操作
        :param history_data: 历史操作数据
        :return: AI预测结果
        """
        return self.ai_predictor.predict(history_data)


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