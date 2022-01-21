# AF

![](https://img.shields.io/badge/python-3.9%2B-green)

## Quick Start

Please refer to examples in the examples' directory.

### Installation

```shell
pip install -r requirements.txt
```

Simple Example

```python
from A.types import KLine
from A.types.ctp import Snapshot
from A import AF, CTPStrategy, logger, AFMode


class Strategy(CTPStrategy):
    def __init__(self):
        super().__init__()
        # set your need to subscribe symbols
        self.sub_symbol_code = ['IF2202', 'IH2202']

    def on_bar(self, bar: KLine):
        logger.debug(bar)

    def on_snapshot(self, tick: Snapshot):
        logger.debug(tick)


def main():
    a = AF(
        AFMode.NORMAL,  # work mode
        ctp_config_path="config/ctp_config.yaml",
        enable_ctp=True
    )

    # you can add multiple strategies using add_strategy
    a.add_strategy(Strategy())
    # start work
    a.start()
```

**Note**: 需要注意的是, 目前 XTPStrategy 中 on_snapshot 返回的数据中, 价格类型均为 float, 而不是自定义类型 Price

1. 提供 60s 的 KLine Bar 数据, 策略中实现 on_bar 方法即可
2. 提供快照行情数据, 策略中实现 on_snapshot 即可

## Reference

[xtp_for_path](https://github.com/ZCKun/xtp-for-python)

## Thanks

[xtp_api_python](https://github.com/ztsec/xtp_api_python)

[ctpwrapper](https://github.com/nooperpudd/ctpwrapper)