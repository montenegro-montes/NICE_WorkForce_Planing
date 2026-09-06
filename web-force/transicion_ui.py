import streamlit as st
import ui
import frameworkNice

#################################
#  Workforce Gap Analysis
#################################

def WorkforceGapAnalysis(nodes):

    with st.container(key="current_workforce_analysis_box"):
        
        col_current, col_target = st.columns(2)
                            
        with col_current:

            st.markdown("""
            <div class="card-section">CURRENT WORKFORCE</div>
            """, unsafe_allow_html=True)
        
            nodes       = st.session_state.nodes
            role_list   = frameworkNice.get_role_list(nodes)
            role_labels = {}
            for role in role_list:
                cov = frameworkNice.calculate_coverage([role], nodes, st.session_state.adj)
                role_labels[role] = f"{role} - {nodes[role].title} (Tasks: {len(cov['tasks'])} Knowledge: {len(cov['knowledge'])} Skills: {len(cov['skills'])} Annual Cost: ${st.session_state.cost_model.cost(role, st.session_state.get('salary_scenario', 'AVERAGE')):,.0f} )"
            
            if "current_roles" not in st.session_state:
                st.session_state.current_roles = []
                
            if "target_roles" not in st.session_state:
                st.session_state.target_roles = st.session_state.current_roles.copy()    
            elif not st.session_state.target_roles and st.session_state.current_roles:
                st.session_state.target_roles = st.session_state.current_roles.copy()

            if st.session_state.current_roles:
                role_table = []
                for role in st.session_state.current_roles:
                    cov = frameworkNice.calculate_coverage([role], nodes, st.session_state.adj)
                    role_table.append({
                        "Role ID": role,
                        "Title": nodes[role].title,
                        "Category": frameworkNice.getCategory(role),
                        "Tasks": len(cov["tasks"]),
                        "Knowledge": len(cov["knowledge"]),
                        "Skills": len(cov["skills"]),
                        "Annual Cost": f"${st.session_state.cost_model.cost(role, st.session_state.get('salary_scenario', 'AVERAGE')):,.0f}"
                    })
                st.caption(f"{len(st.session_state.current_roles)} roles selected")    
                st.dataframe(role_table, width='stretch',height=220)
            else:
                st.info("No roles added yet. Selecciona un role y pulsa 'Add role'.")

        with col_target:

            st.markdown("""
            <div class="card-section">TARGET WORKFORCE</div>
                """, unsafe_allow_html=True)

            if st.session_state.target_roles:
                target_role_table = []
                for role in st.session_state.target_roles:
                    cov = frameworkNice.calculate_coverage([role], nodes, st.session_state.adj)
                    target_role_table.append({
                        "Role ID": role,
                        "Title": nodes[role].title,
                        "Category": frameworkNice.getCategory(role),
                        "Tasks": len(cov["tasks"]),
                        "Knowledge": len(cov["knowledge"]),
                        "Skills": len(cov["skills"]),
                        "Annual Cost": f"${st.session_state.cost_model.cost(role, st.session_state.get('salary_scenario', 'AVERAGE')):,.0f}"
                    })
                st.caption(f"{len(st.session_state.target_roles)} roles selected")    
                st.dataframe(target_role_table, width='stretch',height=220)
            else:
                st.info("No roles added yet. Selecciona un role y pulsa 'Add role'.")

            
        st.markdown("""
            <div class="card-section-info">Target Workforce Management</div>
                    """, unsafe_allow_html=True)
        
        available_roles = [
                    r for r in role_list
                    if r not in st.session_state.target_roles
                ]

        with st.form("role_management_new_form_cfg", clear_on_submit=True):
        # Fila 1: Selectores lado a lado

                col_add, button_add, col_remove, button_remove = st.columns([5, 1, 5, 1])

                with col_add:
                    selected_role = st.selectbox(
                        "Select a role to add:",
                        options=[None] + available_roles,
                        format_func=lambda x: "" if x is None else role_labels[x],
                    )

                    st.caption(
                        f"{len(available_roles)} roles available "
                        f"({len(st.session_state.target_roles)} selected)"
                    )

                with button_add:
                    st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
                    add_submitted = st.form_submit_button(
                        "Add role",
                        use_container_width=True
                    )

                with col_remove:
                    remove_roles = st.multiselect(
                        "Select roles to remove:",
                        options=st.session_state.target_roles,
                        format_func=lambda x: role_labels[x]
                    )

                with button_remove:
                    st.markdown("<div style='height:26px'></div>", unsafe_allow_html=True)
                    remove_submitted = st.form_submit_button(
                        "Remove",
                        use_container_width=True
                    )
                
                if add_submitted:
                        if selected_role is None:
                            st.warning("Please choose a role before adding.")
                        elif selected_role in st.session_state.target_roles:
                            st.warning("This role is already in the table.")
                        else:
                            st.session_state.target_roles.append(selected_role)
                            st.success(f"Added {selected_role}.")
                            st.session_state.last_added_role = selected_role
                            current_cov = frameworkNice.calculate_coverage(st.session_state.target_roles, nodes, st.session_state.adj)
                            st.rerun()
                            
                if remove_submitted:
                        for role in remove_roles:
                            st.session_state.target_roles.remove(role)
                        if remove_roles:
                                st.success(f"Removed {len(remove_roles)} role(s).")
                                st.rerun()
                        else:
                                st.warning("Please select at least one role to remove.")

                    
    
        ## Analysis

        current_roles = st.session_state.current_roles
        target_roles  = st.session_state.target_roles

        current_cov = frameworkNice.calculate_coverage(current_roles, nodes, st.session_state.adj)
        target_cov  = frameworkNice.calculate_coverage(target_roles, nodes, st.session_state.adj)

        work_roles_total = len([n for n in nodes.values() if n.type == "work_role"])
        tasks_total      = len([n for n in nodes.values() if n.type == "task"])
        knowledge_total  = len([n for n in nodes.values() if n.type == "knowledge"])
        skills_total     = len([n for n in nodes.values() if n.type == "skill"])

        delta   = calculate_workforce_delta(current_roles, target_roles)
        cap_gap = calculate_capability_gap(current_cov, target_cov)
        cat_gap = calculate_category_gap(current_roles, target_roles)
        transition_costs = calculate_transition_costs(
            current_roles,
            target_roles,
            st.session_state.cost_model,
            st.session_state.get("salary_scenario", "AVERAGE"),
        )

        st.markdown("""
            <div class="card-section-info">
                Transition Summary
            </div>
        """, unsafe_allow_html=True)

        roles_maintained    = make_badges(delta["maintained"], "maintained")
        roles_maintained    = make_badges(delta["maintained"], "maintained")
        roles_add           = make_badges(delta["added"], "added")
        roles_removed       = make_badges(delta["removed"], "removed")

        maintained_category  = make_badges(cat_gap["maintained"], "maintained")
        add_category         = make_badges(cat_gap["add"], "added")
        remove_category      = make_badges(cat_gap["remove"], "removed")
        
        work_roles           = len([n for n in nodes.values() if n.type == "work_role"])
        tasks                = len([n for n in nodes.values() if n.type == "task"])
        knowledges           = len([n for n in nodes.values() if n.type == "knowledge"])
        skills               = len([n for n in nodes.values() if n.type == "skill"])
        
        #Current overall
        
        task_coverage_current       = len(current_cov["tasks"])
        knowledge_coverage_current  = len(current_cov["knowledge"])
        skill_coverage_current      = len(current_cov["skills"])
    
        
        num_roles_current    = len(st.session_state.current_roles)
        overall_current      = frameworkNice.calculate_overall_coverage(
                            num_roles_current, work_roles,
                            task_coverage_current, tasks,
                            knowledge_coverage_current, knowledges,
                            skill_coverage_current, skills)
        

        #Target overall

        task_coverage_target       = len(target_cov["tasks"])
        knowledge_coverage_target  = len(target_cov["knowledge"])
        skill_coverage_target      = len(target_cov["skills"])
    
        
        num_roles_target    = len(st.session_state.target_roles)
        overall_target      = frameworkNice.calculate_overall_coverage(
                            num_roles_target, work_roles,
                            task_coverage_target, tasks,
                            knowledge_coverage_target, knowledges,
                            skill_coverage_target, skills)
        maturity_target, color_target = frameworkNice.baseline_maturity(overall_target)

        ### Coverage_gain
        coverage_gain = overall_target - overall_current

        if coverage_gain > 0:
            css = "success"
            coverage_gain_str = f"+{coverage_gain:.1f} pp"
        elif coverage_gain < 0:
            css = "danger"
            coverage_gain_str = f"{coverage_gain:.1f} pp"
        else:
            css = ""
            coverage_gain_str = "0.0 pp"

        num_roles_current            = len(current_roles)
        num_roles_target             = len(target_roles)
        
        tasks_gain = len(target_cov["tasks"]) - len(current_cov["tasks"])
        knowledge_gain = len(target_cov["knowledge"]) - len(current_cov["knowledge"])
        skills_gain = len(target_cov["skills"]) - len(current_cov["skills"])

        tasks_label = f"{tasks_gain:+d} Tasks"
        knowledge_label = f"{knowledge_gain:+d} Knowledge"
        skills_label = f"{skills_gain:+d} Skills"

        
        adj = st.session_state.adj
        duplicates_current = None
        duplicates_target  = None

        impact_label =  "No Change"
        impact_class =  "neutral"
        impact_value = 0

        counts_category = frameworkNice.get_category_distribution(target_roles)
        covered_domains = sum(v > 0 for v in counts_category.values())
        total_domains   = len(frameworkNice.categories)

        net_budget_change = transition_costs["net_change"]
        if net_budget_change > 0:
            budget_change_class = "danger"
            budget_change_text = f"+${net_budget_change:,.0f}"
        elif net_budget_change < 0:
            budget_change_class = "success"
            budget_change_text = f"-${abs(net_budget_change):,.0f}"
        else:
            budget_change_class = "neutral"
            budget_change_text = "$0"

        if adj and num_roles_current > 1:
            duplicates_current = frameworkNice.calculate_unique_and_duplicates(current_roles, current_cov, nodes, adj)
            duplicates_target  = frameworkNice.calculate_unique_and_duplicates(target_roles, target_cov, nodes, adj)

            current_efficiency  = overall_efficiency(duplicates_current)
            target_efficiency   = overall_efficiency(duplicates_target)
            impact_value,impact_label,impact_class = calculate_impact(coverage_gain,cat_gap,target_cov,current_cov,tasks_total,
                                                                      knowledge_total,skills_total,current_efficiency,target_efficiency)


            st.markdown(f"""
                <div class="summary-box">
                   <!-- <div class="summary-item">
                        <span class="summary-label">TASKS ADDED</span>
                        <span class="summary-value domains">
                        {num_roles_current} 
                        </span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">KNOWLEDGE ADDED</span>
                        <span class="summary-value">{num_roles_target}</span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">SKILLS ADDED</span>
                        <span class="summary-value">{num_roles_target-num_roles_current}</span>
                    </div>-->
                    <div class="summary-item">
                        <span class="summary-label">COVERAGE GAIN</span>
                        <span class="summary-value success">
                            {coverage_gain_str}
                        </span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">EXPECTED MATURITY</span>
                        <span style="color:{color_target}; font-weight:700;">{maturity_target}</span>
                    </div>
                     <div class="summary-item">
                        <span class="summary-label">CATEGORY COVERED</span>
                        <span class="summary-value success">
                            {covered_domains} / {total_domains}
                        </span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">ESTIMATED IMPACT</span>
                            <span class="summary-value {impact_class}">
                                    {impact_label} ({impact_value:.1f}/100)
                            </span>
                        </span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">CURRENT ANNUAL COST</span>
                        <span class="summary-value">
                            ${transition_costs['current_cost']:,.0f}
                        </span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">TARGET ANNUAL COST</span>
                        <span class="summary-value">
                            ${transition_costs['target_cost']:,.0f}
                        </span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">NET ANNUAL BUDGET CHANGE</span>
                        <span class="summary-value {budget_change_class}">
                            {budget_change_text}
                        </span>
                    </div>
                     <div class="capability-gain-box">
                        <div class="capability-gain-title">Capability Gain</div>
                        <div class="capability-gain-values">
                            <span class="capability-gain-item tasks">{tasks_label}</span>
                            <span class="capability-gain-item knowledge">{knowledge_label}</span>
                            <span class="capability-gain-item skills">{skills_label}</span>
                        </div>
                    </div>
                            
                    
                </div>
                """, unsafe_allow_html=True)

            st.markdown(f"""
                <div class="summary-box">
                    <!--<div class="summary-item">
                        <span class="summary-label">Roles Maintained</span>
                        <span class="summary-value domains">
                        {roles_maintained} 
                        </span>
                    </div> -->
                    <div class="summary-item">
                        <span class="summary-label">Roles Add</span>
                        <span class="summary-value domains">
                        {roles_add} 
                        </span>
                    </div>   
                    <div class="summary-item">
                        <span class="summary-label">Roles Removed</span>
                        <span class="summary-value domains">
                        {roles_removed} 
                        </span>
                    </div>
                    <!--<div class="summary-item">
                        <span class="summary-label">Category Maintained</span>
                        <span class="summary-value domains">
                        {maintained_category} 
                        </span>
                    </div>-->
                    <div class="summary-item">
                        <span class="summary-label">Category Add</span>
                        <span class="summary-value domains">
                        {add_category} 
                        </span>
                    </div>
                    <div class="summary-item">
                        <span class="summary-label">Category Remove</span>
                        <span class="summary-value domains">{remove_category}</span>
                    </div>
                    
                </div>
                """, unsafe_allow_html=True)

        coverage__delta_ui(current_roles, current_cov,target_roles, target_cov, nodes,  adj, duplicates_current,duplicates_target)



######################################
#
######################################

def calculate_workforce_delta(current_roles, target_roles):
    current_set = set(current_roles)
    target_set = set(target_roles)

    return {
        "maintained": sorted(current_set & target_set),
        "added": sorted(target_set - current_set),
        "removed": sorted(current_set - target_set),
    }


def calculate_transition_costs(
    current_roles,
    target_roles,
    cost_model,
    salary_scenario="AVERAGE",
):
    """Calculate annual workforce-cost changes for a role transition."""
    current_set = set(current_roles)
    target_set = set(target_roles)
    added_roles = target_set - current_set
    removed_roles = current_set - target_set

    def total_cost(role_ids):
        total = 0.0
        for role_id in role_ids:
            try:
                total += float(cost_model.cost(role_id, salary_scenario))
            except KeyError:
                continue
        return total

    current_cost = total_cost(current_set)
    target_cost = total_cost(target_set)
    added_cost = total_cost(added_roles)
    removed_savings = total_cost(removed_roles)

    return {
        "current_cost": current_cost,
        "target_cost": target_cost,
        "added_cost": added_cost,
        "removed_savings": removed_savings,
        "net_change": target_cost - current_cost,
    }

######################################
#
######################################

def calculate_capability_gap(current_cov, target_cov):
    return {
        "tasks": sorted(set(target_cov["tasks"]) - set(current_cov["tasks"])),
        "knowledge": sorted(set(target_cov["knowledge"]) - set(current_cov["knowledge"])),
        "skills": sorted(set(target_cov["skills"]) - set(current_cov["skills"])),
    }


######################################
#
######################################

def calculate_category_gap(current_roles, target_roles):
    current_cats = {frameworkNice.getCategory(r) for r in current_roles}
    target_cats = {frameworkNice.getCategory(r) for r in target_roles}

    return {
        "add": sorted(target_cats - current_cats),
        "remove": sorted(current_cats - target_cats),
        "maintained": sorted(current_cats & target_cats),
    }


######################################
#
######################################

def pct(value, total):
    return (value / total * 100) if total > 0 else 0


######################################
#
######################################

def make_badges(items, css_class):
    if not items:
        return '<span class="delta-badge neutral">None</span>'

    return " ".join(
        f'<span class="delta-badge {css_class}">{item}</span>'
        for item in items
    )

######################################
#
######################################

def coverage__delta_ui(current_roles, current_cov, target_roles, target_cov, nodes, adj=None, duplicates_current=None,duplicates_target=None):

    num_roles_current            = len(current_roles)
    task_coverage_current        = len(current_cov["tasks"])
    skill_coverage_current       = len(current_cov["skills"])
    knowledge_coverage_current   = len(current_cov["knowledge"])

    num_roles_target            = len(target_roles)
    task_coverage_target        = len(target_cov["tasks"])
    skill_coverage_target       = len(target_cov["skills"])
    knowledge_coverage_target   = len(target_cov["knowledge"])


    work_roles = len([n for n in nodes.values() if n.type == "work_role"])
    tasks      = len([n for n in nodes.values() if n.type == "task"])
    knowledges = len([n for n in nodes.values() if n.type == "knowledge"])
    skills     = len([n for n in nodes.values() if n.type == "skill"])

    if num_roles_current == num_roles_target:
        main = f"{num_roles_current} / {work_roles}"
        sub = "Coverage unchanged"
        num_roles_target = None
    else:
        main = f"{num_roles_current} → {num_roles_target} / {work_roles}"
        sub  = f"{num_roles_target-num_roles_current:+d} roles"

    roles_card = ui.card_html("Work Roles",main,sub,num_roles_current,work_roles,num_roles_target,None)

    if duplicates_current and duplicates_target:
        tasks_card      = coverage__delta_ui_aux ("tasks",duplicates_current,duplicates_target,task_coverage_current,tasks,task_coverage_target)
        knowledge_card  = coverage__delta_ui_aux ("knowledge", duplicates_current,duplicates_target, knowledge_coverage_current, knowledges, knowledge_coverage_target)
        skills_card     = coverage__delta_ui_aux ("skills", duplicates_current,duplicates_target, skill_coverage_current, skills,skill_coverage_target )
    else:
        tasks_card      = ui.card_html("Tasks",f"{task_coverage_current}","Covered tasks",task_coverage_current,tasks)
        knowledge_card  = ui.card_html("Knowledge",f"{knowledge_coverage_current}","Covered knowledge",knowledge_coverage_current,knowledges)
        skills_card     = ui.card_html("Skills", f"{skill_coverage_current}","Covered skills",skill_coverage_current,skills)

    cards_html = roles_card + tasks_card + knowledge_card + skills_card

    st.markdown(f"""
    <h3>Coverage Evolution</h3>
    <div class="cov-cards">{cards_html}</div>
    """, unsafe_allow_html=True)

######################################
#
######################################

def coverage__delta_ui_aux(type, duplicates_current,duplicates_target, current,total,target):
     
    section =  type.capitalize() 
    d_current = duplicates_current[type]
    d_target  = duplicates_target[type]

    if current == target:
        main   = f"{d_current['unique']} unique"
        sub    = f"{d_current['duplicated']}  duplicated"
        sub2   = f"Efficiency {d_current['efficiency']:.0f}%"
        target = None
    else:
        main    = f"{d_current['unique']} → {d_target['unique']} unique"
        sub     = f"Duplicates: {d_current['duplicated']} → {d_target['duplicated']} "
        sub2    = f"Efficiency: {d_current['efficiency']:.0f}% → {d_target['efficiency']:.0f}%"
        
             
    return  ui.card_html(section,main,sub, current,total, target,sub2)

########################################
# coverage_gain
#   a- Cobertura ganada (40%) - Ganar 20 puntos o más da la puntuación máxima.
#   b- Nuevas categorías NICE (25%) - Si cubres las cinco categorías principales: 25 ptos
#   c- Nuevas capacidades (25%) - El incremento de elementos únicos
#.  d- Penalización por duplicados (10%)

def calculate_impact(coverage_gain,cat_gap,target_cov,current_cov,tasks_total,knowledge_total,skills_total,current_efficiency,target_efficiency):

    coverage_score = min(coverage_gain / 20 * 40, 40)
    new_categories = len(cat_gap["add"])

    category_score = new_categories / 5 * 25

    tasks_gain      = len(target_cov["tasks"]) - len(current_cov["tasks"])
    knowledge_gain  = len(target_cov["knowledge"]) - len(current_cov["knowledge"])
    skills_gain     = len(target_cov["skills"]) - len(current_cov["skills"])

    capability_score = (
        tasks_gain/tasks_total +
        knowledge_gain/knowledge_total +
        skills_gain/skills_total
    ) / 3 * 25

    efficiency_delta = (current_efficiency - target_efficiency)

    penalty = max(0, efficiency_delta)

    impact = (coverage_score +category_score + capability_score - penalty)

    impact = max(0, min(100, impact))

    if abs(impact) < 0.01:
        label = "No Change"
        impact_class = "neutral"
    elif impact < 25:
        label = "Low"
        impact_class = "danger"
    elif impact < 50:
        label = "Moderate"
        impact_class = "warning"
    elif impact < 75:
        label = "High"
        impact_class = "success"
    else:
        label = "Very High"
        impact_class = "excellent"
    
    return impact,label,impact_class

########################################
#
########################################

def overall_efficiency(duplicates):

    unique = (
        duplicates["tasks"]["unique"] +
        duplicates["knowledge"]["unique"] +
        duplicates["skills"]["unique"]
    )

    duplicated = (
        duplicates["tasks"]["duplicated"] +
        duplicates["knowledge"]["duplicated"] +
        duplicates["skills"]["duplicated"]
    )

    return unique / (unique + duplicated) * 100
