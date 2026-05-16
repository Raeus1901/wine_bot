"""
Dataset coverage analysis for the wine recommender.

Computes descriptive statistics and recommender success-rate metrics from the
enriched wine dataset, for documentation in the README "Dataset Analysis" section.

Author: Jean Treves
License: MIT
"""
from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

# The recommender's initial filter slots (from wine_recommender.py)
COLOR_OPTIONS: list[str] = ["Red", "White", "Rosé", "Sparkling"]
ABV_BANDS: list[tuple[float, float]] = [(11, 12), (12, 13), (13, 14), (14, 15)]
PRICE_BANDS: list[tuple[float, float]] = [(10, 20), (20, 30), (30, 40), (40, 50)]
COUNTRY_GROUPS: list[str] = ["France", "Spain", "Italy", "Others"]


def load_dataset(csv_path: Path) -> pd.DataFrame:
    """
    Load and validate the wine dataset.

    Parameters
    ----------
    csv_path : Path
        Path to enriched_wine_data_safari.csv.

    Returns
    -------
    pd.DataFrame
        Validated dataframe with normalized numeric columns.
    """
    df: pd.DataFrame = pd.read_csv(csv_path)
    logger.info("Loaded dataset: shape=%s", df.shape)

    # Normalize column name (Colour → Color)
    if "Colour of Wine" in df.columns:
        df = df.rename(columns={"Colour of Wine": "Color"})

    # Coerce numeric columns
    df["Alcohol Level (ABV)"] = pd.to_numeric(df["Alcohol Level (ABV)"], errors="coerce")
    df["Price"] = pd.to_numeric(
        df["Price"].astype(str).str.replace(r"[\$,€]", "", regex=True),
        errors="coerce",
    )

    # Data quality report
    logger.info("Missing ABV:   %d", df["Alcohol Level (ABV)"].isna().sum())
    logger.info("Missing Price: %d", df["Price"].isna().sum())
    return df


def coverage_report(df: pd.DataFrame) -> dict[str, object]:
    """
    Compute descriptive coverage metrics for the dataset.

    Parameters
    ----------
    df : pd.DataFrame
        The wine dataset.

    Returns
    -------
    dict[str, object]
        Coverage metrics keyed by category.
    """
    report: dict[str, object] = {
        "total_wines": len(df),
        "n_countries": df["Country"].nunique(),
        "n_wineries": df["Winery"].nunique(),
        "price_min": df["Price"].min(),
        "price_max": df["Price"].max(),
        "price_median": df["Price"].median(),
        "abv_min": df["Alcohol Level (ABV)"].min(),
        "abv_max": df["Alcohol Level (ABV)"].max(),
        "abv_mean": df["Alcohol Level (ABV)"].mean(),
        "color_distribution": df["Color"].value_counts().to_dict(),
        "top_countries": df["Country"].value_counts().head(5).to_dict(),
    }
    return report


def recommender_success_rate(df: pd.DataFrame) -> dict[str, float]:
    """
    Compute the share of (Color × ABV × Country × Price) slot combinations
    that yield at least one wine under strict filtering.

    This quantifies how often the recommender returns a direct match before
    needing constraint relaxation — the analogue of a feasible region hit-rate
    in constrained portfolio optimization.

    Parameters
    ----------
    df : pd.DataFrame
        The wine dataset.

    Returns
    -------
    dict[str, float]
        Success rates and combination counts.
    """
    total_combos: int = 0
    strict_hits: int = 0
    relaxed_recoverable: int = 0

    for color in COLOR_OPTIONS:
        color_mask = df["Color"].str.lower().str.contains(color.lower(), na=False)
        for abv_lo, abv_hi in ABV_BANDS:
            for country in COUNTRY_GROUPS:
                if country == "Others":
                    ctry_mask = ~df["Country"].str.lower().isin(["france", "spain", "italy"])
                else:
                    ctry_mask = df["Country"].str.lower() == country.lower()
                for price_lo, price_hi in PRICE_BANDS:
                    total_combos += 1
                    abv_mask = df["Alcohol Level (ABV)"].between(abv_lo, abv_hi)
                    price_mask = df["Price"].between(price_lo, price_hi)

                    strict = df[color_mask & abv_mask & ctry_mask & price_mask]
                    if len(strict) > 0:
                        strict_hits += 1
                        continue

                    # Relaxation: drop ABV, widen price ±5 (matches fallback_order)
                    relaxed_price = df["Price"].between(price_lo - 5, price_hi + 5)
                    relaxed = df[color_mask & ctry_mask & relaxed_price]
                    if len(relaxed) > 0:
                        relaxed_recoverable += 1

    strict_rate: float = strict_hits / total_combos
    combined_rate: float = (strict_hits + relaxed_recoverable) / total_combos

    return {
        "total_combinations": total_combos,
        "strict_hit_rate": strict_rate,
        "strict_plus_relaxed_rate": combined_rate,
        "strict_hits": strict_hits,
        "relaxed_recoverable": relaxed_recoverable,
    }


def main() -> None:
    """CLI entrypoint: print full dataset analysis."""
    csv_path: Path = Path("enriched_wine_data_safari.csv")
    df: pd.DataFrame = load_dataset(csv_path)

    logger.info("=" * 55)
    logger.info("COVERAGE REPORT")
    coverage: dict[str, object] = coverage_report(df)
    for key, value in coverage.items():
        logger.info("  %-22s %s", key, value)

    logger.info("=" * 55)
    logger.info("RECOMMENDER SUCCESS RATE")
    success: dict[str, float] = recommender_success_rate(df)
    for key, value in success.items():
        if isinstance(value, float):
            logger.info("  %-26s %.1f%%", key, value * 100)
        else:
            logger.info("  %-26s %s", key, value)


if __name__ == "__main__":
    main()
