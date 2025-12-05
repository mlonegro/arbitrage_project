import pandas as pd
from dataclasses import dataclass
from typing import Dict
from datetime import datetime

@dataclass
class MarketSnapshot:
    timestamp: datetime
    spot_price: float
    funding_rates: Dict[str, float]
    futures_chain: pd.DataFrame

class ArbMonitor:
    def __init__(self, risk_free_rate_tenor='1d'):
        self.risk_free_tenor = risk_free_rate_tenor

    def process_tick(self, snapshot: MarketSnapshot) -> pd.DataFrame:
        if snapshot.futures_chain.empty:
            return pd.DataFrame()

        df = snapshot.futures_chain.copy()

        # VALIDATION 1: Filter invalid Days
        invalid_days = (df['Days'] <= 0) | (df['Days'] > 730)
        if invalid_days.any():
            print(f"⚠️ Filtered {invalid_days.sum()} contracts with invalid Days (≤0 or >730)")
            df = df[~invalid_days]

        if df.empty:
            return pd.DataFrame()

        # VALIDATION 2: Check spot price
        spot_ref = snapshot.spot_price
        if not spot_ref or spot_ref <= 0:
            print("❌ Invalid spot price (must be > 0)")
            return pd.DataFrame()

        # VALIDATION 3: Filter invalid spreads (Bid >= Ask)
        invalid_spread = df['Bid'] >= df['Ask']
        if invalid_spread.any():
            print(f"⚠️ Filtered {invalid_spread.sum()} contracts with Bid ≥ Ask")
            df = df[~invalid_spread]

        if df.empty:
            return pd.DataFrame()

        funding_rate = snapshot.funding_rates.get(self.risk_free_tenor, 0.0)
        
        if spot_ref > 0:
            df['Implied_TNA_Bid'] = ((df['Bid'] / spot_ref) - 1) * (365 / df['Days'])
            df['Implied_TNA_Ask'] = ((df['Ask'] / spot_ref) - 1) * (365 / df['Days'])
        else:
            df['Implied_TNA_Bid'] = 0.0
            df['Implied_TNA_Ask'] = 0.0
        
        df['Implied_Spot'] = df['Bid'] / (1 + (funding_rate * (df['Days'] / 365)))
        df['Funding_Cost_TNA'] = funding_rate
        
        df['Classic_Spread_bps'] = (df['Implied_TNA_Bid'] - funding_rate) * 10000
        df['Reverse_Spread_bps'] = (funding_rate - df['Implied_TNA_Ask']) * 10000
        df['Max_Spread_bps'] = df[['Classic_Spread_bps', 'Reverse_Spread_bps']].max(axis=1)
        
        def get_strat(row):
            if row['Classic_Spread_bps'] >= row['Reverse_Spread_bps']:
                return "Carry (Sell Fut)"
            else:
                return "Reverse (Buy Fut)"
        
        df['Strategy'] = df.apply(get_strat, axis=1)
        return df