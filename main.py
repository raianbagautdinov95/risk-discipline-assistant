# main.py
import time

from dotenv import load_dotenv
from exchanges.okx_client import OKXClient

from config.settings import OKXConfig, TradingConfig, AIConfig
from config.risk_config import RiskLimits
from ai.deepseek_analyzer import DeepSeekAnalyzer
from ai.trading_strategy import TradingStrategy
from risk_management.position_sizer import PositionSizer
from risk_management.risk_monitor import RiskMonitor
from monitoring.reporter import Reporter
from utils.logger import setup_logger
from utils.helpers import retry_on_error


class TradingBot:
    def __init__(self):
        self.logger = setup_logger()


        self.okx_config = OKXConfig()
        self.trading_config = TradingConfig()
        self.ai_config = AIConfig()
        self.risk_limits = RiskLimits()


        self.exchange = OKXClient(
            api_key=self.okx_config.api_key,
            api_secret=self.okx_config.api_secret,
            passphrase=self.okx_config.passphrase
        )


        self.market_data = None
        self.ai_analyzer = DeepSeekAnalyzer(self.ai_config)
        self.strategy = TradingStrategy(self.trading_config.__dict__)
        self.position_sizer = PositionSizer(self.risk_limits)
        self.risk_monitor = RiskMonitor(self.risk_limits.max_daily_loss)
        self.reporter = Reporter()

        self.logger.info("✅ OKX Trading Bot initialized")

    @retry_on_error(max_attempts=3, delay=2)
    def run_trading_cycle(self):
        self.logger.info("Starting trading cycle...")


        current_price = self.exchange.get_market_price("BTC")
        if not current_price:
            self.logger.error("Failed to get market price")
            return

        balance = self.exchange.get_balance()
        self.logger.info(f"Current price: {current_price} | Balance: {balance} USDT")



    def run(self):
        self.logger.info("Starting trading bot...")
        try:
            while True:
                self.run_trading_cycle()
                time.sleep(60)
        except KeyboardInterrupt:
            self.logger.info("Bot stopped by user")
            self.reporter.print_summary()


if __name__ == "__main__":
    load_dotenv()
    bot = TradingBot()
    bot.run()