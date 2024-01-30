import numpy as np
from alpaca.broker import requests
from alpaca.data import NewsRequest
from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime, timedelta
from alpaca.trading.client import TradingClient
from alpaca.data.historical.news import NewsClient
from alpaca.data.historical import StockHistoricalDataClient
from timedelta import Timedelta
from finbert_utils import estimate_sentiment
from dotenv import load_dotenv
import os

load_dotenv()
ALPACA_CREDS = {
    "API_KEY": os.getenv("ALPACA_Key"),
    "API_SECRET": os.getenv("ALPACA_Secret"),
    "PAPER": True
}


class MLTrader(Strategy):
    def initialize(self, symbol: str = "AAPL", cash_at_risk: float = .5):

        self.symbol = symbol
        self.sleeptime = "24H"
        self.last_trade = None
        self.cash_at_risk = cash_at_risk
        self.tradeClient = TradingClient(os.getenv("ALPACA_Key"), os.getenv("ALPACA_Secret"))
        self.newsClient = NewsClient(os.getenv("ALPACA_Key"), os.getenv("ALPACA_Secret"))

    def position_sizing(self):
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        quantity = round(cash * self.cash_at_risk / last_price, 0)
        return cash, last_price, quantity

    def get_dates(self):
        today = self.get_datetime()
        three_days_prior = today - Timedelta(days=3)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')

    def get_alpaca_news(self, today, three_days_prior):
        newsRequest = NewsRequest(
            symbols=self.symbol,
            start=three_days_prior,
            end=today,
            limit=20
        )
        news = self.newsClient.get_news(newsRequest)
        headlines = []
        summaries = []

        for news_item in news.news:
            headlines.append(news_item.headline)
            summaries.append(news_item.summary)

        return headlines

    def get_sentiment(self):
        today, three_days_prior = self.get_dates()
        news = self.get_alpaca_news(today, three_days_prior)
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment

    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_sizing()
        probability, sentiment = self.get_sentiment()
        print(sentiment)
        if cash > last_price:
            if sentiment == "positive" and probability > .999:
                if self.last_trade == "sell":
                    self.sell_all()
                order = self.create_order(
                    self.symbol,
                    quantity,
                    "buy",
                    type="bracket",
                    take_profit_price=last_price * 1.20,
                    stop_loss_price=last_price * .95
                )
                self.submit_order(order)
                print("buying")
                self.last_trade = "buy"
            elif sentiment == "negative" and probability > .999:
                if self.last_trade == "buy":
                    self.sell_all()
                order = self.create_order(
                    self.symbol,
                    quantity,
                    "sell",
                    type="bracket",
                    take_profit_price=last_price * .8,
                    stop_loss_price=last_price * 1.05
                )
                self.submit_order(order)
                print("selling")
                self.last_trade = "sell"


class MovingAvrTrader(Strategy):
    def initialize(self, symbol: str = "AAPL", cash_at_risk: float = .5):

        self.symbol = symbol
        self.sleeptime = "24H"
        self.last_trade = None
        self.cash_at_risk = cash_at_risk
        self.tradeClient = TradingClient(os.getenv("ALPACA_Key"), os.getenv("ALPACA_Secret"))
        self.newsClient = NewsClient(os.getenv("ALPACA_Key"), os.getenv("ALPACA_Secret"))

    def position_sizing(self):
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        quantity = round(cash * self.cash_at_risk / last_price, 0)
        return cash, last_price, quantity

    def get_dates(self):
        today = self.get_datetime()
        three_days_prior = today - Timedelta(days=3)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')

    def get_alpaca_news(self, today, three_days_prior):
        newsRequest = NewsRequest(
            symbols=self.symbol,
            start=three_days_prior,
            end=today,
            limit=20
        )
        news = self.newsClient.get_news(newsRequest)

        headlines = []
        summaries = []

        for news_item in news.news:
            headlines.append(news_item.headline)
            summaries.append(news_item.summary)

        return headlines

    def get_sentiment(self):
        today, three_days_prior = self.get_dates()
        news = self.get_alpaca_news(today, three_days_prior)
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment

    def on_trading_iteration(self):
        # Define the short and long moving average windows
        short_window = 10
        long_window = 20

        # Get the historical data

        data = self.get_historical_prices(self.symbol, 50, 'day')
        data = data.df
        # Calculate the short and long moving averages
        data['short_mavg'] = data['close'].rolling(window=short_window).mean()
        data['long_mavg'] = data['close'].rolling(window=long_window).mean()

        # Generate the trading signals based on the moving average crossover
        data['signal'] = 0.0
        data.loc[data.index[short_window:], 'signal'] = np.where(
            data['short_mavg'][short_window:] > data['long_mavg'][short_window:], 1.0, 0.0)
        # Generate trading orders
        data['positions'] = data['signal'].diff()

        # Get the last position
        last_position = data['positions'].iloc[-1]

        # Check if we need to execute any trades
        if last_position == 1.0 and self.last_trade != "buy":
            # Moving average crossover occurred, indicating a buy signal
            self.sell_all()
            cash = self.get_cash()
            last_price = self.get_last_price(self.symbol)
            quantity = round(cash / last_price, 0)
            order = self.create_order(self.symbol, quantity, "buy")
            self.submit_order(order)
            self.last_trade = "buy"
            print("buying")
        elif last_position == -1.0 and self.last_trade != "sell":
            # Moving average crossover occurred, indicating a sell signal
            self.sell_all()
            self.last_trade = "sell"
            print("selling")


if __name__ == "__main__":
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2024, 1, 29)
    broker = Alpaca(ALPACA_CREDS)
    strategy = MovingAvrTrader(name='MovingAvrTrader', broker=broker,
                               parameters={"symbol": "AAPL",
                                           "cash_at_risk": .5})
    strategy.backtest(
        YahooDataBacktesting,
        start_date,
        end_date,
        parameters={"symbol": "AAPL", "cash_at_risk": .5},

    )
    #trader = Trader()
    #trader.add_strategy(strategy)
    #trader.run_all()
