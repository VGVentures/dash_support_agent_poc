"""Compare eval pass rate and latency across models, e.g. Sonnet vs. a
cheaper model like Haiku.

Runs the full eval suite once per model (so it makes len(CASES) * len(models)
real API calls) and plots the results with pandas. Run with:
    python3 evals/compare_models.py
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

from agent.core import MODEL
from evals import report
from evals.run_evals import run, write_report

EVALS_DIR = Path(__file__).resolve().parent
DEFAULT_MODELS = [MODEL, "claude-haiku-4-5-20251001"]

VGV_BLUE = "#2A48DE"
VGV_NAVY = "#0A1530"


def results_path_for(model: str, results_dir: Path) -> Path:
    """Where a model's full per-case results (same schema as run_evals.py
    --json) get written, so report.py can render a detail section for it."""
    return results_dir / f"results_{model}.json"


def compare(models: list[str], results_dir: Path) -> pd.DataFrame:
    """Run every case against every model, write each model's full results
    (for report.py's per-model detail sections), and return the flattened
    pass/duration rows used for the summary table and plot."""
    rows = []
    for model in models:
        print(f"\n--- {model} ---")
        results = run(model=model)
        write_report(results, results_path_for(model, results_dir))
        for result in results:
            rows.append(
                {
                    "model": model,
                    "case": result["name"],
                    "passed": result["passed"],
                    "duration_seconds": result["duration_seconds"],
                }
            )
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("model").agg(
        pass_rate=("passed", "mean"),
        avg_duration_seconds=("duration_seconds", "mean"),
    )


def plot(summary: pd.DataFrame, out_path: Path) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(9, 4))

    (summary["pass_rate"] * 100).plot(kind="bar", ax=axes[0], color=VGV_BLUE)
    axes[0].set_ylabel("Pass rate (%)")
    axes[0].set_ylim(0, 100)
    axes[0].set_title("Pass rate by model")
    axes[0].tick_params(axis="x", rotation=20)

    summary["avg_duration_seconds"].plot(kind="bar", ax=axes[1], color=VGV_NAVY)
    axes[1].set_ylabel("Avg duration (s)")
    axes[1].set_title("Latency by model")
    axes[1].tick_params(axis="x", rotation=20)

    fig.tight_layout()
    fig.savefig(out_path, dpi=150)
    plt.close(fig)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--models", nargs="+", default=DEFAULT_MODELS, help="Models to compare")
    parser.add_argument(
        "--csv", type=Path, default=EVALS_DIR / "model_comparison.csv", help="Where to write per-case results"
    )
    parser.add_argument(
        "--plot", type=Path, default=EVALS_DIR / "model_comparison.png", help="Where to write the comparison chart"
    )
    args = parser.parse_args()

    print("=" * 60)
    print(f"Comparing models: {', '.join(args.models)}")
    print("=" * 60)

    csv_path = args.csv
    csv_path.parent.mkdir(parents=True, exist_ok=True)

    df = compare(args.models, csv_path.parent)
    df.to_csv(csv_path, index=False)
    print(f"\nWrote {csv_path}")

    summary = summarize(df)
    print("\n" + summary.to_string())

    plot_path = args.plot
    plot(summary, plot_path)
    print(f"Wrote {plot_path}")

    report.main(
        json_path=csv_path.parent / "results.json",
        out_path=csv_path.parent / "report.pdf",
        comparison_csv=csv_path,
        comparison_plot=plot_path,
    )
