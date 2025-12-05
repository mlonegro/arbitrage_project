# 🇦🇷 Argentine Dollar Futures Arbitrage Monitor

A real-time quantitative finance dashboard that identifies and visualizes arbitrage opportunities between the **Rofex Dollar Futures** curve and the **Caución Bursátil** (Repo) market.

![Python](https://img.shields.io/badge/Python-3.10%2B-blue)
![Streamlit](https://img.shields.io/badge/Streamlit-App-FF4B4B)
![Finance](https://img.shields.io/badge/Domain-Quantitative%20Finance-green)

## 🚀 Project Overview

In Argentina's high-inflation economic environment, capital controls and interest rate volatility often create distortions between the **Implied Devaluation Rate** (derived from Futures) and the **Cost of Leverage** (derived from the Repo/Caución market).

This tool acts as a "Trader's Dashboard" to scan the term structure for two specific arbitrage strategies:

1.  **Cash & Carry (Classic Arb):**
    * **Strategy:** Borrow ARS (Caución) → Buy Spot USD → Sell Future USD.
    * **Logic:** Profit generated when *Implied Yield (Bid) > Funding Cost*.
    
2.  **Reverse Arbitrage:**
    * **Strategy:** Sell Spot USD → Invest ARS (Caución) → Buy Future USD.
    * **Logic:** Profit generated when *Investment Yield > Implied Cost (Ask)*.

## 🛠 Tech Stack & Architecture

* **Frontend:** `Streamlit` for rapid interactive dashboarding and visualization.
* **Data Analysis:** `Pandas` and `NumPy` for vectorized financial calculations (Implied Rates, TNA, Spreads).
* **Visualization:** `Plotly` for interactive yield curves and spread analysis.
* **Data Ingestion:**
    * **API:** `pyRofex` integration for Matba Rofex (Test Environment).
    * **Scraping:** Custom `Requests` + `JSON` parsers to ingest real-time public market data (Ámbito Financiero).
* **Simulation Engine:** A logic layer that allows users to stress-test PnL by widening Bid/Ask spreads and increasing transaction costs.

## ⚙️ Key Features

* **Multi-Source Data Pipeline:** Robust ingestion strategy that falls back to different sources (API → Scraper → Synthetic) to ensure the dashboard never breaks during a demo.
* **Liquidity Stress Testing:** Interactive sliders to model execution friction. Users can simulate widening spreads to see how "Paper Profits" disappear in low-liquidity scenarios.
* **Implied Spot Indicator:** Calculates the market's "Fair Value" for Spot USD based on interest rate parity, serving as a signal for devaluation expectations.
* **Real-Time Yield Curve:** Visual comparison of the Futures Implied Rate curve vs. the proprietary Funding Rate benchmark.

## 📦 Installation & Usage

1.  **Clone the repository:**
    ```bash
    git clone [https://github.com/yourusername/rofex-arb-monitor.git](https://github.com/yourusername/rofex-arb-monitor.git)
    cd rofex-arb-monitor
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Dashboard:**
    ```bash
    streamlit run app.py
    ```

4.  **Select Data Mode:**
    * **Public Scraper:** Fetches real market data from public financial portals.
    * **Simulation:** Generates synthetic data to demonstrate the arbitrage logic when markets are closed.

## 📂 Project Structure

* `app.py`: Main dashboard entry point and UI logic.
* `market_monitor.py`: Financial logic engine (Classes: `ArbMonitor`, `MarketSnapshot`).
* `scraper_feed.py`: Robust data connector for public market data.
* `real_feed.py`: Connector for the official Matba Rofex API (Test Environment).

## ⚠️ Disclaimer

This software is for educational and research purposes only. It does not constitute financial advice. Market data scraping relies on third-party structures that may change without notice.

---

**Author:** Martin Lonegro Gurfinkel  
**Contact:** [ml5215@columbia.edu](mailto:ml5215@columbia.edu)