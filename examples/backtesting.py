import sys
import pathlib
sys.path.append(str(pathlib.Path.cwd()))
from A import AF, AFMode, Strategy, logger, StrategyType


class Backtesting(Strategy):
    def __init__(self):
        super().__init__()
        self._type = StrategyType.CSV
        self.sub_symbol_code = ['IF9999']

    def on_bar(self, bar):
        logger.info(bar)

    def on_snapshot(self, tick):
        logger.info(tick)


def main():
    a = AF(AFMode.BACKTESTING, csv_config_path="config/csv_config.yaml")
    s = Backtesting()
    a.add_strategy(s)
    a.start()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
