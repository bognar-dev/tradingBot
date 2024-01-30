from alpaca.broker import requests
from lumibot.brokers import Alpaca
from lumibot.backtesting import YahooDataBacktesting
from lumibot.strategies.strategy import Strategy
from lumibot.traders import Trader
from datetime import datetime
from alpaca_trade_api import REST
from timedelta import Timedelta
from finbert_utils import estimate_sentiment
from dotenv import load_dotenv
import os

load_dotenv()
API_KEY = os.getenv("ALPACA_Key")
API_SECRET = os.getenv("ALPACA_Secret")
BASE_URL = os.getenv("ALPACA_BASE_URL")

ALPACA_CREDS = {
    "API_KEY":os.getenv("ALPACA_Key"),
    "API_SECRET":os.getenv("ALPACA_Secret"),
    "PAPER": True
}

class MLTrader(Strategy):
    def initialize(self, symbol:str="SPY", cash_at_risk:float=.5):

        self.symbol = symbol
        self.sleeptime = "24H"
        self.last_trade = None
        self.cash_at_risk = cash_at_risk
        self.api = REST(base_url= os.getenv("ALPACA_BASE_URL"), key_id= os.getenv("ALPACA_Key"), secret_key= os.getenv("ALPACA_Secret"))

    def position_sizing(self):
        cash = self.get_cash()
        last_price = self.get_last_price(self.symbol)
        quantity = round(cash * self.cash_at_risk / last_price,0)
        return cash, last_price, quantity

    def get_dates(self):
        today = self.get_datetime()
        three_days_prior = today - Timedelta(days=3)
        return today.strftime('%Y-%m-%d'), three_days_prior.strftime('%Y-%m-%d')


    def get_alpaca_news(self):
        base_url = 'https://data.alpaca.markets/v1beta1/news'
        params = {
            'symbols': ','.join(self.symbol)
        }

        headers = {
            'Apca-Api-Key-Id': API_KEY,
            'Apca-Api-Secret-Key': API_SECRET
        }

        response = requests.get(base_url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()

            # Extract headlines
            headlines = [news_item['headline'] for news_item in data['news']]
            return headlines
        else:
            raise Exception(f'Failed to retrieve data: {response.status_code} - {response.reason}')

    def get_sentiment(self):
        today, three_days_prior = self.get_dates()
        news = self.api.get_news(symbol=self.symbol,
                                 start=three_days_prior,
                                 end=today)
        news = [ev.__dict__["_raw"]["headline"] for ev in news]
        probability, sentiment = estimate_sentiment(news)
        return probability, sentiment

    def on_trading_iteration(self):
        cash, last_price, quantity = self.position_sizing()
        probability, sentiment = self.get_sentiment()

        if cash > last_price:
            if sentiment == "positive" and probability > .999:
                if self.last_trade == "sell":
                    self.sell_all()
                order = self.create_order(
                    self.symbol,
                    quantity,
                    "buy",
                    type="bracket",
                    take_profit_price=last_price*1.20,
                    stop_loss_price=last_price*.95
                )
                self.submit_order(order)
                self.last_trade = "buy"
            elif sentiment == "negative" and probability > .999:
                if self.last_trade == "buy":
                    self.sell_all()
                order = self.create_order(
                    self.symbol,
                    quantity,
                    "sell",
                    type="bracket",
                    take_profit_price=last_price*.8,
                    stop_loss_price=last_price*1.05
                )
                self.submit_order(order)
                self.last_trade = "sell"



if __name__ == "__main__":
    print("Initializing MLTrader")
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2023, 12, 31)
    broker = Alpaca(ALPACA_CREDS)
    strategy = MLTrader(name='mlstrat', broker=broker,
                        parameters={"symbol": "SPY",
                                    "cash_at_risk": .5})
    strategy.backtest(
        YahooDataBacktesting,
        start_date,
        end_date,
        parameters={"symbol": "SPY", "cash_at_risk": .5}
    )
    trader = Trader()
    trader.add_strategy(strategy)
    trader.run_all()