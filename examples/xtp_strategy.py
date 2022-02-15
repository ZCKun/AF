import sys
import json
sys.path.append("..")
from A.types import KLine
from A.types.ctp import Snapshot
from A import AF, XTPStrategy, logger, AFMode, AFOptional, Market


class Strategy(XTPStrategy):

    def __init__(self):
        super().__init__()
        self.sub_symbol_code = ["601919.SH"]

    def on_bar(self, bar: KLine):
        logger.debug(bar)

    def on_snapshot(self, tick: Snapshot):
        logger.debug(tick)

    def __del__(self):
        pass


def main():
    optional = AFOptional()
    optional.run_mode = AFMode.ONLINE
    optional.config_path = "config/xtp_config.yaml"
    optional.market = Market.STOCK
    optional.end_time = 15_00_00

    a = AF(optional)
    a.add_strategy(Strategy())
    # a.add_strategy(SomeStrategy())
    a.start()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
