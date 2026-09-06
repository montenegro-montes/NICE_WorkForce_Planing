import re

import streamlit as st
from frameworkNice import Node, role_coverage
import frameworkNice
from typing import Dict, List, Set
import pulp

def render_recommendations(nodes):

    #st.markdown("SOC / GRC based on coverage improvement")

    col1, col2, col3, col4 = st.columns([0.5,0.5,0.5,1 ], gap="large")

    with col1:
        top_n = st.slider(
            "Number of recommendations",
            min_value=3,
            max_value=10,
            value=5
        )
        
    with col2:
        recommendation_mode = st.radio(
            "Recommendation profile",
            ["BALANCED","SOC", "GRC"],
            horizontal=True,
            key="recommendation_mode"
        )
    
    with col3:
        recommendation_algorithm = st.selectbox(
            "Recommendation algorithm",
            [
                "Greedy",
                "Binary Optimization",
                "Full Binary Optimization (MILP)",
            ],
            key="recommendation_algorithm",
        )    
     
    with col4:    
        st.markdown(
            f"""
            <div style="
            display:flex;justify-content:space-between;
            margin-top:+24px;
            color:#9aa3b8;">
            <span></span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        if "calculate_recommendation" not in st.session_state:
            st.session_state.calculate_recommendation = False

        calculate_clicked = st.button("Calculate recommendation", type="primary")

    with st.expander("Advanced optimization settings"):
        st.caption(
            "Recommendation score coefficients. Values are normalized by their "
            "sum so that the final score remains between 0 and 100."
        )
        beta_col_f, beta_col_n, beta_col_g, beta_col_b = st.columns(4)
        with beta_col_f:
            beta_f = st.number_input(
                "F · Marginal coverage",
                min_value=0.0,
                value=0.50,
                step=0.05,
                format="%.2f",
                key="recommendation_beta_f",
            )
        with beta_col_n:
            beta_n = st.number_input(
                "N · Novel capabilities",
                min_value=0.0,
                value=0.25,
                step=0.05,
                format="%.2f",
                key="recommendation_beta_n",
            )
        with beta_col_g:
            beta_g = st.number_input(
                "G · New NICE category",
                min_value=0.0,
                value=0.20,
                step=0.05,
                format="%.2f",
                key="recommendation_beta_g",
            )
        with beta_col_b:
            beta_b = st.number_input(
                "B · Capability balance",
                min_value=0.0,
                value=0.05,
                step=0.05,
                format="%.2f",
                key="recommendation_beta_b",
            )

        score_weights = {
            "F": float(beta_f),
            "N": float(beta_n),
            "G": float(beta_g),
            "B": float(beta_b),
        }
        coefficient_total = sum(score_weights.values())
        st.caption(f"Coefficient sum: {coefficient_total:.2f}")

    if coefficient_total <= 0:
        st.error("At least one recommendation score coefficient must be positive.")

    previous_config = st.session_state.get("recommendation_config", {})
    score_weights_changed = (
        "recommendations" in st.session_state
        and previous_config.get("score_weights") != score_weights
    )
    if calculate_clicked or score_weights_changed:
        st.session_state.calculate_recommendation = coefficient_total > 0
            
    if recommendation_mode == "BALANCED":
        weights = st.session_state.balanced_weights
    elif recommendation_mode == "SOC":
        weights = st.session_state.soc_weights
    else:
        weights = st.session_state.grc_weights
    
    if st.session_state.calculate_recommendation:

        if recommendation_algorithm == "Greedy":
            st.session_state.recommendations = recommend_greedy(
                elements_nodes=nodes,
                adj=st.session_state.adj,
                focus=st.session_state.recommendation_mode,
                weights=weights,
                current_roles=st.session_state.current_roles,
                top_n=top_n,
                depth=5,
                score_weights=score_weights,
            )

        elif recommendation_algorithm == "Binary Optimization":
            st.session_state.recommendations = recommend_binary_optimization(
                elements_nodes=nodes,
                adj=st.session_state.adj,
                focus=st.session_state.recommendation_mode,
                weights=weights,
                current_roles=st.session_state.current_roles,
                top_n=top_n,
                depth=5,
                score_weights=score_weights,
            )
        else: 
            st.session_state.recommendations = recommend_binary_optimization_full(
                elements_nodes=nodes,
                adj=st.session_state.adj,
                focus=st.session_state.recommendation_mode,
                weights=weights,
                current_roles=st.session_state.current_roles,
                top_n=top_n,
                depth=5,
                score_weights=score_weights,
            )

        st.session_state.recommendation_config = {
            "top_n": top_n,
            "profile": recommendation_mode,
            "algorithm": recommendation_algorithm,
            "score_weights": score_weights,
        }    

        st.session_state.calculate_recommendation = False

    if "recommendations" in st.session_state and st.session_state.recommendations:
        
        cfg = st.session_state.recommendation_config

        st.markdown(
            f"""
            <div style="
            display:flex;justify-content:space-between;
            margin-top:+40px;
            color:#9aa3b8;">
            <span></span>
            </div>

            <div class="card-section-info">
                Top <strong>{cfg["top_n"]}</strong> recommendations · 
                Profile: <strong>{cfg["profile"]}</strong> · 
                Algorithm: <strong>{cfg["algorithm"]}</strong>
                · Score weights: <strong>F={cfg["score_weights"]["F"]:.2f},
                N={cfg["score_weights"]["N"]:.2f},
                G={cfg["score_weights"]["G"]:.2f},
                B={cfg["score_weights"]["B"]:.2f}</strong>
            </div>
            """,
            unsafe_allow_html=True,
        )

        current_cov      = frameworkNice.calculate_coverage(st.session_state.current_roles, nodes, st.session_state.adj)
        tasks_total      = len([n for n in nodes.values() if n.type == "task"])
        knowledge_total  = len([n for n in nodes.values() if n.type == "knowledge"])
        skills_total     = len([n for n in nodes.values() if n.type == "skill"])

        current_tasks       = len(current_cov["tasks"]) 
        current_knowledge   = len(current_cov["knowledge"])
        current_skills      = len(current_cov["skills"])  
        
        current_pct = (
            current_tasks      / tasks_total +
            current_knowledge   / knowledge_total +
            current_skills      / skills_total
        ) / 3 * 100

        cost_model = st.session_state.cost_model 
        
        for i, rec in enumerate(st.session_state.recommendations, start=1):

            category        = rec["category"]
            category_name   = frameworkNice.category_names.get(category, category)

            role_id = rec.get("role_id") or rec.get("id") or rec.get("role") or rec.get("target_role")

            if role_id is None:
                st.error(f"Recommendation without role id: {rec}")
                continue

            new_cov         = frameworkNice.calculate_coverage(    st.session_state.current_roles + [role_id], nodes, st.session_state.adj)

            new_tasks     =  len(new_cov["tasks"]) 
            new_knowledge =  len(new_cov["knowledge"])
            new_skills    =  len(new_cov["skills"])  
            
            tasks_gain_ui     = new_tasks - current_tasks
            knowledge_gain_ui = new_knowledge - current_knowledge
            skills_gain_ui    = new_skills - current_skills

            new_pct = (
                new_tasks       / tasks_total +
                new_knowledge   / knowledge_total +
                new_skills      / skills_total
            ) / 3 * 100

            coverage_gain   = new_pct - current_pct

            role_cost = cost_model.cost(role_id)
            role_cost_fmt = f"${role_cost:,.0f}"

            st.markdown(
                f"""
                <div class="recommendation-card">
                    <div class="rec-rank">{i}</div>
                    <div class="rec-content">
                        <div class="rec-title">{rec["title"]}</div>
                        <div class="rec-meta">{rec["role"]} | <span class="rec-badge">{category_name}</span> </div>
                        <div class="rec-metrics">
                            <div class="rec-metric coverage">
                                <span>Coverage Evolution</span>
                                <div class="coverage-values">
                                    <span class="coverage-current">{current_pct:.1f}%</span>
                                    <span class="coverage-arrow">→</span>
                                    <span class="coverage-new">{new_pct:.1f}%</span>
                                </div>
                                <div class="coverage-gain">
                                    ▲ +{coverage_gain:.2f}%
                                </div>
                            </div>
                            <div class="rec-metric cost">
                                <span>Annual Employment Cost</span>
                                <strong>{role_cost_fmt}</strong>
                                Average salary
                            </div>                            
                            <div class="rec-metric">
                                <span>Tasks Evolution</span>
                                <div class="metric-evolution">
                                    <span>{current_tasks}</span>
                                    <span class="metric-arrow">→</span>
                                    <span class="metric-new">{new_tasks}</span>
                                </div>
                                <div class="metric-gain">▲ +{tasks_gain_ui}</div>
                            </div>
                            <div class="rec-metric">
                                    <span>Knowledge Evolution</span>
                                    <div class="metric-evolution">
                                        <span>{current_knowledge}</span>
                                        <span class="metric-arrow">→</span>
                                        <span class="metric-new">{new_knowledge}</span>
                                    </div>
                                    <div class="metric-gain">▲ +{knowledge_gain_ui}</div>
                            </div>
                            <div class="rec-metric">
                                    <span>Skills Evolution</span>
                                    <div class="metric-evolution">
                                        <span>{current_skills}</span>
                                        <span class="metric-arrow">→</span>
                                        <span class="metric-new">{new_skills}</span>
                                    </div>
                                    <div class="metric-gain">▲ +{skills_gain_ui}</div>
                            </div>
                            <div class="rec-metric score">
                                <span>Score</span>
                                <strong>{rec["score"]:.2f}</strong>
                                <div class="score-bar">
                                    <div class="score-fill" style="width:{rec["score"]}%;"></div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )

#######################################
# Greedy Recommendation evaluates candidate NICE work roles iteratively. At each step, 
# it selects the role that provides the highest adaptive score based on the current 
# organizational coverage. After each selection, the coverage is updated so that subsequent 
# recommendations prioritize complementary capabilities rather than redundant ones. 
# This strategy is computationally efficient and naturally adapts to the organization's 
# evolving workforce profile, although it does not guarantee a globally optimal solution.

def recommend_greedy(
    elements_nodes: Dict[str, Node],
    adj: Dict[str, Set[str]],
    focus: str,
    weights: Dict[str, float],
    current_roles: List[str] | None = None,
    top_n: int = 8,
    depth: int = 5,
    score_weights: Dict[str, float] | None = None,
) -> List[Dict]:

    normalize_weights = frameworkNice.normalize_weights(weights)
    current_roles = current_roles or []
    current_roles_set = set(current_roles)

    focus = focus.upper()

    roles = [
        nid for nid, n in elements_nodes.items()
        if n.type == "work_role"
        and re.match(r"^[A-Z]{2}-WRL-\d{3}$", nid)
    ]

    if focus == "SOC":
        want_role_prefix = {"PD", "IN", "IO"}

    elif focus == "GRC":
        want_role_prefix = {"OG", "DD"}

    elif focus == "BALANCED":
        want_role_prefix = {"PD", "IN", "IO", "OG", "DD"}

    else:
        raise ValueError("focus must be SOC, GRC or BALANCED")

    total_tasks = len([n for n in elements_nodes.values() if n.type == "task"])
    total_skills = len([n for n in elements_nodes.values() if n.type == "skill"])
    total_knowledge = len([n for n in elements_nodes.values() if n.type == "knowledge"])

    current_categories = set(r.split("-")[0] for r in current_roles)

    covered_tasks: Set[str] = set()
    covered_skills: Set[str] = set()
    covered_knowledge: Set[str] = set()

    for r in current_roles:
        cov = role_coverage(r, adj, elements_nodes, depth=depth)

        covered_tasks |= cov["tasks"]
        covered_skills |= cov["skills"]
        covered_knowledge |= cov["knowledge"]

    role_cov: Dict[str, Dict[str, Set[str]]] = {}

    for r in roles:
        if r in current_roles_set:
            continue

        pref = r.split("-")[0]

        if pref not in want_role_prefix:
            continue

        role_cov[r] = role_coverage(r, adj, elements_nodes, depth=depth)

    chosen: List[Dict] = []
    chosen_roles: Set[str] = set()

    for _ in range(top_n):

        best_role = None
        best_score = -1
        best_gain = None

        for r, cov in role_cov.items():

            if r in chosen_roles:
                continue

            tasks_gain_set = cov["tasks"] - covered_tasks
            skills_gain_set = cov["skills"] - covered_skills
            knowledge_gain_set = cov["knowledge"] - covered_knowledge

            tasks_gain = len(tasks_gain_set)
            skills_gain = len(skills_gain_set)
            knowledge_gain = len(knowledge_gain_set)

            category = r.split("-")[0]

            metrics = frameworkNice.adaptive_role_score(
                cov=cov,
                tasks_gain=tasks_gain,
                skills_gain=skills_gain,
                knowledge_gain=knowledge_gain,
                covered_tasks=covered_tasks,
                covered_skills=covered_skills,
                covered_knowledge=covered_knowledge,
                total_tasks=total_tasks,
                total_skills=total_skills,
                total_knowledge=total_knowledge,
                category=category,
                current_categories=current_categories,
                preferred_categories=want_role_prefix,
                weights=normalize_weights,
                score_weights=score_weights,
            )

            score = metrics["score"]
          

            if score > best_score:
                best_score = score
                best_role = r
                best_gain = {
                    **metrics,
                    "tasks_gain_set": tasks_gain_set,
                    "skills_gain_set": skills_gain_set,
                    "knowledge_gain_set": knowledge_gain_set,
                }
             

        if best_role is None or best_gain is None:
            break

        # Si no quieres recomendar roles con ganancia 0, deja este bloque.
        if best_score <= 0:
            break


        chosen.append({
            "role": best_role,
            "title": elements_nodes[best_role].title,
            "category": best_role.split("-")[0],
            "score": round(best_score, 2),

            "tasks_gain": best_gain["tasks_gain"],
            "skills_gain": best_gain["skills_gain"],
            "knowledge_gain": best_gain["knowledge_gain"],

            "coverage_gain": round(best_gain["coverage_gain"], 2),
            "novelty": round(best_gain["novelty"], 2),
            "redundancy": round(best_gain["redundancy"], 2),
            "category_gap": best_gain["category_gap"],
            "profile_alignment": best_gain["profile_alignment"],
            "balance": round(best_gain["balance"], 2)
        })

        chosen_roles.add(best_role)

        covered_tasks       |= best_gain["tasks_gain_set"]
        covered_skills      |= best_gain["skills_gain_set"]
        covered_knowledge   |= best_gain["knowledge_gain_set"]

        current_categories.add(best_role.split("-")[0])

    return chosen

########################################
# Binary Optimization formulates the recommendation problem as a binary integer optimization model. 
# Each candidate role is associated with an adaptive score that combines coverage improvement, 
# novelty, category expansion, profile alignment, balance with the configured capability weights, 
# and redundancy penalties. The optimizer selects up to the desired number of work roles that maximize 
# the total adaptive score of the selected set. Unlike the greedy approach, all recommendations are 
# determined simultaneously, providing a globally optimal solution with respect to the predefined 
# objective function.

def recommend_binary_optimization(
    elements_nodes: Dict[str, "Node"],
    adj: Dict[str, Set[str]],
    focus: str,
    weights: Dict[str, float],
    current_roles: List[str] | None = None,
    top_n: int = 8,
    depth: int = 5,
    score_weights: Dict[str, float] | None = None,
) -> List[Dict]:

    normalize_weights = frameworkNice.normalize_weights(weights)

    current_roles = current_roles or []
    current_roles_set = set(current_roles)
    focus = focus.upper()

    if focus == "SOC":
        want_role_prefix = {"PD", "IN", "IO"}
    elif focus == "GRC":
        want_role_prefix = {"OG", "DD"}
    elif focus == "BALANCED":
        want_role_prefix = {"PD", "IN", "IO", "OG", "DD"}
    else:
        raise ValueError("focus must be SOC, GRC or BALANCED")

    roles = [
        nid for nid, n in elements_nodes.items()
        if n.type == "work_role"
        and re.match(r"^[A-Z]{2}-WRL-\d{3}$", nid)
        and nid not in current_roles_set
        and nid.split("-")[0] in want_role_prefix
    ]

    total_tasks = len([n for n in elements_nodes.values() if n.type == "task"])
    total_skills = len([n for n in elements_nodes.values() if n.type == "skill"])
    total_knowledge = len([n for n in elements_nodes.values() if n.type == "knowledge"])

    covered_tasks: Set[str] = set()
    covered_skills: Set[str] = set()
    covered_knowledge: Set[str] = set()

    for r in current_roles:
        cov = role_coverage(r, adj, elements_nodes, depth=depth)
        covered_tasks |= cov["tasks"]
        covered_skills |= cov["skills"]
        covered_knowledge |= cov["knowledge"]

    current_categories = set(r.split("-")[0] for r in current_roles)

    role_cov: Dict[str, Dict[str, Set[str]]] = {}
    role_score: Dict[str, float] = {}
    role_metrics: Dict[str, Dict] = {}

    for r in roles:
        cov = role_coverage(r, adj, elements_nodes, depth=depth)

        tasks_gain_set = cov["tasks"] - covered_tasks
        skills_gain_set = cov["skills"] - covered_skills
        knowledge_gain_set = cov["knowledge"] - covered_knowledge

        tasks_gain = len(tasks_gain_set)
        skills_gain = len(skills_gain_set)
        knowledge_gain = len(knowledge_gain_set)

        category = r.split("-")[0]

        metrics = frameworkNice.adaptive_role_score(
            cov=cov,
            tasks_gain=tasks_gain,
            skills_gain=skills_gain,
            knowledge_gain=knowledge_gain,
            covered_tasks=covered_tasks,
            covered_skills=covered_skills,
            covered_knowledge=covered_knowledge,
            total_tasks=total_tasks,
            total_skills=total_skills,
            total_knowledge=total_knowledge,
            category=category,
            current_categories=current_categories,
            preferred_categories=want_role_prefix,
            weights=weights,
            score_weights=score_weights,
        )

        role_cov[r] = {
            "tasks_gain_set": tasks_gain_set,
            "skills_gain_set": skills_gain_set,
            "knowledge_gain_set": knowledge_gain_set,
        }

        role_score[r] = metrics["score"]
        role_metrics[r] = metrics

    prob = pulp.LpProblem("Role_Recommendation", pulp.LpMaximize)

    x = {
        r: pulp.LpVariable(f"x_{r}", cat="Binary")
        for r in roles
    }

    prob += pulp.lpSum(role_score[r] * x[r] for r in roles)

    prob += pulp.lpSum(x[r] for r in roles) <= top_n

    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    selected_roles = [
        r for r in roles
        if pulp.value(x[r]) == 1
    ]

    recommendations = []

    for r in selected_roles:
        metrics = role_metrics[r]

        recommendations.append({
            "role": r,
            "title": elements_nodes[r].title,
            "category": r.split("-")[0],
            "score": round(metrics["score"], 2),

            "tasks_gain": metrics["tasks_gain"],
            "skills_gain": metrics["skills_gain"],
            "knowledge_gain": metrics["knowledge_gain"],

            "coverage_gain": round(metrics["coverage_gain"], 2),
            "novelty": round(metrics["novelty"], 2),
            "redundancy": round(metrics["redundancy"], 2),
            "category_gap": metrics["category_gap"],
            "profile_alignment": metrics["profile_alignment"],
            "balance": round(metrics["balance"], 2),
        })

    recommendations.sort(key=lambda x: x["score"], reverse=True)

    return recommendations


##############################################################
# Full Binary Optimization extends the previous model by explicitly optimizing the coverage of individual 
# NICE tasks, knowledge areas, and skills instead of relying solely on role-level scores. Binary decision 
# variables are introduced both for work roles and for individual capabilities, allowing the optimizer to 
# maximize the unique organizational coverage while preventing duplicated capabilities from contributing 
# multiple times to the objective function. Additional constraints reward the incorporation of previously 
# uncovered NICE categories and alignment with the selected organizational profile (SOC, GRC, or Balanced). 
# 
# This formulation captures interactions between simultaneously selected roles, producing recommendations 
# that maximize the overall capability coverage of the workforce rather than the independent value of each 
# individual role.
#
##############################################################

def recommend_binary_optimization_full(
    elements_nodes: Dict[str, "Node"],
    adj: Dict[str, Set[str]],
    focus: str,
    weights: Dict[str, float],
    current_roles: List[str] | None = None,
    top_n: int = 8,
    depth: int = 5,
    score_weights: Dict[str, float] | None = None,
) -> List[Dict]:

    current_roles = current_roles or []
    current_roles_set = set(current_roles)
    focus = focus.upper()

    if focus == "SOC":
        want_role_prefix = {"PD", "IN", "IO"}
    elif focus == "GRC":
        want_role_prefix = {"OG", "DD"}
    elif focus == "BALANCED":
        want_role_prefix = {"PD", "IN", "IO", "OG", "DD"}
    else:
        raise ValueError("focus must be SOC, GRC or BALANCED")

    normalize_weights = frameworkNice.normalize_weights(weights)
    total_tasks = len([
        n for n in elements_nodes.values() if n.type == "task"
    ])
    total_skills = len([
        n for n in elements_nodes.values() if n.type == "skill"
    ])
    total_knowledge = len([
        n for n in elements_nodes.values() if n.type == "knowledge"
    ])

    roles = [
        nid for nid, n in elements_nodes.items()
        if n.type == "work_role"
        and re.match(r"^[A-Z]{2}-WRL-\d{3}$", nid)
        and nid not in current_roles_set
        and nid.split("-")[0] in want_role_prefix
    ]

    covered_tasks, covered_skills, covered_knowledge = set(), set(), set()

    for r in current_roles:
        cov = role_coverage(r, adj, elements_nodes, depth=depth)
        covered_tasks |= cov["tasks"]
        covered_skills |= cov["skills"]
        covered_knowledge |= cov["knowledge"]

    role_cov = {}
    uncovered_elements = set()
    element_weight = {}

    for r in roles:
        cov = role_coverage(r, adj, elements_nodes, depth=depth)

        new_tasks = cov["tasks"] - covered_tasks
        new_skills = cov["skills"] - covered_skills
        new_knowledge = cov["knowledge"] - covered_knowledge

        role_cov[r] = {
            "tasks": new_tasks,
            "skills": new_skills,
            "knowledge": new_knowledge,
            "all": new_tasks | new_skills | new_knowledge,
        }

        for e in new_tasks:
            uncovered_elements.add(e)
            element_weight[e] = (
                normalize_weights["tasks"] / total_tasks if total_tasks else 0
            )

        for e in new_skills:
            uncovered_elements.add(e)
            element_weight[e] = (
                normalize_weights["skills"] / total_skills if total_skills else 0
            )

        for e in new_knowledge:
            uncovered_elements.add(e)
            element_weight[e] = (
                normalize_weights["knowledge"] / total_knowledge
                if total_knowledge else 0
            )

    prob = pulp.LpProblem("Role_Recommendation_Full", pulp.LpMaximize)

    x = {
        r: pulp.LpVariable(f"x_{r}", cat="Binary")
        for r in roles
    }

    y = {
        e: pulp.LpVariable(f"y_{e}", cat="Binary")
        for e in uncovered_elements
    }

    # Categorías nuevas cubiertas
    current_categories = set(r.split("-")[0] for r in current_roles)
    candidate_categories = sorted({r.split("-")[0] for r in roles})

    z_cat = {
        c: pulp.LpVariable(f"z_cat_{c}", cat="Binary")
        for c in candidate_categories
        if c not in current_categories
    }

    # Objetivo principal: cobertura única
    coverage_objective = pulp.lpSum(
        element_weight[e] * y[e]
        for e in uncovered_elements
    )

    # Bonus por categorías nuevas
    category_objective = pulp.lpSum(
        z_cat[c]
        for c in z_cat
    )

    # Bonus por alineación con perfil
    profile_objective = pulp.lpSum(
        x[r]
        for r in roles
        if r.split("-")[0] in want_role_prefix
    )

    prob += (
        0.70 * coverage_objective
        + 0.20 * category_objective
        + 0.10 * profile_objective
    )

    # Máximo número de roles
    prob += pulp.lpSum(x[r] for r in roles) <= top_n

    # Relación elemento cubierto ↔ roles seleccionados
    for e in uncovered_elements:
        covering_roles = [
            r for r in roles
            if e in role_cov[r]["all"]
        ]

        prob += y[e] <= pulp.lpSum(x[r] for r in covering_roles)

        for r in covering_roles:
            prob += y[e] >= x[r]

    # Relación categoría cubierta ↔ roles seleccionados
    for c in z_cat:
        roles_in_cat = [
            r for r in roles
            if r.split("-")[0] == c
        ]

        prob += z_cat[c] <= pulp.lpSum(x[r] for r in roles_in_cat)

        for r in roles_in_cat:
            prob += z_cat[c] >= x[r]

    prob.solve(pulp.PULP_CBC_CMD(msg=False))

    selected_roles = [
        r for r in roles
        if pulp.value(x[r]) == 1
    ]

    recommendations = []

    selected_covered_tasks = set(covered_tasks)
    selected_covered_skills = set(covered_skills)
    selected_covered_knowledge = set(covered_knowledge)

    for r in selected_roles:
        cov = role_coverage(r, adj, elements_nodes, depth=depth)

        tasks_gain_set = cov["tasks"] - covered_tasks
        skills_gain_set = cov["skills"] - covered_skills
        knowledge_gain_set = cov["knowledge"] - covered_knowledge

        tasks_gain = len(tasks_gain_set)
        skills_gain = len(skills_gain_set)
        knowledge_gain = len(knowledge_gain_set)

        metrics = frameworkNice.adaptive_role_score(
            cov=cov,
            tasks_gain=tasks_gain,
            skills_gain=skills_gain,
            knowledge_gain=knowledge_gain,
            covered_tasks=covered_tasks,
            covered_skills=covered_skills,
            covered_knowledge=covered_knowledge,
            total_tasks=total_tasks,
            total_skills=total_skills,
            total_knowledge=total_knowledge,
            category=r.split("-")[0],
            current_categories=current_categories,
            preferred_categories=want_role_prefix,
            weights=normalize_weights,
            score_weights=score_weights,
        )

        recommendations.append({
            "role": r,
            "title": elements_nodes[r].title,
            "category": r.split("-")[0],
            "score": round(metrics["score"], 2),
            "tasks_gain": tasks_gain,
            "skills_gain": skills_gain,
            "knowledge_gain": knowledge_gain,
            "coverage_gain": round(metrics["coverage_gain"], 2),
            "novelty": round(metrics["novelty"], 2),
            "redundancy": round(metrics["redundancy"], 2),
            "category_gap": metrics["category_gap"],
            "profile_alignment": metrics["profile_alignment"],
            "balance": round(metrics["balance"], 2),
        })

        selected_covered_tasks |= cov["tasks"]
        selected_covered_skills |= cov["skills"]
        selected_covered_knowledge |= cov["knowledge"]

    recommendations.sort(key=lambda x: x["score"], reverse=True)

    return recommendations
