# Argentine Dollar Futures Arbitrage Monitor

A quantitative finance application that identifies and analyzes arbitrage opportunities in the Argentine dollar futures market by comparing the implied devaluation rate from Rofex futures contracts against the cost of leverage in the Caución Bursátil (repo) market.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B)
![Finance](https://img.shields.io/badge/Domain-Quantitative%20Finance-green)

## Overview

Argentina's high-inflation environment, combined with strict capital controls and volatile interest rates, frequently creates pricing inefficiencies between the dollar futures market and the repo market. This application provides real-time analysis of these discrepancies, enabling traders to identify potential arbitrage opportunities.

The system monitors the term structure of dollar futures contracts (DLR) traded on Matba Rofex and calculates implied annual rates. These rates are compared against the funding cost available in the Caución market to identify two distinct arbitrage strategies:

**Cash & Carry Arbitrage:**
- Borrow ARS via Caución at the funding rate
- Purchase USD in the spot market
- Sell USD futures contracts
- Profit when the implied futures rate exceeds the funding cost

**Reverse Arbitrage:**
- Sell USD in the spot market for ARS
- Invest ARS via Caución at the funding rate
- Purchase USD futures contracts
- Profit when the funding rate exceeds the implied futures rate

## Technical Architecture

**Data Layer:**
- Primary source: pyRofex API integration with Matba Rofex (test environment)
- Fallback source: Web scraper for Ámbito Financiero market data
- Simulation mode: Synthetic data generator for testing and demonstrations

**Processing Layer:**
- `ArbMonitor` class: Core calculation engine for implied rates and spread analysis
- `MarketSnapshot` dataclass: Standardized container for market state
- Pandas/NumPy: Vectorized financial calculations (TNA, implied rates, days to maturity)

**Presentation Layer:**
- Streamlit framework: Interactive dashboard and real-time updates
- Plotly: Term structure visualizations and yield curve analysis
- Custom styling: Professional light-theme interface optimized for financial data

## Key Features

**Flexible Data Ingestion:**
Multi-source pipeline with automatic fallback ensures data availability regardless of API status or market hours. The system gracefully handles missing bid/ask data by using settlement prices with synthetic spreads.

**Execution Simulation:**
Interactive controls allow users to model real-world trading conditions by adjusting commission rates and bid/ask spreads, demonstrating how transaction costs impact theoretical arbitrage profits.

**Implied Rate Calculation:**
Computes annualized implied devaluation rates from futures prices using interest rate parity principles, providing insight into market expectations for currency depreciation.

**Term Structure Visualization:**
Displays the complete futures curve alongside the funding rate benchmark, making it easy to identify which maturities offer the most attractive arbitrage spreads.

## Installation

Clone the repository:
```bash
git clone https://github.com/yourusername/arb-monitor.git
cd arb-monitor
```

Install dependencies:
```bash
pip install -r requirements.txt
```

Run the application:
```bash
streamlit run app.py
```

## Usage

1. Select a data source from the sidebar (ROFEX API, Ámbito scraper, or simulation mode)
2. Adjust the Caución funding rate to reflect current market conditions
3. Optionally add commission costs or spread widening to model execution friction
4. Review the displayed metrics, yield curve, and contract table for opportunities
5. Analyze the spread (in basis points) to identify profitable trades

## Project Structure

```
├── app.py                  # Streamlit UI and main application logic
├── market_monitor.py       # ArbMonitor class and financial calculations
├── scraper_feed.py         # Ámbito Financiero web scraper
├── real_feed.py            # pyRofex API integration and mock data generator
└── requirements.txt        # Python dependencies
```

## Dependencies

- `streamlit` - Web application framework
- `pandas` - Data manipulation and analysis
- `numpy` - Numerical computing
- `plotly` - Interactive charting
- `pyrofex` - Rofex API client
- `requests` - HTTP library for web scraping
- `lxml` - XML/HTML parsing

## Disclaimer

This software is provided for educational and research purposes only. It does not constitute investment advice or a recommendation to trade. Market data obtained via web scraping may be subject to terms of service restrictions and structural changes. The author assumes no liability for trading decisions made using this tool.

---

**Author:** Martin Lonegro Gurfinkel
**Contact:** ml5215@columbia.edu