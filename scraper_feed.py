import pandas as pd
import requests
from datetime import datetime
import json
import re
from dataclasses import dataclass
from typing import Dict, Optional

# Define MarketSnapshot to avoid import circularity
@dataclass
class MarketSnapshot:
    timestamp: datetime
    spot_price: float
    funding_rates: Dict[str, float]
    futures_chain: pd.DataFrame

class ScraperFeed:
    """
    Fetches ACTUAL market data from Ámbito Financiero's API endpoints.
    """
    def __init__(self):
        self.url_futures = "https://mercados.ambito.com//dolarfuturo/datos"
        self.url_spot = "https://mercados.ambito.com//dolar/mayorista/variacion"
        
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://www.ambito.com/",
            "Origin": "https://www.ambito.com",
            "Accept": "application/json"
        }

    def get_snapshot(self, use_mock_fallback=False) -> Optional[MarketSnapshot]:
        """
        Main entry point for App.
        """
        # 1. Get Futures
        df_futures = self.fetch_futures()
        if df_futures.empty:
            print("⚠️ Scraper failed to get futures.")
            if use_mock_fallback:
                return None # Or return mock if you wanted to implement fallback logic here
            return None

        # 2. Get Spot Price
        spot = self.fetch_spot_price()

        # 3. Default Rates (User overrides this with slider anyway)
        rates = {'1d': 0.35} 

        return MarketSnapshot(
            timestamp=datetime.now(),
            spot_price=spot,
            funding_rates=rates,
            futures_chain=df_futures
        )

    def fetch_spot_price(self) -> float:
        try:
            resp = requests.get(self.url_spot, headers=self.headers, timeout=5)
            data = resp.json()
            # We use 'venta' (Ask) as the reference price to BUY spot
            price_str = data.get('venta', '0')
            return self._clean_price(price_str)
        except:
            return 1050.00 # Fallback

    def _parse_contract_maturity(self, text):
        spanish_months = {
            'enero': 1, 'febrero': 2, 'marzo': 3, 'abril': 4, 'mayo': 5, 'junio': 6,
            'julio': 7, 'agosto': 8, 'septiembre': 9, 'octubre': 10, 'noviembre': 11, 'diciembre': 12
        }
        try:
            pattern = r"(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre).*?(\d{4})"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                month = spanish_months.get(match.group(1).lower())
                year = int(match.group(2))
                # Rofex Rule: Last Business Day of the Month
                dt = pd.Timestamp(year=year, month=month, day=1)
                return (dt + pd.offsets.BMonthEnd()).date()
            return None
        except:
            return None

    def _clean_price(self, val):
        if isinstance(val, (int, float)): return float(val)
        if isinstance(val, str):
            val = val.strip()
            try:
                return float(val)
            except ValueError:
                # Try Argentine format "1.050,50"
                clean_val = val.replace('.', '').replace(',', '.')
                try: return float(clean_val)
                except: return 0.0
        return 0.0

    def fetch_futures(self) -> pd.DataFrame:
        try:
            response = requests.get(self.url_futures, headers=self.headers, timeout=10)
            data = response.json()
            
            futures_data = []
            for item in data:
                name = item.get('contrato', '') or item.get('nombre', '')
                price_str = item.get('ultimo', '') or item.get('cierre', '')
                bid_str = item.get('compra', '')
                ask_str = item.get('venta', '')
                
                last = self._clean_price(price_str)
                bid = self._clean_price(bid_str)
                ask = self._clean_price(ask_str)
                
                # Gap Fill Logic
                if last == 0:
                    if bid > 0 and ask > 0: last = (bid + ask) / 2
                    elif ask > 0: last = ask
                    elif bid > 0: last = bid

                if bid == 0: bid = last
                if ask == 0: ask = last

                maturity = self._parse_contract_maturity(name)
                
                if maturity and last > 0:
                    days = (maturity - datetime.now().date()).days
                    if days > 0:
                        ticker = f"DLR/{maturity.strftime('%b%y').upper()}"
                        futures_data.append({
                            'Ticker': ticker,
                            'Maturity': maturity,
                            'Days': days,
                            'Bid': bid,
                            'Ask': ask,
                            'Last': last
                        })

            df = pd.DataFrame(futures_data)
            if not df.empty:
                df = df.sort_values('Days').reset_index(drop=True)
            return df

        except Exception as e:
            print(f"❌ Error scraping Ambito: {e}")
            return pd.DataFrame()