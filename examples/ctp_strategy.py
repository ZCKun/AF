import sys
sys.path.append("..")
from A.types import KLine
from A.types.ctp import Snapshot
from A import AF, CTPStrategy, logger, AFMode


class Strategy(CTPStrategy):
    def __init__(self):
        super().__init__()
        self.sub_symbol_code = ['IF2202', 'IH2202']

    def on_bar(self, bar: KLine):
        logger.debug(bar)

    def on_snapshot(self, tick: Snapshot):
        # logger.debug(tick)
        pass


def main():
    a = AF(AFMode.NORMAL,
           ctp_config_path="config/ctp_config.yaml",
           enable_ctp=True)

    s = Strategy()
    a.add_strategy(s)
    a.start()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
