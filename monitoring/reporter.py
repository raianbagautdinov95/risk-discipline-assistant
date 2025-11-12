
from typing import Dict, Any, List
from datetime import datetime
import json
from pathlib import Path


class Reporter:
    def __init__(self):
        self.report_dir = Path("reports")
        self.report_dir.mkdir(exist_ok=True)
        self.daily_trades = []

    def add_trade(self, trade_data: Dict[str, Any]):

        trade_data["timestamp"] = datetime.now().isoformat()
        self.daily_trades.append(trade_data)

    def generate_daily_report(self) -> Dict[str, Any]:

        if not self.daily_trades:
            return {"message": "No trades today"}

        total_trades = len(self.daily_trades)
        winning_trades = sum(1 for t in self.daily_trades if t.get("pnl", 0) > 0)
        total_pnl = sum(t.get("pnl", 0) for t in self.daily_trades)

        report = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "total_trades": total_trades,
            "winning_trades": winning_trades,
            "win_rate": round((winning_trades / total_trades * 100), 2) if total_trades > 0 else 0,
            "total_pnl": round(total_pnl, 2),
            "trades": self.daily_trades
        }


        filename = self.report_dir / f"daily_report_{datetime.now():%Y%m%d}.json"
        with open(filename, "w") as f:
            json.dump(report, f, indent=2)

        return report

    def print_summary(self):

        report = self.generate_daily_report()
        print("\n" + "=" * 50)
        print(f"DAILY TRADING REPORT - {report.get('date', 'N/A')}")
        print("=" * 50)
        print(f"Total Trades: {report.get('total_trades', 0)}")
        print(f"Win Rate: {report.get('win_rate', 0)}%")
        print(f"Total P&L: {report.get('total_pnl', 0)} USDT")
        print("=" * 50)