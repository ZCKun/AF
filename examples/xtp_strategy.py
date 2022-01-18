import sys
sys.path.append("..")
from A.types import KLine
from A.types.ctp import Snapshot
from A import AF, XTPStrategy, logger, AFMode


class Strategy(XTPStrategy):
    def __init__(self):
        super().__init__()
        self.sub_symbol_code = ['000001.SZ', '000016.SH', '399905.SZ', '399300.SZ']

    def on_bar(self, bar: KLine):
        logger.debug(bar)

    def on_snapshot(self, tick: Snapshot):
        logger.debug(tick)


def main():
    a = AF(AFMode.NORMAL,
           xtp_config_path="config/xtp_config.yaml",
           enable_xtp=True)

    s = Strategy()
    a.add_strategy(s)
    a.start()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
