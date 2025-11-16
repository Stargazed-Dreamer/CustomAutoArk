import inspect
import os
import socket
import subprocess
import time
from datetime import datetime
import threading
from enum import Enum
from typing import Optional, Tuple

import cv2
import numpy as np
from PySide6.QtCore import QObject, Signal, Slot

from data import data as DATA
from data_manager import data_manager
from log import log_manager
from tool import tool, error_record
#==============================
ADB_PATH = "D:\\YXArkNights-12.0\\shell\\adb.exe"
IMG_PATH = ".\\img"
region_tag = (0.30,0.47,0.66,0.70)
region_agent = (0.45, 0.67, 0.87, 0.85)
region_history = (0.44, 0.27, 0.71, 0.91)
region_certificate = (0.776, 0.363, 1, 0.9)
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
                result = self.connect(adb_path=self.adb_path)
                if isinstance(result, tuple) and result[0] is False and "device offline" in result[1]:
                    if not self.reset_server(adb_path=self.adb_path):
                        raise ConnectionError("无法连接到设备")
                    result = self.connect(adb_path=self.adb_path)
                if result is False or (isinstance(result, tuple) and result[0] is False):
                    raise ConnectionError("无法连接到设备")
                self._connected = True
                return True
            except Exception as e:
                error_record(e)
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
            error_record(e)
            log.error(f"设备连接丢失: {str(e)}")
            self._connected = False
            self.cleanup()
            return False

    def reset_server(self, adb_path):
        try:
            log.info("尝试重新启动adb server")
            subprocess.run([self.adb_path, "kill-server"], check=True)
            subprocess.run([self.adb_path, "start-server"], check=True)
            return True
        except subprocess.CalledProcessError as e:
            error_record(e)
            log.error(f"重启失败:{e.stderr}")
            return False
        except Exception as e:
            error_record(e)
            log.error(f"重启失败:{e}")
            return False

    def connect(self, adb_path = None) -> bool:
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
            log.info(f"屏幕方向: {self.orientation*90}度")
            
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
                
                #time.sleep(0.4)  # 等待minitouch启动
                
                if self.minitouch_proc.poll() is not None:
                    raise RuntimeError("minitouch启动失败")
                else:
                    log.info("minitouch启动成功")
                    
            except Exception as e:
                error_record(e)
                log.error(f"设置minitouch失败: {e}")
                # 清理minitouch相关资源
                self.cleanup(b_killADB=False)
                
            return True
        except subprocess.CalledProcessError as e:
            error_record(e)
            log.error(f"连接失败:{e.stderr}")
            return False, str(e.stderr)
        except Exception as e:
            error_record(e)
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
            a, b = x, y
        elif self.orientation == 1:  # 90度
            a, b = self.screen_size[0] - y, x
        elif self.orientation == 2:  # 180度
            a, b = self.screen_size[1] - x, self.screen_size[0] - y
        elif self.orientation == 3:  # 270度
            a, b = y, self.screen_size[1] - x
        return int(a), int(b)
            
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
            error_record(e)
            raise ValueError(f"坐标{x}或{y}或按下时间{press_time}不是数字")
        try:
            # 转换坐标
            conv_x, conv_y = self._convert_coordinates(x, y)
            log.debug(f"点击坐标: ({x}, {y}) -> ({conv_x}, {conv_y}), 按下时间: {press_time}ms")
            
            if self.minitouch_proc and self.minitouch_proc.poll() is None:
                # 使用minitouch进行点击
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.connect(('127.0.0.1', 1111))
                    # 禁用Nagle算法，减少延迟
                    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
                    # 按下
                    s.sendall(f"d 0 {conv_x} {conv_y} 50\nc\n".encode())
                    time.sleep(press_time / 1000)  # 转换为秒
                    # 抬起
                    s.sendall("u 0\nc\n".encode())
                    # 短暂延迟确保命令发送完成
                    time.sleep(0.01)
            else:
                # 回退到input命令
                log.debug("minitouch未启动，使用input命令")
                subprocess.run([
                    self.adb_path, "-s", self.device_addr, "shell",
                    f"input swipe {conv_x} {conv_y} {conv_x} {conv_y} {press_time}"  # 使用swipe模拟长按
                ], check=True)
        except Exception as e:
            error_record(e)
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
            error_record(e)
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
                    # 禁用Nagle算法，减少延迟
                    s.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
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
                    # 短暂延迟确保命令发送完成
                    time.sleep(0.01)
            else:
                # 回退到input命令
                log.debug("minitouch未启动，使用input命令")
                subprocess.run([
                    self.adb_path, "-s", self.device_addr, "shell",
                    f"input swipe {conv_start_x} {conv_start_y} {conv_end_x} {conv_end_y} {duration}"
                ], check=True)
        except Exception as e:
            error_record(e)
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
                error_record(e)
                log.error(f"截图失败: {e}")
                if i < retries - 1:
                    time.sleep(1)  # 等待1秒后重试
                continue
            except Exception as e:
                error_record(e)
                log.error(f"截图时发生未知错误: {e}")
                if i < retries - 1:
                    time.sleep(1)
                continue
        
        log.error("截图失败，已达到最大重试次数")
        return None

    def cleanup(self, b_killADB=True):
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
                    error_record(e)
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
                    error_record(e)
                    log.error(f"删除推送的minitouch文件时发生错误: {str(e)}")
            if b_killADB:
                try:
                    subprocess.run([self.adb_path, "kill-server"], check=True)
                    log.info("adb服务已杀死")
                except Exception as e:
                    error_record(e)
                    log.error(f"杀死adb服务时发生错误: {str(e)}")
        except Exception as e:
            error_record(e)
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
    SCREEN_TO_MEM  = "截屏并追加进MEM列表"
    CROP_FROM_MEM  = "裁切MEM列表指定index的图片"
    SAVE_FROM_MEM  = "存储MEM列表指定index的内容"
    # 界面切换操作
    ENTER_SLOT    = "进入指定公招池"
    SWIPE_TO_PAGE = "划动到指定页面"
    #ENTER_GACHA_STATISTICS = "进入当前寻访界面的历史记录"
    # 流程控制任务
    NOP = "无"
    STEP_COMPLETED = "一个步骤已完成" # 用于循环任务阶段性完成后分配下一组任务
    IF = "条件任务组"        # 可选negation参数
    WHILE = "条件循环任务组"  # 可选negation参数
    END = "终止" # 用于单次执行的任务

class Task:
    """任务类，定义单个任务的属性和行为"""
    aimRecruitSlot = 1
    aimGachaPage = 1
    currentPage = 0
    d_imgs = None
    d_reuseableCoordinate = {}
    l_MEM = []

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
        memIndex       = -1,    # MEM操作指定的index
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
        self.memIndex = memIndex
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
                # !!!！！！记得改回来
                """
                if bestNum > 2:
                    raise StopError("最好tag超出阈值，请自己选择")
                """
                if bestNum > 3:
                    l_chosen = []
                    for i in range(3):
                        if l_sorted[i][1] == bestNum:
                            l_chosen.append(l_sorted[i][0])
                        else:
                            break
                    log.debug(f"选择的tag: {l_chosen}")
                    # 点击
                    for tag in l_chosen:
                        self.click_item(self.find_nameOnScreen, tag)
                '''
                l_chosen = []
                for i in range(3):
                    if l_sorted[i][1] == bestNum:
                        l_chosen.append(l_sorted[i][0])
                    else:
                        break
                log.debug(f"选择的tag: {l_chosen}")
                # 点击
                for tag in l_chosen:
                    self.click_item(self.find_nameOnScreen, tag)
                '''
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
                    return (True, TaskType.RECORD_AGENT, agent)
                else:
                    return (False, TaskType.RECORD_AGENT, tool.cropping(img, region_agent, mode="percent"))
            elif self.taskType == TaskType.RECORD_HISTORY_PAGE:
                img = Task.simulator.screenshot()
                l_history, b_flag = tool.getHistory(img)
                log.debug(f"识别到的历史记录: {l_history}, 标志: {b_flag}")
                if b_flag:
                    return (True, TaskType.RECORD_HISTORY_PAGE, l_history)
                else:
                    return (False, TaskType.RECORD_HISTORY_PAGE, (tool.cropping(img, region_history, mode="percent"), l_history))
            elif self.taskType == TaskType.RECORD_SCREEN:
                img = Task.simulator.screenshot()
                # 三种识别挨个判定正确的
                l_tag = tool.getTag(img)
                log.debug(f"屏幕识别结果: tag={l_tag}")
                if len(l_tag) == 5:
                    return (True, TaskType.RECORD_TAG, l_tag)
                l_history, b_flag = tool.getHistory(img)
                log.debug(f"屏幕识别结果: 历史={l_history}, 标志={b_flag}")
                if b_flag:
                    return (True, TaskType.RECORD_HISTORY_PAGE, l_history)
                agent = tool.getAgent(img)
                log.debug(f"屏幕识别结果: 干员={agent}")
                if agent is not None:
                    return (True, TaskType.RECORD_AGENT, agent)
                # 找不到
                return (False, TaskType.RECORD_SCREEN, img)
            elif self.taskType == TaskType.RECORD_HISTORY_FLEX:
                aim = self.param
                log.debug(f"开始记录历史记录，目标数量: {aim}")
                b_less = False
                l_agent = []
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
                        self.click_item(self.find_imgOnScreen, "gachaHistoryButton_right", True)
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
            elif self.taskType == TaskType.SCREEN_TO_MEM:
                log.debug("执行截屏到MEM")
                self.l_MEM.append(Task.simulator.screenshot())
            elif self.taskType == TaskType.CROP_FROM_MEM:
                log.debug("执行从MEM裁切")
                img = self.l_MEM[self.memIndex]
                # self.param = (0.44, 0.27, 0.71, 0.91)
                cropped = tool.cropping(img, self.param, mode="percent")
                self.l_MEM[self.memIndex] = cropped
            elif self.taskType == TaskType.SAVE_FROM_MEM:
                log.debug("执行从MEM存储")
                # self.kwargs = {"mode":"png"}
                # self.kwargs = {"mode":"txt"}
                # self.param = "C:\\Users\\Administrator\\Desktop"
                if "mode" not in self.kwargs:
                    raise ValueError(f"保存模式 'mode' 参数未定义")
                timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S-%f")
                fileName = f"{timestamp}.{self.kwargs['mode']}"
                # 如果路径包含中文，报错
                for i in self.param:
                    if ord(i) > 128:
                        raise ValueError(f"路径包含中文") 
                if not os.path.exists(self.param):
                    os.makedirs(self.param)
                path = os.path.join(self.param, fileName)
                img = self.l_MEM.pop(self.memIndex)
                if self.kwargs["mode"] == "png":
                    cv2.imwrite(path, img)
                    log.debug(f"图片已保存: {path}")
                elif self.kwargs["mode"] == "txt":
                    with open(path, "w") as f:
                        f.write(self.l_MEM[self.memIndex])
                    log.debug(f"文本已保存: {path}")
                else:
                    raise ValueError(f"保存模式{self.kwargs['mode']}未定义")
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
            elif self.taskType == TaskType.IF or self.taskType == TaskType.WHILE:
                log.debug(f"执行条件判断: {self.param}")
                if self.param is True:
                    return (True, TaskType.IF, True)
                elif self.param is False:
                    return (True, TaskType.IF, False)
                elif not isinstance(self.param, str):
                    raise TypeError(f"IF/WHILE 任务的参数必须是True False str中的一种，'{self.param}'是'{type(self.param)}'")
                if callable(getattr(self, self.param)):
                    result = getattr(self, self.param)(*self.args, **self.kwargs)
                    if "negation" in self.kwargs:
                        result = not result
                    log.debug(f"条件判断结果: {result}")
                    return (True, TaskType.IF, result)
                else:
                    raise TypeError(f"IF/WHILE 任务的str参数必须是可调用的，'{getattr(self, self.param)}'是'{type(self.param)}'")
            elif self.taskType == TaskType.END:
                raise RuntimeError("END 任务不应在此处被捕获")
            log.debug(f"任务执行完成: {self.description}")
            return True
        except Exception as e:
            error_record(e)
            raise

    def isOriginiteOnScreen(self, *args, **kwargs):
        result = self.find_nameOnScreen("至纯源石")
        log.debug(f"检查源石: {'存在' if result else '不存在'}")
        if result is None:
            return False
        return True

    def isCertificateOnScreen(self, *args, **kwargs):
        result = self.find_nameOnScreen("凭证")
        log.debug(f"检查凭证: {'存在' if result else '不存在'}")
        if result is None:
            return False
        return True

    def isTextOnScreen(self, *args, **kwargs):
        if "name" not in kwargs:
            raise ValueError("调用的isTextOnScreen函数缺少文本'name'参数")
        result = self.find_nameOnScreen(*args, **kwargs)
        log.debug(f"文本'{kwargs['name']}': {'存在' if result else '不存在'}于截图")
        if result is None:
            return False
        return True

    def isImgOnScreen(self, *args, **kwargs):
        if "name" not in kwargs:
            raise ValueError("调用的isImgOnScreen函数缺少图片路径'name'参数")
        result = self.find_imgOnScreen(*args, b_paddleOutput=False, **kwargs)
        log.debug(f"图片{kwargs['name']}: {'存在' if result else '不存在'}于截图")
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

    def find_nameOnScreen(self, name, limit = 0.7, b_allGet = False, **kwargs):
        """
        在屏幕上查找指定文字
        :param name: 要查找的文字
        :return: OCR识别结果
        """
        Task.simulator.ensure_connected()
        b_sameOnly = False
        if "b_sameOnly" in kwargs and kwargs["b_sameOnly"]:
            b_sameOnly = True
        log.debug(f"查找文字: {name}, 阈值={limit}, 全部获取={b_allGet}, 全字匹配={b_sameOnly}, kwargs:{kwargs}")
        img = Task.simulator.screenshot()
        regionOffset = (0,0)
        if self.region is not None:
            h, w = img.shape[:2]
            regionOffset = (int(self.region[0] * w), int(self.region[1] * h))
            img = tool.cropping(img, self.region, mode="percent")
            log.debug(f"在区域内查找: {self.region}")
        results = tool.ocr(img)
        l_output = []
        for result in results:
            l_position, t_text = result
            if (b_sameOnly and name == t_text[0]) or ((not b_sameOnly) and name in t_text[0]):
                points = [
                    [l_position[0][0]+regionOffset[0], l_position[0][1]+regionOffset[1]],
                    [l_position[1][0]+regionOffset[0], l_position[1][1]+regionOffset[1]],
                    [l_position[2][0]+regionOffset[0], l_position[2][1]+regionOffset[1]],
                    [l_position[3][0]+regionOffset[0], l_position[3][1]+regionOffset[1]],
                ]
                l_output.append([points, result[1]])
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

    def find_imgOnScreen(self, name, limit=0.7, b_allGet=False, b_paddleOutput=True, b_counterexampleMode=True, **kwargs):
        if name not in Task.d_imgs:
            raise KeyError(f"'{name}'可能不存在于识别图片路径中")

        log.debug(f"查找图片: {name}, 阈值={limit}, 全部获取={b_allGet}, 反例模式={b_counterexampleMode}, kwargs:{kwargs}")
        screenshot = Task.simulator.screenshot()
        regionOffset = (0,0)
        if self.region is not None:
            h, w = img.shape[:2]
            regionOffset = (int(self.region[0] * w), int(self.region[1] * h))
            img = tool.cropping(img, self.region, mode="percent")
            log.debug(f"在区域内查找: {self.region}")
        template = Task.d_imgs[name]
        l_results = tool.find_imgOnImg(screenshot, template, match_threshold = limit, b_needTemplate2GRAY = False)
        if b_counterexampleMode and (name + "#") in Task.d_imgs:
            template = Task.d_imgs[name + "#"]
            l_results_c = tool.find_imgOnImg(screenshot, template, match_threshold = limit, b_needTemplate2GRAY = False)
            log.debug(f"反例匹配结果: {l_results_c}")
        else:
            l_results_c = []
        if l_results_c and l_results and (l_results_c[0][1] > l_results[0][1]):
            l_results = []
        log.debug(f"找到结果: {l_results}")
        if len(l_results) == 0:
            return None
        l_output = []
        for result in l_results:
            points = [result[0][0]+regionOffset[0], result[0][1]+regionOffset[1], result[0][2] + regionOffset[0], result[0][3] + regionOffset[1]]
            l_output.append((points, result[1]))
        if b_paddleOutput:
            # 配合paddle的格式
            l_output = [ [[(result[0][0], result[0][1]), None, (result[0][2], result[0][3]), None], result[1]] for result in l_output]
        if b_allGet:
            return l_output
        return l_output[0]

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
            log.debug(f"使用已记录的坐标: ({x}, {y})")
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
            log.debug(f"匹配当前公招栏的位置: ({x}, {y})")
        else:
            #4.常规模式
            x, y = findCoodinate()
            log.debug(f"无条件: ({x}, {y})")
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
        return self.tasks[0].description if hasattr(self.tasks, "description") else None
    
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
                        error_record(e)
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
                if self.current_task.taskType == TaskType.WHILE:
                    if not isinstance(self.tasks[0], list):
                        raise TypeError("WHILE 类型的任务后必须接一个任务列表")
                    if result[2] is True:
                        l = self.tasks.pop(0)
                        selfTaskGroup = [self.current_task, l]
                        self.tasks = l + selfTaskGroup + self.tasks
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
                error_record(e)
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
        error_record(e)
    
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
            self.break_connection()
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
            error_record(e)
            self.device_connected.emit(False)
    
    def break_connection(self):
        try:
            if hasattr(Task, "simulator"):
                del Task.simulator
            if hasattr(self, "task_manager"):
                del self.task_manager
        except Exception as e:
            error_record(e)
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
                elif self.current_mode == OperationMode.RECRUIT:
                    self.taskAdd_recruitEndUp()
                else:
                    self.taskAdd_endUp()
                self.is_running = False
        except Exception as e:
            error_record(e)
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
                    self.update_macro_step("INFO", f"出现罕见tag:{', '.join(rare_tags)}！")
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
                if result in DATA.d_agent and int(DATA.d_agent[result]["star"])+1 == 6:
                    self.update_macro_step("INFO", f"获得六星干员{result}！")
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
                    if agent in DATA.d_agent and int(DATA.d_agent[agent]["star"])+1 == 6:
                        self.update_macro_step("INFO", f"获得六星干员{agent}！")
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
            error_record(e)
            log.error(str(e))
            self.reset_operation()

    @Slot()
    def _on_task_failed(self, error: str):
        """任务失败处理"""
        self.log_with_time("ERROR", f"出现错误：{error}")
        self.reset_operation()

    @execute_tasks
    def taskAdd_recruitEndUp(self):
        return [
            Task(TaskType.ENTER_SLOT, None, post_wait=0.3, description="进入公招池"),
            Task(TaskType.RECORD_TAG, None),
            Task(TaskType.CLICK_IMG, "RecruitRefuse", b_reuse=True, description="点击×退出"),
            Task(TaskType.END, None),
        ]
    @execute_tasks
    def taskAdd_tenModeEndUp(self):
        return [
            Task(TaskType.CLICK_TEXT, "查看详情", b_reuse=True, description="点击查看详情"),
            Task(TaskType.CLICK_TEXT, "查询记录", b_reuse=True, description="点击查询记录"),
            Task(TaskType.RECORD_HISTORY_FLEX, self.gacha_count, pre_wait=0.3, description="记录招募历史"),
            Task(TaskType.CLICK_IMG, "gachaHistoryButton_exit", b_reuse=True, description="点击×退出"),
            Task(TaskType.CLICK_TEXT, None, pre_wait=0.3, description="点击任意位置退出"),
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
            Task(TaskType.ENTER_SLOT, None, post_wait=0.3, description="进入公招池"),
            Task(TaskType.RECORD_TAG, None),
        ]
    @execute_tasks
    def taskAdd_recruit_break(self):
        return [
            Task(TaskType.CLICK_IMG, "RecruitConfirm", b_reuse=True, description="点击对勾开始招募"),
            Task(TaskType.CLICK_TEXT, "停止招募", b_recruitCheck=True, description="点击停止招募"),
            Task(TaskType.CLICK_TEXT, "确认停止", b_recruitCheck=True, description="点击确认停止"),
            Task(TaskType.STEP_COMPLETED, None),
        ]
    @execute_tasks
    def taskAdd_recruit_accelerate(self):
        return [
            Task(TaskType.CLICK_IMG, "RecruitTimerDecrement", b_reuse=True, description="点击向下箭头增加时间"),
            Task(TaskType.CLICK_BEST_TAGS, None, description="选好tag"),
            Task(TaskType.CLICK_IMG, "RecruitConfirm", b_reuse=True, description="点击对勾开始招募"),
            Task(TaskType.CLICK_TEXT, "立即招募", b_recruitCheck=True, description="点击立即招募"),
            Task(TaskType.CLICK_IMG, "RecruitNowConfirm", b_reuse=True, description="确认使用加速券"),
            Task(TaskType.CLICK_TEXT, "聘用候选人", b_recruitCheck=True, description="点击聘用候选人"),
            Task(TaskType.CLICK_TEXT, "SKIP", b_reuse=True, description="点击SKIP"),
            Task(TaskType.WHILE, "isCertificateOnScreen", description="检查是否有凭证可以点击"),
            [
                Task(TaskType.CLICK_TEXT, None, description="点击任意处"),
            ],
            Task(TaskType.STEP_COMPLETED, None),
        ]
    @execute_tasks
    def taskAdd_gacha_once(self):
        return ([
            Task(TaskType.CLICK_TEXT, "寻访一次", b_reuse=True, description="点击寻访一次"),
            ] + 
            self.l_originiteCheckTask + 
            [
            Task(TaskType.CLICK_TEXT, "确认", b_reuse=True, description="点击确认寻访"),
            #Task(TaskType.CLICK_TEXT, "SKIP", b_reuse=True, post_wait=0.3, description="点击SKIP"),
            Task(TaskType.CLICK_COORDINATE_RELATIVE, (0.98, 0.02), pre_wait=0.5, description="点击SKIP"),
            Task(TaskType.RECORD_AGENT, None),
            Task(TaskType.WHILE, "isCertificateOnScreen", description="检查是否有凭证可以点击"),
            [
                Task(TaskType.CLICK_TEXT, None, description="点击任意处"),
            ],
            Task(TaskType.STEP_COMPLETED, None),
        ])
    @execute_tasks
    def taskAdd_gacha_ten(self):
        return ([
            Task(TaskType.CLICK_TEXT, "寻访十次", b_reuse=True, description="点击寻访十次"),
            ] + 
            self.l_originiteCheckTask + 
            [
            Task(TaskType.CLICK_TEXT, "确认", b_reuse=True, description="点击确认寻访"),
            #Task(TaskType.CLICK_TEXT, "SKIP", b_reuse=True, description="点击SKIP"),
            Task(TaskType.CLICK_COORDINATE_RELATIVE, (0.98, 0.02), pre_wait=0.5, description="点击SKIP"),
            Task(TaskType.CLICK_TEXT, None, pre_wait=2.5, description="点击任意位置跳过干员"),
            #Task(TaskType.CLICK_TEXT, None, pre_wait=0.5, description="点击任意位置跳过信物"),
            Task(TaskType.CLICK_COORDINATE_RELATIVE, (0.5, 0.9), pre_wait=0.5, description="点击屏幕下方"),
            Task(TaskType.STEP_COMPLETED, None),
        ])
    @execute_tasks
    def taskAdd_gacha_tenWithRecord(self):
        return ([
            Task(TaskType.CLICK_TEXT, "寻访十次", b_reuse=True, description="点击寻访十次"),
            ] + 
            self.l_originiteCheckTask + 
            [
            Task(TaskType.CLICK_TEXT, "确认", b_reuse=True, description="点击确认寻访"),
            #Task(TaskType.CLICK_TEXT, "SKIP", b_reuse=True, description="点击SKIP"),
            Task(TaskType.CLICK_COORDINATE_RELATIVE, (0.98, 0.02), pre_wait=0.5, description="点击SKIP"),
            Task(TaskType.CLICK_TEXT, None, pre_wait=2.5, description="点击任意位置跳过干员"),
            #Task(TaskType.CLICK_TEXT, None, pre_wait=0.5, description="点击任意位置跳过信物"),
            Task(TaskType.CLICK_COORDINATE_RELATIVE, (0.5, 0.9), pre_wait=0.5, description="点击屏幕下方"),
            Task(TaskType.CLICK_TEXT, "查看详情", b_reuse=True, description="点击查看详情"),
            Task(TaskType.CLICK_TEXT, "查询记录", b_reuse=True, description="点击查询记录"),
            Task(TaskType.RECORD_HISTORY_PAGE, None, pre_wait=0.3, description="记录一页招募历史"),
            Task(TaskType.CLICK_IMG, "gachaHistoryButton_exit", b_reuse=True, description="点击×退出"),
            Task(TaskType.CLICK_TEXT, None, pre_wait=0.3, description="点击任意位置退出"),
            Task(TaskType.STEP_COMPLETED, None),
        ])
    
    @execute_tasks
    def taskAdd_customTask_loop(self):
        return [
            Task(TaskType.WHILE, True),
            [
                Task(TaskType.CLICK_IMG, "RecruitTimerDecrement", b_reuse=True, description="点击向下箭头增加时间"),
                Task(TaskType.CLICK_BEST_TAGS, None, description="检查tag"),
                Task(TaskType.SCREEN_TO_MEM, None),
                Task(TaskType.CLICK_IMG, "RecruitConfirm", b_reuse=True, description="点击对勾开始招募"),
                Task(TaskType.CROP_FROM_MEM, region_tag),
                Task(TaskType.SAVE_FROM_MEM, "E:\\System_ProgramDataPath\\Desktop\\111", mode="png"),
                Task(TaskType.WHILE, "isTextOnScreen", name="立即招募", b_sameOnly=True, negation=True, description="等待文字出现"),
                [
                    Task(TaskType.NOP, None),
                ],
                Task(TaskType.CLICK_TEXT, "立即招募", b_recruitCheck=True, description="点击立即招募"),
                Task(TaskType.CLICK_IMG, "RecruitNowConfirm", b_reuse=True, description="确认使用加速券"),
                Task(TaskType.CLICK_TEXT, "聘用候选人", b_recruitCheck=True, description="点击聘用候选人"),
                Task(TaskType.WHILE, "isCertificateOnScreen", negation=True, region=region_certificate, description="检查是否有凭证可以点击"),
                [
                    Task(TaskType.CLICK_TEXT, "SKIP", b_reuse=True, description="点击SKIP"),
                ],
                Task(TaskType.SCREEN_TO_MEM, None),
                Task(TaskType.CROP_FROM_MEM, (0.33, 0.55, 0.87, 0.85)),
                Task(TaskType.SAVE_FROM_MEM, "E:\\System_ProgramDataPath\\Desktop\\111", mode="png"),
                Task(TaskType.WHILE, "isCertificateOnScreen", region=region_certificate, description="检查是否有凭证可以点击"),
                [
                    Task(TaskType.CLICK_TEXT, None, description="点击任意处"),
                ],
                Task(TaskType.ENTER_SLOT, None, post_wait=0.2, description="进入公招池"),
            ]
        ]
        '''
        return [
            Task(TaskType.WHILE, True),
            [
                Task(TaskType.CLICK_TEXT, "最少", b_reuse=True, description="点击最少", region=(0.35, 0.8, 0.47, 1), pre_wait=0.1),
                Task(TaskType.WHILE, "isTextOnScreen", name="1", b_sameOnly=True, negation=True, region=(0.5, 0.872, 0.562, 0.939), description="检查选中数量是否正确"),
                [
                    Task(TaskType.WHILE, "isTextOnScreen", name="-20", b_sameOnly=True, negation=True, region=(0.761, 0.84, 0.83, 1), description="检查消耗物资数量是否正确"),
                    [
                        Task(TaskType.CLICK_TEXT, "最少", b_reuse=True, description="点击最少", region=(0.35, 0.8, 0.47, 1)),
                    ],
                ],
                Task(TaskType.CLICK_COORDINATE_RELATIVE, (0.85, 0.9), description="点击任命"),
                Task(TaskType.IF, "isTextOnScreen", name="道具不足", description="判断终止条件", region=(0.8, 0.13, 0.871, 0.18), pre_wait=0.5, post_wait=0.4),
                [
                    Task(TaskType.END, None),
                ],
                Task(TaskType.SCREEN_TO_MEM, None),
                Task(TaskType.CLICK_COORDINATE_RELATIVE, (0.85, 0.857), description="点击确认"),
                Task(TaskType.CROP_FROM_MEM, (0.135, 0.265, 0.238, 0.448)),
                #Task(TaskType.SAVE_FROM_MEM, "E:\\System_ProgramDataPath\\Desktop\\111\\laojunxiao", mode="png"),
                Task(TaskType.SAVE_FROM_MEM, "E:\\System_ProgramDataPath\\Desktop\\111\\ico", mode="png"),
                #Task(TaskType.SAVE_FROM_MEM, "E:\\System_ProgramDataPath\\Desktop\\111\\yuer", mode="png"),
            ],
        ]
        '''