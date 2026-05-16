"""
Dataset coverage analysis for the wine recommender.

Computes descriptive statistics and recommender success-rate metrics from the
enriched wine dataset, for documentation in the README "Dataset Analysis" section.

The raw dataset contains a small number of malformed rows (out-of-range ABV,
zero price, missing colour). These are filtered explicitly and the number of
dropped rows is logged -- no silent data loss.

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

# Data quality bounds (matches wine_recommender.py ABV filter of 5-20)
ABV_VALID_MIN: float = 5.0
ABV_VALID_MAX: float = 20.0
PRICE_VALID_MIN: float = 0.01  # a wine priced at exactly $0 is a data error


def load_dataset(csv_path: Path) -> pd.DataFrame:
    """
    Load, validate, and clean the wine dataset.

    Cleaning steps (each logged):
        1. Normalize the colour column name.
        2. Coerce ABV and Price to numeric.
        3. Drop rows with ABV outside [5, 20] % (matches recommender filter).
        4. Drop rows with non-positive price.
        5. Drop rows with missing colour.

    Parameters
    ----------
    csv_path : Path
        Path to enriched_wine_data_safari.csv.

    Returns
    -------
    pd.DataFrame
        Cleaned dataframe ready for analysis.
    """
    df: pd.DataFrame = pd.read_csv(csv_path)
    n_raw: int = len(df)
    logger.info("Loaded raw dataset: shape=%s", df.shape)

    # Normalize column name (Colour -> Color)
    if "Colour of Wine" in df.columns:
        df = df.rename(columns={"Colour of Wine": "Color"})

    # Coerce numeric columns
    df["Alcohol Level (ABV)"] = pd.to_numeric(df["Alcohol Level (ABV)"], errors="coerce")
    df["Price"] = pd.to_numeric(
        df["Price"].astype(str).str.replace(r"[\$,€]", "", regex=True),
        errors="coerce",
    )

    # --- Data quality filtering (explicit, logged) ---
    n_bad_abv: int = int((~df["Alcohol Level (ABV)"].between(ABV_VALID_MIN, ABV_VALID_MAX)).sum())
    df = df[df["Alcohol Level (ABV)"].between(ABV_VALID_MIN, ABV_VALID_MAX)]
    logger.info("Dropped %d rows: ABV outside [%.0f, %.0f]%%", n_bad_abv, ABV_VALID_MIN, ABV_VALID_MAX)

    n_bad_price: int = int((~(df["Price"] >= PRICE_VALID_MIN)).sum())
    df = df[df["Price"] >= PRICE_VALID_MIN]
    logger.info("Dropped %d rows: non-positive or missing price", n_bad_price)

    n_bad_color: int = int(df["Color"].isna().sum())
    df = df[df["Color"].notna()]
    logger.info("Dropped %d rows: missing colour", n_bad_color)

    n_clean: int = len(df)
    logger.info("Clean dataset: %d wines (%d dropped from %d raw)", n_clean, n_raw - n_clean, n_raw)
    return df.reset_index(drop=True)


def coverage_report(df: pd.DataFrame) -> dict[str, object]:
    """
    Compute descriptive coverage metrics for the cleaned dataset.

    Parameters
    ----------
    df : pd.DataFrame
        The cleaned wine dataset.

    Returns
    -------
    dict[str, object]
        Coverage metrics keyed by category.
    """
    return {
        "total_wines": len(df),
        "n_countries": df["Country"].nunique(),
        "n_wineries": df["Winery"].nunique(),
        "price_min": round(df["Price"].min(), 2),
        "price_max": round(df["Price"].max(), 2),
        "price_median": round(df["Price"].median(), 2),
        "abv_min": round(df["Alcohol Level (ABV)"].min(), 1),
        "abv_max": round(df["Alcohol Level (ABV)"].max(), 1),
        "abv_mean": round(df["Alcohol Level (ABV)"].mean(), 1),
        "color_distribution": df["Color"].value_counts().to_dict(),
        "top_countries": df["Country"].value_counts().head(5).to_dict(),
    }


def recommender_success_rate(df: pd.DataFrame) -> dict[str, object]:
    """
    Compute the share of (Color x ABV x Country x Price) slot combinations
    that yield at least one wine under strict filtering.

    This quantifies how often the recommender returns a direct match before
    needing constraint relaxation -- the analogue of a feasible-region hit
    rate in constrained portfolio optimization.

    Parameters
    ----------
    df : pd.DataFrame
        The cleaned wine dataset.

    Returns
    -------
    dict[str, object]
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

                    # Relaxation: drop ABV, widen price +/-5 (matches fallback_order)
                    relaxed_price = df["Price"].between(price_lo - 5, price_hi + 5)
                    relaxed = df[color_mask & ctry_mask & relaxed_price]
                    if len(relaxed) > 0:
                        relaxed_recoverable += 1

    return {
        "total_combinations": total_combos,
        "strict_hits": strict_hits,
        "strict_hit_rate": strict_hits / total_combos,
        "relaxed_recoverable": relaxed_recoverable,
        "strict_plus_relaxed_rate": (strict_hits + relaxed_recoverable) / total_combos,
    }


def main() -> None:
    """CLI entrypoint: print full dataset analysis."""
    csv_path: Path = Path("enriched_wine_data_safari.csv")
    df: pd.DataFrame = load_dataset(csv_path)

    logger.info("=" * 55)
    logger.info("COVERAGE REPORT")
    for key, value in coverage_report(df).items():
        logger.info("  %-22s %s", key, value)

    logger.info("=" * 55)
    logger.info("RECOMMENDER SUCCESS RATE")
    for key, value in recommender_success_rate(df).items():
        if isinstance(value, float):
            logger.info("  %-26s %.1f%%", key, value * 100)
        else:
            logger.info("  %-26s %s", key, value)


if __name__ == "__main__":
    main()
