"""Load official monthly total NAV returns from iShares fund workbooks.

The downloaded `.xls` files are XML Spreadsheet workbooks. Published monthly
total NAV returns are the primary series. A daily NAV-plus-distribution
reconstruction validates those returns and fills isolated missing months.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from lxml import etree


ASSETS = ("IVV", "IEF", "IAU", "SHV")


def _worksheet_rows(path: Path, worksheet_name: str) -> list[list[str]]:
    """Return text values from one worksheet in an XML Spreadsheet file."""

    namespace = {"s": "urn:schemas-microsoft-com:office:spreadsheet"}
    name_key = "{urn:schemas-microsoft-com:office:spreadsheet}Name"
    parser = etree.XMLParser(recover=True, huge_tree=True)
    root = etree.parse(str(path), parser).getroot()
    worksheet = next(
        sheet
        for sheet in root.findall("s:Worksheet", namespace)
        if sheet.get(name_key) == worksheet_name
    )

    rows: list[list[str]] = []
    for row in worksheet.find("s:Table", namespace).findall("s:Row", namespace):
        values: list[str] = []
        for cell in row.findall("s:Cell", namespace):
            data = cell.find("s:Data", namespace)
            values.append("".join(data.itertext()).strip() if data is not None else "")
        rows.append(values)
    return rows


def _parse_daily_history(path: Path) -> pd.DataFrame:
    rows = _worksheet_rows(path, "Historical")
    frame = pd.DataFrame(rows[1:], columns=rows[0]).rename(
        columns={"As Of": "date", "NAV per Share": "nav", "Ex-Dividends": "distribution"}
    )
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["nav"] = pd.to_numeric(frame["nav"], errors="coerce")
    frame["distribution"] = pd.to_numeric(frame["distribution"], errors="coerce").fillna(0.0)
    frame = frame.dropna(subset=["date", "nav"]).sort_values("date").set_index("date")
    frame["daily_total_return"] = (
        (frame["nav"] + frame["distribution"]) / frame["nav"].shift(1) - 1.0
    )
    frame["wealth_index"] = (1.0 + frame["daily_total_return"].fillna(0.0)).cumprod()
    return frame[["nav", "distribution", "daily_total_return", "wealth_index"]]


def _parse_published_monthly_returns(path: Path) -> pd.Series:
    rows = _worksheet_rows(path, "Performance")
    header_position = next(
        index
        for index, values in enumerate(rows)
        if len(values) >= 2
        and values[0] == "Month End Date"
        and values[1] == "Monthly Total (NAV) Return"
    )

    observations: list[tuple[pd.Timestamp, float]] = []
    for values in rows[header_position + 1 :]:
        if len(values) < 2:
            continue
        date = pd.to_datetime(values[0], errors="coerce")
        total_return_percent = pd.to_numeric(values[1], errors="coerce")
        if pd.notna(date):
            observations.append((date, total_return_percent / 100.0))

    series = pd.Series(dict(observations), name="published_monthly_total_nav_return").sort_index()
    series.index = series.index.to_period("M").to_timestamp("M")
    return series


def load_monthly_total_returns(
    raw_dir: Path,
    start: str = "2008-01-31",
    end: str = "2026-08-31",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load aligned asset returns and return a compact validation table."""

    monthly_returns: dict[str, pd.Series] = {}
    validation_records: list[dict[str, object]] = []

    for ticker in ASSETS:
        path = raw_dir / f"{ticker}_fund_data.xls"
        if not path.exists():
            raise FileNotFoundError(
                f"Missing {path}. Follow data/README.md to download the official workbook."
            )

        published = _parse_published_monthly_returns(path)
        daily = _parse_daily_history(path)
        reconstructed_wealth = daily["wealth_index"].resample("ME").last()
        reconstructed = reconstructed_wealth.pct_change(fill_method=None)
        combined = published.combine_first(reconstructed)
        monthly_returns[ticker] = combined

        comparison = pd.concat(
            [published.rename("published"), reconstructed.rename("reconstructed")], axis=1
        ).loc[start:end].dropna()
        difference_bps = (comparison["published"] - comparison["reconstructed"]).abs() * 10_000
        published_window = published.loc[start:end]
        fallback_dates = published_window[published_window.isna()].index
        validation_records.append(
            {
                "asset": ticker,
                "overlapping_months": len(comparison),
                "mean_absolute_difference_bps": difference_bps.mean(),
                "maximum_absolute_difference_bps": difference_bps.max(),
                "months_above_3bps": int((difference_bps > 3.0).sum()),
                "fallback_months": "; ".join(date.strftime("%Y-%m-%d") for date in fallback_dates),
            }
        )

    returns = pd.DataFrame(monthly_returns).loc[start:end]
    if returns.isna().any().any():
        missing = returns.columns[returns.isna().any()].tolist()
        raise ValueError(f"Missing monthly returns remain for: {', '.join(missing)}")

    returns.index.name = "date"
    validation = pd.DataFrame(validation_records).set_index("asset")
    return returns, validation
