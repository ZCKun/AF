class Rolling:
    def __init__(self, feature, N, func):
        self.feature = feature
        self.N = N
        self.func = func

    def __str__(self):
        return "{}({},{})".format(type(self).__name__, self.feature, self.N)


class WMA(Rolling):
    def __init__(self, feature, N):
        super(WMA, self).__init__(feature, N, "wma")

    def _load_internal(self, instrument: str, start_index, end_index, freq):
        series = self.feature
