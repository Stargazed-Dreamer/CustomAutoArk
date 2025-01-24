import os
import time
import subprocess
import cv2
import numpy as np
import logging
from typing import Optional, Tuple
from datetime import datetime
import socket
import winreg
import shutil

class Core:
    def __init__(self, log_dir: str = "log", resource_dir: str = "resource"):
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
        # 常见的模拟器注册表路径和对应的adb相对路径
        emulator_reg_paths = {
            # MUMU模拟器
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\NetEase\MuMuPlayer"): [
                ["InstallDir", "emulator\\nemu\\vmonitor\\bin\\adb.exe"],
                ["InstallDir", "vmonitor\\bin\\adb.exe"],
            ],
            # 夜神模拟器
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Netease\Nemu"): [
                ["InstallDir", "bin\\nemu_adb.exe"],
            ],
            # 蓝叠模拟器
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\BlueStacks_nxt"): [
                ["InstallDir", "HD-Adb.exe"],
            ],
            # 雷电模拟器
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\leidian\ldplayer"): [
                ["InstallDir", "adb.exe"],
            ],
        }
        
        # 1. 从注册表查找模拟器
        for (hkey, reg_path), adb_paths in emulator_reg_paths.items():
            try:
                with winreg.OpenKey(hkey, reg_path) as key:
                    install_dir = winreg.QueryValueEx(key, adb_paths[0][0])[0]
                    for _, rel_path in adb_paths:
                        adb_path = os.path.join(install_dir, rel_path)
                        if os.path.exists(adb_path):
                            self.logger.info(f"在注册表中找到adb: {adb_path}")
                            return adb_path
            except WindowsError:
                continue
                
        # 2. 从Android SDK注册表项查找
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Android SDK Tools") as key:
                sdk_path = winreg.QueryValueEx(key, "Path")[0]
                adb_path = os.path.join(sdk_path, "platform-tools", "adb.exe")
                if os.path.exists(adb_path):
                    self.logger.info(f"在Android SDK注册表中找到adb: {adb_path}")
                    return adb_path
        except WindowsError:
            self.logger.debug("未在注册表中找到Android SDK")
            
        # 3. 从环境变量查找
        for path in os.environ["PATH"].split(os.pathsep):
            adb_path = os.path.join(path, "adb.exe")
            if os.path.exists(adb_path):
                self.logger.info(f"在环境变量中找到adb: {adb_path}")
                return adb_path
                
        # 4. 检查常见安装路径
        common_paths = [
            # MUMU模拟器
            r"C:\Program Files\MuMu\emulator\nemu\vmonitor\bin\adb.exe",
            r"D:\Program Files\MuMu\emulator\nemu\vmonitor\bin\adb.exe",
            # 夜神模拟器
            r"C:\Program Files\Nox\bin\nox_adb.exe",
            r"D:\Program Files\Nox\bin\nox_adb.exe",
            # 蓝叠模拟器
            r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe",
            r"D:\Program Files\BlueStacks_nxt\HD-Adb.exe",
            # 雷电模拟器
            r"C:\Program Files\LDPlayer\adb.exe",
            r"D:\Program Files\LDPlayer\adb.exe",
            # 逍遥模拟器
            r"C:\Program Files\Microvirt\MEmu\adb.exe",
            r"D:\Program Files\Microvirt\MEmu\adb.exe",
            # Android SDK
            r"C:\Users\%USERNAME%\AppData\Local\Android\Sdk\platform-tools\adb.exe",
        ]
        
        # 展开用户名
        common_paths = [p.replace("%USERNAME%", os.getenv("USERNAME", "")) for p in common_paths]
        
        for path in common_paths:
            if os.path.exists(path):
                self.logger.info(f"在常见路径中找到adb: {path}")
                return path
                
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
            self.logger.info(f"屏幕方向: {self.orientation}度")
            
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
            self.logger.debug(f"点击坐标: ({x}, {y}) -> ({conv_x}, {conv_y}), 按下时间: {press_time}ms")
            
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
            if self.minitouch_socket:
                self.minitouch_socket.close()
                self.minitouch_socket = None
            
            if self.minitouch_proc:
                self.minitouch_proc.terminate()
                self.minitouch_proc = None
            
            if self.device_addr:
                # 忽略清理错误，因为可能本来就不存在
                subprocess.run(
                    [self.adb_path, "-s", self.device_addr, "forward", "--remove", "tcp:1111"],
                    capture_output=True
                )
                subprocess.run(
                    [self.adb_path, "-s", self.device_addr, "shell", "rm", "/data/local/tmp/minitouch"],
                    capture_output=True
                )
        except Exception as e:
            self.logger.debug(f"清理时发生错误: {e}")

    def __del__(self):
        """析构函数"""
        self.cleanup() 