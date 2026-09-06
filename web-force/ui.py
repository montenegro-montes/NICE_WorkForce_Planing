import streamlit as st
import frameworkNice 
import json
from configuration import COMPANY_JSON_PATH


#################################
#
#################################


def metric_card(title, value):

    st.markdown(f"""
      <h2>{title}</h2>
      <div class="cards">
        <div class="card"><div class="card-label">Current Roles</div><div class="card-value" id="cur-roles">—</div><div class="card-sub">Baseline workforce</div></div>
        <div class="card green"><div class="card-label">Target Roles</div><div class="card-value" id="tgt-roles">—</div><div class="card-sub">After optimization</div></div>
        <div class="card"><div class="card-label">Total Budget</div><div class="card-value" id="total-budget">—</div><div class="card-sub">2-year horizon</div></div>
        <div class="card yellow"><div class="card-label">Risk Reduction</div><div class="card-value" id="risk-avg">—</div><div class="card-sub">Avg across scenarios</div></div>
      </div>
                            
    <div class="metric-card">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
    </div>
    """, unsafe_allow_html=True)


#################################
# NICE Information Cards
#################################

def nice_information(nodes,edges,framework_info):
    total_nodes = len(nodes)
    work_roles = len([n for n in nodes.values() if n.type == "work_role"])
    tasks = len([n for n in nodes.values() if n.type == "task"])
    knowledges = len([n for n in nodes.values() if n.type == "knowledge"])
    skills = len([n for n in nodes.values() if n.type == "skill"])
    relationships = len(edges)

    st.markdown(f"""
      <div class="section-card">          
       <div class="card-section">Nice overview</div>
        <div class="card-section-subtitle">
            {framework_info}
        </div>
        <div class="nice-summary">
            <div class="nice-stat">
                <span class="nice-label">Work Roles</span>
                <span class="nice-value roles">{work_roles}</span>
            </div>
            <div class="nice-stat">
                <span class="nice-label">Tasks</span>
                <span class="nice-value knowledge">{tasks}</span>
            </div>
            <div class="nice-stat">
                <span class="nice-label">Knowledge</span>
                <span class="nice-value knowledge">{knowledges}</span>
            </div>
            <div class="nice-stat">
                <span class="nice-label">Skills</span>
                <span class="nice-value knowledge">{skills}</span>
            </div>
            <div class="nice-stat">
                <span class="nice-label">Nodes</span>
                <span class="nice-value graph">{total_nodes}</span>
            </div>
            <div class="nice-stat">
                <span class="nice-label">Relationships</span>
                <span class="nice-value graph">{relationships}</span>
            </div>
        </div>
        </div>
     </div>
    
    """, unsafe_allow_html=True)    

#################################
# Company profile
#################################

def company_profile():

    with st.container(key="company_profile_box"):
        
        st.markdown("""
        <div class="card-section">COMPANY PROFILE</div>
        <div class="card-section-subtitle">
            Information about the company and simulation context
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3, col4, col5, col6 = st.columns(
            [2, 2, 2, 4, 1.5, 1.5]
        )
        with col1:
            organization_size = st.selectbox(
                "Organization Size",
                [
                    "Small (<50 employees)",
                    "Medium (50-250 employees)",
                    "Large (250-1000 employees)",
                    "Enterprise (>1000 employees)"
                ],
                key="organization_size"
            )

        with col2:
            industry_sector = st.selectbox(
                "Industry Sector",
                [
                    "Financial Services",
                    "Healthcare",
                    "Government",
                    "Education",
                    "Manufacturing",
                    "Energy & Utilities",
                    "Telecommunications",
                    "Technology",
                    "Retail & E-Commerce",
                    "Transportation",
                    "Other"
                ],
                key="industry_sector"
            )

        with col3:
            business_criticality = st.selectbox(
                "Business Criticality",
                ["Low", "Medium", "High", "Critical"],
                index=2,
                key="business_criticality"
            )

        
        with col4:
            regulatory_environment = st.multiselect(
                "Regulatory Environment",
                [
                    "GDPR",
                    "NIS2",
                    "ISO 27001",
                    "PCI-DSS",
                    "HIPAA",
                    "SOX",
                    "DORA",
                    "Other"
                ],
                default=["GDPR", "NIS2"],
                key="regulatory_environment"
            )

        with col5:
            target_maturity = st.selectbox(
                "Target Security Maturity",
                ["Basic", "Intermediate", "Advanced", "Expert"],
                index=2,
                key="target_maturity"
            )
        
        with col6:
            security_team_size = st.number_input(
                "Security Team Size",
                min_value=0,
                value=5,
                step=1,
                key="security_team_size"
            )

        st.session_state.company_profile = {
            "organization_size": organization_size,
            "industry_sector": industry_sector,
            "security_team_size": security_team_size,
            "business_criticality": business_criticality,
            "regulatory_environment": regulatory_environment,
            "target_maturity": target_maturity
        }

#################################
# Current Workforce Status
#################################

def currentWorkforceStatus():

    with st.container(key="company_workforce_status_box"):
        
        st.markdown("""
        <div class="card-section">Current Workforce Status</div>
        <div class="card-section-subtitle">
            Information about the company and simulation context
        </div>
        """, unsafe_allow_html=True)

        # Initialize current_roles if not already set
        if "current_roles" not in st.session_state:
            st.session_state.current_roles = []
        
        nodes = st.session_state.nodes

        current_cov = frameworkNice.calculate_coverage(st.session_state.current_roles, nodes, st.session_state.adj)

        if current_cov is not None and st.session_state.current_roles:

            num_roles = len(st.session_state.current_roles)

            task_coverage = len(current_cov["tasks"])
            skill_coverage = len(current_cov["skills"])
            knowledge_coverage = len(current_cov["knowledge"])
    
            work_roles = len([n for n in nodes.values() if n.type == "work_role"])
            tasks = len([n for n in nodes.values() if n.type == "task"])
            knowledges = len([n for n in nodes.values() if n.type == "knowledge"])
            skills = len([n for n in nodes.values() if n.type == "skill"])

            counts = frameworkNice.get_category_distribution(st.session_state.current_roles, nodes)

            covered = [c for c, v in counts.items() if v > 0]
            missing = [code for code in frameworkNice.category_names if counts.get(code, 0) == 0]
            
            len_covered = len(covered)
            len_missing = len(missing)

            overall = frameworkNice.calculate_overall_coverage(
                    num_roles, work_roles,
                    task_coverage, tasks,
                    knowledge_coverage, knowledges,
                    skill_coverage, skills
            )
            
            maturity, color = frameworkNice.baseline_maturity(overall)

            active_html = ""
            inactive_html = ""

            for cat in frameworkNice.categories:

                value = counts.get(cat, 0)
                name = frameworkNice.category_names.get(cat, cat)

                if value > 0:
                    active_html += (
                        f'<span class="nice-badge covered" '
                        f'title="{name}">'
                        f'{cat} ({value})'
                        f'</span> '
                    )
                else:
                    inactive_html += (
                        f'<span class="nice-badge missing" '
                        f'title="{name}">'
                        f'{cat}'
                        f'</span> '
                    )
            
            duplicates = None
            if num_roles >= 1:
                duplicates = frameworkNice.calculate_unique_and_duplicates(st.session_state.current_roles, current_cov, nodes, st.session_state.adj)

            if duplicates:
                d = duplicates["tasks"]
                efficiency = 0+ d['efficiency'];
                d = duplicates["knowledge"]
                efficiency += d['efficiency'];
                d = duplicates["skills"]
                efficiency += d['efficiency'];
                efficiency /= 3

            st.markdown(f"""
            <div class="summary-box">
                <div class="summary-item">
                    <span class="summary-label">Represented Domains</span>
                    <span class="summary-value domains">
                    {len_covered / (len_covered + len_missing) * 100:.1f} %
                    </span>
                </div>
                <div class="summary-item">
                    <span class="summary-label">Framework Coverage</span>
                    <span class="summary-value">{overall:.1f}%</span>
                </div>
                <div class="summary-item">
                    <span class="summary-label">Roles Selected</span>
                    <span class="summary-value">{len(st.session_state.current_roles)}</span>
                </div>
                <div class="summary-item">
                    <span class="summary-label">Covered Categories</span>
                    <span class="summary-value success">
                        {active_html}
                    </span>
                </div>
                <div class="summary-item">
                    <span class="summary-label">Missing Categories</span>
                    <span class="summary-value danger">
                        {inactive_html}
                    </span>
                </div>
                <div class="summary-item">
                    <span class="summary-label">Workforce Efficiency</span>
                    <span class="summary-value">{efficiency:.0f}%</span>
                </div>
                <div class="summary-item">
                    <span class="summary-label">Maturity</span>
                    <span style="color:{color}; font-weight:700;">{maturity}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
          
        else:
            st.markdown(f"""
                NO roles selected. Please add roles in the "Current Workforce" section to see coverage information.
                </div>
            """, unsafe_allow_html=True)    
    
#################################
# Current Workforce
#################################

def currentWorkforce(nodes):

    with st.container(key="current_workforce_box"):
        
        st.markdown("""
        <div class="card-section">CURRENT WORKFORCE</div>
        <div class="card-section-subtitle">
            Information about the current workforce and their roles
        </div>
        """, unsafe_allow_html=True)
    
        nodes       = st.session_state.nodes
        role_list   = frameworkNice.get_role_list(nodes)
        role_labels = {}
        for role in role_list:
            cov = frameworkNice.calculate_coverage([role], nodes, st.session_state.adj)
            role_labels[role] = f"{role} - {nodes[role].title} (Tasks: {len(cov['tasks'])} Knowledge: {len(cov['knowledge'])} Skills: {len(cov['skills'])})"
        if "current_roles" not in st.session_state:
            st.session_state.current_roles = []

        with st.form("role_management_form_cfg", clear_on_submit=True):

                available_roles = [
                    r for r in role_list
                    if r not in st.session_state.current_roles
                ]
                  
                # Fila 1: Selectores lado a lado
                col_add, col_remove = st.columns(2)
                            
                with col_add:
                    selected_role = st.selectbox(
                        "Select a role to add:",
                        options=[None] + available_roles,
                        format_func=lambda x: "" if x is None else role_labels[x],
                    )
                    current_cov = frameworkNice.calculate_coverage(st.session_state.current_roles, nodes, st.session_state.adj)


                with col_remove:
                    remove_roles = st.multiselect(
                        "Select roles to remove:",
                        options=st.session_state.current_roles,
                        format_func=lambda x: role_labels[x]
                    )

                # Fila 2: Botones
                button_add, button_remove = st.columns(2)
                
                with button_add:
                    add_submitted = st.form_submit_button("Add role")

                with button_remove:
                    remove_submitted = st.form_submit_button("Remove selected")
                
                if add_submitted:
                        if selected_role is None:
                            st.warning("Please choose a role before adding.")
                        elif selected_role in st.session_state.current_roles:
                            st.warning("This role is already in the table.")
                        else:
                            st.session_state.current_roles.append(selected_role)
                            st.success(f"Added {selected_role}.")
                            current_cov = frameworkNice.calculate_coverage(st.session_state.current_roles, nodes, st.session_state.adj)
                            st.session_state.selected_role_to_add = None
                            st.rerun()

                            
                if remove_submitted:
                        for role in remove_roles:
                            st.session_state.current_roles.remove(role)
                        if remove_roles:
                                st.success(f"Removed {len(remove_roles)} role(s).")
                                st.rerun()
                        else:
                                st.warning("Please select at least one role to remove.")
            
            
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
                            "Skills": len(cov["skills"])
                        })
                    st.dataframe(role_table, width='stretch')
                else:
                    st.info("No roles added yet. Selecciona un role y pulsa 'Add role'.")

                if current_cov is not None and st.session_state.current_roles:
                    coverage_ui(st.session_state.current_roles, current_cov, nodes, st.session_state.adj)
   

#################################
# Configuratrion Management
#################################

def configurationManagement():

    with st.container(key="configuration_management_box"):
      
        st.markdown("""
            <div class="card-section">CONFIGURATION MANAGEMENT</div>
            <div class="card-section-subtitle">
                Save and load your current configuration of roles and company profile
            </div>
        """, unsafe_allow_html=True)

        message_placeholder = st.empty()

        col_empty1, col1, col2, col_empty2 = st.columns([3, 1, 1, 3])

        with col1:
                if  st.button( "💾 Save", width='stretch'):
                    save_company_state()
                    message_placeholder.success("Company state saved successfully.")

        with col2:
                if  st.button( "📂 Load", width='stretch'):
                     load_company_state()
                     #message_placeholder.success("Company state loaded successfully.")


##############################################################

def apply_loaded_company_state():
    if "loaded_company_state" not in st.session_state:
        return

    state   = st.session_state.pop("loaded_company_state")
    profile = state.get("company_profile", {})

    st.session_state["organization_size"]       = profile.get("organization_size", "Medium (50-250 employees)")
    st.session_state["industry_sector"]         = profile.get("industry_sector", "Financial Services")
    st.session_state["security_team_size"]      = profile.get("security_team_size", 5)
    st.session_state["business_criticality"]    = profile.get("business_criticality", "High")
    st.session_state["regulatory_environment"]  = profile.get("regulatory_environment", ["GDPR", "NIS2"])
    st.session_state["target_maturity"]         = profile.get("target_maturity", "Advanced")

    st.session_state["current_roles"] = state.get("current_roles", [])

##############################################################

def load_company_state():
    try:
        with open(COMPANY_JSON_PATH, "r", encoding="utf-8") as f:
            company_state = json.load(f)

        st.session_state["loaded_company_state"] = company_state
        st.session_state.company_profile = company_state.get("company_profile", {})
        st.session_state.current_roles = company_state.get("current_roles", [])

        st.toast("Company state loaded successfully.", icon="📂")
        st.rerun()

        return company_state

    except FileNotFoundError:
        st.error("No saved company state found.")
        return None
    
##############################################################

def save_company_state():
    company_state = {
        "company_profile": st.session_state.get("company_profile", {}),
        "current_roles": st.session_state.get("current_roles", [])
    }

    with open(COMPANY_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(company_state, f, indent=4, ensure_ascii=False)



#######################################################################

def card_html(title,main,sub,current,total,target=None,sub2=None):
   
    if target is None or target == current:
        bar = coverage_bar_html(current, total)
    else:
        bar = transition_bar_html(current, target, total)

    if sub2 is None:
        sub_html = f'<div class="cov-metric-sub two-lines">{sub}</div>'
    else:
        sub_html = (
            f'<div class="cov-metric-sub two-lines">'
            f'{sub}<br>{sub2}'
            f'</div>'
        )

    return (
        f'<div class="cov-card yellow">'
        f'<div class="cov-card-label">{title}</div>'
        f'<div class="cov-metric-main">{main}</div>'
        f'{sub_html}'
        f'{bar}'
        f'</div>'
    )
#######################################################################

def coverage_ui(role_list, current_cov, nodes, adj=None):

    num_roles           = len(role_list)

    task_coverage       = len(current_cov["tasks"])
    skill_coverage      = len(current_cov["skills"])
    knowledge_coverage  = len(current_cov["knowledge"])

    work_roles      = len([n for n in nodes.values() if n.type == "work_role"])
    tasks           = len([n for n in nodes.values() if n.type == "task"])
    knowledges      = len([n for n in nodes.values() if n.type == "knowledge"])
    skills          = len([n for n in nodes.values() if n.type == "skill"])

    duplicates = None
    if adj and num_roles > 1:
        duplicates = frameworkNice.calculate_unique_and_duplicates(role_list, current_cov, nodes, adj)

    roles_card = card_html(
        "Work Roles", f"{num_roles} / {work_roles}",
        "Current workforce roles",num_roles, work_roles,
    )

    if duplicates:
        duplicate_tasks = duplicates["tasks"]
       

        tasks_card = card_html(
            "Tasks",
            f"{duplicate_tasks['unique']} unique",
            f"Duplicates: {duplicate_tasks['duplicated']}",
            task_coverage,
            tasks,
            None,
            f"Efficiency {duplicate_tasks['efficiency']:.0f}%",
        )

        duplicate_knowledge = duplicates["knowledge"]
        knowledge_card = card_html(
            "Knowledge",
            f"{duplicate_knowledge['unique']} unique",
            f"Duplicates: {duplicate_knowledge['duplicated']}",
            knowledge_coverage,
            knowledges,
            None,
            f"Efficiency {duplicate_knowledge['efficiency']:.0f}%",
        )

        duplicate_skills = duplicates["skills"]
        skills_card = card_html(
            "Skills",
            f"{duplicate_skills['unique']} unique",
            f"Duplicates: {duplicate_skills['duplicated']}",
            skill_coverage,
            skills,
            None,
            f"Efficiency {duplicate_skills['efficiency']:.0f}%",
        )

    else:
        tasks_card = card_html(
            "Tasks",
            f"{task_coverage}",
            "Covered tasks",
            task_coverage,
            tasks
        )

        knowledge_card = card_html(
            "Knowledge",
            f"{knowledge_coverage}",
            "Covered knowledge",
            knowledge_coverage,
            knowledges
        )

        skills_card = card_html(
            "Skills",
            f"{skill_coverage}",
            "Covered skills",
            skill_coverage,
            skills
        )

    cards_html = roles_card + tasks_card + knowledge_card + skills_card

    st.markdown(f"""
    <h3>Current Organizational Coverage</h3>
    <div class="cov-cards">{cards_html}</div>
    """, unsafe_allow_html=True)

    #overall = calculate_overall_coverage(
    #    num_roles, work_roles,
    #    task_coverage, tasks,
    #    knowledge_coverage, knowledges,
    #    skill_coverage, skills
    #)

    #baseline_score_card(overall)
    #category_coverage_ui(role_list, nodes)

   

def get_color(pct):
    if pct < 25:
        return "#ff4b4b"      # rojo
    elif pct < 50:
        return "#ff9800"      # naranja
    elif pct < 75:
        return "#ffc107"      # amarillo
    else:
        return "#4caf50"      # verde

    
def coverage_bar(title, current, total):
    pct = (current / total * 100) if total > 0 else 0
    color = get_color(pct)

    html = f"""<div style="margin-bottom:15px;"><div style="display:flex;justify-content:space-between;"><span><b>{title}</b></span><span>{current} / {total} ({pct:.1f}%)</span></div><div style="width:100%;height:16px;background:#2a2d3a;border-radius:8px;overflow:hidden;margin-top:4px;"><div style="width:{pct:.1f}%;height:100%;background:{color};"></div></div></div>"""
    
    return html


def coverage_bar_html(current, total):
    pct = (current / total * 100) if total > 0 else 0
    color = get_color(pct)

    return (
        f'<div class="coverage-header">'
        f'<span>{current} / {total}</span>'
        f'<span>{pct:.1f}%</span>'
        f'</div>'
        f'<div class="progress-bg">'
        f'<div class="progress-fill" style="width:{pct:.1f}%; background:{color};"></div>'
        f'</div>'
    )



def metric_card_html(title, main, sub, bar_html):
    return (
        f'<div class="card yellow">'
        f'<div class="card-label">{title}</div>'
        f'<div class="metric-main">{main}</div>'
        f'<div class="metric-sub">{sub}</div>'
        f'{bar_html}'
        f'</div>'
    )


def transition_bar_html(current, target, total):
    current_pct = (current / total * 100) if total > 0 else 0
    target_pct = (target / total * 100) if total > 0 else 0

    current_pct = min(current_pct, 100)
    target_pct = min(target_pct, 100)

    gain = target - current
    gain_pct = target_pct - current_pct

    gain_text = f"{gain:+d}"
    gain_pct_text = f"{gain_pct:+.1f} pp"

    return (
        f'<div class="coverage-header">'
        f'<span>{current} → {target} / {total}</span>'
        f'<span>{target_pct:.1f}% ({gain_pct_text})</span>'
        f'</div>'

        f'<div class="transition-bg">'
        f'<div class="transition-target" style="width:{target_pct:.1f}%;"></div>'
        f'<div class="transition-current" style="width:{current_pct:.1f}%;"></div>'
        f'</div>'

        f'<div class="transition-gain">'
        #f'Gain: {gain_text}'
        f'</div>'
    )
#################################

def baseline_score_card(overall):
    maturity, color = frameworkNice.baseline_maturity(overall)

    st.markdown(f"""
    <div class="card blue" style="margin-bottom:1.5rem;">
        <div class="card-label">Overall NICE Coverage</div>
        <div class="card-value">{overall:.1f}%</div>
        <div class="card-sub">
            Baseline maturity:
            <span style="color:{color}; font-weight:700;">{maturity}</span>
        </div>
        <div class="progress-bg" style="margin-top:1rem;">
            <div class="progress-fill" style="width:{overall:.1f}%; background:{color};"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


#################################

