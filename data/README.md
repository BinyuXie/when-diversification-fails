# Data setup

The analysis uses the official iShares fund data workbooks for four US-listed ETFs. The source files are not redistributed in this repository. This keeps the source provenance clear and avoids republishing third-party data.

Download each workbook using the **Data Download** link on the official fund page:

| Ticker | Fund | Official page | Local filename |
|---|---|---|---|
| IVV | iShares Core S&P 500 ETF | https://www.ishares.com/us/products/239726/ishares-core-sp-500-etf | `IVV_fund_data.xls` |
| IEF | iShares 7-10 Year Treasury Bond ETF | https://www.ishares.com/us/products/239456/ishares-7-10-year-treasury-bond-etf | `IEF_fund_data.xls` |
| IAU | iShares Gold Trust | https://www.ishares.com/us/products/239561/ishares-gold-trust-fund | `IAU_fund_data.xls` |
| SHV | iShares Short Treasury Bond ETF | https://www.ishares.com/us/products/239466/ishares-short-treasury-bond-etf | `SHV_fund_data.xls` |

Place the four files in `data/raw/`, then run all cells in `analysis.ipynb`.

The notebook fixes the research snapshot at **31 August 2026**. Published monthly NAV total returns are the primary series. Daily NAV and ex-distribution fields are used as a validation and to fill isolated missing published months.
