import sys
sys.path.append("..")
from A import AF, AFMode, Strategy, logger, StrategyType


def sma(n: int, price_lst: list[float]) -> float:
    if (size := len(price_lst)) < n:
        return 0
    prices = price_lst[size - n:]
    return sum(prices) / n


def ema(price_lst: list[float], n: int, smoothing: int = 2, ema_lst: list[float] = None) -> float:
    if (size := len(price_lst)) < n:
        return 0

    if not ema_lst:
        ema = sum(price_lst[size - n:]) / n
        return ema

    val = smoothing / (1 + n)
    l = price_lst[-1] * val
    r = ema_lst[-1] * (1 - val)
    return l + r


class Backtesting(Strategy):

    def __init__(self):
        super().__init__()
        self._type = StrategyType.CSV
        self.sub_symbol_code = ['IF9999']

        self.price_lst: list[float] = list()
        self.dif_list: list[float] = list()
        self.ema1_lst: list[float] = list()
        self.ema2_lst: list[float] = list()
        self.dif_ema_lst: list[float] = list()

    def dif(self, close_price: float):
        ma1 = ema(self.price_lst, 12, ema_lst=self.ema1_lst)
        ma2 = ema(self.price_lst, 26, ema_lst=self.ema2_lst)
        self.ema1_lst.append(ma1)
        self.ema2_lst.append(ma2)

        dif = (ma1 - ma2) / close_price
        return dif

    def dea(self, n: int, close_price: float):
        if len(self.dif_list) < n:
            return 0
        dif_ema = ema(self.dif_list, n, ema_lst=self.dif_ema_lst)
        dea = dif_ema / close_price
        self.dif_ema_lst.append(dif_ema)
        return dea

    def macd(self, price) -> tuple[float, float, float]:
        dif = self.dif(price)
        dea = self.dea(9, price)
        macd = 2 * (dif - dea)
        self.dif_list.append(dif)
        self.price_lst.append(price)
        return macd, dif, dea

    def on_bar(self, bar):
        close_price = bar.close
        macd, dif, dea = self.macd(close_price)
        if bar.datetime.year > 2018:
            logger.debug(f"{bar.datetime.strftime('%Y-%m-%d %H:%M:%S')} - MACD:{macd}, DIF:{dif}, DEA:{dea}, "
                         f"ma12:{self.ema1_lst[-1]}, ma26:{self.ema2_lst[-1]}")

    def on_snapshot(self, tick):
        logger.info(tick)


def main():
    a = AF(AFMode.BACKTESTING, csv_config_path="config/csv_config.yaml", end_time=999999)
    s = Backtesting()
    a.add_strategy(s)
    a.start()


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        pass
