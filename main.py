import datetime as dt
import matplotlib.pyplot as plt
import yfinance as yf


class StockAnalyzer:
    def __init__(self, symbol, ma_Range, ma_1, ma_2):
        self.ma_range = ma_Range
        self.symbol = symbol
        self.data = None
        self.ma_1 = ma_1
        self.ma_2 = ma_2
        self.profit = float('-inf')
        self.max_profit = float('-inf')
        self.optimal_ma = None

    def plot(self):
        plt.style.use('dark_background')
        plt.figure(figsize=(12, 8))
        plt.plot(self.data['Close'], label=self.symbol, color='blue')
        plt.plot(self.data[f'SMA_{self.ma_1}'], label=f'SMA_{self.ma_1}', color='orange', linestyle='--')
        plt.plot(self.data[f'SMA_{self.ma_2}'], label=f'SMA_{self.ma_2}', color='pink', linestyle='--')
        plt.plot(self.data['Buy Signals'], label='Buy', marker='^', color='green')
        plt.plot(self.data['Sell Signals'], label='Sell', marker='v', color='red')
        plt.text(s=f'Profit: {self.profit}', x=dt.datetime.now(), y=self.data['Close'].iloc[-1], fontsize=12)
        plt.legend(loc='best')
        plt.title(f'{self.symbol} Close Price History Buy & Sell Signals')
        plt.show()

    def get_data(self):
        ticker = yf.Ticker(self.symbol)
        self.data = ticker.history(period='3y', interval='1d')

    def set_sma(self):

        self.data[f'SMA_{self.ma_1}'] = self.data['Close'].rolling(window=self.ma_1).mean()
        self.data[f'SMA_{self.ma_2}'] = self.data['Close'].rolling(window=self.ma_2).mean()
        #self.data = self.data.iloc[self.ma_2:]

    def generate_signals(self):
        buy_signals = []
        sell_signals = []
        trigger = 0
        for x in range(len(self.data)):
            if self.data[f'SMA_{self.ma_1}'].iloc[x] > self.data[f'SMA_{self.ma_2}'].iloc[x] and trigger != 1:
                buy_signals.append(self.data['Close'].iloc[x])
                sell_signals.append(float('nan'))
                trigger = 1
            elif self.data[f'SMA_{self.ma_1}'].iloc[x] < self.data[f'SMA_{self.ma_2}'].iloc[x] and trigger != -1:
                buy_signals.append(float('nan'))
                sell_signals.append(self.data['Close'].iloc[x])
                trigger = -1
            elif x == 0:
                buy_signals.append(self.data['Close'].iloc[x])
                sell_signals.append(float('nan'))
                trigger = 1
            else:
                buy_signals.append(float('nan'))
                sell_signals.append(float('nan'))
        self.data['Buy Signals'] = buy_signals
        self.data['Sell Signals'] = sell_signals


    def calculate_profit(self):
        profit = 0
        sellIdx = 0
        buyIdx = 0
        for x in range(len(self.data['Buy Signals'])):
            if str(self.data['Buy Signals'].iloc[x]) != 'nan':
                buyIdx = x
            if str(self.data['Sell Signals'].iloc[x]) != 'nan':
                sellIdx = x
                if sellIdx > buyIdx:
                    profit += self.data['Sell Signals'].iloc[sellIdx] - self.data['Buy Signals'].iloc[buyIdx]
        self.profit = profit

    def find_optimal_ma(self):
        for ma_1 in self.ma_range:
            for ma_2 in self.ma_range:
                if ma_1 == ma_2:
                    print("MA1 == MA2")
                    continue
                self.ma_1 = ma_1
                self.ma_2 = ma_2
                self.set_sma()
                self.generate_signals()
                self.calculate_profit()

                if self.profit > self.max_profit:
                    print(f"MA1: {ma_1}, MA2: {ma_2}, Profit: {self.profit}")
                    self.max_profit = self.profit
                    self.optimal_ma = (ma_1, ma_2)
        # Recalculate SMAs with optimal values
        print(f"Optimal MA1: {self.optimal_ma[0]}, Optimal MA2: {self.optimal_ma[1]}, Profit: {self.max_profit}")
        self.ma_1, self.ma_2 = self.optimal_ma
        self.set_sma()
        self.generate_signals()
        self.calculate_profit()

    def calc_invest_return(self, invest):
        d = self.data.copy()
        first_buy_signal = d["Buy Signals"].dropna().iloc[0]
        numShares = invest / first_buy_signal

        # Get the last non-NaN sell signal
        last_sell_signal = d["Sell Signals"].dropna().iloc[-1]
        finalVal = numShares * last_sell_signal
        return finalVal


def calculate_profit(buy_signals, sell_signals):
    profit = 0
    sellIdx = 0
    buyIdx = 0
    for x in range(len(buy_signals)):
        if str(buy_signals[x]) != 'nan':
            buyIdx = x
        if str(sell_signals[x]) != 'nan':
            sellIdx = x
            if sellIdx > buyIdx:
                profit += sell_signals[sellIdx] - buy_signals[buyIdx]
    return profit


def get_data(symbol):
    tsla = yf.Ticker(symbol)
    data = tsla.history(period='3y', interval='1d')
    return data


def calculate_sma(data, ma_1, ma_2):
    data[f'SMA_{ma_1}'] = data['Close'].rolling(window=ma_1).mean()
    data[f'SMA_{ma_2}'] = data['Close'].rolling(window=ma_2).mean()
    data = data.iloc[ma_2:]
    return data


def generate_signals(data, ma_1, ma_2):
    buy_signals = []
    sell_signals = []
    trigger = 0
    for x in range(len(data)):
        if data[f'SMA_{ma_1}'].iloc[x] > data[f'SMA_{ma_2}'].iloc[x] and trigger != 1:
            buy_signals.append(data['Close'].iloc[x])
            sell_signals.append(float('nan'))
            trigger = 1
        elif data[f'SMA_{ma_1}'].iloc[x] < data[f'SMA_{ma_2}'].iloc[x] and trigger != -1:
            buy_signals.append(float('nan'))
            sell_signals.append(data['Close'].iloc[x])
            trigger = -1
        else:
            buy_signals.append(float('nan'))
            sell_signals.append(float('nan'))
    data['Buy Signals'] = buy_signals
    data['Sell Signals'] = sell_signals
    profit = calculate_profit(buy_signals, sell_signals)
    return data, profit


def plot_data(data, symbol, profit, ma_1, ma_2):
    plt.style.use('dark_background')
    plt.figure(figsize=(12, 8))
    plt.plot(data['Close'], label=symbol, color='blue')
    plt.plot(data[f'SMA_{ma_1}'], label=f'SMA_{ma_1}', color='orange', linestyle='--')
    plt.plot(data[f'SMA_{ma_2}'], label=f'SMA_{ma_2}', color='pink', linestyle='--')
    plt.plot(data['Buy Signals'], label='Buy', marker='^', color='green')
    plt.plot(data['Sell Signals'], label='Sell', marker='v', color='red')
    plt.text(s=f'Profit: {profit}', x=dt.datetime.now(), y=data['Close'].iloc[-1], fontsize=12)
    plt.legend(loc='best')
    plt.title(f'{symbol} Close Price History Buy & Sell Signals')
    plt.show()


def find_optimal_ma(symbol, ma_range):
    max_profit = float('-inf')
    optimal_ma = None
    data = get_data(symbol)
    for ma_1 in ma_range:
        for ma_2 in ma_range:
            if ma_1 == ma_2:
                continue

            data = calculate_sma(data, ma_1, ma_2)
            data, profit = generate_signals(data, ma_1, ma_2)
            print(f"MA1: {ma_1}, MA2: {ma_2}, Profit: {profit}")
            if profit > max_profit:
                max_profit = profit
                optimal_ma = (ma_1, ma_2)

    data = get_data(symbol)
    data = calculate_sma(data, optimal_ma[0], optimal_ma[1])
    data, _ = generate_signals(data, optimal_ma[0], optimal_ma[1])
    return data, optimal_ma, max_profit


def main():
    s = StockAnalyzer('AAPL', range(3, 50), 4, 3)
    s.get_data()

    s.set_sma()
    s.generate_signals()
    s.calculate_profit()
    print(f"Profit: {s.profit}")
    final_value = s.calc_invest_return(1)
    print(f"Final value of investment: {final_value} Pounds")
    s.plot()
    s.find_optimal_ma()
    s.plot()




if __name__ == '__main__':
    main()
