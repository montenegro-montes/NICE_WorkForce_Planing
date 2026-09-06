from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import pandas as pd
import streamlit as st

from configuration import get_scenario_model_path

# ---------------------------------------------------------------------
# Domain layer: single source of truth for optimization and coverage
# ---------------------------------------------------------------------

from threat_budget_coverage import ( 
    Algorithm,
    CoverageMode,
    ProblemData,
    budget_curve,
    budget_reference_points,
    kneedle_saturation_point,
    minimum_cost_for_target,
    optimize_greedy,
    optimize_milp,
    prepare_problem,
)

from coverage_charts import create_coverage_figure 


# ---------------------------------------------------------------------
# Research configuration
# ---------------------------------------------------------------------

# Production view: ATTACK-BERT is the single embedding model used.
MODELS_TO_COMPARE = {
    "ATTACK-BERT": "ATTACK_BERT",
}

MAPPING_CONTEXT_OPTIONS = {
    "Technique only": "A",
    "Technique + tactic": "B",
    "Technique + tactic + mitigation": "C",
}

COVERAGE_MODE_OPTIONS = {
    "Hybrid Coverage": "hybrid",
    "Technique Coverage": "techniques",
    "Weighted Task Coverage": "weighted_tasks",
    "Task Coverage": "tasks",
}

ALGORITHM_OPTIONS = {
    "Greedy": "greedy",
    "MILP": "milp",
}

COST_SCENARIO_OPTIONS = {
    "Average": "avg",
    "Minimum": "min",
    "Maximum": "max",
}

TASK_ALPHA_DEFAULT = 0.70


def parse_budget_value(value: Any, default: float = 1_500_000) -> float:
    """Normalize numeric and previously formatted Streamlit budget values."""
    if value is None:
        return float(default)
    if isinstance(value, str):
        value = value.replace("$", "").replace(",", "").strip()
    try:
        return float(value)
    except (TypeError, ValueError):
        return float(default)

# Same budget grid used in the paper, plus the selected UI budget when needed.
PAPER_CURVE_BUDGETS = [
    100_000,
    200_000,
    300_000,
    400_000,
    500_000,
    600_000,
    700_000,
    800_000,
    900_000,
    1_000_000,
    1_250_000,
    1_500_000,
    1_750_000,
    2_000_000,
    2_250_000,
    2_500_000,
    2_750_000,
    3_000_000,
    3_250_000,
    3_500_000,
    3_750_000,
    4_000_000,
    4_250_000,
    4_500_000,
    4_750_000,
    5_000_000,
]


# ---------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def load_threat_data(
    scenario_tasks_path: str,
    role_details_path: str,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Load the two inputs consumed by prepare_problem().

    No coverage, ranking, recommendation, or optimization logic is
    implemented in the Streamlit layer.
    """
    scenario_tasks = pd.read_csv(
        scenario_tasks_path,
        low_memory=False,
    )
    task_role_details = pd.read_csv(
        role_details_path,
        low_memory=False,
    )

    if "role_id" not in task_role_details.columns:
        if "work_role" not in task_role_details.columns:
            raise ValueError(
                "The task-role details file must contain "
                "'role_id' or 'work_role'."
            )

        task_role_details = task_role_details.rename(
            columns={"work_role": "role_id"}
        )

    required_scenario_columns = {
        "scenario_id",
        "scenario_name",
        "attack_id",
        "task_id",
    }
    missing = required_scenario_columns - set(scenario_tasks.columns)
    if missing:
        raise ValueError(
            "Scenario task data is missing columns: "
            f"{sorted(missing)}"
        )

    required_role_columns = {"task_id", "role_id"}
    missing = required_role_columns - set(task_role_details.columns)
    if missing:
        raise ValueError(
            "Task-role data is missing columns: "
            f"{sorted(missing)}"
        )

    return scenario_tasks, task_role_details


def resolve_data_paths(
    year: int,
    variant: str,
    model: str,
) -> tuple[Path, Path]:
    """Resolve scenario-task and detailed Task-to-Work-Role files."""
    scenario_model_path, roles_model_path = get_scenario_model_path(
        year,
        variant,
        model,
    )

    scenario_model_path = Path(scenario_model_path)
    roles_model_path = Path(roles_model_path)

    role_details_path = roles_model_path.with_name(
        f"{roles_model_path.stem}_details{roles_model_path.suffix}"
    )

    return scenario_model_path, role_details_path


def load_all_model_inputs(
    year: int,
    variant: str,
) -> dict[str, dict[str, Any]]:
    """Load the ATTACK-BERT mapping used by the workforce study."""
    inputs: dict[str, dict[str, Any]] = {}

    for model_label, model_id in MODELS_TO_COMPARE.items():
        scenario_path, role_path = resolve_data_paths(
            year,
            variant,
            model_id,
        )

        scenario_tasks, task_role_details = load_threat_data(
            str(scenario_path),
            str(role_path),
        )

        inputs[model_label] = {
            "model_id": model_id,
            "scenario_path": scenario_path,
            "role_path": role_path,
            "scenario_tasks": scenario_tasks,
            "task_role_details": task_role_details,
        }

    return inputs


def common_scenarios(
    model_inputs: dict[str, dict[str, Any]],
) -> list[str]:
    """Return scenario names available in every embedding-model dataset."""
    scenario_sets: list[set[str]] = []

    for model_data in model_inputs.values():
        names = {
            str(value)
            for value in model_data["scenario_tasks"]["scenario_name"]
            .dropna()
            .unique()
        }
        scenario_sets.append(names)

    if not scenario_sets:
        return []

    common = set.intersection(*scenario_sets)
    return sorted(common)


def role_costs_dataframe(cost_model) -> pd.DataFrame:
    """Adapt the application's CostModel to prepare_problem()."""
    rows: list[dict[str, Any]] = []

    for role_id, role in cost_model.roles.items():
        rows.append({
            "role_id": role_id,
            "role_name": getattr(role, "role_name", role_id),
            "category": getattr(
                role,
                "category",
                role_id.split("-")[0],
            ),
            "mapped_job": getattr(role, "mapped_job", ""),
            "salary_model": getattr(role, "salary_model", ""),
            "confidence": getattr(role, "confidence", ""),
            "cost_min": cost_model.cost(role_id, "MINIMUM"),
            "cost_avg": cost_model.cost(role_id, "AVERAGE"),
            "cost_max": cost_model.cost(role_id, "MAXIMUM"),
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------
# Thin UI adapters around threat_budget_coverage.py
# ---------------------------------------------------------------------

def run_optimizer(
    problem: ProblemData,
    *,
    budget: float,
    algorithm: Algorithm,
    coverage_mode: CoverageMode,
    current_roles,
    task_alpha: float,
):
    """Dispatch to the selected optimizer; no local optimization logic."""
    if algorithm == "milp":
        return optimize_milp(
            problem=problem,
            budget=budget,
            coverage_mode=coverage_mode,
            current_roles=current_roles,
            task_alpha=task_alpha,
        )

    return optimize_greedy(
        problem=problem,
        budget=budget,
        coverage_mode=coverage_mode,
        current_roles=current_roles,
        task_alpha=task_alpha,
    )


def build_curve_budgets() -> list[float]:
    """Return the fixed budget grid shared by both embedding charts."""
    return [float(budget) for budget in PAPER_CURVE_BUDGETS]


def fmt_money(value: float | None) -> str:
    if value is None:
        return "Not reached"
    if isinstance(value, float) and math.isnan(value):
        return "Not reachable"
    return f"${value:,.0f}"


def fmt_budget_million(value: float | None) -> str:
    if value is None:
        return "Not reached"
    if isinstance(value, float) and math.isnan(value):
        return "Not reachable"
    return f"${value / 1_000_000:.2f}M"


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "—"
    if isinstance(value, float) and math.isnan(value):
        return "—"
    return f"{value:.1f}%"


def fmt_pp(value: float) -> str:
    return f"{value:+.1f} pp"


def calculate_rowi(baseline, result) -> float:
    """Return objective coverage gain in percentage points per $100K spent."""
    if result.spent_budget <= 0:
        return 0.0
    capability_gain = (
        result.objective_coverage_pct
        - baseline.objective_coverage_pct
    )
    return capability_gain / result.spent_budget * 100_000


def objective_label(coverage_mode: str) -> str:
    labels = {
        "hybrid": "Hybrid Coverage",
        "techniques": "Technique Coverage",
        "weighted_tasks": "Weighted Task Coverage",
        "tasks": "Task Coverage",
    }
    return labels[coverage_mode]


# ---------------------------------------------------------------------
# Research controls
# ---------------------------------------------------------------------

def configuration_menu() -> dict[str, Any]:
    """
    Experimental controls shared by both embedding models.

    ATTACK-BERT is fixed as the embedding model for this study view.
    """
    c1, c2, c3 = st.columns(
        [1.35, 0.75, 1.65],
        vertical_alignment="bottom",
    )

    scenario_slot = c1.empty()

    year = c2.selectbox(
        "ENISA edition",
        [2024, 2025],
    )

    mapping_label = c3.selectbox(
        "ATT&CK-to-NICE context",
        list(MAPPING_CONTEXT_OPTIONS),
        index=2,
    )
    variant = MAPPING_CONTEXT_OPTIONS[mapping_label]

    st.session_state.setdefault("threat_algorithm", "Greedy")
    st.session_state.setdefault("threat_cost_scenario", "Average")
    st.session_state.setdefault("threat_coverage_label", "Hybrid Coverage")
    st.session_state.setdefault("threat_task_alpha", TASK_ALPHA_DEFAULT)
    st.session_state.setdefault("threat_exact_target_cost", False)

    algorithm_label = st.session_state.threat_algorithm
    cost_label = st.session_state.threat_cost_scenario
    coverage_label = st.session_state.threat_coverage_label
    task_alpha = float(st.session_state.threat_task_alpha)
    exact_target_cost = bool(st.session_state.threat_exact_target_cost)
    algorithm = ALGORITHM_OPTIONS[algorithm_label]
    cost_scenario = COST_SCENARIO_OPTIONS[cost_label]
    coverage_mode = COVERAGE_MODE_OPTIONS[coverage_label]

    return {
        "scenario_slot": scenario_slot,
        "year": year,
        "variant": variant,
        "mapping_label": mapping_label,
        "coverage_mode": coverage_mode,
        "coverage_label": coverage_label,
        "algorithm": algorithm,
        "algorithm_label": algorithm_label,
        "budget": parse_budget_value(
            st.session_state.get("threat_budget"),
            1_500_000,
        ),
        "cost_scenario": cost_scenario,
        "cost_label": cost_label,
        "task_alpha": float(task_alpha),
        "exact_target_cost": bool(exact_target_cost),
    }


# ---------------------------------------------------------------------
# Model analysis
# ---------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def analyze_embedding_model(
    *,
    model_label: str,
    model_data: dict[str, Any],
    config: dict[str, Any],
    selected_scenario: str,
    role_costs: pd.DataFrame,
    current_roles,
) -> dict[str, Any]:
    """Run the complete threat-workforce analysis for one embedding model."""
    scenario_tasks: pd.DataFrame = model_data["scenario_tasks"]
    task_role_details: pd.DataFrame = model_data["task_role_details"]

    scenario_rows = scenario_tasks[
        scenario_tasks["scenario_name"] == selected_scenario
    ].copy()

    if scenario_rows.empty:
        raise ValueError(
            f"Scenario '{selected_scenario}' is not available for {model_label}."
        )

    scenario_id = str(scenario_rows["scenario_id"].iloc[0])
    problem = prepare_problem(
        scenario_tasks=scenario_tasks,
        task_role=task_role_details,
        role_costs=role_costs,
        scenario_id=scenario_id,
        cost_scenario=config["cost_scenario"],
    )
    current_role_ids = sorted({
        str(role_id).strip()
        for role_id in (current_roles or [])
        if str(role_id).strip()
    })
    current_workforce_cost = sum(
        float(problem["role_cost"].get(role_id, 0.0))
        for role_id in current_role_ids
    )

    # Baseline = current workforce without additional investment.
    baseline = optimize_greedy(
        problem=problem,
        budget=0.0,
        coverage_mode=config["coverage_mode"],
        current_roles=current_roles,
        task_alpha=config["task_alpha"],
    )

    available_budgets = sorted({
        current_workforce_cost,
        *(
            float(budget)
            for budget in build_curve_budgets()
            if float(budget) >= current_workforce_cost
        ),
    })
    additional_budgets = [
        max(0.0, budget - current_workforce_cost)
        for budget in available_budgets
    ]
    curve = budget_curve(
        problem=problem,
        budgets=additional_budgets,
        algorithm=config["algorithm"],
        coverage_mode=config["coverage_mode"],
        current_roles=current_roles,
        task_alpha=config["task_alpha"],
    )
    curve["additional_budget"] = curve["budget"]
    curve["additional_budget_million"] = curve["budget_million"]
    curve["available_annual_budget"] = (
        curve["additional_budget"] + current_workforce_cost
    )
    curve["budget"] = curve["available_annual_budget"]
    curve["budget_million"] = curve["budget"] / 1_000_000
    curve["total_workforce_cost"] = (
        curve["spent_budget"] + current_workforce_cost
    )

    reference_points = budget_reference_points(
        curve,
        sensitivity=1.0,
    )
    decision_reference_points = {
        "saturation": kneedle_saturation_point(
            curve,
            "objective_coverage_pct",
            sensitivity=1.0,
        ),
    }

    figure = create_coverage_figure(
        curve,
        reference_points,
        title="",
        currency="$",
        budget_label="Available annual budget",
    )

    return {
        "label": model_label,
        "model_id": model_data["model_id"],
        "scenario_tasks": scenario_tasks,
        "scenario_rows": scenario_rows,
        "scenario_id": scenario_id,
        "problem": problem,
        "baseline": baseline,
        "curve": curve,
        "reference_points": reference_points,
        "decision_reference_points": decision_reference_points,
        "coverage_label": config["coverage_label"],
        "current_role_ids": current_role_ids,
        "current_workforce_cost": current_workforce_cost,
        "figure": figure,
    }


# ---------------------------------------------------------------------
# Comparison helpers
# ---------------------------------------------------------------------

def selected_role_ids(analysis: dict[str, Any]) -> set[str]:
    return {
        str(role["role_id"])
        for role in analysis["result"].selected_roles
    }


def workforce_agreement(
    analyses: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    mini_roles = selected_role_ids(analyses["MiniLM"])
    attack_roles = selected_role_ids(analyses["ATTACK-BERT"])

    common = mini_roles & attack_roles
    union = mini_roles | attack_roles

    jaccard = len(common) / len(union) if union else 1.0

    return {
        "jaccard": jaccard,
        "common": common,
        "minilm_only": mini_roles - attack_roles,
        "attackbert_only": attack_roles - mini_roles,
    }


def comparison_table(
    analyses: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    """Compare both embedding models at the selected budget."""
    mini = analyses["MiniLM"]["result"]
    attack = analyses["ATTACK-BERT"]["result"]
    mini_rowi = calculate_rowi(analyses["MiniLM"]["baseline"], mini)
    attack_rowi = calculate_rowi(
        analyses["ATTACK-BERT"]["baseline"],
        attack,
    )

    rows = [
        (
            "Task Coverage",
            mini.final_task_coverage_pct,
            attack.final_task_coverage_pct,
            "pct",
        ),
        (
            "Weighted Task Coverage",
            mini.final_weighted_task_coverage_pct,
            attack.final_weighted_task_coverage_pct,
            "pct",
        ),
        (
            "Technique Coverage",
            mini.final_technique_coverage_pct,
            attack.final_technique_coverage_pct,
            "pct",
        ),
        (
            "Hybrid Coverage",
            mini.final_hybrid_coverage_pct,
            attack.final_hybrid_coverage_pct,
            "pct",
        ),
        (
            "Objective Coverage",
            mini.objective_coverage_pct,
            attack.objective_coverage_pct,
            "pct",
        ),
        (
            "Return on Workforce Investment (ROWI)",
            mini_rowi,
            attack_rowi,
            "rowi",
        ),
        (
            "Selected Work Roles",
            float(len(mini.selected_roles)),
            float(len(attack.selected_roles)),
            "count",
        ),
        (
            "Budget Spent",
            mini.spent_budget,
            attack.spent_budget,
            "money",
        ),
        (
            "Runtime",
            mini.runtime_seconds,
            attack.runtime_seconds,
            "seconds",
        ),
    ]

    table_rows: list[dict[str, str]] = []

    for metric, mini_value, attack_value, kind in rows:
        difference = mini_value - attack_value

        if kind == "pct":
            mini_text = f"{mini_value:.2f}%"
            attack_text = f"{attack_value:.2f}%"
            diff_text = f"{difference:+.2f} pp"
        elif kind == "money":
            mini_text = fmt_money(mini_value)
            attack_text = fmt_money(attack_value)
            diff_text = f"${difference:+,.0f}"
        elif kind == "seconds":
            mini_text = f"{mini_value:.3f} s"
            attack_text = f"{attack_value:.3f} s"
            diff_text = f"{difference:+.3f} s"
        elif kind == "rowi":
            mini_text = f"{mini_value:.2f} pp/$100K"
            attack_text = f"{attack_value:.2f} pp/$100K"
            diff_text = f"{difference:+.2f} pp/$100K"
        else:
            mini_text = f"{int(mini_value)}"
            attack_text = f"{int(attack_value)}"
            diff_text = f"{int(difference):+d}"

        table_rows.append({
            "Metric": metric,
            "MiniLM": mini_text,
            "ATTACK-BERT": attack_text,
            "Δ MiniLM − ATTACK-BERT": diff_text,
        })

    return pd.DataFrame(table_rows)


def reference_comparison_table(
    analyses: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    """Compare investment reference points derived from both curves."""
    rows: list[dict[str, str]] = []

    for metric_key, label in [
        ("technique_full", "100% Technique Coverage"),
        ("saturation", "Saturation Budget"),
        ("hybrid_full", "100% Hybrid Coverage"),
    ]:
        values: dict[str, float | None] = {}

        for model_label in MODELS_TO_COMPARE:
            point = analyses[model_label]["reference_points"].get(metric_key)
            values[model_label] = (
                float(point["budget"])
                if point is not None
                else None
            )

        mini_value = values["MiniLM"]
        attack_value = values["ATTACK-BERT"]

        if mini_value is not None and attack_value is not None:
            difference = fmt_budget_million(mini_value - attack_value)
            if mini_value - attack_value >= 0:
                difference = "+" + difference
        else:
            difference = "—"

        rows.append({
            "Reference point": label,
            "MiniLM": fmt_budget_million(mini_value),
            "ATTACK-BERT": fmt_budget_million(attack_value),
            "Δ MiniLM − ATTACK-BERT": difference,
        })

    mini_sat = analyses["MiniLM"]["reference_points"].get("saturation")
    attack_sat = analyses["ATTACK-BERT"]["reference_points"].get("saturation")

    mini_cov = float(mini_sat["coverage"]) if mini_sat else None
    attack_cov = float(attack_sat["coverage"]) if attack_sat else None

    diff_cov = (
        f"{mini_cov - attack_cov:+.2f} pp"
        if mini_cov is not None and attack_cov is not None
        else "—"
    )

    rows.append({
        "Reference point": "Hybrid Coverage at Saturation",
        "MiniLM": fmt_pct(mini_cov),
        "ATTACK-BERT": fmt_pct(attack_cov),
        "Δ MiniLM − ATTACK-BERT": diff_cov,
    })

    return pd.DataFrame(rows)


def role_comparison_table(
    analyses: dict[str, dict[str, Any]],
) -> pd.DataFrame:
    """Show which selected Work Roles are shared or model-specific."""
    records: dict[str, dict[str, Any]] = {}

    for model_label in MODELS_TO_COMPARE:
        roles = analyses[model_label]["result"].selected_roles

        for role in roles:
            role_id = str(role["role_id"])
            record = records.setdefault(
                role_id,
                {
                    "role_id": role_id,
                    "role_name": role.get("role_name", ""),
                    "category": role.get("category", ""),
                    "MiniLM rank": None,
                    "ATTACK-BERT rank": None,
                    "MiniLM gain": None,
                    "ATTACK-BERT gain": None,
                },
            )

            record[f"{model_label} rank"] = role.get("selection_order")
            record[f"{model_label} gain"] = role.get(
                "marginal_coverage_gain_pct"
            )

    if not records:
        return pd.DataFrame()

    table = pd.DataFrame(records.values())

    table["Selected by"] = table.apply(
        lambda row: (
            "Both"
            if pd.notna(row["MiniLM rank"])
            and pd.notna(row["ATTACK-BERT rank"])
            else (
                "MiniLM only"
                if pd.notna(row["MiniLM rank"])
                else "ATTACK-BERT only"
            )
        ),
        axis=1,
    )

    sort_group = {
        "Both": 0,
        "MiniLM only": 1,
        "ATTACK-BERT only": 2,
    }
    table["_sort"] = table["Selected by"].map(sort_group)

    return (
        table.sort_values(
            ["_sort", "role_id"],
            ascending=[True, True],
        )
        .drop(columns="_sort")
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------
# Gap and data-quality tables
# ---------------------------------------------------------------------

def task_gap_table(
    scenario_tasks: pd.DataFrame,
    problem: ProblemData,
    uncovered_tasks: set[str],
) -> pd.DataFrame:
    """Build a display table for gaps identified by OptimizationResult."""
    if not uncovered_tasks:
        return pd.DataFrame()

    subset = scenario_tasks[
        scenario_tasks["task_id"].isin(uncovered_tasks)
    ].copy()

    if subset.empty:
        return pd.DataFrame({
            "task_id": sorted(uncovered_tasks),
            "task_weight": [
                problem["task_weights"].get(task_id, 0.0)
                for task_id in sorted(uncovered_tasks)
            ],
        })

    aggregations: dict[str, tuple[str, str]] = {
        "techniques": ("attack_id", "nunique"),
    }

    if "task_description" in subset.columns:
        aggregations["task_description"] = (
            "task_description",
            "first",
        )

    if "similarity_score" in subset.columns:
        aggregations["best_similarity"] = (
            "similarity_score",
            "max",
        )

    table = (
        subset.groupby("task_id", as_index=False)
        .agg(**aggregations)
    )

    table["task_weight"] = table["task_id"].map(
        problem["task_weights"]
    ).fillna(0.0)

    preferred = [
        "task_id",
        "task_description",
        "techniques",
        "task_weight",
        "best_similarity",
    ]
    columns = [
        column for column in preferred if column in table.columns
    ]

    return (
        table[columns]
        .sort_values("task_weight", ascending=False)
        .reset_index(drop=True)
    )


def technique_gap_table(
    scenario_tasks: pd.DataFrame,
    uncovered_techniques: set[str],
) -> pd.DataFrame:
    """Build a display table for ATT&CK techniques left uncovered."""
    if not uncovered_techniques:
        return pd.DataFrame()

    subset = scenario_tasks[
        scenario_tasks["attack_id"].isin(uncovered_techniques)
    ].copy()

    if subset.empty:
        return pd.DataFrame({
            "attack_id": sorted(uncovered_techniques)
        })

    name_column = next(
        (
            column
            for column in [
                "technique_name",
                "attack_name",
                "attack_technique_name",
            ]
            if column in subset.columns
        ),
        None,
    )

    if name_column is None:
        return (
            subset[["attack_id"]]
            .drop_duplicates()
            .sort_values("attack_id")
            .reset_index(drop=True)
        )

    return (
        subset[["attack_id", name_column]]
        .drop_duplicates()
        .rename(columns={name_column: "technique_name"})
        .sort_values("attack_id")
        .reset_index(drop=True)
    )


# ---------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------

def render_summary_card(
    container,
    label: str,
    value: str,
    *,
    detail: str | None = None,
    value_class: str = "success",
    large_value: bool = False,
    medium_value: bool = False,
    help_text: str | None = None,
) -> None:
    detail_html = (
        f'<span class="card-sub threat-summary-detail">{detail}</span>'
        if detail is not None
        else "<span class='card-sub'>&nbsp;</span>"
    )
    size_class = (
        " threat-summary-value-large"
        if large_value
        else " threat-summary-value-medium" if medium_value else ""
    )
    help_html = (
        f'<span class="threat-summary-help" tabindex="0" '
        f'data-help="{help_text}">?</span>'
        if help_text is not None
        else ""
    )
    container.markdown(
        f"""
        <div class="summary-box threat-summary-card">
            <div class="summary-item">
                <span class="summary-label">{label} {help_html}</span>
                <div class="threat-summary-value-row">
                    <span class="summary-value {value_class}{size_class}">{value}</span>
                    {detail_html}
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_experiment_context(
    config: dict[str, Any],
    selected_scenario: str,
) -> None:
    st.markdown(f""" <div class="card-section-info">
                       Threat scenario: <strong>{selected_scenario}</strong> {config['year']} · Available annual budget: <strong>{fmt_money(config['budget'])}</strong> · Objective: <strong>{config['coverage_label']}</strong> 
                      </div>
                    """, unsafe_allow_html=True)
        
    
    #st.markdown(
     #     f"{selected_scenario} · ENISA {config['year']} · "
     #     f"{config['mapping_label']} · "
     #     f"{config['coverage_label']} · "
     #     f"{config['algorithm_label']} · "
     #     f"Additional budget {fmt_money(config['budget'])}"
     # )


def render_model_summary(
    analyses: dict[str, dict[str, Any]],
    config: dict[str, Any],
) -> None:
    attack_baseline = analyses["ATTACK-BERT"]["result_baseline"]
    attack_result = analyses["ATTACK-BERT"]["result"]
    attack_rowi = calculate_rowi(attack_baseline, attack_result)
    added_role_count = len(attack_result.selected_roles)
    total_role_count = (
        int(analyses["ATTACK-BERT"]["current_role_count"])
        + added_role_count
    )
    current_workforce_cost = float(
        analyses["ATTACK-BERT"]["current_workforce_cost"]
    )
    total_workforce_cost = current_workforce_cost + attack_result.spent_budget

    m1, m2, m3, m4, m5, m6, m7 = st.columns(7)
    render_summary_card(
        m1,
        "Selected Work Roles",
        str(total_role_count),
        detail=f"+{added_role_count} roles",
        large_value=True,
    )
    render_summary_card(
        m2,
        "Task Coverage",
        fmt_pct(attack_result.final_task_coverage_pct),
        detail=fmt_pp(
            attack_result.final_task_coverage_pct
            - attack_baseline.final_task_coverage_pct
        ),
        large_value=True,
    )
    render_summary_card(
        m3,
        "Weighted Task Coverage",
        fmt_pct(attack_result.final_weighted_task_coverage_pct),
        detail=fmt_pp(
            attack_result.final_weighted_task_coverage_pct
            - attack_baseline.final_weighted_task_coverage_pct
        ),
        large_value=True,
    )
    render_summary_card(
        m4,
        "Technique Coverage",
        fmt_pct(attack_result.final_technique_coverage_pct),
        detail=fmt_pp(
            attack_result.final_technique_coverage_pct
            - attack_baseline.final_technique_coverage_pct
        ),
        large_value=True,
    )
    render_summary_card(
        m5,
        "Hybrid Coverage",
        fmt_pct(attack_result.final_hybrid_coverage_pct),
        detail=fmt_pp(
            attack_result.final_hybrid_coverage_pct
            - attack_baseline.final_hybrid_coverage_pct
        ),
        large_value=True,
    )
    render_summary_card(
        m6,
        "ROWI",
        f"{attack_rowi:.2f}",
        detail="pp/$100K",
        large_value=True,
    )
    render_summary_card(
        m7,
        "Budget Used",
        fmt_money(total_workforce_cost),
        detail=f"+{fmt_money(attack_result.spent_budget)}",
        medium_value=True,
    )

    


def render_charts(
    analyses: dict[str, dict[str, Any]],
) -> None:
    with st.container(key="plot-container"):
        chart_column, reference_column = st.columns(
            [1.35, 1.15],
            vertical_alignment="top",
        )
        with chart_column:
            st.markdown("""
                        <div class="card-section">Coverage Curves</div>
                                        """, unsafe_allow_html=True)
            st.pyplot(
                analyses["ATTACK-BERT"]["figure"],
                width="stretch",
            )

        with reference_column:
            render_reference_comparison(analyses)


def render_reference_comparison(
    analyses: dict[str, dict[str, Any]],
) -> None:

    st.markdown(""" <div class="card-section" style="margin-bottom: 0.5rem;">
                                   Investment decision panel
                                </div>
                            """, unsafe_allow_html=True)

    analysis = analyses["ATTACK-BERT"]
    points = analysis["decision_reference_points"]
    coverage_label = str(analysis["coverage_label"])
    curve = analysis["curve"].sort_values("budget").reset_index(drop=True)
    saturation = points.get("saturation")

    baseline_coverage = float(
        analysis["baseline"].objective_coverage_pct
    )
    saturation_budget: float | None = None
    saturation_coverage: float | None = None
    coverage_gain_at_saturation: float | None = None
    additional_cost_at_saturation: float | None = None
    current_role_ids = list(analysis["current_role_ids"])
    problem = analysis["problem"]
    current_workforce_cost = sum(
        float(problem["role_cost"].get(role_id, 0.0))
        for role_id in current_role_ids
    )
    total_workforce_cost: float | None = None
    roles_at_saturation = "—"
    marginal_rowi = "—"
    selected_role_ids_at_saturation: list[str] = []

    if saturation is not None:
        saturation_budget = float(saturation["budget"])
        saturation_coverage = float(saturation["coverage"])
        coverage_gain_at_saturation = (
            saturation_coverage - baseline_coverage
        )
        nearest_index = int(
            (curve["budget"] - saturation_budget).abs().idxmin()
        )
        saturation_row = curve.loc[nearest_index]
        additional_cost_at_saturation = float(
            saturation_row["spent_budget"]
        )
        total_workforce_cost = (
            current_workforce_cost + additional_cost_at_saturation
        )
        added_role_count = int(saturation_row["selected_roles"])
        roles_at_saturation = str(len(current_role_ids) + added_role_count)
        selected_role_ids_at_saturation = [
            role_id
            for role_id in str(
                saturation_row.get("selected_role_ids_ordered", "")
            ).split(";")
            if role_id
        ]
        marginal_value = saturation_row.get("marginal_gain_per_100k")
        if pd.notna(marginal_value):
            marginal_rowi = f"{float(marginal_value):.2f} pp/$100K"

    p1, p2 = st.columns(2)
    render_summary_card(
        p1,
        "Workforce cost at diminishing returns",
        fmt_money(total_workforce_cost),
        detail=(
            f"+{fmt_money(additional_cost_at_saturation)}"
            if additional_cost_at_saturation is not None
            else None
        ),
        large_value=True,
    )
    render_summary_card(
        p2,
        "Diminishing-returns budget",
        fmt_budget_million(saturation_budget),
        large_value=True,
    )

    p3, p4 = st.columns(2)
    render_summary_card(
        p3,
        "Coverage at diminishing returns",
        fmt_pct(saturation_coverage),
        large_value=True,
    )
    render_summary_card(
        p4,
        "Coverage gain at diminishing returns",
        (
            fmt_pp(coverage_gain_at_saturation)
            if coverage_gain_at_saturation is not None
            else "Not detected"
        ),
        large_value=True,
    )

    p5, p6 = st.columns(2)
    render_summary_card(
        p5,
        "Roles at diminishing returns",
        roles_at_saturation,
        detail=(
            f"+{len(selected_role_ids_at_saturation)} roles"
            if saturation is not None
            else None
        ),
        large_value=True,
    )
    render_summary_card(
        p6,
        "Marginal ROWI",
        marginal_rowi,
        large_value=True,
    )

    #if saturation_budget is not None:
    #    st.info(
    #        f"Investment beyond {fmt_money(saturation_budget)} is expected "
    #        f"to provide progressively smaller {coverage_label.lower()} "
    #        "gains."
   #     )
   # else:
    #    st.info(
    #        "No clear saturation point was detected in the evaluated "
    #        "budget range; review the full curve before setting a target."
    #    )

    st.markdown(
        '<div style="margin-top: 0.35rem; margin-bottom: 0.45rem;"><strong>'
        'Workforce composition at diminishing returns</strong></div>',
        unsafe_allow_html=True,
    )
    if current_role_ids or selected_role_ids_at_saturation:
        role_rows = []

        for role_id in current_role_ids:
            metadata = problem["metadata"].get(role_id, {})
            role_rows.append({
                "Status": "Current",
                "Priority": "—",
                "Work Role": role_id,
                "Name": metadata.get("role_name", ""),
                "Category": metadata.get("category", ""),
                "Mapped Job": metadata.get("mapped_job", ""),
                "Annual Cost": problem["role_cost"].get(role_id),
            })

        for priority, role_id in enumerate(
            selected_role_ids_at_saturation,
            start=1,
        ):
            metadata = problem["metadata"].get(role_id, {})
            role_rows.append({
                "Status": "Additional",
                "Priority": str(priority),
                "Work Role": role_id,
                "Name": metadata.get("role_name", ""),
                "Category": metadata.get("category", ""),
                "Mapped Job": metadata.get("mapped_job", ""),
                "Annual Cost": float(problem["role_cost"].get(role_id, 0.0)),
            })

        st.dataframe(
            pd.DataFrame(role_rows),
            width="stretch",
            height=275,
            hide_index=True,
            column_config={
                "Status": "Status",
                "Priority": "Priority",
                "Work Role": "Work Role",
                "Name": "Role Name",
                "Category": "Category",
                "Mapped Job": "Mapped Job",
                "Annual Cost": st.column_config.NumberColumn(
                    "Annual Cost",
                    format="$%.0f",
                ),
            },
        )
    elif saturation is None:
        st.caption("No diminishing-returns workforce is available.")
    else:
        st.caption("No Work Roles are present at diminishing returns.")



def render_budget_execution_controls(
    analyses: dict[str, dict[str, Any]],
    config: dict[str, Any],
    selected_scenario: str,
    current_roles,
) -> bool:
    """Render the budget action and retain only matching executed results."""
    with st.container(key="optimization-execution-card"):
        st.markdown("""
                            <div class="card-section">Run workforce optimization</div>
                                            """, unsafe_allow_html=True)        
                
        budget_column, button_column = st.columns(
            [1.2, 1],
            vertical_alignment="bottom",
        )
        current_workforce_cost = float(
            analyses["ATTACK-BERT"]["current_workforce_cost"]
        )
        minimum_budget = max(
            100_000,
            int(math.ceil(current_workforce_cost / 100_000) * 100_000),
        )
        maximum_budget = max(5_000_000, minimum_budget)
        budget_options = list(range(
            minimum_budget,
            maximum_budget + 1,
            100_000,
        ))
        current_budget = int(parse_budget_value(
            st.session_state.get("threat_budget"),
            max(1_500_000, minimum_budget),
        ))
        if current_budget not in budget_options:
            current_budget = min(
                budget_options,
                key=lambda value: abs(value - current_budget),
            )
        st.session_state.threat_budget = current_budget
        budget = budget_column.selectbox(
            "Available annual budget",
            options=budget_options,
            format_func=lambda value: f"${value:,.0f}",
            key="threat_budget",
        )
        config["budget"] = float(budget)

        with st.expander("Advanced optimization settings"):
            a1, a2, a3, a4, a5 = st.columns([0.9, 1, 1.25, 1.2, 1.3])

            algorithm_label = a1.selectbox(
                "Algorithm",
                list(ALGORITHM_OPTIONS),
                key="threat_algorithm",
            )
            cost_label = a2.selectbox(
                "Salary cost scenario",
                list(COST_SCENARIO_OPTIONS),
                key="threat_cost_scenario",
            )
            coverage_label = a3.selectbox(
                "Optimization objective",
                list(COVERAGE_MODE_OPTIONS),
                key="threat_coverage_label",
            )
            task_alpha = a4.slider(
                "Hybrid weight for Weighted Task Coverage (α)",
                min_value=0.0,
                max_value=1.0,
                step=0.05,
                disabled=COVERAGE_MODE_OPTIONS[coverage_label] != "hybrid",
                help=(
                    "Hybrid Coverage = α × Weighted Task Coverage "
                    "+ (1 − α) × Technique Coverage."
                ),
                key="threat_task_alpha",
            )
            exact_target_cost = a5.checkbox(
                "Compute exact 100% target cost",
                help=(
                    "Runs the MILP minimum-cost formulation for each embedding "
                    "model. This is more computationally expensive."
                ),
                key="threat_exact_target_cost",
            )

        config["algorithm_label"] = algorithm_label
        config["algorithm"] = ALGORITHM_OPTIONS[algorithm_label]
        config["cost_label"] = cost_label
        config["cost_scenario"] = COST_SCENARIO_OPTIONS[cost_label]
        config["coverage_label"] = coverage_label
        config["coverage_mode"] = COVERAGE_MODE_OPTIONS[coverage_label]
        config["task_alpha"] = float(task_alpha)
        config["exact_target_cost"] = bool(exact_target_cost)

        signature = (
            selected_scenario,
            config["year"],
            config["variant"],
            config["coverage_mode"],
            config["algorithm"],
            config["cost_scenario"],
            config["task_alpha"],
            config["exact_target_cost"],
            float(budget),
            tuple(sorted(current_roles)),
        )

        if button_column.button(
            "Run optimization",
            type="primary",
            use_container_width=True,
        ):
            st.session_state.threat_execution_signature = signature

    return st.session_state.get("threat_execution_signature") == signature


def execute_budget_optimization(
    analyses: dict[str, dict[str, Any]],
    config: dict[str, Any],
    current_roles,
) -> None:
    """Attach selected-budget optimization results to both model analyses."""
    for analysis in analyses.values():
        current_workforce_cost = float(analysis["current_workforce_cost"])
        available_annual_budget = float(config["budget"])
        additional_budget = max(
            0.0,
            available_annual_budget - current_workforce_cost,
        )
        analysis["available_annual_budget"] = available_annual_budget
        analysis["additional_budget"] = additional_budget
        analysis["current_role_count"] = len({
            str(role_id).strip()
            for role_id in (current_roles or [])
            if str(role_id).strip()
        })
        analysis["result_baseline"] = optimize_greedy(
            problem=analysis["problem"],
            budget=0.0,
            coverage_mode=config["coverage_mode"],
            current_roles=current_roles,
            task_alpha=config["task_alpha"],
        )
        result = run_optimizer(
            analysis["problem"],
            budget=additional_budget,
            algorithm=config["algorithm"],
            coverage_mode=config["coverage_mode"],
            current_roles=current_roles,
            task_alpha=config["task_alpha"],
        )
        analysis["result"] = result
        analysis["full_target"] = None

        if (
            config["exact_target_cost"]
            and result.max_reachable_objective_coverage_pct >= 100.0 - 1e-6
        ):
            analysis["full_target"] = minimum_cost_for_target(
                problem=analysis["problem"],
                target_pct=100.0,
                coverage_mode=config["coverage_mode"],
                current_roles=current_roles,
                task_alpha=config["task_alpha"],
            )


def render_budget_reachability(
    analyses: dict[str, dict[str, Any]],
    config: dict[str, Any],
) -> None:
    """Render target-cost and reachability facts after budget execution."""
    if config["exact_target_cost"]:
        exact_rows = []
        for model_label in MODELS_TO_COMPARE:
            analysis = analyses[model_label]
            result = analysis["result"]
            full_target = analysis["full_target"]

            if result.max_reachable_objective_coverage_pct < 100.0 - 1e-6:
                value = "Not reachable"
            elif full_target is None or full_target.get("status") != "Optimal":
                value = "Not calculated"
            else:
                value = fmt_money(
                    float(analysis["current_workforce_cost"])
                    + float(full_target["minimum_cost"])
                )

            exact_rows.append({
                "Embedding model": model_label,
                f"Exact minimum annual budget for 100% {config['coverage_label']}": value,
            })

        st.dataframe(
            pd.DataFrame(exact_rows),
            width="stretch",
            hide_index=True,
        )

    for model_label in MODELS_TO_COMPARE:
        result = analyses[model_label]["result"]
        if result.max_reachable_objective_coverage_pct < 100.0 - 1e-6:
            st.warning(
                f"{model_label}: 100% {config['coverage_label']} is not "
                "reachable with the available Task–Work Role mappings and "
                f"cost data. Maximum reachable coverage is "
                f"{result.max_reachable_objective_coverage_pct:.1f}%."
            )


def render_workforce_agreement(
    analyses: dict[str, dict[str, Any]],
) -> None:

    st.markdown(f""" <div class="card-section-info">
                       Workforce agreement between embedding models
                      </div>
                    """, unsafe_allow_html=True)
    

    agreement = workforce_agreement(analyses)
    mini_roles = selected_role_ids(analyses["MiniLM"])
    attack_roles = selected_role_ids(analyses["ATTACK-BERT"])

    c1, c2, c3, c4, c5, c6 = st.columns(6)
    render_summary_card(c1, "MiniLM Selected Roles", str(len(mini_roles)), large_value=True)
    render_summary_card(c2, "ATTACK-BERT Selected Roles", str(len(attack_roles)), large_value=True)
    render_summary_card(c3, "Common Work Roles", str(len(agreement["common"])), large_value=True)
    render_summary_card(c4, "MiniLM-only Roles", str(len(agreement["minilm_only"])), large_value=True)
    render_summary_card(
        c5,
        "ATTACK-BERT-only Roles",
        str(len(agreement["attackbert_only"])),
        large_value=True
    )
    render_summary_card(
        c6,
        "Jaccard similarity",
        f"{agreement['jaccard']:.3f}",
        large_value=True,
        help_text=(
            "Similarity between the Work Role sets selected by MiniLM and "
            "ATTACK-BERT. A value of 1 means identical sets; 0 means no "
            "selected roles in common."
        ),
    )

    table = role_comparison_table(analyses)
    if not table.empty:
        st.dataframe(
            table,
            width="stretch",
            hide_index=True,
            column_config={
                "role_id": "Work Role",
                "role_name": "Work Role Name",
                "category": "Category",
                "MiniLM rank": st.column_config.NumberColumn(
                    "MiniLM Rank",
                    format="%d",
                ),
                "ATTACK-BERT rank": st.column_config.NumberColumn(
                    "ATTACK-BERT Rank",
                    format="%d",
                ),
                "MiniLM gain": st.column_config.NumberColumn(
                    "MiniLM Marginal Gain",
                    format="%.2f pp",
                ),
                "ATTACK-BERT gain": st.column_config.NumberColumn(
                    "ATTACK-BERT Marginal Gain",
                    format="%.2f pp",
                ),
                "Selected by": "Selected by",
            },
        )


def render_selected_roles(analysis: dict[str, Any]) -> None:
    result = analysis["result"]
    current_role_ids = list(analysis["current_role_ids"])
    problem = analysis["problem"]

    if not result.selected_roles and not current_role_ids:
        st.info(
            "No current or additional Work Roles are available."
        )
        return

    role_rows: list[dict[str, Any]] = []
    for role_id in current_role_ids:
        metadata = problem["metadata"].get(role_id, {})
        role_rows.append({
            "status": "Current",
            "selection_order": pd.NA,
            "role_id": role_id,
            "role_name": metadata.get("role_name", ""),
            "category": metadata.get("category", ""),
            "mapped_job": metadata.get("mapped_job", ""),
            "annual_cost": problem["role_cost"].get(role_id),
        })

    for selected_role in result.selected_roles:
        role_rows.append({
            "status": "Additional",
            **selected_role,
        })

    roles = pd.DataFrame(role_rows)
    roles["selection_order"] = pd.to_numeric(
        roles["selection_order"],
        errors="coerce",
    ).astype("Int64")

    display_columns = [
        "status",
        "selection_order",
        "role_id",
        "role_name",
        "category",
        "mapped_job",
        "new_tasks",
        "new_techniques",
        "annual_cost",
        "marginal_coverage_gain_pct",
        "gain_per_100k",
        "cumulative_cost",
        "objective_coverage_after_pct",
    ]
    display_columns = [
        column for column in display_columns if column in roles.columns
    ]

    st.dataframe(
        roles[display_columns],
        width="stretch",
        hide_index=True,
        column_config={
            "status": "Status",
            "selection_order": st.column_config.NumberColumn(
                "Rank",
                format="%d",
            ),
            "role_id": "Work Role",
            "role_name": "Work Role Name",
            "category": "Category",
            "mapped_job": "Mapped Job",
            "new_tasks": st.column_config.NumberColumn(
                "New Tasks",
                format="%d",
            ),
            "new_techniques": st.column_config.NumberColumn(
                "New Techniques",
                format="%d",
            ),
            "annual_cost": st.column_config.NumberColumn(
                "Annual Cost",
                format="$%.0f",
            ),
            "marginal_coverage_gain_pct": st.column_config.NumberColumn(
                "Marginal Gain",
                format="%.2f pp",
            ),
            "gain_per_100k": st.column_config.NumberColumn(
                "Partial ROWI (pp/$100K)",
                format="%.2f pp",
            ),
            "cumulative_cost": st.column_config.NumberColumn(
                "Cumulative Cost",
                format="$%.0f",
            ),
            "objective_coverage_after_pct": st.column_config.NumberColumn(
                "Objective Coverage",
                format="%.2f%%",
            ),
        },
    )


def render_role_tabs(
    analyses: dict[str, dict[str, Any]],
) -> None:
    st.markdown(f""" <div class="card-section-info">
                       Selected NICE Work Roles
                      </div>
                    """, unsafe_allow_html=True)
    render_selected_roles(analyses["ATTACK-BERT"])


def render_gaps_for_model(
    analysis: dict[str, Any],
) -> None:
    result = analysis["result"]
    scenario_rows = analysis["scenario_rows"]
    problem = analysis["problem"]

    covered_tasks = task_gap_table(
        scenario_rows,
        problem,
        result.covered_tasks,
    )
    uncovered_tasks = task_gap_table(
        scenario_rows,
        problem,
        result.uncovered_tasks,
    )

    column_config = {
        "task_id": "Task ID",
        "task_description": "NICE Task",
        "techniques": st.column_config.NumberColumn(
            "ATT&CK Techniques",
            format="%d",
        ),
        "task_weight": st.column_config.NumberColumn(
            "Optimization Weight",
            format="%.3f",
        ),
        "best_similarity": st.column_config.NumberColumn(
            "Best Semantic Score",
            format="%.3f",
        ),
    }

    covered_column, uncovered_column = st.columns(2)
    with covered_column:
        st.markdown("**Covered NICE Tasks**")
        if covered_tasks.empty:
            st.info("No NICE Tasks are covered.")
        else:
            st.dataframe(
                covered_tasks,
                width="stretch",
                height=360,
                hide_index=True,
                column_config=column_config,
            )

    with uncovered_column:
        st.markdown("**Uncovered NICE Tasks**")
        if uncovered_tasks.empty:
            st.success("All scenario NICE Tasks are covered.")
        else:
            st.dataframe(
                uncovered_tasks,
                width="stretch",
                height=360,
                hide_index=True,
                column_config=column_config,
            )


def render_gap_tabs(
    analyses: dict[str, dict[str, Any]],
) -> None:

    st.markdown(f""" <div class="card-section-info">
                       NICE Task
                      </div>
                    """, unsafe_allow_html=True)

    attack_result = analyses["ATTACK-BERT"]["result"]
    c1, c2, c3 = st.columns(3)
    render_summary_card(
        c1,
        "Covered NICE Tasks",
        str(len(attack_result.covered_tasks)),
        large_value=True,
    )
    render_summary_card(
        c2,
        "Uncovered NICE Tasks",
        str(len(attack_result.uncovered_tasks)),
        value_class="warning",
        large_value=True,
    )
    render_summary_card(
        c3,
        "Task Coverage",
        f"{attack_result.final_task_coverage_pct:.1f}%",
        large_value=True,
    )
    render_gaps_for_model(analyses["ATTACK-BERT"])


def render_data_quality_for_model(
    analysis: dict[str, Any],
) -> None:
    result = analysis["result"]

    q1, q2, q3, q4 = st.columns(4)

    render_summary_card(
        q1,
        "Tasks without eligible role",
        str(len(result.missing_task_role_mappings)),
        value_class="warning",
    )
    render_summary_card(
        q2,
        "Unreachable techniques",
        str(len(result.unreachable_techniques)),
        value_class="warning",
    )
    render_summary_card(
        q3,
        "Roles without cost",
        str(len(result.missing_cost_roles)),
        value_class="warning",
    )
    render_summary_card(
        q4,
        "Excluded roles",
        str(len(result.excluded_roles)),
        value_class="warning",
    )

    if result.missing_task_role_mappings:
        st.write(
            "**Tasks without eligible Work Role:**",
            ", ".join(result.missing_task_role_mappings),
        )

    if result.unreachable_techniques:
        st.write(
            "**Unreachable ATT&CK techniques:**",
            ", ".join(result.unreachable_techniques),
        )

    if result.missing_cost_roles:
        st.write(
            "**Work Roles without usable cost data:**",
            ", ".join(result.missing_cost_roles),
        )

    if result.excluded_roles:
        st.dataframe(
            pd.DataFrame(result.excluded_roles),
            width="stretch",
            hide_index=True,
        )


def render_data_quality(
    analyses: dict[str, dict[str, Any]],
) -> None:
    total_issues = sum(
        len(analysis["result"].missing_task_role_mappings)
        + len(analysis["result"].unreachable_techniques)
        + len(analysis["result"].missing_cost_roles)
        + len(analysis["result"].excluded_roles)
        for analysis in analyses.values()
    )

    with st.expander(
        f"Mapping and cost data quality ({total_issues} issues)"
    ):
        render_data_quality_for_model(analyses["ATTACK-BERT"])


# ---------------------------------------------------------------------
# Main page
# ---------------------------------------------------------------------

def render_threat_scenarios(nodes=None):
    """
    Threat-driven workforce planning research view.

    `nodes` is retained only for backward compatibility with the caller.
    Coverage, optimization, reachability, selected Work Roles, and budget
    curves all come from threat_budget_coverage.py.

    ATTACK-BERT provides the semantic mapping used throughout this view.
    """
    config = configuration_menu()

    try:
        model_inputs = load_all_model_inputs(
            config["year"],
            config["variant"],
        )
    except Exception as exc:
        st.error(
            "Unable to load the ATTACK-BERT threat mapping: "
            f"{exc}"
        )
        return

    available_scenarios = common_scenarios(model_inputs)

    if not available_scenarios:
        st.warning(
            "No threat scenarios are available for ATTACK-BERT under "
            "the selected configuration."
        )
        return

    selected_scenario = config["scenario_slot"].selectbox(
        "Threat scenario",
        available_scenarios,
        key="scenario_select",
    )

    current_roles = st.session_state.get("current_roles", [])
    cost_model = st.session_state.get("cost_model")

    if cost_model is None:
        st.error("The workforce cost model has not been loaded.")
        return

    try:
        role_costs = role_costs_dataframe(cost_model)
    except Exception as exc:
        st.error(f"Unable to prepare role cost data: {exc}")
        return

    analyses: dict[str, dict[str, Any]] = {}
    curve_config = {
        key: value
        for key, value in config.items()
        if key not in {"budget", "exact_target_cost", "scenario_slot"}
    }
    # The strategic coverage curve is always evaluated with the hybrid metric.
    # The objective selected under Advanced settings applies only to the
    # budget-specific optimization executed below.
    curve_config["coverage_mode"] = "hybrid"
    curve_config["coverage_label"] = "Hybrid Coverage"

    with st.spinner(
        "Evaluating the ATTACK-BERT workforce coverage curve..."
    ):
        for model_label in MODELS_TO_COMPARE:
            try:
                analyses[model_label] = analyze_embedding_model(
                    model_label=model_label,
                    model_data=model_inputs[model_label],
                    config=curve_config,
                    selected_scenario=selected_scenario,
                    role_costs=role_costs,
                    current_roles=current_roles,
                )
            except Exception as exc:
                st.error(
                    f"Unable to analyze {model_label}: {exc}"
                )
                return

    render_charts(analyses)

    if not render_budget_execution_controls(
        analyses,
        config,
        selected_scenario,
        current_roles,
    ):
        st.info(
            "Select an available annual budget and click "
            "'Run optimization' to display budget-specific results."
        )
        return

    with st.spinner(
        f"Optimizing ATTACK-BERT for {fmt_money(config['budget'])}..."
    ):
        try:
            execute_budget_optimization(
                analyses,
                config,
                current_roles,
            )
        except Exception as exc:
            st.error(f"Unable to run the selected-budget optimization: {exc}")
            return

    with st.container(key="optimization-results-card"):
        render_experiment_context(
            config,
            selected_scenario,
        )
        render_model_summary(
            analyses,
            config,
        )
        render_budget_reachability(analyses, config)

    with st.container(key="optimization-roles-card"):
        render_role_tabs(analyses)

    with st.container(key="optimization-gaps-card"):
        render_gap_tabs(analyses)

    #detail_tabs = st.tabs([
    #    "Selected Work Roles",
    #    "Coverage Gaps",
    #])

    #with detail_tabs[0]:
     #   render_role_tabs(analyses)

    #with detail_tabs[1]:
     #   render_gap_tabs(analyses)

    #render_data_quality(analyses)
