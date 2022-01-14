from A import AF, XTPStrategy, CTPStrategy, logger, AFMode
from A.types import KLine
from A.types.ctp import Snapshot


class Strategy(CTPStrategy):
    def __init__(self):
        super().__init__()
        self.sub_symbol_code = ['IF2201', 'IH2201']

    def on_bar(self, bar: KLine):
        logger.debug(bar)

    def on_snapshot(self, tick: Snapshot):
        logger.debug(tick)


class Strategy2(XTPStrategy):
    def __init__(self):
        super().__init__()
        self.sub_symbol_code = ['000001.SZ', '000016.SH', '399905.SZ', '399300.SZ']

    def on_bar(self, bar: KLine):
        logger.debug(bar)

    def on_snapshot(self, tick: Snapshot):
        logger.debug(tick)


def main():
    a = AF(AFMode.NORMAL,
           ctp_config_path="ctp_config.yaml",
           xtp_config_path="xtp_config.yaml",
           csv_config_path="csv_config.yaml",
           enable_ctp=True)

    cs = Strategy()
    xs = Strategy2()

    a.docking(cs)
    a.docking(xs)
    a.start()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
