import os
import time
from datetime import datetime

import cv2
import numpy as np
from PySide6.QtCore import QObject, Signal, Slot

from data import data as DATA
from log import log_manager
from tool import tool, error_record

log = log_manager

#==============================
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

from .enums import TaskType
from .simulator import Simulator

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

# 初始化图片模板
Task.init_img(IMG_PATH)