from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.figure import Figure


METRICS = (
    ("weighted_task_coverage_pct", "Weighted task coverage", "o"),
    ("technique_coverage_pct", "Technique coverage", "s"),
    ("hybrid_coverage_pct", "Hybrid coverage", "^"),
    ("task_coverage_pct", "Task coverage", "D"),
)


def create_coverage_figure(
    curve: pd.DataFrame,
    reference_points: dict[str, dict | None],
    *,
    title: str,
    selected_budget: float | None = None,
    currency: str = "$",
    budget_label: str = "Additional workforce budget",
) -> Figure:
    """
    Render the paper-style budget-versus-coverage chart.

    All coverage values and analytical reference points are expected to have
    been calculated by threat_budget_coverage.py. This module only renders them.
    """
    required = {
        "budget",
        "task_coverage_pct",
        "weighted_task_coverage_pct",
        "technique_coverage_pct",
        "hybrid_coverage_pct",
    }
    missing = required - set(curve.columns)
    if missing:
        raise ValueError(
            f"Coverage curve is missing columns: {sorted(missing)}"
        )

    data = curve.sort_values("budget").copy()
    x = data["budget"].to_numpy(dtype=float) / 1_000_000

    fig, ax = plt.subplots(figsize=(10.5, 6.0))

    for column, label, marker in METRICS:
        ax.plot(
            x,
            data[column].to_numpy(dtype=float),
            marker=marker,
            markersize=4,
            linewidth=2.2,
            label=label,
        )

    technique_full = reference_points.get("technique_full")
    if technique_full is not None:
        budget_m = technique_full["budget"] / 1_000_000
        coverage = technique_full["coverage"]

        ax.axvline(
            budget_m,
            linestyle="--",
            linewidth=1,
            alpha=0.7,
        )
        ax.scatter([budget_m], [coverage], s=55, zorder=5)
        ax.annotate(
            f"100% techniques\n{currency}{budget_m:.2f}M",
            xy=(budget_m, coverage),
            xytext=(budget_m + 0.12, 84.0),
            arrowprops={
                "arrowstyle": "->",
                "connectionstyle": "arc3,rad=0.08",
            },
            fontsize=9,
        )

    saturation = reference_points.get("saturation")
    if saturation is not None:
        budget_m = saturation["budget"] / 1_000_000
        coverage = saturation["coverage"]

        ax.axvline(
            budget_m,
            linestyle="--",
            linewidth=1,
            alpha=0.7,
        )
        ax.scatter([budget_m], [coverage], s=55, zorder=5)
        ax.annotate(
            (
                "Diminishing-returns point\n"
                f"{currency}{budget_m:.2f}M, {coverage:.1f}%"
            ),
            xy=(budget_m, coverage),
            xytext=(
                max(0.05, budget_m + 0.12),
                max(8.0, coverage - 18.0),
            ),
            arrowprops={
                "arrowstyle": "->",
                "connectionstyle": "arc3,rad=0.08",
            },
            fontsize=9,
        )

    hybrid_full = reference_points.get("hybrid_full")
    if hybrid_full is not None:
        budget_m = hybrid_full["budget"] / 1_000_000
        coverage = hybrid_full["coverage"]

        ax.axvline(
            budget_m,
            linestyle="--",
            linewidth=1,
            alpha=0.7,
        )
        ax.scatter([budget_m], [coverage], s=55, zorder=5)
        ax.annotate(
            f"100% Hybrid Coverage\n{currency}{budget_m:.2f}M",
            xy=(budget_m, coverage),
            xytext=(max(0.05, budget_m - 0.9), 80.0),
            arrowprops={
                "arrowstyle": "->",
                "connectionstyle": "arc3,rad=0.08",
            },
            fontsize=9,
        )

    if selected_budget is not None:
        selected_budget_m = selected_budget / 1_000_000
        ax.axvline(
            selected_budget_m,
            linestyle="-.",
            linewidth=1.4,
            alpha=0.8,
            label="Selected budget",
        )

    maximum_budget = float(data["budget"].max()) / 1_000_000

    ax.set_title(title)
    ax.set_xlabel(f"{budget_label} ({currency} million)")
    ax.set_ylabel("Coverage (%)")
    ax.set_xlim(0, maximum_budget + 0.05)
    ax.set_ylim(0, 104)
    ax.set_xticks(np.arange(0, maximum_budget + 0.5, 0.5))
    ax.set_yticks(np.arange(0, 101, 10))
    ax.grid(axis="y", linewidth=0.7, alpha=0.3)
    ax.legend(loc="lower right", frameon=True)

    fig.tight_layout()
    return fig
