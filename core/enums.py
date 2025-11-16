from enum import Enum

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