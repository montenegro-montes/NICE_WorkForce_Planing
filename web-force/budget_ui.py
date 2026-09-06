import streamlit as st
import frameworkNice
import pulp
import re
import pandas as pd

def render_budget(nodes):

    tasks_total = len([
        n for n in nodes.values()
        if n.type == "task"
    ])

    knowledge_total = len([
        n for n in nodes.values()
        if n.type == "knowledge"
    ])

    skills_total = len([
        n for n in nodes.values()
        if n.type == "skill"
    ])

    # Cobertura actual del equipo
    current_cov = frameworkNice.calculate_coverage(
        st.session_state.current_roles,
        nodes,
        st.session_state.adj
    )

    current_tasks = len(current_cov["tasks"])
    current_knowledge = len(current_cov["knowledge"])
    current_skills = len(current_cov["skills"])

    # Porcentaje de cobertura actual
    current_pct = (
        current_tasks / tasks_total +
        current_knowledge / knowledge_total +
        current_skills / skills_total
    ) / 3 * 100

   #st.markdown("Budget Planning")

    cost_model = st.session_state.cost_model

    st.session_state.setdefault("salary_scenario", "AVERAGE")
    st.session_state.setdefault("budget_algorithm", "Greedy ROWI")
    salary_scenario = st.session_state.salary_scenario

    current_team_cost = sum(
        cost_model.cost(role_id, salary_scenario)
        for role_id in st.session_state.current_roles
    )

    col1, col2, col3, col4, col5 = st.columns([1, 1.2, 1, 1, 1])

    with col1:
        minimum_budget = max(
            100_000,
            int((current_team_cost + 99_999) // 100_000 * 100_000),
        )
        maximum_budget = max(5_000_000, minimum_budget)
        budget_options = list(range(
            minimum_budget,
            maximum_budget + 1,
            100_000,
        ))
        saved_budget_value = st.session_state.get("budget", 1_500_000)
        if isinstance(saved_budget_value, str):
            saved_budget_value = (
                saved_budget_value
                .replace("$", "")
                .replace(",", "")
                .strip()
            )
        try:
            saved_budget = int(float(saved_budget_value))
        except (TypeError, ValueError):
            saved_budget = max(1_500_000, minimum_budget)
        st.session_state.budget = min(
            budget_options,
            key=lambda value: abs(value - saved_budget),
        )
        budget = st.selectbox(
            "Available annual budget",
            options=budget_options,
            format_func=lambda value: f"${value:,.0f}",
            key="budget",
        )

    with col2:
        budget_profile = st.radio(
                    "Budget profile",
                    ["BALANCED","SOC", "GRC"],
                    horizontal=True,
                    key="budget_profile"
        )

    with col3:
        remaining_budget = budget - current_team_cost

        st.markdown(f"""
                <div class="summary-box">
                    <div class="summary-item">
                        <span class="summary-label">Current team annual cost</span>
                        <span class="summary-value success">
                            ${current_team_cost:,.0f}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    with col4:

         st.markdown(f"""
                <div class="summary-box">
                    <div class="summary-item">
                        <span class="summary-label">Available budget</span>
                        <span class="summary-value success">
                            ${remaining_budget:,.0f}
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
    with col5:
        button_slot = st.empty()

    # Streamlit reruns the script after every interaction. Keep the active
    # profile weights available both when calculating a new plan and when
    # rendering a result stored in session state.
    weights = st.session_state.balanced_weights
    if budget_profile == "SOC":
        weights = st.session_state.soc_weights
    elif budget_profile == "GRC":
        weights = st.session_state.grc_weights

    with st.expander("Advanced optimization settings"):
        advanced_salary, advanced_algorithm = st.columns(2)
        salary_scenario = advanced_salary.selectbox(
            "Salary scenario",
            ["AVERAGE", "MINIMUM", "PERT", "MAXIMUM"],
            key="salary_scenario",
        )
        budget_algorithm = advanced_algorithm.selectbox(
            "Budget optimization algorithm",
            [
                "Greedy ROWI",
                "Greedy Marginal Coverage",
                "Binary Unique Coverage Optimization",
                "Full MILP Unique Coverage",
            ],
            key="budget_algorithm",
        )

    with button_slot.container():
        st.markdown('<div style="height: 1.55rem;"></div>', unsafe_allow_html=True)
        if st.button(
            "Calculate budget planning",
            type="primary",
            use_container_width=True,
        ):
            #normalize_weights = frameworkNice.normalize_weights(weights)
            #st.markdown(f"Using weights: {budget_profile} - Tasks: {weights['tasks']:.3f}, Skills: {weights['skills']:.3f}, Knowledge: {weights['knowledge']:.3f}")

            greedy_strategies = {
                "Greedy ROWI": "rowi",
                "Greedy Marginal Coverage": "coverage",
            }

            if budget_algorithm == "Binary Unique Coverage Optimization":

                result = optimize_team_by_budget_knapsack(
                    nodes=nodes,
                    adj=st.session_state.adj,
                    current_roles=st.session_state.current_roles,
                    cost_model=st.session_state.cost_model,
                    remaining_budget=remaining_budget,
                    salary_scenario=salary_scenario,
                    tasks_total=tasks_total,
                    knowledge_total=knowledge_total,
                    skills_total=skills_total,
                    weights=weights,
                    max_roles=None,
                )

            elif budget_algorithm == "Full MILP Unique Coverage":

                result = optimize_team_by_budget_full_milp_unique_coverage(
                    nodes=nodes,
                    adj=st.session_state.adj,
                    current_roles=st.session_state.current_roles,
                    cost_model=st.session_state.cost_model,
                    remaining_budget=remaining_budget,
                    salary_scenario=salary_scenario,
                    tasks_total=tasks_total,
                    knowledge_total=knowledge_total,
                    skills_total=skills_total,
                    weights=weights,
                    max_roles=None,
                )

            elif budget_algorithm in greedy_strategies:

                result = optimize_team_by_budget_greedy(
                    nodes=nodes,
                    adj=st.session_state.adj,
                    current_roles=st.session_state.current_roles,
                    cost_model=st.session_state.cost_model,
                    remaining_budget=remaining_budget,
                    salary_scenario=salary_scenario,
                    tasks_total=tasks_total,
                    knowledge_total=knowledge_total,
                    skills_total=skills_total,
                    weights=weights,
                    strategy=greedy_strategies[budget_algorithm],
                )

            else:
                raise ValueError(f"Unknown budget algorithm: {budget_algorithm}")


            st.session_state.budget_result = result

    if "budget_result" in st.session_state:

        result = st.session_state.budget_result

        st.markdown("""
            <div class="card-section">
                Proposed Workforce Additions
            </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
                <div class="summary-box threat-summary-card budget-proposal-summary">
                    <div class="summary-item">
                        <span class="summary-label">Additional roles</span>
                        <span class="summary-value success threat-summary-value-large">
                            {len(result["team"])}
                        </span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Additional annual cost</span>
                        <span class="summary-value success threat-summary-value-large">
                            ${result['total_cost']:,.0f}
                        </span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Unused optimization budget</span>
                        <span class="summary-value success threat-summary-value-large">
                            ${result['remaining_budget']:,.0f}
                        </span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Aggregate ROWI (pp/$100K)</span>
                        <span class="summary-value success threat-summary-value-large">
                            {result['rowi']:.2f}
                        </span>
                    </div>
                     <div class="summary-item">
                        <span class="summary-label">Coverage</span>
                        <span class="summary-value success threat-summary-value-large">
                            {result['initial_coverage_pct']:.1f}% → {result['final_coverage_pct']:.1f}%
                            ({result['total_gain']:.2f})
                        </span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
       
        for i, role in enumerate(result["team"], start=1):
            category        = role["category"]
            category_name   = frameworkNice.category_names.get(category, category)

            st.markdown(
                f"""
                <div class="recommendation-card">
                    <div class="rec-rank">{i}</div>
                    <div class="rec-content">
                        <div class="rec-title">{role["title"]}</div>
                        <div class="rec-meta">{role["role_id"]} | <span class="rec-badge">{category_name}</span> </div>
                        <div class="rec-metrics">  
                            <div class="rec-metric coverage">
                                <span>Coverage Evolution</span>
                                <div class="coverage-values">
                                    <span class="coverage-current">{role["before_coverage_pct"]:.1f}%</span>
                                    <span class="coverage-arrow">→</span>
                                    <span class="coverage-new">{role["after_coverage_pct"]:.1f}%</span>
                                </div>
                                <div class="coverage-gain">
                                    ▲ +{role["coverage_gain"]:.2f}%
                                </div>
                            </div>
                            <div class="rec-metric cost">
                                <span>Annual Employment Cost</span>
                                <strong> ${role["cost"]:,.0f}</strong>
                                Average salary
                            </div>   
                            <div class="rec-metric cost">
                                <span>Partial ROWI (pp/$100K)</span>
                                <strong>{role["rowi"]:.2f}</strong>
                            </div> 
                            <div class="rec-metric">
                                <span>Tasks Evolution</span>
                                <div class="metric-evolution">
                                    <span>{role["before_tasks"]}</span>
                                    <span class="metric-arrow">→</span>
                                    <span class="metric-new">{role["after_tasks"]}</span>
                                </div>
                                <div class="metric-gain">
                                    ▲ +{role["after_tasks"] - role["before_tasks"]}
                                </div>
                            </div>
                            <div class="rec-metric">
                                <span>Knowledge Evolution</span>
                                <div class="metric-evolution">
                                    <span>{role["before_knowledge"]}</span>
                                    <span class="metric-arrow">→</span>
                                    <span class="metric-new">{role["after_knowledge"]}</span>
                                </div>
                                <div class="metric-gain">
                                    ▲ +{role["after_knowledge"] - role["before_knowledge"]}
                                </div>
                            </div>
                            <div class="rec-metric">
                                <span>Skills Evolution</span>
                                <div class="metric-evolution">
                                    <span>{role["before_skills"]}</span>
                                    <span class="metric-arrow">→</span>
                                    <span class="metric-new">{role["after_skills"]}</span>
                                </div>
                                <div class="metric-gain">
                                    ▲ +{role["after_skills"] - role["before_skills"]}
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        st.markdown("""
                    <div class="card-section">
                        Workforce Information
                    </div>
                """, unsafe_allow_html=True)

        with st.container(key="budget-selected-roles-card"):
            st.markdown("""
                <div class="card-section-info">
                    Selected NICE Work Roles
                </div>
            """, unsafe_allow_html=True)

            selected_by_id = {
                str(role["role_id"]): (priority, role)
                for priority, role in enumerate(result["team"], start=1)
            }
            current_role_count = len(st.session_state.current_roles)
            additional_role_count = len(result["team"])
            total_role_count = current_role_count + additional_role_count
            additional_annual_cost = float(result["total_cost"])
            total_annual_cost = current_team_cost + additional_annual_cost

            st.markdown(f"""
                <div class="summary-box threat-summary-card budget-workforce-summary">
                    <div class="summary-item">
                        <span class="summary-label">Current roles</span>
                        <span class="summary-value success threat-summary-value-large">{current_role_count}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Additional roles</span>
                        <span class="summary-value success threat-summary-value-large">{additional_role_count}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Total roles</span>
                        <span class="summary-value success threat-summary-value-large">{total_role_count}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Current annual cost</span>
                        <span class="summary-value success threat-summary-value-large">${current_team_cost:,.0f}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Additional annual cost</span>
                        <span class="summary-value success threat-summary-value-large">${additional_annual_cost:,.0f}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Total annual cost</span>
                        <span class="summary-value success threat-summary-value-large">${total_annual_cost:,.0f}</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            workforce_rows = []

            for role_id in st.session_state.current_roles:
                node = nodes.get(role_id)
                cost_role = cost_model.roles.get(role_id)
                workforce_rows.append({
                    "Status": "Current",
                    "Rank": "—",
                    "Work Role": role_id,
                    "Work Role Name": getattr(node, "title", ""),
                    "Category": frameworkNice.category_names.get(
                        role_id.split("-")[0],
                        role_id.split("-")[0],
                    ),
                    "Mapped Job": getattr(cost_role, "mapped_job", ""),
                    "New Tasks": None,
                    "New Knowledge": None,
                    "New Skills": None,
                    "Annual Cost": cost_model.cost(role_id, salary_scenario),
                    "Marginal Gain": None,
                    "Partial ROWI": None,
                    "Cumulative Cost": None,
                    "Objective Coverage": None,
                })

            working_roles = list(st.session_state.current_roles)
            cumulative_cost = 0.0
            for role_id, (priority, role) in selected_by_id.items():
                cost_role = cost_model.roles.get(role_id)
                before_coverage = frameworkNice.calculate_coverage(
                    working_roles,
                    nodes,
                    st.session_state.adj,
                )
                after_coverage = frameworkNice.calculate_coverage(
                    working_roles + [role_id],
                    nodes,
                    st.session_state.adj,
                )
                before_pct = coverage_pct(
                    before_coverage,
                    tasks_total,
                    knowledge_total,
                    skills_total,
                    weights,
                )
                after_pct = coverage_pct(
                    after_coverage,
                    tasks_total,
                    knowledge_total,
                    skills_total,
                    weights,
                )
                marginal_gain = after_pct - before_pct
                annual_cost = float(role["cost"])
                cumulative_cost += annual_cost
                workforce_rows.append({
                    "Status": "Additional",
                    "Rank": str(priority),
                    "Work Role": role_id,
                    "Work Role Name": role.get("title", ""),
                    "Category": frameworkNice.category_names.get(
                        str(role.get("category", "")),
                        str(role.get("category", "")),
                    ),
                    "Mapped Job": getattr(cost_role, "mapped_job", ""),
                    "New Tasks": len(
                        after_coverage["tasks"] - before_coverage["tasks"]
                    ),
                    "New Knowledge": len(
                        after_coverage["knowledge"]
                        - before_coverage["knowledge"]
                    ),
                    "New Skills": len(
                        after_coverage["skills"] - before_coverage["skills"]
                    ),
                    "Annual Cost": annual_cost,
                    "Marginal Gain": marginal_gain,
                    "Partial ROWI": (
                        marginal_gain / annual_cost * 100_000
                        if annual_cost > 0
                        else 0.0
                    ),
                    "Cumulative Cost": cumulative_cost,
                    "Objective Coverage": after_pct,
                })
                working_roles.append(role_id)

            st.dataframe(
                pd.DataFrame(workforce_rows),
                width="stretch",
                height=225,
                hide_index=True,
                column_config={
                    "Status": "Status",
                    "Rank": "Rank",
                    "Work Role": "Work Role",
                    "Work Role Name": "Work Role Name",
                    "Category": "Category",
                    "Mapped Job": "Mapped Job",
                    "New Tasks": st.column_config.NumberColumn(
                        "New Tasks",
                        format="%d",
                    ),
                    "New Knowledge": st.column_config.NumberColumn(
                        "New Knowledge",
                        format="%d",
                    ),
                    "New Skills": st.column_config.NumberColumn(
                        "New Skills",
                        format="%d",
                    ),
                    "Annual Cost": st.column_config.NumberColumn(
                        "Annual Cost",
                        format="$%.0f",
                    ),
                    "Marginal Gain": st.column_config.NumberColumn(
                        "Marginal Gain",
                        format="%.2f pp",
                    ),
                    "Partial ROWI": st.column_config.NumberColumn(
                        "Partial ROWI (pp/$100K)",
                        format="%.2f pp",
                    ),
                    "Cumulative Cost": st.column_config.NumberColumn(
                        "Cumulative Cost",
                        format="$%.0f",
                    ),
                    "Objective Coverage": st.column_config.NumberColumn(
                        "Objective Coverage",
                        format="%.2f%%",
                    ),
                },
            )

        with st.container(key="budget-nice-tasks-card"):
            st.markdown("""
                <div class="card-section-info">
                    NICE Tasks
                </div>
            """, unsafe_allow_html=True)

            final_role_ids = list(st.session_state.current_roles) + [
                str(role["role_id"])
                for role in result["team"]
            ]
            final_coverage = frameworkNice.calculate_coverage(
                final_role_ids,
                nodes,
                st.session_state.adj,
            )
            all_task_ids = {
                str(node_id)
                for node_id, node in nodes.items()
                if node.type == "task"
            }
            covered_task_ids = all_task_ids & set(final_coverage["tasks"])
            uncovered_task_ids = all_task_ids - covered_task_ids
            task_coverage_pct = (
                len(covered_task_ids) / len(all_task_ids) * 100.0
                if all_task_ids
                else 0.0
            )

            st.markdown(f"""
                <div class="summary-box threat-summary-card budget-nice-summary">
                    <div class="summary-item">
                        <span class="summary-label">Covered NICE Tasks</span>
                        <span class="summary-value success threat-summary-value-large">{len(covered_task_ids)}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Uncovered NICE Tasks</span>
                        <span class="summary-value warning threat-summary-value-large">{len(uncovered_task_ids)}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Task Coverage</span>
                        <span class="summary-value success threat-summary-value-large">{task_coverage_pct:.1f}%</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)

            def task_table(task_ids):
                rows = [
                    {
                        "Task ID": task_id,
                        "NICE Task": (
                            nodes[task_id].text
                            or nodes[task_id].title
                        ),
                    }
                    for task_id in sorted(task_ids)
                ]
                return pd.DataFrame(
                    rows,
                    columns=["Task ID", "NICE Task"],
                )

            covered_column, uncovered_column = st.columns(2)
            with covered_column:
                st.markdown("**Covered NICE Tasks**")
                st.dataframe(
                    task_table(covered_task_ids),
                    width="stretch",
                    height=360,
                    hide_index=True,
                )

            with uncovered_column:
                st.markdown("**Uncovered NICE Tasks**")
                st.dataframe(
                    task_table(uncovered_task_ids),
                    width="stretch",
                    height=360,
                    hide_index=True,
                )



######################################
#
#
######################################

def coverage_pct(
    cov,
    tasks_total,
    knowledge_total,
    skills_total,
    weights=None,
):
    """Weighted objective coverage in percentage points."""
    return frameworkNice.calculate_weighted_coverage_pct(
        cov,
        total_tasks=tasks_total,
        total_skills=skills_total,
        total_knowledge=knowledge_total,
        weights=weights or {"tasks": 1, "skills": 1, "knowledge": 1},
    )

######################################
#
#
######################################

def build_budget_candidates(
    nodes,
    adj,
    current_roles,
    cost_model,
    remaining_budget,
    salary_scenario,
    tasks_total,
    knowledge_total,
    skills_total,
    weights,
):

    current_cov = frameworkNice.calculate_coverage(
        current_roles,
        nodes,
        adj
    )

    current_pct = coverage_pct(
        current_cov,
        tasks_total,
        knowledge_total,
        skills_total,
        weights,
    )

    candidates = []

    for role_id, node in nodes.items():

        if node.type != "work_role":
            continue

        if role_id in current_roles:
            continue

        role_cost = cost_model.cost(role_id, salary_scenario)

        if role_cost > remaining_budget:
            continue

        target_roles = current_roles + [role_id]

        target_cov = frameworkNice.calculate_coverage(
            target_roles,
            nodes,
            adj
        )

        target_pct = coverage_pct(
            target_cov,
            tasks_total,
            knowledge_total,
            skills_total,
            weights,
        )

        coverage_gain = target_pct - current_pct

        if coverage_gain <= 0:
            continue

        rowi = coverage_gain / role_cost * 100000 if role_cost > 0 else 0

        candidates.append({
            "role_id": role_id,
            "title": node.title,
            "category": role_id.split("-")[0],
            "cost": role_cost,
            "coverage_gain": coverage_gain,
            "rowi": rowi,

            "before_coverage_pct": current_pct,
            "after_coverage_pct": target_pct,

            "before_tasks": len(current_cov["tasks"]),
            "after_tasks": len(target_cov["tasks"]),

            "before_knowledge": len(current_cov["knowledge"]),
            "after_knowledge": len(target_cov["knowledge"]),

            "before_skills": len(current_cov["skills"]),
            "after_skills": len(target_cov["skills"]),
        })

    return candidates


############################
#
############################

def optimize_team_by_budget_greedy(
    nodes,
    adj,
    current_roles,
    cost_model,
    remaining_budget,
    salary_scenario,
    tasks_total,
    knowledge_total,
    skills_total,
    weights,
    strategy="rowi",
):

    selected = []
    working_roles = list(current_roles)
    budget_left = remaining_budget
    total_cost = 0

    initial_cov = frameworkNice.calculate_coverage(
        working_roles,
        nodes,
        adj
    )

    initial_pct = coverage_pct(
        initial_cov,
        tasks_total,
        knowledge_total,
        skills_total,
        weights,
    )

    while True:

        candidates = build_budget_candidates(
            nodes=nodes,
            adj=adj,
            current_roles=working_roles,
            cost_model=cost_model,
            remaining_budget=budget_left,
            salary_scenario=salary_scenario,
            tasks_total=tasks_total,
            knowledge_total=knowledge_total,
            skills_total=skills_total,
            weights=weights,
        )

        if not candidates:
            break

        if strategy == "rowi":
            best = max(candidates, key=lambda x: x["rowi"])
        elif strategy == "coverage":
            best = max(candidates, key=lambda x: x["coverage_gain"])

        else:
            raise ValueError("Unknown greedy strategy")

        selected.append(best)
        working_roles.append(best["role_id"])
        budget_left -= best["cost"]
        total_cost += best["cost"]

    final_cov = frameworkNice.calculate_coverage(
        working_roles,
        nodes,
        adj
    )

    final_pct = coverage_pct(
        final_cov,
        tasks_total,
        knowledge_total,
        skills_total,
        weights,
    )

    total_gain = final_pct - initial_pct
    rowi = total_gain / total_cost * 100000 if total_cost > 0 else 0

    return {
        "team": selected,
        "total_cost": total_cost,
        "remaining_budget": budget_left,
        "total_gain": total_gain,
        "rowi": rowi,
        "initial_coverage_pct": initial_pct,
        "final_coverage_pct": final_pct,
        "final_tasks": len(final_cov["tasks"]),
        "final_knowledge": len(final_cov["knowledge"]),
        "final_skills": len(final_cov["skills"]),
        "algorithm": strategy,
    }

############################
#
############################


def optimize_team_by_budget_knapsack(
    nodes,
    adj,
    current_roles,
    cost_model,
    remaining_budget,
    salary_scenario,
    tasks_total,
    knowledge_total,
    skills_total,
    weights,
    max_roles=None,
):
    # The former knapsack summed independent role scores and could count the
    # same capability more than once. Use the unique-coverage MILP instead.
    result = optimize_team_by_budget_full_milp_unique_coverage(
        nodes=nodes,
        adj=adj,
        current_roles=current_roles,
        cost_model=cost_model,
        remaining_budget=remaining_budget,
        salary_scenario=salary_scenario,
        tasks_total=tasks_total,
        knowledge_total=knowledge_total,
        skills_total=skills_total,
        weights=weights,
        max_roles=max_roles,
    )
    result["algorithm"] = "Binary Unique Coverage Optimization"
    return result

#############################
#
#############################

def optimize_team_by_budget_full_milp_unique_coverage(
    nodes,
    adj,
    current_roles,
    cost_model,
    remaining_budget,
    salary_scenario,
    tasks_total,
    knowledge_total,
    skills_total,
    weights,
    max_roles=None,
):

    def safe_var_name(prefix, value):
        return prefix + "_" + re.sub(r"[^a-zA-Z0-9_]", "_", value)

    w = frameworkNice.normalize_weights(weights)

    initial_cov = frameworkNice.calculate_coverage(
        current_roles,
        nodes,
        adj
    )

    initial_pct = coverage_pct(
        initial_cov,
        tasks_total,
        knowledge_total,
        skills_total,
        weights,
    )

    current_categories = set(
        role_id.split("-")[0]
        for role_id in current_roles
    )

    candidate_roles = []

    role_cost = {}
    role_cov = {}

    for role_id, node in nodes.items():

        if node.type != "work_role":
            continue

        if role_id in current_roles:
            continue

        cost = cost_model.cost(role_id, salary_scenario)

        if cost > remaining_budget:
            continue

        cov = frameworkNice.calculate_coverage(
            [role_id],
            nodes,
            adj
        )

        new_tasks = cov["tasks"] - initial_cov["tasks"]
        new_skills = cov["skills"] - initial_cov["skills"]
        new_knowledge = cov["knowledge"] - initial_cov["knowledge"]

        if not new_tasks and not new_skills and not new_knowledge:
            continue

        candidate_roles.append(role_id)

        role_cost[role_id] = cost

        role_cov[role_id] = {
            "tasks": new_tasks,
            "skills": new_skills,
            "knowledge": new_knowledge,
            "all": new_tasks | new_skills | new_knowledge,
        }

    if not candidate_roles:
        return {
            "team": [],
            "total_cost": 0,
            "remaining_budget": remaining_budget,
            "total_gain": 0,
            "rowi": 0,
            "initial_coverage_pct": initial_pct,
            "final_coverage_pct": initial_pct,
            "final_tasks": len(initial_cov["tasks"]),
            "final_knowledge": len(initial_cov["knowledge"]),
            "final_skills": len(initial_cov["skills"]),
            "algorithm": "Full MILP Unique Coverage",
        }

    uncovered_elements = set()
    element_weight = {}

    for role_id in candidate_roles:

        for task_id in role_cov[role_id]["tasks"]:
            uncovered_elements.add(task_id)
            element_weight[task_id] = (
                w["tasks"] / tasks_total if tasks_total else 0
            )

        for skill_id in role_cov[role_id]["skills"]:
            uncovered_elements.add(skill_id)
            element_weight[skill_id] = (
                w["skills"] / skills_total if skills_total else 0
            )

        for knowledge_id in role_cov[role_id]["knowledge"]:
            uncovered_elements.add(knowledge_id)
            element_weight[knowledge_id] = (
                w["knowledge"] / knowledge_total if knowledge_total else 0
            )

    candidate_categories = sorted({
        role_id.split("-")[0]
        for role_id in candidate_roles
        if role_id.split("-")[0] not in current_categories
    })

    prob = pulp.LpProblem(
        "Budget_Full_MILP_Unique_Coverage",
        pulp.LpMaximize
    )

    x = {
        role_id: pulp.LpVariable(
            safe_var_name("x", role_id),
            cat="Binary"
        )
        for role_id in candidate_roles
    }

    y = {
        element_id: pulp.LpVariable(
            safe_var_name("y", element_id),
            cat="Binary"
        )
        for element_id in uncovered_elements
    }

    z_cat = {
        category: pulp.LpVariable(
            safe_var_name("z_cat", category),
            cat="Binary"
        )
        for category in candidate_categories
    }

    coverage_objective = pulp.lpSum(
        element_weight[element_id] * y[element_id]
        for element_id in uncovered_elements
    )

    # Primary budget objective: maximize unique weighted capability coverage.
    # Category variables remain linked below for reporting, but do not trade
    # coverage away through an arbitrary weighted heuristic.
    prob += coverage_objective

    prob += pulp.lpSum(
        role_cost[role_id] * x[role_id]
        for role_id in candidate_roles
    ) <= remaining_budget

    if max_roles is not None:
        prob += pulp.lpSum(
            x[role_id]
            for role_id in candidate_roles
        ) <= max_roles

    for element_id in uncovered_elements:

        covering_roles = [
            role_id
            for role_id in candidate_roles
            if element_id in role_cov[role_id]["all"]
        ]

        prob += y[element_id] <= pulp.lpSum(
            x[role_id]
            for role_id in covering_roles
        )

        for role_id in covering_roles:
            prob += y[element_id] >= x[role_id]

    for category in z_cat:

        roles_in_category = [
            role_id
            for role_id in candidate_roles
            if role_id.split("-")[0] == category
        ]

        prob += z_cat[category] <= pulp.lpSum(
            x[role_id]
            for role_id in roles_in_category
        )

        for role_id in roles_in_category:
            prob += z_cat[category] >= x[role_id]

    prob.solve(
        pulp.PULP_CBC_CMD(msg=False)
    )

    # Lexicographic tie-break: preserve maximum coverage and then minimize
    # annual cost. This prevents redundant zero-gain roles from being selected.
    optimal_coverage = pulp.value(coverage_objective) or 0.0
    prob += coverage_objective >= optimal_coverage - 1e-9
    prob.sense = pulp.LpMinimize
    prob.setObjective(pulp.lpSum(
        role_cost[role_id] * x[role_id]
        for role_id in candidate_roles
    ))
    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    selected_role_ids = [
        role_id
        for role_id in candidate_roles
        if pulp.value(x[role_id]) == 1
    ]

    selected = []
    working_roles = list(current_roles)

    while selected_role_ids:

        current_cov = frameworkNice.calculate_coverage(
            working_roles,
            nodes,
            adj
        )

        current_pct = coverage_pct(
            current_cov,
            tasks_total,
            knowledge_total,
            skills_total,
            weights,
        )

        best_role = None
        best_score = -1
        best_data = None

        for role_id in selected_role_ids:

            target_roles = working_roles + [role_id]

            target_cov = frameworkNice.calculate_coverage(
                target_roles,
                nodes,
                adj
            )

            target_pct = coverage_pct(
                target_cov,
                tasks_total,
                knowledge_total,
                skills_total,
                weights,
            )

            coverage_gain = target_pct - current_pct

            tasks_gain = len(target_cov["tasks"]) - len(current_cov["tasks"])
            knowledge_gain = len(target_cov["knowledge"]) - len(current_cov["knowledge"])
            skills_gain = len(target_cov["skills"]) - len(current_cov["skills"])

            # Si ya no aporta nada incremental, no lo añadimos a la secuencia visual
            if tasks_gain <= 0 and knowledge_gain <= 0 and skills_gain <= 0:
                continue

            if coverage_gain > best_score:
                best_score = coverage_gain
                best_role = role_id
                best_data = {
                    "target_cov": target_cov,
                    "target_pct": target_pct,
                    "coverage_gain": coverage_gain,
                }

        # Protección importante: si ningún rol aporta ya mejora incremental, salimos
        if best_role is None or best_data is None:
            break

        node = nodes[best_role]
        cost = role_cost[best_role]

        selected.append({
            "role_id": best_role,
            "title": node.title,
            "category": best_role.split("-")[0],
            "cost": cost,
            "coverage_gain": best_data["coverage_gain"],
            "rowi": best_data["coverage_gain"] / cost * 100000 if cost else 0,

            "before_coverage_pct": current_pct,
            "after_coverage_pct": best_data["target_pct"],

            "before_tasks": len(current_cov["tasks"]),
            "after_tasks": len(best_data["target_cov"]["tasks"]),

            "before_knowledge": len(current_cov["knowledge"]),
            "after_knowledge": len(best_data["target_cov"]["knowledge"]),

            "before_skills": len(current_cov["skills"]),
            "after_skills": len(best_data["target_cov"]["skills"]),
        })

        working_roles.append(best_role)
        selected_role_ids.remove(best_role)

    final_cov = frameworkNice.calculate_coverage(
        working_roles,
        nodes,
        adj
    )

    final_pct = coverage_pct(
        final_cov,
        tasks_total,
        knowledge_total,
        skills_total,
        weights,
    )

    total_cost = sum(
        role["cost"]
        for role in selected
    )

    total_gain = final_pct - initial_pct

    rowi = total_gain / total_cost * 100000 if total_cost > 0 else 0

    return {
        "team": selected,
        "total_cost": total_cost,
        "remaining_budget": remaining_budget - total_cost,
        "total_gain": total_gain,
        "rowi": rowi,
        "initial_coverage_pct": initial_pct,
        "final_coverage_pct": final_pct,
        "final_tasks": len(final_cov["tasks"]),
        "final_knowledge": len(final_cov["knowledge"]),
        "final_skills": len(final_cov["skills"]),
        "algorithm": "Full MILP Unique Coverage",
    }
