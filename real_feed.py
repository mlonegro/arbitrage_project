import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass
import pyRofex
import requests

# Fallback definition if market_monitor.py is missing
@dataclass
class MarketSnapshot:
    timestamp: datetime
    spot_price: float
    funding_rates: Dict[str, float]
    futures_chain: pd.DataFrame

class RealFeed:
    """
    Real market data feed using pyRofex API.
    Fetches dollar futures (DLR) market data from ROFEX.
    """
    def __init__(self, username, password, account_id, environment=None):
        """
        Initialize RealFeed with pyRofex credentials.

        Args:
            username: ROFEX user
            password: ROFEX password
            account_id: ROFEX account ID
            environment: pyRofex.Environment.REMARKET (demo) or pyRofex.Environment.LIVE (production)
        """
        self.username = username
        self.password = password
        self.account_id = account_id
        self.environment = environment or pyRofex.Environment.REMARKET
        self._initialized = False

    def _initialize_connection(self):
        """Initialize pyRofex connection if not already initialized."""
        if not self._initialized:
            try:
                pyRofex.initialize(
                    user=self.username,
                    password=self.password,
                    account=self.account_id,
                    environment=self.environment
                )
                self._initialized = True
            except Exception as e:
                print(f"Failed to initialize pyRofex connection: {e}")
                raise

    def get_dlr_futures_tickers(self, limit: int = 12, monthly_only: bool = True, a_series_only: bool = False) -> List[str]:
        """
        Get available DLR futures tickers.

        Args:
            limit: Maximum number of tickers to return
            monthly_only: If True, only return monthly futures (e.g., DLR/ENE26, DLR/FEB26)
                         excluding spread contracts and options
            a_series_only: If True, only return 'A' series contracts (e.g., DLR/ENE26A)

        Returns:
            List of DLR futures ticker symbols (e.g., ['DLR/DIC25', 'DLR/ENE26'])
        """
        self._initialize_connection()

        try:
            instruments = pyRofex.get_all_instruments()

            if instruments and instruments.get('status') == 'OK':
                all_tickers = instruments.get('instruments', [])

                # Filter for DLR futures
                dlr_tickers = []
                for ticker in all_tickers:
                    symbol = ticker['instrumentId']['symbol']
                    if symbol.startswith('DLR/'):
                        if monthly_only:
                            # Only include simple monthly contracts
                            # Exclude spreads (with multiple '/'), and options (containing ' P' or ' C')
                            parts = symbol.split('/')
                            if len(parts) == 2:  # Should be exactly DLR/MONTH or DLR/MONTHA
                                month_part = parts[1]

                                # Check for A series (6 characters ending in A)
                                if a_series_only:
                                    # Format: ENE26A, FEB26A (6 chars, first 3 alpha, next 2 digits, last is 'A')
                                    if (len(month_part) == 6 and
                                        month_part[:3].isalpha() and
                                        month_part[3:5].isdigit() and
                                        month_part[5] == 'A'):
                                        dlr_tickers.append(symbol)
                                else:
                                    # Original format: ENE26, FEB26 (5 chars)
                                    # Or A series format: ENE26A (6 chars)
                                    if len(month_part) == 5 and month_part[:3].isalpha() and month_part[3:].isdigit():
                                        dlr_tickers.append(symbol)
                                    elif len(month_part) == 6 and month_part[:3].isalpha() and month_part[3:5].isdigit() and month_part[5] == 'A':
                                        dlr_tickers.append(symbol)
                        else:
                            dlr_tickers.append(symbol)

                return sorted(dlr_tickers)[:limit]

            return []
        except Exception as e:
            print(f"Error fetching DLR tickers: {e}")
            return []

    def _fetch_spot_from_ambito(self) -> Optional[float]:
        """
        Fetch real spot USD/ARS price from Ámbito Financiero.
        Returns the 'mayorista' (wholesale) dollar price which is the reference for futures.
        """
        try:
            url = "https://mercados.ambito.com//dolar/mayorista/variacion"
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                "Accept": "application/json"
            }
            response = requests.get(url, headers=headers, timeout=5)
            data = response.json()

            # Use 'venta' (ask) as reference - this is what you'd pay to buy USD
            price_str = data.get('venta', '0')

            # Clean price (handle Argentine format "1.050,50")
            if isinstance(price_str, str):
                clean_price = price_str.replace('.', '').replace(',', '.')
                return float(clean_price)
            return float(price_str)
        except Exception as e:
            print(f"⚠️ Failed to fetch spot from Ámbito: {e}")
            return None

    def _parse_expiry_date(self, ticker: str) -> Optional[datetime]:
        """
        Parse expiry date from ticker symbol.
        Example: DLR/ENE26 -> January 2026
        Example: DLR/ENE26A -> January 2026
        """
        try:
            parts = ticker.split('/')
            if len(parts) != 2:
                return None

            month_year = parts[1]

            # Handle both ENE26 (5 chars) and ENE26A (6 chars) formats
            if len(month_year) == 6 and month_year[5] == 'A':
                # Remove the 'A' suffix
                month_year = month_year[:5]
            elif len(month_year) != 5:
                return None

            month_code = month_year[:3]
            year_code = month_year[3:]

            # Spanish month codes
            month_map = {
                'ENE': 1, 'FEB': 2, 'MAR': 3, 'ABR': 4, 'MAY': 5, 'JUN': 6,
                'JUL': 7, 'AGO': 8, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DIC': 12
            }

            month = month_map.get(month_code)
            if month is None:
                return None

            year = 2000 + int(year_code)

            # Expiry is typically last business day of the month
            # For simplicity, use the last day of the month
            import calendar
            last_day = calendar.monthrange(year, month)[1]

            return datetime(year, month, last_day)
        except:
            return None

    def get_dlr_market_data(self, tickers: Optional[List[str]] = None) -> pd.DataFrame:
        """
        Extract market data for dollar futures from pyRofex API.

        Args:
            tickers: List of DLR ticker symbols (e.g., ['DLR/DIC25', 'DLR/ENE26'])
                    If None, will fetch available tickers automatically.

        Returns:
            DataFrame with columns: Ticker, Bid, BidSize, Ask, AskSize, Last, LastSize,
                                   OpenInterest, Volume, SettlementPrice, etc.
        """
        self._initialize_connection()

        # Get tickers if not provided
        if tickers is None:
            tickers = self.get_dlr_futures_tickers()

        if not tickers:
            print("No DLR tickers found")
            return pd.DataFrame()

        # Define market data entries we want to retrieve
        entries = [
            pyRofex.MarketDataEntry.BIDS,
            pyRofex.MarketDataEntry.OFFERS,
            pyRofex.MarketDataEntry.LAST,
            pyRofex.MarketDataEntry.OPENING_PRICE,
            pyRofex.MarketDataEntry.CLOSING_PRICE,
            pyRofex.MarketDataEntry.SETTLEMENT_PRICE,
            pyRofex.MarketDataEntry.TRADE_VOLUME,
            pyRofex.MarketDataEntry.OPEN_INTEREST
        ]

        market_data_list = []

        for ticker in tickers:
            try:
                # Get market data for each ticker
                md = pyRofex.get_market_data(ticker=ticker, entries=entries)

                if md and md.get('status') == 'OK':
                    data = md.get('marketData', {})

                    # Extract bid information
                    bids = data.get('BI', [])
                    if isinstance(bids, list) and len(bids) > 0:
                        bid_price = bids[0].get('price') if isinstance(bids[0], dict) else None
                        bid_size = bids[0].get('size') if isinstance(bids[0], dict) else None
                    else:
                        bid_price = None
                        bid_size = None

                    # Extract offer information
                    offers = data.get('OF', [])
                    if isinstance(offers, list) and len(offers) > 0:
                        ask_price = offers[0].get('price') if isinstance(offers[0], dict) else None
                        ask_size = offers[0].get('size') if isinstance(offers[0], dict) else None
                    else:
                        ask_price = None
                        ask_size = None

                    # Extract last trade
                    last_data = data.get('LA')
                    if isinstance(last_data, dict):
                        last_price = last_data.get('price')
                        last_size = last_data.get('size')
                    elif isinstance(last_data, (int, float)):
                        last_price = last_data
                        last_size = None
                    else:
                        last_price = None
                        last_size = None

                    # Extract other data
                    opening_data = data.get('OP')
                    opening_price = opening_data.get('price') if isinstance(opening_data, dict) else opening_data

                    closing_data = data.get('CL')
                    closing_price = closing_data.get('price') if isinstance(closing_data, dict) else closing_data

                    settlement_data = data.get('SE')
                    settlement_price = settlement_data.get('price') if isinstance(settlement_data, dict) else settlement_data

                    # Enhanced fallback logic: Use settlement/closing/last price when bid/ask missing
                    fallback_used = False
                    if bid_price is None or ask_price is None:
                        # Priority: SettlementPrice > ClosingPrice > Last
                        fallback_price = None
                        if settlement_price and settlement_price > 0:
                            fallback_price = settlement_price
                        elif closing_price and closing_price > 0:
                            fallback_price = closing_price
                        elif last_price and last_price > 0:
                            fallback_price = last_price

                        if fallback_price and fallback_price > 0:
                            # Apply small synthetic spread to avoid bid=ask (0.01% spread)
                            if bid_price is None:
                                bid_price = fallback_price * 0.9999
                                fallback_used = True
                            if ask_price is None:
                                ask_price = fallback_price * 1.0001
                                fallback_used = True

                    if fallback_used:
                        print(f"⚠️ Using settlement/closing fallback for {ticker}: settlement=${settlement_price}, closing=${closing_price}, bid=${bid_price:.2f}, ask=${ask_price:.2f}")

                    volume = data.get('TV')
                    open_interest = data.get('OI')

                    # Parse expiry date from ticker
                    expiry_date = self._parse_expiry_date(ticker)

                    # Calculate days to expiry
                    days_to_expiry = None
                    maturity_date = None
                    if expiry_date:
                        maturity_date = expiry_date.date()
                        days_to_expiry = (maturity_date - datetime.now().date()).days

                    market_data_list.append({
                        'Ticker': ticker,
                        'Maturity': maturity_date,
                        'Days': days_to_expiry,
                        'Bid': bid_price,
                        'BidSize': bid_size,
                        'Ask': ask_price,
                        'AskSize': ask_size,
                        'Last': last_price,
                        'LastSize': last_size,
                        'OpeningPrice': opening_price,
                        'ClosingPrice': closing_price,
                        'SettlementPrice': settlement_price,
                        'Volume': volume,
                        'OpenInterest': open_interest,
                        'Timestamp': datetime.now()
                    })

            except Exception as e:
                print(f"Error fetching data for {ticker}: {e}")

        return pd.DataFrame(market_data_list)

    def get_snapshot(self, use_mock_fallback=True) -> MarketSnapshot:
        """
        Get market snapshot with real DLR futures data.
        Falls back to mock data if real data fetch fails and use_mock_fallback=True.
        """
        try:
            # Get A-series contracts by default
            tickers = self.get_dlr_futures_tickers(limit=30, monthly_only=True, a_series_only=True)
            futures_df = self.get_dlr_market_data(tickers=tickers)

            if futures_df.empty and use_mock_fallback:
                return self._generate_mock_snapshot()

            # Get real spot price from Ámbito (mayorista wholesale rate)
            spot_price = self._fetch_spot_from_ambito()

            # Fallback to discounted nearest futures if Ámbito fails
            if not spot_price and not futures_df.empty:
                print("⚠️ Using nearest futures as spot fallback")
                futures_sorted = futures_df.sort_values('Days')
                nearest = futures_sorted.iloc[0]

                # Priority: Settlement > Last > Mid-quote
                if pd.notna(nearest['SettlementPrice']):
                    spot_price = nearest['SettlementPrice']
                elif pd.notna(nearest['Last']):
                    spot_price = nearest['Last']
                elif pd.notna(nearest['Bid']) and pd.notna(nearest['Ask']):
                    spot_price = (nearest['Bid'] + nearest['Ask']) / 2

                # Discount back to spot approximation
                if spot_price and pd.notna(nearest['Days']) and nearest['Days'] > 0:
                    discount_factor = 1 / (1 + (0.35 * nearest['Days'] / 365))
                    spot_price = spot_price * discount_factor

            return MarketSnapshot(
                timestamp=datetime.now(),
                spot_price=spot_price,
                funding_rates={'1d': 0.0},  # Calculate if needed
                futures_chain=futures_df
            )

        except Exception as e:
            print(f"Error getting snapshot: {e}")
            if use_mock_fallback:
                return self._generate_mock_snapshot()
            raise

    def _generate_mock_snapshot(self) -> MarketSnapshot:
        spot = 1450.50
        months = range(1, 7)
        futures_data = []
        for m in months:
            days = 30 * m
            # Theoretical price assuming ~40% rate
            fair_price = spot * (1 + (0.40 * days / 365))
            noise = np.random.uniform(-5, 10)
            price = fair_price + noise
            
            futures_data.append({
                'Ticker': f'DLR/MOCK{m}',
                'Maturity': datetime.now().date() + timedelta(days=days),
                'Days': days,
                'Bid': round(price - 2, 2),
                'Ask': round(price + 2, 2),
                'Last': round(price, 2)
            })
        
        return MarketSnapshot(
            timestamp=datetime.now(),
            spot_price=spot,
            funding_rates={'1d': 0.35},
            futures_chain=pd.DataFrame(futures_data)
        )


def main():
    """
    Main function to fetch and display DLR monthly futures market data.
    """
    import os
    from tabulate import tabulate

    print("=" * 100)
    print("DLR MONTHLY FUTURES - MARKET DATA")
    print("=" * 100)
    print()

    # Try to load credentials from secrets.toml first, then env vars
    username = None
    password = None
    account_id = None

    try:
        import toml
        secrets_path = os.path.join(os.path.dirname(__file__), '.streamlit', 'secrets.toml')
        if os.path.exists(secrets_path):
            secrets = toml.load(secrets_path)
            username = secrets.get('ROFEX_USER')
            password = secrets.get('ROFEX_PASSWORD')
            account_id = secrets.get('ROFEX_ACCOUNT')
    except:
        pass

    # Fall back to environment variables
    if not username:
        username = os.getenv('ROFEX_USER', 'your_username')
        password = os.getenv('ROFEX_PASSWORD', 'your_password')
        account_id = os.getenv('ROFEX_ACCOUNT', 'your_account')

    # Initialize the feed
    feed = RealFeed(
        username=username,
        password=password,
        account_id=account_id,
        environment=pyRofex.Environment.REMARKET
    )

    print("Fetching DLR monthly futures contracts (A series)...")

    # Get only monthly A series futures (excluding spreads and options)
    tickers = feed.get_dlr_futures_tickers(limit=30, monthly_only=True, a_series_only=True)

    if not tickers:
        print("No monthly A series futures found or connection failed.")
        return

    print(f"Found {len(tickers)} monthly A series contracts")
    print()

    # Fetch market data
    df = feed.get_dlr_market_data(tickers=tickers)

    if df.empty:
        print("No market data retrieved.")
        return

    # Filter out contracts with no bid/ask data
    df_filtered = df[df['Bid'].notna() & df['Ask'].notna()].copy()

    if df_filtered.empty:
        print("No contracts with active bid/ask quotes found.")
        return

    # Format the expiry date for display
    df_filtered['Expiry Date'] = df_filtered['Expiry'].apply(
        lambda x: x.strftime('%Y-%m-%d') if pd.notna(x) else 'N/A'
    )

    # Calculate days to expiry
    today = datetime.now()
    df_filtered['Days to Expiry'] = df_filtered['Expiry'].apply(
        lambda x: (x - today).days if pd.notna(x) else None
    )

    # Create display table with only relevant columns
    display_df = df_filtered[[
        'Ticker', 'Expiry Date', 'Days to Expiry', 'Bid', 'Ask'
    ]].copy()

    # Add spread
    display_df['Spread'] = display_df['Ask'] - display_df['Bid']

    # Sort by expiry date
    display_df = display_df.sort_values('Days to Expiry')

    print(tabulate(
        display_df,
        headers='keys',
        tablefmt='grid',
        floatfmt='.2f',
        showindex=False
    ))

    print()
    print(f"Data retrieved at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 100)


if __name__ == "__main__":
    main()