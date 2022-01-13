from A import AFramework, CTPStrategy, logger
from A.types import KLine
from A.types.ctp import Snapshot


class Strategy(CTPStrategy):
    def __init__(self):
        super().__init__()
        self.sub_instrument_id = ['IF2201', 'IH2201']

    def on_bar(self, bar: KLine):
        logger.debug(bar)

    def on_snapshot(self, tick: Snapshot):
        logger.debug(tick)


def main():
    a = AFramework("ctp_config.yaml")

    my_s = Strategy()
    a.docking(my_s)
    a.start()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
