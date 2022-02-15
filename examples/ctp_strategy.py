import sys
sys.path.append("..")
from A.types import KLine
from A.types.ctp import Snapshot
from A import AF, CTPStrategy, logger, AFMode, AFOptional, Market


class Strategy(CTPStrategy):
    def __init__(self):
        super().__init__()
        self.sub_symbol_code = [
            "IF2202",
            "IF2203",
            "IF2206",
            "IF2209",
            "IC2202",
            "IC2203",
            "IC2206",
            "IC2209",
            "IH2202",
            "IH2203",
            "IH2206",
            "IH2209",
        ]

    def on_bar(self, bar: KLine):
        logger.debug(bar)

    def on_snapshot(self, tick: Snapshot):
        logger.debug(tick)


def main():
    optional = AFOptional()
    optional.market = Market.FUTURE
    optional.config_path = "config/ctp_config.yaml"
    optional.end_time = 15_00_00
    optional.run_mode = AFMode.ONLINE

    a = AF(optional)
    a.add_strategy(Strategy())
    # a.add_strategy(SomeStrategy())
    a.start()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
