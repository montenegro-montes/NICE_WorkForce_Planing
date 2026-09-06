from __future__ import annotations

import argparse
import math
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Literal, TypedDict, cast

import pandas as pd

try:
    import pulp
except ImportError:
    pulp = None

try:
    from kneed import KneeLocator
except ImportError:
    KneeLocator = None


CostScenario = Literal["min", "avg", "max"]
CoverageMode = Literal["tasks", "weighted_tasks", "techniques", "hybrid"]
Algorithm = Literal["greedy", "milp"]


class ProblemData(TypedDict):
    scenario_id: str
    scenario_name: str
    all_tasks: set[str]
    all_techniques: set[str]
    task_weights: dict[str, float]
    role_tasks: dict[str, set[str]]
    role_techniques: dict[str, set[str]]
    role_cost: dict[str, float]
    metadata: dict[str, dict]
    missing_task_role_mappings: list[str]
    unreachable_techniques: list[str]
    missing_cost_roles: list[str]
    excluded_roles: list[dict]
    cost_scenario: str


@dataclass
class OptimizationResult:
    scenario_id: str
    scenario_name: str
    algorithm: str
    coverage_mode: str
    cost_scenario: str
    budget: float
    spent_budget: float
    remaining_budget: float
    budget_utilization_pct: float
    runtime_seconds: float

    initial_task_coverage_pct: float
    initial_weighted_task_coverage_pct: float
    initial_technique_coverage_pct: float
    initial_hybrid_coverage_pct: float

    final_task_coverage_pct: float
    final_weighted_task_coverage_pct: float
    final_technique_coverage_pct: float
    final_hybrid_coverage_pct: float
    objective_coverage_pct: float

    max_reachable_task_coverage_pct: float
    max_reachable_weighted_task_coverage_pct: float
    max_reachable_technique_coverage_pct: float
    max_reachable_hybrid_coverage_pct: float
    max_reachable_objective_coverage_pct: float

    covered_task_count: int
    total_task_count: int
    covered_technique_count: int
    total_technique_count: int

    cost_per_covered_task: float
    cost_per_covered_technique: float

    selected_roles: list[dict]
    covered_tasks: set[str]
    covered_techniques: set[str]
    uncovered_tasks: set[str]
    uncovered_techniques: set[str]

    missing_cost_roles: list[str]
    missing_task_role_mappings: list[str]
    unreachable_techniques: list[str]
    excluded_roles: list[dict]


def _clean_id(series: pd.Series) -> pd.Series:
    """Normalize identifier columns while preserving missing values."""
    return series.astype("string").str.strip()


def _first_existing(
    columns: Iterable[str],
    candidates: Iterable[str],
) -> str:
    """Return the first candidate column present in a DataFrame."""
    available = set(columns)
    for candidate in candidates:
        if candidate in available:
            return candidate
    raise ValueError(
        f"None of these columns were found: {list(candidates)}"
    )


def _validate_task_alpha(task_alpha: float) -> None:
    """Validate the hybrid objective weight."""
    if not 0.0 <= task_alpha <= 1.0:
        raise ValueError("task_alpha must be between 0.0 and 1.0")


def _validate_budget(budget: float) -> None:
    """Validate a non-negative budget."""
    if budget < 0:
        raise ValueError("budget cannot be negative")


def _parse_csv_list(value: str) -> list[str]:
    """Parse a comma-separated string into trimmed values."""
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_float_list(value: str) -> list[float]:
    """Parse a comma-separated list of floating-point values."""
    return [float(item) for item in _parse_csv_list(value)]


def _safe_filename(value: str) -> str:
    """Convert arbitrary text into a filesystem-safe lowercase token."""
    cleaned = re.sub(r"[^a-zA-Z0-9._-]+", "_", value.strip())
    return cleaned.strip("_").lower() or "result"


def load_inputs(
    scenario_tasks_file: str | Path,
    task_role_file: str | Path,
    role_costs_file: str | Path,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Load and validate the three required input datasets.

    scenario_tasks:
        Threat -> ATT&CK technique -> NICE task mappings.

    task_role:
        Detailed NICE task -> NICE Work Role mappings.

    role_costs:
        Annual role costs containing cost_min, cost_avg and cost_max.
    """
    scenario_tasks = pd.read_csv(scenario_tasks_file, low_memory=False)
    task_role = pd.read_csv(task_role_file, low_memory=False)
    role_costs = pd.read_csv(role_costs_file, low_memory=False)

    required_tasks = {
        "scenario_id",
        "scenario_name",
        "attack_id",
        "task_id",
    }
    missing = required_tasks - set(scenario_tasks.columns)
    if missing:
        raise ValueError(
            f"scenario_tasks is missing required columns: {sorted(missing)}"
        )

    task_col = _first_existing(
        task_role.columns,
        ["task_id", "task", "nice_task_id"],
    )
    role_col = _first_existing(
        task_role.columns,
        ["role_id", "work_role", "work_role_id", "nice_role_id"],
    )

    rename_map: dict[str, str] = {}
    if task_col != "task_id":
        rename_map[task_col] = "task_id"
    if role_col != "role_id":
        rename_map[role_col] = "role_id"
    task_role = task_role.rename(columns=rename_map)

    required_costs = {
        "role_id",
        "role_name",
        "cost_min",
        "cost_avg",
        "cost_max",
    }
    missing = required_costs - set(role_costs.columns)
    if missing:
        raise ValueError(
            f"role_costs is missing required columns: {sorted(missing)}"
        )

    for df, columns in [
        (
            scenario_tasks,
            ["scenario_id", "scenario_name", "attack_id", "task_id"],
        ),
        (
            task_role,
            ["scenario_id", "scenario_name", "attack_id", "task_id", "role_id"],
        ),
        (
            role_costs,
            ["role_id", "role_name", "category", "confidence", "salary_model"],
        ),
    ]:
        for column in columns:
            if column in df.columns:
                df[column] = _clean_id(df[column])

    scenario_tasks = scenario_tasks.dropna(
        subset=["scenario_id", "scenario_name", "attack_id", "task_id"]
    )
    task_role = task_role.dropna(subset=["task_id", "role_id"])
    role_costs = role_costs.dropna(subset=["role_id", "role_name"])

    duplicated_costs = role_costs["role_id"].duplicated(keep=False)
    if duplicated_costs.any():
        duplicated = sorted(
            role_costs.loc[duplicated_costs, "role_id"].unique()
        )
        raise ValueError(
            f"Duplicated role IDs in role_costs: {duplicated}"
        )

    for column in ["cost_min", "cost_avg", "cost_max"]:
        role_costs[column] = pd.to_numeric(
            role_costs[column],
            errors="coerce",
        )

    if role_costs[["cost_min", "cost_avg", "cost_max"]].isna().all(axis=None):
        raise ValueError("No valid numeric role costs were found")

    return scenario_tasks, task_role, role_costs


def prepare_problem(
    scenario_tasks: pd.DataFrame,
    task_role: pd.DataFrame,
    role_costs: pd.DataFrame,
    scenario_id: str,
    cost_scenario: CostScenario = "avg",
    min_similarity: float | None = None,
    accepted_review_status: set[str] | None = None,
    allowed_confidence: set[str] | None = None,
    exclude_estimated_costs: bool = False,
) -> ProblemData:
    """
    Build the optimization structures for one threat scenario.

    The function removes duplicate mappings, filters the detailed task-role
    mapping by scenario and ATT&CK technique, constructs role coverage sets,
    and records missing mappings and unavailable costs.
    """
    scenario_key = scenario_id.strip().casefold()

    st = scenario_tasks[
        scenario_tasks["scenario_id"].str.casefold() == scenario_key
    ].copy()

    if st.empty:
        available = sorted(scenario_tasks["scenario_id"].dropna().unique())
        raise ValueError(
            f"Unknown or empty scenario_id '{scenario_id}'. "
            f"Available scenarios: {available}"
        )

    if min_similarity is not None:
        if not 0.0 <= min_similarity <= 1.0:
            raise ValueError("min_similarity must be between 0.0 and 1.0")
        if "similarity_score" not in st.columns:
            raise ValueError(
                "min_similarity requires the similarity_score column"
            )
        st["similarity_score"] = pd.to_numeric(
            st["similarity_score"],
            errors="coerce",
        )
        st = st[st["similarity_score"] >= min_similarity]

    if accepted_review_status is not None:
        if "review_status" not in st.columns:
            raise ValueError(
                "accepted_review_status requires review_status"
            )
        accepted = {value.casefold() for value in accepted_review_status}
        st = st[
            st["review_status"]
            .astype("string")
            .str.casefold()
            .isin(accepted)
        ]

    if st.empty:
        raise ValueError(
            "No scenario-task rows remain after applying filters"
        )

    cost_column = f"cost_{cost_scenario}"
    costs = role_costs.copy()

    excluded_roles: list[dict] = []

    invalid_cost_rows = costs[
        costs[cost_column].isna() | (costs[cost_column] <= 0)
    ]
    for _, row in invalid_cost_rows.iterrows():
        excluded_roles.append({
            "role_id": row["role_id"],
            "reason": "invalid_or_missing_cost",
            "cost_value": row.get(cost_column),
        })

    costs = costs.dropna(subset=[cost_column])
    costs = costs[costs[cost_column] > 0]

    if allowed_confidence is not None:
        if "confidence" not in costs.columns:
            raise ValueError(
                "allowed_confidence requires confidence in role_costs"
            )
        accepted = {value.casefold() for value in allowed_confidence}
        rejected = costs[
            ~costs["confidence"]
            .astype("string")
            .str.casefold()
            .isin(accepted)
        ]
        for _, row in rejected.iterrows():
            excluded_roles.append({
                "role_id": row["role_id"],
                "reason": "confidence_filter",
                "confidence": row.get("confidence"),
            })
        costs = costs[
            costs["confidence"]
            .astype("string")
            .str.casefold()
            .isin(accepted)
        ]

    if exclude_estimated_costs:
        if "salary_model" not in costs.columns:
            raise ValueError(
                "exclude_estimated_costs requires salary_model"
            )
        rejected = costs[
            costs["salary_model"]
            .astype("string")
            .str.casefold()
            == "estimated"
        ]
        for _, row in rejected.iterrows():
            excluded_roles.append({
                "role_id": row["role_id"],
                "reason": "estimated_cost_excluded",
                "salary_model": row.get("salary_model"),
            })
        costs = costs[
            costs["salary_model"]
            .astype("string")
            .str.casefold()
            != "estimated"
        ]

    all_tasks: set[str] = {
        str(task_id)
        for task_id in st["task_id"].dropna().unique()
    }
    all_techniques: set[str] = {
        str(attack_id)
        for attack_id in st["attack_id"].dropna().unique()
    }

    if "similarity_score" in st.columns:
        similarity = pd.to_numeric(
            st["similarity_score"],
            errors="coerce",
        ).fillna(0.0)
    else:
        similarity = pd.Series(1.0, index=st.index, dtype=float)

    if "weight" in st.columns:
        mapping_weight = pd.to_numeric(
            st["weight"],
            errors="coerce",
        ).fillna(1.0)
    else:
        mapping_weight = pd.Series(1.0, index=st.index, dtype=float)

    st["_task_weight"] = (
        similarity * mapping_weight
    ).clip(lower=0.0)

    task_weight_series = (
        st.groupby("task_id")["_task_weight"]
        .max()
        .astype(float)
    )
    task_weights: dict[str, float] = {
        str(task_id): float(weight)
        for task_id, weight in task_weight_series.items()
    }

    if not any(weight > 0 for weight in task_weights.values()):
        task_weights = {
            task_id: 1.0
            for task_id in all_tasks
        }

    relevant_map = task_role.copy()

    if "scenario_id" in relevant_map.columns:
        relevant_map = relevant_map[
            relevant_map["scenario_id"].str.casefold() == scenario_key
        ]

    if "attack_id" in relevant_map.columns:
        relevant_map = relevant_map[
            relevant_map["attack_id"].isin(all_techniques)
        ]

    relevant_map = relevant_map[
        relevant_map["task_id"].isin(all_tasks)
    ].drop_duplicates(["task_id", "role_id"])

    mapped_roles: set[str] = {
        str(role_id)
        for role_id in relevant_map["role_id"].dropna()
    }
    available_roles: set[str] = {
        str(role_id)
        for role_id in costs["role_id"].dropna()
    }
    missing_cost_roles = sorted(mapped_roles - available_roles)

    relevant_map = relevant_map[
        relevant_map["role_id"].isin(available_roles)
    ]

    role_task_series = (
        relevant_map.groupby("role_id")["task_id"]
        .apply(lambda values: {str(value) for value in values})
    )
    role_tasks: dict[str, set[str]] = {
        str(role_id): set(tasks)
        for role_id, tasks in role_task_series.items()
    }

    task_technique_series = (
        st.groupby("task_id")["attack_id"]
        .apply(lambda values: {str(value) for value in values})
    )
    task_techniques: dict[str, set[str]] = {
        str(task_id): set(techniques)
        for task_id, techniques in task_technique_series.items()
    }

    role_techniques: dict[str, set[str]] = {
        role_id: set().union(
            *(
                task_techniques.get(task_id, set())
                for task_id in tasks
            )
        )
        for role_id, tasks in role_tasks.items()
    }

    metadata_records = costs.set_index("role_id").to_dict("index")
    metadata: dict[str, dict] = {
        str(role_id): dict(values)
        for role_id, values in metadata_records.items()
    }

    role_cost_series = (
        costs.set_index("role_id")[cost_column]
        .astype(float)
    )
    role_cost: dict[str, float] = {
        str(role_id): float(cost)
        for role_id, cost in role_cost_series.items()
    }

    mapped_tasks = (
        set().union(*role_tasks.values())
        if role_tasks
        else set()
    )
    mapped_techniques = (
        set().union(*role_techniques.values())
        if role_techniques
        else set()
    )

    return {
        "scenario_id": scenario_id,
        "scenario_name": str(st["scenario_name"].iloc[0]),
        "all_tasks": all_tasks,
        "all_techniques": all_techniques,
        "task_weights": task_weights,
        "role_tasks": role_tasks,
        "role_techniques": role_techniques,
        "role_cost": role_cost,
        "metadata": metadata,
        "missing_task_role_mappings": sorted(all_tasks - mapped_tasks),
        "unreachable_techniques": sorted(
            all_techniques - mapped_techniques
        ),
        "missing_cost_roles": missing_cost_roles,
        "excluded_roles": excluded_roles,
        "cost_scenario": cost_scenario,
    }


def _role_union(
    mapping: dict[str, set[str]],
    roles: Iterable[str],
) -> set[str]:
    """Return the union of all elements covered by the supplied roles."""
    role_list = list(roles)
    if not role_list:
        return set()
    return set().union(
        *(mapping.get(role_id, set()) for role_id in role_list)
    )


def _coverage_value(
    problem: ProblemData,
    tasks: set[str],
    techniques: set[str],
    mode: CoverageMode,
    task_alpha: float = 0.7,
) -> tuple[float, float]:
    """
    Return objective coverage and weighted task coverage, both in percent.
    """
    _validate_task_alpha(task_alpha)

    all_tasks = problem["all_tasks"]
    all_techniques = problem["all_techniques"]
    task_weights = problem["task_weights"]

    task_pct = (
        100.0 * len(tasks) / len(all_tasks)
        if all_tasks
        else 0.0
    )
    technique_pct = (
        100.0 * len(techniques) / len(all_techniques)
        if all_techniques
        else 0.0
    )

    weighted_denominator = sum(
        task_weights.get(task_id, 1.0)
        for task_id in all_tasks
    )
    weighted_numerator = sum(
        task_weights.get(task_id, 1.0)
        for task_id in tasks
    )

    weighted_task_pct = (
        100.0 * weighted_numerator / weighted_denominator
        if weighted_denominator
        else 0.0
    )

    if mode == "tasks":
        objective = task_pct
    elif mode == "weighted_tasks":
        objective = weighted_task_pct
    elif mode == "techniques":
        objective = technique_pct
    else:
        objective = (
            task_alpha * weighted_task_pct
            + (1.0 - task_alpha) * technique_pct
        )

    return objective, weighted_task_pct


def _reachable_coverages(
    problem: ProblemData,
    task_alpha: float,
) -> tuple[float, float, float]:
    """Return maximum reachable task, weighted-task and technique coverage."""
    reachable_tasks = _role_union(
        problem["role_tasks"],
        problem["role_tasks"].keys(),
    )
    reachable_techniques = _role_union(
        problem["role_techniques"],
        problem["role_techniques"].keys(),
    )

    task_pct = (
        100.0
        * len(reachable_tasks)
        / len(problem["all_tasks"])
        if problem["all_tasks"]
        else 0.0
    )

    _, weighted_pct = _coverage_value(
        problem,
        reachable_tasks,
        reachable_techniques,
        "weighted_tasks",
        task_alpha,
    )

    technique_pct = (
        100.0
        * len(reachable_techniques)
        / len(problem["all_techniques"])
        if problem["all_techniques"]
        else 0.0
    )

    return task_pct, weighted_pct, technique_pct


def optimize_greedy(
    problem: ProblemData,
    budget: float,
    coverage_mode: CoverageMode = "hybrid",
    current_roles: Iterable[str] | None = None,
    task_alpha: float = 0.7,
) -> OptimizationResult:
    """
    Greedy baseline maximizing marginal objective gain per unit of cost.
    """
    _validate_budget(budget)
    _validate_task_alpha(task_alpha)

    start = time.perf_counter()

    current = {
        str(role_id).strip()
        for role_id in (current_roles or [])
    }
    role_tasks = problem["role_tasks"]
    role_techniques = problem["role_techniques"]
    role_cost = problem["role_cost"]

    covered_tasks = _role_union(role_tasks, current)
    covered_techniques = _role_union(role_techniques, current)

    initial_tasks = set(covered_tasks)
    initial_techniques = set(covered_techniques)

    candidates = set(role_tasks) - current
    selected: list[dict] = []
    spent = 0.0

    while candidates:
        current_objective, _ = _coverage_value(
            problem,
            covered_tasks,
            covered_techniques,
            coverage_mode,
            task_alpha,
        )

        best_key: tuple | None = None
        best_data: tuple | None = None

        for role_id in candidates:
            cost = role_cost.get(role_id)

            if (
                cost is None
                or cost <= 0
                or spent + cost > budget + 1e-9
            ):
                continue

            new_tasks = role_tasks[role_id] - covered_tasks
            new_techniques = (
                role_techniques.get(role_id, set())
                - covered_techniques
            )

            if not new_tasks and not new_techniques:
                continue

            trial_tasks = covered_tasks | role_tasks[role_id]
            trial_techniques = (
                covered_techniques
                | role_techniques.get(role_id, set())
            )

            trial_objective, _ = _coverage_value(
                problem,
                trial_tasks,
                trial_techniques,
                coverage_mode,
                task_alpha,
            )

            gain = trial_objective - current_objective
            roi = gain / cost * 100_000

            key = (
                roi,
                gain,
                len(new_tasks),
                len(new_techniques),
                -cost,
                role_id,
            )

            if best_key is None or key > best_key:
                best_key = key
                best_data = (
                    role_id,
                    cost,
                    new_tasks,
                    new_techniques,
                    trial_objective,
                    gain,
                    roi,
                )

        if best_data is None:
            break

        (
            role_id,
            cost,
            new_tasks,
            new_techniques,
            trial_objective,
            gain,
            roi,
        ) = best_data

        covered_tasks |= role_tasks[role_id]
        covered_techniques |= role_techniques.get(role_id, set())
        spent += cost

        metadata = problem["metadata"].get(role_id, {})

        selected.append({
            "selection_order": len(selected) + 1,
            "role_id": role_id,
            "role_name": metadata.get("role_name", ""),
            "category": metadata.get("category", ""),
            "mapped_job": metadata.get("mapped_job", ""),
            "salary_model": metadata.get("salary_model", ""),
            "confidence": metadata.get("confidence", ""),
            "annual_cost": cost,
            "new_tasks": len(new_tasks),
            "new_techniques": len(new_techniques),
            "marginal_coverage_gain_pct": gain,
            "gain_per_100k": roi,
            "cumulative_cost": spent,
            "objective_coverage_after_pct": trial_objective,
        })

        candidates.remove(role_id)

    runtime = time.perf_counter() - start

    return _build_result(
        problem=problem,
        algorithm="greedy",
        coverage_mode=coverage_mode,
        budget=budget,
        spent=spent,
        initial_tasks=initial_tasks,
        initial_techniques=initial_techniques,
        covered_tasks=covered_tasks,
        covered_techniques=covered_techniques,
        selected=selected,
        task_alpha=task_alpha,
        runtime_seconds=runtime,
    )

def _add_binary_coverage_constraints(
    model,
    variable,
    elements: list[str],
    initial_elements: set[str],
    roles: list[str],
    role_elements: dict[str, set[str]],
    role_variables,
) -> None:
    """Link binary coverage variables to role-selection variables."""

    if pulp is None:
        raise RuntimeError(
            "MILP requires PuLP: pip install pulp"
        )

    for element in elements:
        if element in initial_elements:
            model += variable[element] == 1
            continue

        providers = [
            role_id
            for role_id in roles
            if element in role_elements.get(role_id, set())
        ]

        if not providers:
            model += variable[element] == 0
            continue

        model += (
            variable[element]
            <= pulp.lpSum(
                role_variables[role_id]
                for role_id in providers
            )
        )

        for role_id in providers:
            model += (
                variable[element]
                >= role_variables[role_id]
            )

def optimize_milp(
    problem: ProblemData,
    budget: float,
    coverage_mode: CoverageMode = "hybrid",
    current_roles: Iterable[str] | None = None,
    task_alpha: float = 0.7,
    time_limit_seconds: int = 60,
) -> OptimizationResult:
    """
    Solve the budget-constrained maximum coverage problem optimally with MILP.
    """
    _validate_budget(budget)
    _validate_task_alpha(task_alpha)

    if pulp is None:
        raise RuntimeError("MILP requires PuLP: pip install pulp")

    start = time.perf_counter()

    current = {
        str(role_id).strip()
        for role_id in (current_roles or [])
    }

    roles = sorted(set(problem["role_tasks"]) - current)
    tasks = sorted(problem["all_tasks"])
    techniques = sorted(problem["all_techniques"])

    initial_tasks = _role_union(problem["role_tasks"], current)
    initial_techniques = _role_union(
        problem["role_techniques"],
        current,
    )

    model = pulp.LpProblem(
        "ThreatBudgetCoverage",
        pulp.LpMaximize,
    )

    x = pulp.LpVariable.dicts("select_role", roles, cat="Binary")
    y = pulp.LpVariable.dicts("cover_task", tasks, cat="Binary")
    z = pulp.LpVariable.dicts(
        "cover_technique",
        techniques,
        cat="Binary",
    )

    model += (
        pulp.lpSum(
            problem["role_cost"][role_id] * x[role_id]
            for role_id in roles
        )
        <= budget
    )

    _add_binary_coverage_constraints(
        model,
        y,
        tasks,
        initial_tasks,
        roles,
        problem["role_tasks"],
        x,
    )
    _add_binary_coverage_constraints(
        model,
        z,
        techniques,
        initial_techniques,
        roles,
        problem["role_techniques"],
        x,
    )

    task_weight_denominator = (
        sum(
            problem["task_weights"].get(task_id, 1.0)
            for task_id in tasks
        )
        or 1.0
    )

    weighted_tasks_expr = pulp.lpSum(
        problem["task_weights"].get(task_id, 1.0)
        / task_weight_denominator
        * y[task_id]
        for task_id in tasks
    )

    raw_tasks_expr = (
        pulp.lpSum(y[task_id] for task_id in tasks)
        / (len(tasks) or 1)
    )

    techniques_expr = (
        pulp.lpSum(z[attack_id] for attack_id in techniques)
        / (len(techniques) or 1)
    )

    if coverage_mode == "tasks":
        objective_expr = raw_tasks_expr
    elif coverage_mode == "weighted_tasks":
        objective_expr = weighted_tasks_expr
    elif coverage_mode == "techniques":
        objective_expr = techniques_expr
    else:
        objective_expr = (
            task_alpha * weighted_tasks_expr
            + (1.0 - task_alpha) * techniques_expr
        )

    model += objective_expr

    solver = pulp.PULP_CBC_CMD(
        msg=False,
        timeLimit=time_limit_seconds,
    )
    model.solve(solver)

    status = pulp.LpStatus[model.status]
    if status != "Optimal":
        raise RuntimeError(f"MILP solver status: {status}")

    chosen = [
        role_id
        for role_id in roles
        if pulp.value(x[role_id]) is not None
        and pulp.value(x[role_id]) > 0.5
    ]

    covered_tasks = (
        initial_tasks
        | _role_union(problem["role_tasks"], chosen)
    )
    covered_techniques = (
        initial_techniques
        | _role_union(problem["role_techniques"], chosen)
    )

    spent = sum(problem["role_cost"][role_id] for role_id in chosen)

    selected = _order_selected_roles(
        problem,
        chosen,
        initial_tasks,
        initial_techniques,
        coverage_mode,
        task_alpha,
    )

    runtime = time.perf_counter() - start

    return _build_result(
        problem=problem,
        algorithm="milp",
        coverage_mode=coverage_mode,
        budget=budget,
        spent=spent,
        initial_tasks=initial_tasks,
        initial_techniques=initial_techniques,
        covered_tasks=covered_tasks,
        covered_techniques=covered_techniques,
        selected=selected,
        task_alpha=task_alpha,
        runtime_seconds=runtime,
    )


def _order_selected_roles(
    problem: ProblemData,
    chosen_roles: Iterable[str],
    initial_tasks: set[str],
    initial_techniques: set[str],
    coverage_mode: CoverageMode,
    task_alpha: float,
) -> list[dict]:
    """Order an MILP solution by marginal contribution for interpretation."""
    remaining = set(chosen_roles)
    before_tasks = set(initial_tasks)
    before_techniques = set(initial_techniques)
    cumulative_cost = 0.0
    selected: list[dict] = []

    while remaining:
        current_objective, _ = _coverage_value(
            problem,
            before_tasks,
            before_techniques,
            coverage_mode,
            task_alpha,
        )

        def role_key(role_id: str) -> tuple:
            after_tasks = before_tasks | problem["role_tasks"][role_id]
            after_techniques = (
                before_techniques
                | problem["role_techniques"].get(role_id, set())
            )
            objective, _ = _coverage_value(
                problem,
                after_tasks,
                after_techniques,
                coverage_mode,
                task_alpha,
            )
            gain = objective - current_objective
            cost = problem["role_cost"][role_id]
            return (
                gain,
                gain / cost if cost else 0.0,
                -cost,
                role_id,
            )

        role_id = max(remaining, key=role_key)

        after_tasks = before_tasks | problem["role_tasks"][role_id]
        after_techniques = (
            before_techniques
            | problem["role_techniques"].get(role_id, set())
        )

        after_objective, _ = _coverage_value(
            problem,
            after_tasks,
            after_techniques,
            coverage_mode,
            task_alpha,
        )

        gain = after_objective - current_objective
        cost = problem["role_cost"][role_id]
        cumulative_cost += cost
        metadata = problem["metadata"].get(role_id, {})

        selected.append({
            "selection_order": len(selected) + 1,
            "role_id": role_id,
            "role_name": metadata.get("role_name", ""),
            "category": metadata.get("category", ""),
            "mapped_job": metadata.get("mapped_job", ""),
            "salary_model": metadata.get("salary_model", ""),
            "confidence": metadata.get("confidence", ""),
            "annual_cost": cost,
            "new_tasks": len(after_tasks - before_tasks),
            "new_techniques": len(
                after_techniques - before_techniques
            ),
            "marginal_coverage_gain_pct": gain,
            "gain_per_100k": (
                gain / cost * 100_000
                if cost
                else 0.0
            ),
            "cumulative_cost": cumulative_cost,
            "objective_coverage_after_pct": after_objective,
        })

        before_tasks = after_tasks
        before_techniques = after_techniques
        remaining.remove(role_id)

    return selected


def _build_result(
    problem: ProblemData,
    algorithm: str,
    coverage_mode: CoverageMode,
    budget: float,
    spent: float,
    initial_tasks: set[str],
    initial_techniques: set[str],
    covered_tasks: set[str],
    covered_techniques: set[str],
    selected: list[dict],
    task_alpha: float,
    runtime_seconds: float,
) -> OptimizationResult:
    """Create all summary metrics for one optimization run."""
    objective, weighted_task_coverage = _coverage_value(
        problem,
        covered_tasks,
        covered_techniques,
        coverage_mode,
        task_alpha,
    )

    hybrid_coverage, _ = _coverage_value(
        problem,
        covered_tasks,
        covered_techniques,
        "hybrid",
        task_alpha,
    )

    _, initial_weighted_task_coverage = _coverage_value(
        problem,
        initial_tasks,
        initial_techniques,
        coverage_mode,
        task_alpha,
    )

    initial_hybrid_coverage, _ = _coverage_value(
        problem,
        initial_tasks,
        initial_techniques,
        "hybrid",
        task_alpha,
    )

    (
        max_task,
        max_weighted,
        max_technique,
    ) = _reachable_coverages(problem, task_alpha)

    max_hybrid = (
        task_alpha * max_weighted
        + (1.0 - task_alpha) * max_technique
    )

    if coverage_mode == "tasks":
        max_objective = max_task
    elif coverage_mode == "weighted_tasks":
        max_objective = max_weighted
    elif coverage_mode == "techniques":
        max_objective = max_technique
    else:
        max_objective = max_hybrid

    covered_task_count = len(covered_tasks)
    covered_technique_count = len(covered_techniques)

    initial_task_coverage = (
        100.0
        * len(initial_tasks)
        / len(problem["all_tasks"])
        if problem["all_tasks"]
        else 0.0
    )

    initial_technique_coverage = (
        100.0
        * len(initial_techniques)
        / len(problem["all_techniques"])
        if problem["all_techniques"]
        else 0.0
    )

    final_task_coverage = (
        100.0
        * covered_task_count
        / len(problem["all_tasks"])
        if problem["all_tasks"]
        else 0.0
    )

    final_technique_coverage = (
        100.0
        * covered_technique_count
        / len(problem["all_techniques"])
        if problem["all_techniques"]
        else 0.0
    )

    return OptimizationResult(
        scenario_id=problem["scenario_id"],
        scenario_name=problem["scenario_name"],
        algorithm=algorithm,
        coverage_mode=coverage_mode,
        cost_scenario=problem["cost_scenario"],
        budget=float(budget),
        spent_budget=float(spent),
        remaining_budget=float(budget - spent),
        budget_utilization_pct=(
            100.0 * spent / budget
            if budget > 0
            else 0.0
        ),
        runtime_seconds=runtime_seconds,

        initial_task_coverage_pct=initial_task_coverage,
        initial_weighted_task_coverage_pct=initial_weighted_task_coverage,
        initial_technique_coverage_pct=initial_technique_coverage,
        initial_hybrid_coverage_pct=initial_hybrid_coverage,

        final_task_coverage_pct=final_task_coverage,
        final_weighted_task_coverage_pct=weighted_task_coverage,
        final_technique_coverage_pct=final_technique_coverage,
        final_hybrid_coverage_pct=hybrid_coverage,
        objective_coverage_pct=objective,

        max_reachable_task_coverage_pct=max_task,
        max_reachable_weighted_task_coverage_pct=max_weighted,
        max_reachable_technique_coverage_pct=max_technique,
        max_reachable_hybrid_coverage_pct=max_hybrid,
        max_reachable_objective_coverage_pct=max_objective,

        covered_task_count=covered_task_count,
        total_task_count=len(problem["all_tasks"]),
        covered_technique_count=covered_technique_count,
        total_technique_count=len(problem["all_techniques"]),

        cost_per_covered_task=(
            spent / covered_task_count
            if covered_task_count
            else math.nan
        ),
        cost_per_covered_technique=(
            spent / covered_technique_count
            if covered_technique_count
            else math.nan
        ),

        selected_roles=selected,
        covered_tasks=covered_tasks,
        covered_techniques=covered_techniques,
        uncovered_tasks=problem["all_tasks"] - covered_tasks,
        uncovered_techniques=(
            problem["all_techniques"] - covered_techniques
        ),

        missing_cost_roles=problem["missing_cost_roles"],
        missing_task_role_mappings=problem[
            "missing_task_role_mappings"
        ],
        unreachable_techniques=problem["unreachable_techniques"],
        excluded_roles=problem["excluded_roles"],
    )


def role_ranking(
    problem: ProblemData,
    coverage_mode: CoverageMode = "hybrid",
    current_roles: Iterable[str] | None = None,
    task_alpha: float = 0.7,
) -> pd.DataFrame:
    """Rank every candidate role by standalone marginal contribution."""
    current = {
        str(role_id).strip()
        for role_id in (current_roles or [])
    }
    base_tasks = _role_union(problem["role_tasks"], current)
    base_techniques = _role_union(
        problem["role_techniques"],
        current,
    )
    base_objective, _ = _coverage_value(
        problem,
        base_tasks,
        base_techniques,
        coverage_mode,
        task_alpha,
    )

    rows: list[dict] = []

    for role_id in sorted(set(problem["role_tasks"]) - current):
        after_tasks = base_tasks | problem["role_tasks"][role_id]
        after_techniques = (
            base_techniques
            | problem["role_techniques"].get(role_id, set())
        )
        objective, weighted = _coverage_value(
            problem,
            after_tasks,
            after_techniques,
            coverage_mode,
            task_alpha,
        )
        gain = objective - base_objective
        cost = problem["role_cost"][role_id]
        metadata = problem["metadata"].get(role_id, {})

        rows.append({
            "role_id": role_id,
            "role_name": metadata.get("role_name", ""),
            "category": metadata.get("category", ""),
            "annual_cost": cost,
            "standalone_new_tasks": len(
                problem["role_tasks"][role_id] - base_tasks
            ),
            "standalone_new_techniques": len(
                problem["role_techniques"].get(role_id, set())
                - base_techniques
            ),
            "standalone_weighted_task_coverage_pct": weighted,
            "standalone_objective_gain_pct": gain,
            "gain_per_100k": (
                gain / cost * 100_000 if cost else 0.0
            ),
            "salary_model": metadata.get("salary_model", ""),
            "confidence": metadata.get("confidence", ""),
        })

    ranking = pd.DataFrame(rows)
    if ranking.empty:
        return ranking

    return ranking.sort_values(
        by=[
            "gain_per_100k",
            "standalone_objective_gain_pct",
            "standalone_new_tasks",
        ],
        ascending=[False, False, False],
    ).reset_index(drop=True)


def budget_curve(
    problem: ProblemData,
    budgets: Iterable[float],
    algorithm: Algorithm = "milp",
    coverage_mode: CoverageMode = "hybrid",
    current_roles: Iterable[str] | None = None,
    task_alpha: float = 0.7,
) -> pd.DataFrame:
    """
    Evaluate coverage over a sequence of budgets.

    All four coverage metrics are always returned, independently of the
    optimization objective. This allows the UI and the paper figures to
    compare Task, Weighted Task, Technique and Hybrid Coverage consistently.
    """
    optimizer = optimize_milp if algorithm == "milp" else optimize_greedy

    rows: list[dict] = []
    previous_budget: float | None = None
    previous_objective: float | None = None
    previous_hybrid: float | None = None
    previous_spent: float | None = None
    initial_role_ids = sorted({
        str(role_id).strip()
        for role_id in (current_roles or [])
        if str(role_id).strip()
    })
    initial_workforce_cost = sum(
        problem["role_cost"].get(role_id, 0.0)
        for role_id in initial_role_ids
    )

    for budget in sorted(set(float(value) for value in budgets)):
        result = optimizer(
            problem,
            budget,
            coverage_mode,
            current_roles,
            task_alpha,
        )

        marginal_objective_gain = math.nan
        marginal_hybrid_gain = math.nan
        marginal_hybrid_rowi_actual_spend = math.nan

        if previous_budget is not None and budget > previous_budget:
            if previous_objective is not None:
                marginal_objective_gain = (
                    result.objective_coverage_pct - previous_objective
                ) / (budget - previous_budget) * 100_000

            if previous_hybrid is not None:
                marginal_hybrid_gain = (
                    result.final_hybrid_coverage_pct - previous_hybrid
                ) / (budget - previous_budget) * 100_000

        if (
            previous_spent is not None
            and result.spent_budget > previous_spent + 1e-9
            and previous_hybrid is not None
        ):
            marginal_hybrid_rowi_actual_spend = (
                result.final_hybrid_coverage_pct - previous_hybrid
            ) / (result.spent_budget - previous_spent) * 100_000

        selected_role_ids = [
            str(role["role_id"])
            for role in result.selected_roles
        ]
        total_role_ids = sorted(
            set(initial_role_ids) | set(selected_role_ids)
        )
        total_budget = result.budget + initial_workforce_cost
        total_spent = result.spent_budget + initial_workforce_cost

        rows.append({
            "scenario_id": result.scenario_id,
            "scenario_name": result.scenario_name,
            "algorithm": result.algorithm,
            "coverage_mode": result.coverage_mode,
            "cost_scenario": result.cost_scenario,
            "budget": result.budget,
            "budget_million": result.budget / 1_000_000,
            "spent_budget": result.spent_budget,
            "additional_budget": result.budget,
            "additional_spent": result.spent_budget,
            "total_budget": total_budget,
            "total_budget_million": total_budget / 1_000_000,
            "total_spent": total_spent,
            "total_budget_utilization_pct": (
                100.0 * total_spent / total_budget
                if total_budget > 0
                else 0.0
            ),
            "initial_workforce": ";".join(initial_role_ids),
            "initial_workforce_cost": initial_workforce_cost,
            "initial_role_count": len(initial_role_ids),
            "initial_task_coverage_pct": (
                result.initial_task_coverage_pct
            ),
            "initial_weighted_task_coverage_pct": (
                result.initial_weighted_task_coverage_pct
            ),
            "initial_technique_coverage_pct": (
                result.initial_technique_coverage_pct
            ),
            "initial_hybrid_coverage_pct": (
                result.initial_hybrid_coverage_pct
            ),
            "remaining_budget": result.remaining_budget,
            "budget_utilization_pct": result.budget_utilization_pct,
            "runtime_seconds": result.runtime_seconds,
            "selected_roles": len(result.selected_roles),
            "additional_roles_selected": len(selected_role_ids),
            "total_roles": len(total_role_ids),
            "total_role_ids": ";".join(total_role_ids),
            "selected_role_ids": ";".join(sorted(
                role_id for role_id in selected_role_ids
            )),
            "selected_role_ids_ordered": ";".join(
                role_id for role_id in selected_role_ids
            ),
            "task_coverage_pct": result.final_task_coverage_pct,
            "weighted_task_coverage_pct": (
                result.final_weighted_task_coverage_pct
            ),
            "technique_coverage_pct": (
                result.final_technique_coverage_pct
            ),
            "hybrid_coverage_pct": (
                result.final_hybrid_coverage_pct
            ),
            "objective_coverage_pct": (
                result.objective_coverage_pct
            ),
            "marginal_gain_per_100k": marginal_objective_gain,
            "marginal_hybrid_gain_per_100k": marginal_hybrid_gain,
            "marginal_hybrid_gain_per_100k_available_budget": (
                marginal_hybrid_gain
            ),
            "marginal_hybrid_rowi_per_100k_actual_spend": (
                marginal_hybrid_rowi_actual_spend
            ),
        })

        previous_budget = budget
        previous_objective = result.objective_coverage_pct
        previous_hybrid = result.final_hybrid_coverage_pct
        previous_spent = result.spent_budget

    return pd.DataFrame(rows)


def first_budget_reaching_curve(
    curve: pd.DataFrame,
    coverage_column: str,
    threshold: float = 100.0,
    tolerance: float = 1e-6,
) -> dict | None:
    """Return the first sampled budget reaching a coverage threshold."""
    required = {"budget", coverage_column}
    missing = required - set(curve.columns)
    if missing:
        raise ValueError(
            f"Curve is missing required columns: {sorted(missing)}"
        )

    candidates = curve.loc[
        curve[coverage_column] >= threshold - tolerance,
        ["budget", coverage_column],
    ].sort_values("budget")

    if candidates.empty:
        return None

    row = candidates.iloc[0]
    return {
        "budget": float(row["budget"]),
        "coverage": float(row[coverage_column]),
    }


def kneedle_saturation_point(
    curve: pd.DataFrame,
    coverage_column: str = "hybrid_coverage_pct",
    sensitivity: float = 1.0,
) -> dict | None:
    """
    Detect the Kneedle saturation point for a cumulative coverage curve.

    The returned budget is expressed in the same currency units as curve["budget"].
    """
    if KneeLocator is None:
        raise RuntimeError(
        "Kneedle saturation requires 'kneed': pip install kneed"
    )

    required = {"budget", coverage_column}
    missing = required - set(curve.columns)
    if missing:
        raise ValueError(
            f"Curve is missing required columns: {sorted(missing)}"
        )

    data = (
        curve[["budget", coverage_column]]
        .dropna()
        .sort_values("budget")
        .drop_duplicates(subset="budget")
    )

    if len(data) < 3:
        return None

    x = data["budget"].to_numpy(dtype=float) / 1_000_000
    y = data[coverage_column].to_numpy(dtype=float)

    detector = KneeLocator(
        x=x,
        y=y,
        S=sensitivity,
        curve="concave",
        direction="increasing",
        interp_method="interp1d",
        online=False,
    )

    if detector.knee is None or detector.knee_y is None:
        return None

    return {
        "budget": float(detector.knee) * 1_000_000,
        "coverage": float(detector.knee_y),
    }


def budget_reference_points(
    curve: pd.DataFrame,
    sensitivity: float = 1.0,
) -> dict[str, dict | None]:
    """
    Return the reference points used by the paper-style coverage chart.

    - first sampled budget reaching 100% Technique Coverage;
    - Kneedle saturation point of Hybrid Coverage;
    - first sampled budget reaching 100% Hybrid Coverage.
    """
    return {
        "technique_full": first_budget_reaching_curve(
            curve,
            "technique_coverage_pct",
            100.0,
        ),
        "saturation": kneedle_saturation_point(
            curve,
            "hybrid_coverage_pct",
            sensitivity,
        ),
        "hybrid_full": first_budget_reaching_curve(
            curve,
            "hybrid_coverage_pct",
            100.0,
        ),
    }


def minimum_cost_for_target(
    problem: ProblemData,
    target_pct: float,
    coverage_mode: CoverageMode = "hybrid",
    current_roles: Iterable[str] | None = None,
    task_alpha: float = 0.7,
    time_limit_seconds: int = 60,
) -> dict:
    """Minimize annual cost subject to a target coverage percentage."""
    _validate_task_alpha(task_alpha)

    if pulp is None:
        raise RuntimeError(
            "Minimum-cost optimization requires PuLP: pip install pulp"
        )
    if not 0.0 <= target_pct <= 100.0:
        raise ValueError("target_pct must be between 0 and 100")

    current = {
        str(role_id).strip()
        for role_id in (current_roles or [])
    }
    initial_role_ids = sorted(current)
    initial_workforce_cost = sum(
        problem["role_cost"].get(role_id, 0.0)
        for role_id in initial_role_ids
    )
    roles = sorted(set(problem["role_tasks"]) - current)
    tasks = sorted(problem["all_tasks"])
    techniques = sorted(problem["all_techniques"])

    initial_tasks = _role_union(problem["role_tasks"], current)
    initial_techniques = _role_union(
        problem["role_techniques"],
        current,
    )

    model = pulp.LpProblem(
        "MinimumCostForCoverage",
        pulp.LpMinimize,
    )

    x = pulp.LpVariable.dicts("select_role", roles, cat="Binary")
    y = pulp.LpVariable.dicts("cover_task", tasks, cat="Binary")
    z = pulp.LpVariable.dicts(
        "cover_technique",
        techniques,
        cat="Binary",
    )

    model += pulp.lpSum(
        problem["role_cost"][role_id] * x[role_id]
        for role_id in roles
    )

    _add_binary_coverage_constraints(
        model,
        y,
        tasks,
        initial_tasks,
        roles,
        problem["role_tasks"],
        x,
    )
    _add_binary_coverage_constraints(
        model,
        z,
        techniques,
        initial_techniques,
        roles,
        problem["role_techniques"],
        x,
    )

    task_weight_denominator = (
        sum(
            problem["task_weights"].get(task_id, 1.0)
            for task_id in tasks
        )
        or 1.0
    )

    weighted_tasks_expr = pulp.lpSum(
        problem["task_weights"].get(task_id, 1.0)
        / task_weight_denominator
        * y[task_id]
        for task_id in tasks
    )
    raw_tasks_expr = (
        pulp.lpSum(y[task_id] for task_id in tasks)
        / (len(tasks) or 1)
    )
    technique_expr = (
        pulp.lpSum(z[attack_id] for attack_id in techniques)
        / (len(techniques) or 1)
    )

    if coverage_mode == "tasks":
        coverage_expr = raw_tasks_expr
    elif coverage_mode == "weighted_tasks":
        coverage_expr = weighted_tasks_expr
    elif coverage_mode == "techniques":
        coverage_expr = technique_expr
    else:
        coverage_expr = (
            task_alpha * weighted_tasks_expr
            + (1.0 - task_alpha) * technique_expr
        )

    model += coverage_expr >= target_pct / 100.0

    start = time.perf_counter()
    model.solve(
        pulp.PULP_CBC_CMD(
            msg=False,
            timeLimit=time_limit_seconds,
        )
    )
    runtime = time.perf_counter() - start

    status = pulp.LpStatus[model.status]

    if status != "Optimal":
        return {
            "target_pct": target_pct,
            "status": status,
            "minimum_cost": math.nan,
            "additional_minimum_cost": math.nan,
            "total_minimum_cost": math.nan,
            "initial_workforce": ";".join(initial_role_ids),
            "initial_workforce_cost": initial_workforce_cost,
            "initial_role_count": len(initial_role_ids),
            "number_of_roles": 0,
            "additional_roles_selected": 0,
            "total_roles": len(initial_role_ids),
            "selected_roles": "",
            "runtime_seconds": runtime,
        }

    chosen = [
        role_id
        for role_id in roles
        if pulp.value(x[role_id]) is not None
        and pulp.value(x[role_id]) > 0.5
    ]

    additional_minimum_cost = sum(
        problem["role_cost"][role_id]
        for role_id in chosen
    )
    return {
        "target_pct": target_pct,
        "status": status,
        "minimum_cost": additional_minimum_cost,
        "additional_minimum_cost": additional_minimum_cost,
        "total_minimum_cost": (
            initial_workforce_cost + additional_minimum_cost
        ),
        "initial_workforce": ";".join(initial_role_ids),
        "initial_workforce_cost": initial_workforce_cost,
        "initial_role_count": len(initial_role_ids),
        "number_of_roles": len(chosen),
        "additional_roles_selected": len(chosen),
        "total_roles": len(set(initial_role_ids) | set(chosen)),
        "selected_roles": ";".join(chosen),
        "total_role_ids": ";".join(sorted(
            set(initial_role_ids) | set(chosen)
        )),
        "runtime_seconds": runtime,
    }


def minimum_cost_table(
    problem: ProblemData,
    targets: Iterable[float],
    coverage_mode: CoverageMode = "hybrid",
    current_roles: Iterable[str] | None = None,
    task_alpha: float = 0.7,
) -> pd.DataFrame:
    """Compute minimum cost for multiple target coverage levels."""
    return pd.DataFrame([
        minimum_cost_for_target(
            problem,
            float(target),
            coverage_mode,
            current_roles,
            task_alpha,
        )
        for target in targets
    ])



def export_result(
    result: OptimizationResult,
    problem: ProblemData,
    output_dir: str | Path,
    current_roles: Iterable[str] | None = None,
    available_annual_budget: float | None = None,
) -> None:
    """Export all run-level result tables."""
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    stem = _safe_filename(
        f"{result.scenario_id}_{result.algorithm}_"
        f"{result.cost_scenario}_{result.coverage_mode}"
    )

    summary = asdict(result)
    for key in [
        "spent_budget",
        "selected_roles",
        "covered_tasks",
        "covered_techniques",
        "uncovered_tasks",
        "uncovered_techniques",
        "missing_cost_roles",
        "missing_task_role_mappings",
        "unreachable_techniques",
        "excluded_roles",
    ]:
        summary.pop(key, None)

    initial_role_ids = sorted({
        str(role_id).strip()
        for role_id in (current_roles or [])
        if str(role_id).strip()
    })
    selected_role_ids = [
        str(role["role_id"])
        for role in result.selected_roles
    ]
    total_role_ids = sorted(
        set(initial_role_ids) | set(selected_role_ids)
    )
    initial_workforce_cost = sum(
        problem["role_cost"].get(role_id, 0.0)
        for role_id in initial_role_ids
    )
    total_budget = (
        float(available_annual_budget)
        if available_annual_budget is not None
        else result.budget + initial_workforce_cost
    )
    total_spent = result.spent_budget + initial_workforce_cost
    initial_objective = {
        "tasks": result.initial_task_coverage_pct,
        "weighted_tasks": result.initial_weighted_task_coverage_pct,
        "techniques": result.initial_technique_coverage_pct,
        "hybrid": result.initial_hybrid_coverage_pct,
    }[result.coverage_mode]
    summary.update({
        "additional_budget": result.budget,
        "additional_spent": result.spent_budget,
        "total_budget": total_budget,
        "total_spent": total_spent,
        "total_budget_utilization_pct": (
            100.0 * total_spent / total_budget
            if total_budget > 0
            else 0.0
        ),
        "initial_workforce": ";".join(initial_role_ids),
        "initial_workforce_cost": initial_workforce_cost,
        "initial_role_count": len(initial_role_ids),
        "initial_objective_coverage_pct": initial_objective,
        "additional_roles_selected": len(selected_role_ids),
        "selected_role_ids": ";".join(selected_role_ids),
        "total_roles": len(total_role_ids),
        "total_role_ids": ";".join(total_role_ids),
    })
    summary["budget"] = total_budget

    pd.DataFrame([summary]).to_csv(
        output / f"{stem}_summary.csv",
        index=False,
    )

    pd.DataFrame(result.selected_roles).to_csv(
        output / f"{stem}_selected_roles.csv",
        index=False,
    )

    pd.DataFrame({
        "task_id": sorted(result.uncovered_tasks)
    }).to_csv(
        output / f"{stem}_uncovered_tasks.csv",
        index=False,
    )

    pd.DataFrame({
        "attack_id": sorted(result.uncovered_techniques)
    }).to_csv(
        output / f"{stem}_uncovered_techniques.csv",
        index=False,
    )

    pd.DataFrame({
        "task_id": result.missing_task_role_mappings
    }).to_csv(
        output / f"{stem}_tasks_without_mapping.csv",
        index=False,
    )

    pd.DataFrame({
        "attack_id": result.unreachable_techniques
    }).to_csv(
        output / f"{stem}_techniques_without_mapping.csv",
        index=False,
    )

    pd.DataFrame({
        "role_id": result.missing_cost_roles
    }).to_csv(
        output / f"{stem}_roles_without_cost.csv",
        index=False,
    )

    pd.DataFrame(result.excluded_roles).to_csv(
        output / f"{stem}_excluded_roles.csv",
        index=False,
    )

    role_ranking(
        problem,
        cast(CoverageMode, result.coverage_mode),
        current_roles,
    ).to_csv(
        output / f"{stem}_role_ranking.csv",
        index=False,
    )


def run_single(
    scenario_tasks_file: str | Path,
    task_role_file: str | Path,
    role_costs_file: str | Path,
    scenario_id: str,
    budget: float,
    algorithm: Algorithm,
    cost_scenario: CostScenario,
    coverage_mode: CoverageMode,
    task_alpha: float,
    output_dir: str | Path,
    current_roles: Iterable[str] | None = None,
    min_similarity: float | None = None,
    exclude_estimated_costs: bool = False,
    curve_budgets: Iterable[float] | None = None,
    target_coverages: Iterable[float] | None = None,
) -> OptimizationResult:
    """Execute one complete experiment and export every requested analysis."""
    scenario_tasks, task_role, role_costs = load_inputs(
        scenario_tasks_file,
        task_role_file,
        role_costs_file,
    )

    problem = prepare_problem(
        scenario_tasks,
        task_role,
        role_costs,
        scenario_id,
        cost_scenario,
        min_similarity=min_similarity,
        exclude_estimated_costs=exclude_estimated_costs,
    )

    optimizer = optimize_milp if algorithm == "milp" else optimize_greedy

    initial_role_ids = sorted({
        str(role_id).strip()
        for role_id in (current_roles or [])
        if str(role_id).strip()
    })
    initial_workforce_cost = sum(
        problem["role_cost"].get(role_id, 0.0)
        for role_id in initial_role_ids
    )
    if budget + 1e-9 < initial_workforce_cost:
        raise ValueError(
            "Available annual budget "
            f"(${budget:,.2f}) is below the initial workforce cost "
            f"(${initial_workforce_cost:,.2f})."
        )
    additional_budget = max(0.0, budget - initial_workforce_cost)

    result = optimizer(
        problem,
        additional_budget,
        coverage_mode,
        current_roles,
        task_alpha,
    )
    result.available_annual_budget = float(budget)
    result.initial_workforce_cost = float(initial_workforce_cost)
    result.total_spent_budget = float(
        initial_workforce_cost + result.spent_budget
    )

    export_result(
        result,
        problem,
        output_dir,
        current_roles,
        available_annual_budget=budget,
    )

    print("\nCandidate roles:", len(problem["role_tasks"]))
    print(sorted(problem["role_tasks"].keys()))

    print("\nSelected roles:")
    for role in result.selected_roles:
        print(
            role["role_id"],
            f"cost={role['annual_cost']:.0f}",
            f"new_tasks={role['new_tasks']}",
            f"new_techniques={role['new_techniques']}"
        )
        
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    stem = _safe_filename(
        f"{scenario_id}_{algorithm}_{cost_scenario}_{coverage_mode}"
    )

    if curve_budgets:
        total_curve_budgets = sorted({
            initial_workforce_cost,
            *(
                float(value) for value in curve_budgets
                if float(value) + 1e-9 >= initial_workforce_cost
            ),
        })
        additional_curve_budgets = [
            max(0.0, value - initial_workforce_cost)
            for value in total_curve_budgets
        ]
        curve = budget_curve(
            problem,
            additional_curve_budgets,
            algorithm,
            coverage_mode,
            current_roles,
            task_alpha,
        )
        curve["budget"] = curve["total_budget"]
        curve["budget_million"] = (
            curve["budget"] / 1_000_000
        )

        curve.drop(columns=["spent_budget"], errors="ignore").to_csv(
            output / f"{stem}_budget_curve.csv",
            index=False,
        )

        reference_points = budget_reference_points(curve)

        rows = []
        initial_role_ids = sorted({
            str(role_id).strip()
            for role_id in (current_roles or [])
            if str(role_id).strip()
        })
        initial_workforce_cost = sum(
            problem["role_cost"].get(role_id, 0.0)
            for role_id in initial_role_ids
        )

        for point_name, point in reference_points.items():
            if point is not None:
                rows.append({
                    "point": point_name,
                    "budget": point["budget"],
                    "additional_budget": max(
                        0.0, point["budget"] - initial_workforce_cost
                    ),
                    "total_budget": point["budget"],
                    "initial_workforce": ";".join(initial_role_ids),
                    "initial_workforce_cost": initial_workforce_cost,
                    "coverage_pct": point["coverage"],
                })
            else:
                rows.append({
                    "point": point_name,
                    "budget": math.nan,
                    "additional_budget": math.nan,
                    "total_budget": math.nan,
                    "initial_workforce": ";".join(initial_role_ids),
                    "initial_workforce_cost": initial_workforce_cost,
                    "coverage_pct": math.nan,
                })

        pd.DataFrame(rows).to_csv(
            output / f"{stem}_reference_points.csv",
            index=False,
        )

    if target_coverages:
        minimum_cost_table(
            problem,
            target_coverages,
            coverage_mode,
            current_roles,
            task_alpha,
        ).to_csv(
            output / f"{stem}_minimum_budget.csv",
            index=False,
        )

    return result


def _extract_experiment_metadata(path: Path) -> dict[str, str]:
    """
    Infer year, scenario variant and embedding model from common filenames.
    """
    name = path.stem.lower()

    year_match = re.search(r"(20\d{2})", name)
    variant_match = re.search(r"(?:^|_)([abc])(?:_|$)", name)

    known_models = [
        "attack_bert",
        "attack-bert",
        "minilm",
        "mpnet",
        "cysecbert",
    ]
    model = next(
        (candidate for candidate in known_models if candidate in name),
        "unknown",
    )

    return {
        "year": year_match.group(1) if year_match else "unknown",
        "variant": (
            variant_match.group(1).upper()
            if variant_match
            else "unknown"
        ),
        "model": model.replace("-", "_"),
    }


def run_batch(
    scenario_tasks_glob: str,
    task_role_glob: str,
    role_costs_file: str | Path,
    scenarios: Iterable[str],
    budgets: Iterable[float],
    algorithms: Iterable[Algorithm],
    cost_scenarios: Iterable[CostScenario],
    coverage_modes: Iterable[CoverageMode],
    task_alpha: float,
    output_dir: str | Path,
    current_roles: Iterable[str] | None = None,
) -> pd.DataFrame:
    """
    Execute matched experiments across years, models and A/B/C variants.

    Files are matched using inferred (year, variant, model) metadata.
    """
    task_files = sorted(Path().glob(scenario_tasks_glob))
    role_files = sorted(Path().glob(task_role_glob))
    requested_budgets = sorted({float(value) for value in budgets})
    requested_algorithms = list(dict.fromkeys(algorithms))

    if not task_files:
        raise ValueError(
            f"No scenario task files matched: {scenario_tasks_glob}"
        )
    if not role_files:
        raise ValueError(
            f"No task-role files matched: {task_role_glob}"
        )

    role_index: dict[tuple[str, str, str], Path] = {}
    for path in role_files:
        meta = _extract_experiment_metadata(path)
        role_index[
            (meta["year"], meta["variant"], meta["model"])
        ] = path

    rows: list[dict] = []

    for task_path in task_files:
        meta = _extract_experiment_metadata(task_path)
        key = (meta["year"], meta["variant"], meta["model"])
        role_path = role_index.get(key)

        if role_path is None:
            rows.append({
                **meta,
                "scenario_tasks_file": str(task_path),
                "task_role_file": "",
                "status": "missing_matching_role_file",
            })
            continue

        scenario_tasks, task_role, role_costs = load_inputs(
            task_path,
            role_path,
            role_costs_file,
        )

        available_scenarios = set(
            scenario_tasks["scenario_id"].dropna().unique()
        )

        for scenario in scenarios:
            if scenario not in available_scenarios:
                rows.append({
                    **meta,
                    "scenario": scenario,
                    "scenario_tasks_file": str(task_path),
                    "task_role_file": str(role_path),
                    "status": "scenario_not_found",
                })
                continue

            for cost_scenario in cost_scenarios:
                problem = prepare_problem(
                    scenario_tasks,
                    task_role,
                    role_costs,
                    scenario,
                    cost_scenario,
                )
                initial_role_ids = sorted({
                    str(role_id).strip()
                    for role_id in (current_roles or [])
                    if str(role_id).strip()
                })
                initial_workforce_cost = sum(
                    problem["role_cost"].get(role_id, 0.0)
                    for role_id in initial_role_ids
                )

                for algorithm in requested_algorithms:
                    optimizer = (
                        optimize_milp
                        if algorithm == "milp"
                        else optimize_greedy
                    )

                    for coverage_mode in coverage_modes:
                        evaluated_budgets = sorted({
                            initial_workforce_cost,
                            *requested_budgets,
                        })
                        for budget in evaluated_budgets:
                            try:
                                if budget + 1e-9 < initial_workforce_cost:
                                    rows.append({
                                        **meta,
                                        "scenario": scenario,
                                        "scenario_tasks_file": str(task_path),
                                        "task_role_file": str(role_path),
                                        "status": (
                                            "budget_below_initial_workforce_cost"
                                        ),
                                        "algorithm": algorithm,
                                        "cost_scenario": cost_scenario,
                                        "coverage_mode": coverage_mode,
                                        "budget": budget,
                                        "total_budget": budget,
                                        "initial_workforce": ";".join(
                                            initial_role_ids
                                        ),
                                        "initial_workforce_cost": (
                                            initial_workforce_cost
                                        ),
                                    })
                                    continue
                                additional_budget = max(
                                    0.0,
                                    budget - initial_workforce_cost,
                                )
                                result = optimizer(
                                    problem,
                                    additional_budget,
                                    coverage_mode,
                                    current_roles,
                                    task_alpha,
                                )
                                selected_role_ids = [
                                    str(role["role_id"])
                                    for role in result.selected_roles
                                ]
                                total_role_ids = sorted(
                                    set(initial_role_ids)
                                    | set(selected_role_ids)
                                )
                                if coverage_mode == "tasks":
                                    initial_objective = (
                                        result.initial_task_coverage_pct
                                    )
                                elif coverage_mode == "weighted_tasks":
                                    initial_objective = (
                                        result.initial_weighted_task_coverage_pct
                                    )
                                elif coverage_mode == "techniques":
                                    initial_objective = (
                                        result.initial_technique_coverage_pct
                                    )
                                else:
                                    initial_objective = (
                                        result.initial_hybrid_coverage_pct
                                    )
                                total_budget = budget
                                total_spent = (
                                    result.spent_budget
                                    + initial_workforce_cost
                                )
                                rows.append({
                                    **meta,
                                    "scenario": scenario,
                                    "scenario_tasks_file": str(task_path),
                                    "task_role_file": str(role_path),
                                    "status": "ok",
                                    "algorithm": algorithm,
                                    "cost_scenario": cost_scenario,
                                    "coverage_mode": coverage_mode,
                                    "budget": budget,
                                    "additional_budget": additional_budget,
                                    "additional_spent": result.spent_budget,
                                    "total_budget": total_budget,
                                    "total_spent": total_spent,
                                    "total_budget_utilization_pct": (
                                        100.0 * total_spent / total_budget
                                        if total_budget > 0
                                        else 0.0
                                    ),
                                    "initial_workforce": ";".join(
                                        initial_role_ids
                                    ),
                                    "initial_workforce_cost": (
                                        initial_workforce_cost
                                    ),
                                    "initial_role_count": len(
                                        initial_role_ids
                                    ),
                                    "initial_task_coverage_pct": (
                                        result.initial_task_coverage_pct
                                    ),
                                    "initial_weighted_task_coverage_pct": (
                                        result.initial_weighted_task_coverage_pct
                                    ),
                                    "initial_technique_coverage_pct": (
                                        result.initial_technique_coverage_pct
                                    ),
                                    "initial_hybrid_coverage_pct": (
                                        result.initial_hybrid_coverage_pct
                                    ),
                                    "initial_objective_coverage_pct": (
                                        initial_objective
                                    ),
                                    "roles_selected": len(
                                        result.selected_roles
                                    ),
                                    "additional_roles_selected": len(
                                        selected_role_ids
                                    ),
                                    "selected_role_ids": ";".join(
                                        selected_role_ids
                                    ),
                                    "total_roles": len(total_role_ids),
                                    "total_role_ids": ";".join(
                                        total_role_ids
                                    ),
                                    "task_coverage_pct": (
                                        result.final_task_coverage_pct
                                    ),
                                    "weighted_task_coverage_pct": (
                                        result.final_weighted_task_coverage_pct
                                    ),
                                    "technique_coverage_pct": (
                                        result.final_technique_coverage_pct
                                    ),
                                    "hybrid_coverage_pct": (
                                        result.final_hybrid_coverage_pct
                                    ),
                                    "objective_coverage_pct": (
                                        result.objective_coverage_pct
                                    ),
                                    "runtime_seconds": (
                                        result.runtime_seconds
                                    ),
                                })
                            except Exception as exc:
                                rows.append({
                                    **meta,
                                    "scenario": scenario,
                                    "scenario_tasks_file": str(task_path),
                                    "task_role_file": str(role_path),
                                    "status": "error",
                                    "error": str(exc),
                                    "algorithm": algorithm,
                                    "cost_scenario": cost_scenario,
                                    "coverage_mode": coverage_mode,
                                    "budget": budget,
                                })

    result_df = pd.DataFrame(rows)
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    for algorithm in requested_algorithms:
        algorithm_df = (
            result_df.loc[result_df["algorithm"] == algorithm]
            if "algorithm" in result_df.columns
            else result_df.iloc[0:0]
        )
        algorithm_df.to_csv(
            output / f"batch_experiments_{algorithm}.csv",
            index=False,
        )
    return result_df


def print_result(result: OptimizationResult) -> None:
    """Print a compact human-readable optimization summary."""
    print(f"Scenario: {result.scenario_name}")
    print(f"Algorithm: {result.algorithm}")
    total_budget = getattr(result, "available_annual_budget", None)
    initial_cost = getattr(result, "initial_workforce_cost", 0.0)
    total_spent = getattr(result, "total_spent_budget", None)
    if total_budget is not None:
        print(f"Available annual budget: ${total_budget:,.2f}")
        print(f"Initial workforce cost: ${initial_cost:,.2f}")
        print(f"Additional optimization budget: ${result.budget:,.2f}")
        print(f"Additional spent: ${result.spent_budget:,.2f}")
        print(f"Total spent: ${total_spent:,.2f}")
    else:
        print(f"Budget: ${result.budget:,.2f}")
        print(f"Spent: ${result.spent_budget:,.2f}")
    print(
        f"Additional-budget utilization: "
        f"{result.budget_utilization_pct:.2f}%"
    )
    print(f"Runtime: {result.runtime_seconds:.3f} s")
    print(
        f"Task coverage: "
        f"{result.final_task_coverage_pct:.2f}%"
    )
    print(
        f"Weighted task coverage: "
        f"{result.final_weighted_task_coverage_pct:.2f}%"
    )
    print(
        f"Technique coverage: "
        f"{result.final_technique_coverage_pct:.2f}%"
    )
    print(
        f"Hybrid coverage: "
        f"{result.final_hybrid_coverage_pct:.2f}%"
    )
    print(
        f"Objective coverage: "
        f"{result.objective_coverage_pct:.2f}%"
    )
    print(
        f"Maximum reachable task coverage: "
        f"{result.max_reachable_task_coverage_pct:.2f}%"
    )
    print(
        f"Maximum reachable weighted task coverage: "
        f"{result.max_reachable_weighted_task_coverage_pct:.2f}%"
    )
    print(
        f"Maximum reachable technique coverage: "
        f"{result.max_reachable_technique_coverage_pct:.2f}%"
    )
    print(f"Roles selected: {len(result.selected_roles)}")
    print(
        f"Covered tasks: "
        f"{result.covered_task_count}/{result.total_task_count}"
    )
    print(
        f"Covered techniques: "
        f"{result.covered_technique_count}/"
        f"{result.total_technique_count}"
    )
    print(
        f"Cost per covered task: "
        f"${result.cost_per_covered_task:,.2f}"
    )
    print(
        f"Cost per covered technique: "
        f"${result.cost_per_covered_technique:,.2f}"
    )
    print(
        f"Unmapped scenario tasks: "
        f"{len(result.missing_task_role_mappings)}"
    )
    print(
        f"Unreachable techniques: "
        f"{len(result.unreachable_techniques)}"
    )
    print(
        f"Roles without cost data: "
        f"{len(result.missing_cost_roles)}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Budget-constrained threat workforce coverage optimization"
        )
    )

    parser.add_argument("--scenario-tasks")
    parser.add_argument("--task-role")
    parser.add_argument("--role-costs", required=True)
    parser.add_argument("--scenario")
    parser.add_argument(
        "--budget",
        type=float,
        help="Total available annual budget, including current workforce",
    )
    parser.add_argument(
        "--algorithm",
        choices=["greedy", "milp"],
        default="milp",
    )
    parser.add_argument(
        "--cost-scenario",
        choices=["min", "avg", "max"],
        default="avg",
    )
    parser.add_argument(
        "--coverage-mode",
        choices=[
            "tasks",
            "weighted_tasks",
            "techniques",
            "hybrid",
        ],
        default="hybrid",
    )
    parser.add_argument("--task-alpha", type=float, default=0.7)
    parser.add_argument("--min-similarity", type=float)
    parser.add_argument(
        "--exclude-estimated-costs",
        action="store_true",
    )
    parser.add_argument(
        "--current-roles",
        default="",
        help="Comma-separated role IDs",
    )
    parser.add_argument(
        "--output-dir",
        default="coverage_results",
    )
    parser.add_argument(
        "--curve-budgets",
        default="",
        help=(
            "Comma-separated total annual budgets for the coverage frontier"
        ),
    )
    parser.add_argument(
        "--target-coverages",
        default="50,75,90,100",
        help="Comma-separated minimum-coverage targets",
    )
    

    parser.add_argument("--batch", action="store_true")
    parser.add_argument("--scenario-tasks-glob")
    parser.add_argument("--task-role-glob")
    parser.add_argument(
        "--batch-scenarios",
        default="RANSOMWARE",
    )
    parser.add_argument(
        "--batch-budgets",
        default="100000,200000,300000,400000,500000",
        help="Comma-separated total annual budgets, including current workforce",
    )
    parser.add_argument(
        "--batch-algorithms",
        default="greedy,milp",
    )
    parser.add_argument(
        "--batch-cost-scenarios",
        default="avg",
    )
    parser.add_argument(
        "--batch-coverage-modes",
        default="hybrid",
    )

    args = parser.parse_args()

    _validate_task_alpha(args.task_alpha)

    if args.batch:
        if not args.scenario_tasks_glob or not args.task_role_glob:
            parser.error(
                "--batch requires --scenario-tasks-glob "
                "and --task-role-glob"
            )

        run_batch(
            scenario_tasks_glob=args.scenario_tasks_glob,
            task_role_glob=args.task_role_glob,
            role_costs_file=args.role_costs,
            scenarios=_parse_csv_list(args.batch_scenarios),
            budgets=_parse_float_list(args.batch_budgets),
            algorithms=[
                cast(Algorithm, value)
                for value in _parse_csv_list(args.batch_algorithms)
            ],
            cost_scenarios=[
                cast(CostScenario, value)
                for value in _parse_csv_list(
                    args.batch_cost_scenarios
                )
            ],
            coverage_modes=[
                cast(CoverageMode, value)
                for value in _parse_csv_list(
                    args.batch_coverage_modes
                )
            ],
            task_alpha=args.task_alpha,
            output_dir=args.output_dir,
            current_roles=_parse_csv_list(args.current_roles),
        )
        return

    required = {
        "--scenario-tasks": args.scenario_tasks,
        "--task-role": args.task_role,
        "--scenario": args.scenario,
        "--budget": args.budget,
    }
    missing = [name for name, value in required.items() if value is None]
    if missing:
        parser.error(
            "Single-run mode requires: " + ", ".join(missing)
        )

    result = run_single(
        scenario_tasks_file=cast(str, args.scenario_tasks),
        task_role_file=cast(str, args.task_role),
        role_costs_file=args.role_costs,
        scenario_id=cast(str, args.scenario),
        budget=cast(float, args.budget),
        algorithm=cast(Algorithm, args.algorithm),
        cost_scenario=cast(CostScenario, args.cost_scenario),
        coverage_mode=cast(CoverageMode, args.coverage_mode),
        task_alpha=args.task_alpha,
        output_dir=args.output_dir,
        current_roles=_parse_csv_list(args.current_roles),
        min_similarity=args.min_similarity,
        exclude_estimated_costs=args.exclude_estimated_costs,
        curve_budgets=(
            _parse_float_list(args.curve_budgets)
            if args.curve_budgets
            else None
        ),
        target_coverages=(
            _parse_float_list(args.target_coverages)
            if args.target_coverages
            else None
        )
    )

    print_result(result)


if __name__ == "__main__":
    main()
