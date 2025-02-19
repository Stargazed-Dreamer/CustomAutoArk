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
#==============================
from paddleocr import PaddleOCR
#==============================
ADB_PATH = "D:\\YXArkNights-12.0\\shell\\adb.exe"
region_tag = (0.30,0.47,0.66,0.70)
region_agent = (0.45, 0.67, 0.87, 0.85)
#==============================
from data import data
#==============================
class CantFindNameError(Exception):
    pass

class MouseMoveError(Exception):
    pass

class OcrError(Exception):
    pass
#==============================
from log import log_manager

# 使用全局日志管理器
log = log_manager
#==============================
 
#==============================
class MUMU(Simulator):
    
    def find_nameOnScreen(self, name, limit = 0.5, b_allGet = False):
        """
        在屏幕上查找指定文字
        :param name: 要查找的文字
        :return: OCR识别结果
        """
        self.ensure_connected()
        log.info(f"在窗口内查找: {name}")
        img = self.screenshot()
        results = tool.ocr(img)
        l_output = []
        for result in results:
            l_position, t_text = result
            if t_text[0] == name:
                l_output.append(result)
        offset = 0
        for i in range(len(l_output)):
            if l_output[i-offset][1][1] < limit:
                l_output.pop(i-offset)
                offset += 1
        if b_allGet:
            return l_output
        else:
            if len(l_output) == 0:
                return None
            l_output.sort(key=lambda result: result[1][1])
            return l_output[-1]

    def click_text(self, name: Optional[str] = None, retry: int = 3):
        """
        点击指定文字位置
        :param name: 要点击的文字
        :param retry: 重试次数
        """
        self.ensure_connected()
        if retry == 3:
            log.debug(f"点击: {name}")
        else:
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
                height, width = self.screen_size
                self.click(width//2, height//2)
                return
            
            results = self.find_nameOnScreen(name)
            log.debug(f"寻找结果: {results}")
            if not results:
                raise Exception(f"找不到文字: {name}")
            
            center = tool.find_centerOnResult(results)
            self.click(*center)
            
        except Exception as e:
            if retry <= 0:
                raise e
            retry -= 1
            self.click_text(name, retry)
    
    def to_rightPage(self):
        """向右翻页"""
        self.ensure_connected()
        log.debug("向右翻页")
        height, width = self.screen_size
        x = width
        y = height
        x1 = x/3
        y_2 = y/2
        self.swipe(x1*2, y_2, x1, y_2)
    
    def to_leftPage(self):
        """向左翻页"""
        self.ensure_connected()
        log.debug("向左翻页")
        height, width = self.screen_size
        x = width
        y = height
        x1 = x/3
        y_2 = y/2
        self.swipe(x1, y_2, x1*2, y_2)

    def getTag(self) -> List[str]:
        """获取标签"""
        self.ensure_connected()
        img = self.screenshot()
        data.l_tag = tool.getTag(img)
        if len(data.l_tag) == 5:
            return data.l_tag
        return None

    def getAgent(self) -> Optional[str]:
        """获取干员"""
        self.ensure_connected()
        img = self.screenshot()
        agent = tool.getAgent(img)
        return agent
    
    def recruit_break(self):
        """执行一次公开招募"""
        log.debug("招募一次开始")
        l_tag = []
        try:
            # 点击√
            self.click_text("开始招募")
            time.sleep(0.5)
            # 点击停止招募
            self.click_text("停止招募")
            time.sleep(0.5)
            # 再次点击停止招募
            self.click_text("停止招募")
            time.sleep(0.5)
            # 点击加号
            self.click_text("开始招募干员")
            time.sleep(0.5)
            # 收集数据
            l_tag = self.getTag()
            log.debug("招募一次结束")
            return l_tag, True
        except Exception as e:
            log.error(f"招募失败: {str(e)}")
            return l_tag, False

    def recruit_accelerate(self):
        """执行一次公开招募"""
        log.debug("招募一次开始")
        l_tag = []
        try:
            # 点击“↓”
            self.click_text("↓")
            time.sleep(0.5)
            # 点击开始公招
            self.click_text("开始招募")
            time.sleep(0.5)
            # 点击立即招募
            self.click_text("立即招募")
            time.sleep(0.5)
            # 点击“√”
            self.click_text("√")
            time.sleep(0.5)
            # 聘用候选人
            self.click_text("聘用候选人")
            time.sleep(1.2)
            # 点击skip
            self.click_text("SKIP")
            time.sleep(1)
            # 点击任意位置回到抽卡界面
            self.click_text("凭证")
            time.sleep(0.5)
            # 点击加号
            self.click_text("开始招募干员")
            # 收集数据
            l_tag = self.getTag()
            log.debug("招募一次结束")
            return l_tag, True
        except Exception as e:
            log.error(f"招募失败: {str(e)}")
            return l_tag, False
    
    def draw_once(self):
        """执行一次寻访"""
        log.debug("寻访一次开始")
        agent = None
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
            return agent, True
        except Exception as e:
            log.error(f"寻访失败: {str(e)}")
            return None, False

    def draw_ten(self):
        """执行十次寻访"""
        height, width = self.screen_size
        log.debug("寻访十次开始")
        l_agent = []
        try:
            # 点击单抽
            time.sleep(0.7)
            self.click_text("寻访十次")
            time.sleep(0.6)
            # 点击确认
            self.click_text("确认")
            time.sleep(1.2)
            # 从右到左划开
            self.swipe(0.9*width, height//2, 0.1*width, height//2)
            time.sleep(8)
            for i in range(10):
                # 收集数据
                agent = self.getAgent()
                time.sleep(1)
                # 点击任意位置回到抽卡界面
                self.click_text("凭证")
                l_agent.append(agent)
                log.debug(f"第{i+1}个得到: {agent}")
            log.debug("寻访十次结束")
            return l_agent, True
        except Exception as e:
            log.error(f"寻访失败: {str(e)}")
            return l_agent, False

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