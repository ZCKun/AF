import random
import secrets
import uuid

import numpy as np
import numpy.core.defchararray as nchar
import pandas as pd

from numpy import ndarray

import os
import re

from tabulate import tabulate
from enum import IntEnum
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from .color import Light, Deep

SINGLE_VERT_LINE = '│'
SINGLE_HOR_LINE = '─'
SINGLE_LEFT_CORNER_UP = '┌'
SINGLE_RIGHT_CORNER_UP = '┐'
SINGLE_LEFT_CORNER_DOWN = '└'
SINGLE_RIGHT_CORNER_DOWN = '┘'


def max_len_str(text: List):
    pre = ''
    for i in text:
        if len(i) > len(pre):
            pre = i
    return pre


def print_box(text: str, width: int = -1, center: bool = True, box_color: int = 0,
              msg_length: List[int] = None) -> None:
    """绘制方框，将text输出到方框中
    :param text:
    :param width:
    :param center:
    :param box_color:
    :param msg_length:
    :return:
    """
    box_width = width

    if msg_length is None:
        msg_length = len(max_len_str(text.split('\n'))) if '\n' in text else len(text)

    if width == -1:
        _, width = os.popen('stty size').read().strip().split(' ')
        # 如果terminal宽大于100，取1/2
        box_width = (width := int(width)) < 100 or width // 2

    # hor line length = box length - corner length
    hor_line_len = box_width - 2
    pretty_print(f"{SINGLE_LEFT_CORNER_UP}{SINGLE_HOR_LINE * hor_line_len}{SINGLE_RIGHT_CORNER_UP}",
                 show_date=False,
                 color=box_color)

    if '\n' not in text:
        margin = box_width - len(text) - 2
        margin = margin // 2 if center else margin
        message = ' ' * margin if center else ''
        message += f"{text}{' ' * margin}"
        print(f"\x1b[{box_color}m{SINGLE_VERT_LINE}\x1b[0m{message}\x1b[{box_color}m{SINGLE_VERT_LINE}\x1b[0m")
    else:
        # 防止text中出现\x1b，这会让计算margin出现问题
        blocks = text.split('\n')
        for block in blocks:
            string_length = len(block)
            # 排除\x1b[_m等颜色字符串
            if '\x1b[' in block:
                string_length = 0
                if special_str := re.findall(r"\x1b\[\d+m.*?\x1b\[0m", block):
                    for special in special_str:
                        if strings := re.findall(r"\x1b\[\d+m(.*?)\x1b\[0m", special):
                            for string in strings:
                                string_length += len(string)
                # 别忘了空格
                # if space := re.findall(' ', block):
                #     string_length += len(space)
                # 别忘了冒号
                if colon := re.findall(':', block):
                    string_length += len(colon)

            # padding length = box length - string length - vert line length
            padding = box_width - string_length - 2
            msg = f"{SINGLE_VERT_LINE}{block}{' ' * padding}{SINGLE_VERT_LINE}"
            # 如果需要居中，调整padding
            if center:
                if padding % 2:
                    padding_left = padding // 2
                    padding_right = padding // 2 + 1
                else:
                    padding_right = padding_left = padding // 2
                msg = f"{SINGLE_VERT_LINE}{' ' * padding_left}{block}{' ' * padding_right}{SINGLE_VERT_LINE}"
            pretty_print(msg, highlight={SINGLE_VERT_LINE: box_color}, show_date=False)

    pretty_print(f"{SINGLE_LEFT_CORNER_DOWN}{SINGLE_HOR_LINE * hor_line_len}{SINGLE_RIGHT_CORNER_DOWN}",
                 show_date=False,
                 color=box_color)


def stupid_string2float(string: str) -> float:
    """fucking stupid string to float"""
    return float('.'.join(string.split('.'))) if '.' in string else float(string)


def delta_time(curr_time: datetime, pre_time: datetime) -> int:
    curr_second = curr_time.hour * 3600 + curr_time.minute * 60 + curr_time.second
    pre_second = pre_time.hour * 3600 + pre_time.minute * 60 + pre_time.second
    return curr_second - pre_second


def get_last_trading_day(date: Optional[Any] = None) -> datetime:
    if date is None:
        date = datetime.today()
    elif isinstance(date, str):
        date = datetime.strptime(date, "%Y%m%d")

    while True:
        date -= timedelta(days=1)
        if date.weekday() not in [5, 6]:
            break
    return date  # - timedelta(days=8)


def log2dict(line: str) -> Dict[str, str]:
    text = line.split(':order:')[1] \
        .replace('{', '') \
        .replace('}', '') \
        .replace(' ', '') \
        .strip()
    ret: Dict[str, str] = {}
    for item in text.split(','):
        if not item:
            continue
        pair = item.split(':')
        ret[str(pair[0]).strip()] = ':'.join(pair[1:]).strip()
    return ret


def to_float(num: str) -> float:
    if '.' in num:
        nums: List[str] = num.split('.')
        return float(f"{nums[0]}.{nums[1]}")
    else:
        return float(num)


def kb2gb(kb): return int(kb) // 1024 // 1024


def check_disk(config: Dict[str, str]) -> None:
    """
    磁盘检查
    :param config:
    """
    df_out = os.popen('df').read()
    titles = ['FileSystem', 'Size', 'Used', 'Avail', 'Use%', 'Mounted On']

    for line in [i.strip() for i in df_out.split("\n") if i.strip() != '']:
        if line.endswith('/'):  # and configs.get("disk_file_system") in line:
            items = [j.strip() for j in line.split(' ') if j.strip() != '']
            threshold = config.get("disk_threshold").upper()

            if threshold.endswith('G'):
                file_system = items[0]
                size = kb2gb(items[1])
                used = kb2gb(items[2])
                avail = kb2gb(items[3])
                use = items[4]
                mounted_on = items[5]

                if avail < int(threshold.split("G")[0]):
                    table = [[file_system, size, used, f"\x1b[91m{avail}\x1b[0m", use, mounted_on]]
                    pretty_print(f"系统空间小于阀值大小{threshold}, 请即使通知管理人员!!!", color=Deep.RED)
                else:
                    table = [[file_system, size, used, avail, use, mounted_on]]

                print('=' * 100)
                print(tabulate(table, headers=titles, tablefmt="github"))
                print('=' * 100, end='\n\n')


def pretty_print(msg: Any,
                 color: int = Deep.WHITE,
                 show_date: bool = True,
                 date_format: str = '%Y-%m-%d %H:%M:%S',
                 date_color: IntEnum = Light.CYAN_BLUE,
                 highlight: Dict[str, Any] = None,
                 **kwargs):
    """
    Pretty print message.
    :param msg: what needs to be print.
    :param color: msg color.
    :param show_date: whether to display the date.
    :param date_format: date format.
    :param date_color: date color.
    :param highlight: need to highlight.
                        key is the content to be highlight, value is the content color.
                        If the value is a list, then the first two elements will be the character index to be replaced,
                        -1 means all.
    """
    if highlight and not isinstance(highlight, dict):
        raise TypeError("highlight must be dict.")

    if bool(highlight):
        for k, v in zip(highlight.keys(), highlight.values()):
            if isinstance(v, list) and len(v) > 0:
                _color = v[0]
                if len(v) == 1:
                    count = -1
                else:
                    count = v[1]
                replace = f"\x1b[0m\x1b[{_color}m{k}"
                if count == -1:
                    msg = msg.replace(k, replace)
                else:
                    msg = list(msg)
                    k_indexes = [i for i, x in enumerate(msg) if x == k][0:count]
                    for index in k_indexes:
                        if k_indexes.index(index) == len(k_indexes) - 1:
                            msg[index] = f"{replace}\x1b[{color}m"
                        else:
                            msg[index] = replace
                    msg = ''.join(msg)
            # 如果value不是list类型将默认认为value是颜色
            else:
                if not isinstance(v, int) or (isinstance(v, IntEnum) and not isinstance(v.value, int)):
                    v = 0
                replace = f"\x1b[{v}m{k}\x1b[0m"
                msg = msg.replace(k, replace)

    dt = ""
    if show_date:
        if not date_format or date_format == '':
            print(f"\x1b[{Light.YELLOW}warning:date_format is empty, the default format will be used.\x1b[0m")
            date_format = '%Y-%m-%d %H:%M:%S'
        dt = f"\x1b[{date_color}m[{datetime.now().strftime(date_format)}]\x1b[0m "

    print(f"{dt if dt else ''}\x1b[{color}m{msg}\x1b[0m", **kwargs)


STATES = [True]


def auto_pretty_print(msg: str,
                      color: int = Light.GREEN,
                      state: bool = True,
                      highlight: Dict[str, Any] = None,
                      **kwargs) -> None:
    """
    当上一个调用该方法时传入的 state 是 False，那么当前方法将不会输出 state 为 True 的内容
    :param msg: 消息
    :param color: 消息颜色
    :param state: 消息状态；True：Success，False：Error
    :param highlight: 需高亮显示部分
    :param kwargs:
    :return:
    """
    global STATES
    if state:
        if STATES[0]:
            pretty_print(msg, color=color, highlight=highlight, **kwargs)
            STATES[0] = state
    else:
        pretty_print(msg, color=color, highlight=highlight, **kwargs)
        STATES[0] = state


def csv_to_array(file_path: str, skip_header: bool) -> ndarray:
    """ convert csv file to numpy array
    Args:
        file_path:  csv file path.
        skip_header: skip the header line for csv file.
    Returns:
    """
    try:
        arr = np.genfromtxt(file_path, delimiter=',', encoding='gbk', dtype=np.str, skip_header=skip_header)
    except UnicodeDecodeError:
        arr = np.genfromtxt(file_path, delimiter=',', encoding='utf-8', dtype=np.str)

    return arr


def time_to_datetime(time_str: str) -> datetime:
    return datetime.strptime(time_str, '%H:%M:%S.%f')


RD = random.Random(secrets.randbits(128))


def generate_uuid(prefix=''):
    return f"{prefix + '_' if prefix else ''}{uuid.UUID(int=RD.getrandbits(128)).hex}"


def get_data_from_file(file_path: str) -> pd.DataFrame:
    """
    Args:
        file_path (str): 文件路径
    Returns:
    """
    source_df = pd.read_csv(file_path, encoding='gbk')
    if int(source_df.loc[0, '最后修改时间'].replace(':', '')) < 93000:
        source_df = source_df.drop([0])

    data_df = source_df.loc[:, ("最新价", "数量", "最后修改时间")]
    data_df.columns = ['last_price', 'volume', 'last_modified']

    last_modified = data_df.last_modified.to_numpy(dtype=str)
    last_modified_ms = source_df['最后修改毫秒'].to_numpy(dtype=str)
    last_modified = nchar.add(nchar.add(last_modified, '.'), last_modified_ms)

    data_df.loc[:, 'last_modified'] = pd.to_datetime(last_modified)
    trading_day_df = pd.to_datetime(source_df['交易日'].astype(str)).dt.strftime('%Y-%m-%d')
    last_modified_full = trading_day_df + ' ' + last_modified  # source_df['最后修改时间']
    data_df.loc[:, 'last_modified_full'] = pd.to_datetime(last_modified_full)

    data_df.loc[:, 'date'] = source_df['交易日']
    data_df.loc[:, 'last_price'] = data_df.last_price.astype(float)

    return data_df


def to_negative(number):
    return 0 - number


def trading_time_generator() -> list[datetime]:
    trading_times = list()

    dt = datetime.strptime("93100", "%H%M%S")
    end_dt = datetime.strptime("150000", "%H%M%S")

    _11_30 = datetime.strptime("113000", "%H%M%S")
    _13_00 = datetime.strptime("130000", "%H%M%S")

    while dt <= end_dt:
        if dt <= _11_30 or dt > _13_00:
            trading_times.append(dt)
        dt += timedelta(minutes=1)

    return trading_times


def trading_time_split_with_divide(arr, n) -> list:
    k, m = divmod(len(arr), n)
    return [arr[i * k + min(i, m): (i + 1) * k + min(i + 1, m)] for i in range(n)]
