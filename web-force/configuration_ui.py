import streamlit as st
import ui
import frameworkNice
import json
from configuration import COMPANY_JSON_PATH

DEFAULT_CURRENT_ROLES = []

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

    with st.expander("Nice overview"):

        st.markdown(f"""
        <div class="section-card">          
        <!--<div class="card-section">Nice overview</div>-->
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

    with st.expander("Company Profile"):

        with st.container(key="company_profile_box"):
    
            st.markdown("""
            <!--<div class="card-section">COMPANY PROFILE</div>-->
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
                    key="regulatory_environment"
                )

            with col5:
                target_maturity = st.selectbox(
                    "Target Security Maturity",
                    ["Basic", "Intermediate", "Advanced", "Expert"],
                    key="target_maturity"
                )
            
            with col6:
                security_team_size = st.number_input(
                    "Security Team Size",
                    min_value=0,
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
# weigth_configuration
#################################

def weigth_configuration():

    if "balanced_weights" not in st.session_state:
        st.session_state.balanced_weights = {"tasks": 34, "skills": 33,"knowledge": 33,}

    if "soc_weights" not in st.session_state:
        st.session_state.soc_weights = {"tasks": 60, "skills": 25,"knowledge": 15,}
    
    if "grc_weights" not in st.session_state:
        st.session_state.grc_weights = {"tasks": 20,"skills": 30,"knowledge": 50,}

    with st.expander("Optimization Algorithm Parameters"):

     with st.container(key="weight_configuration_box"):
        
        st.markdown("""
        <!--<div class="card-section">WEIGHT CONFIGURATION</div>-->
        <div class="card-section-subtitle">
            These weights are used by the recommendation and budget optimization algorithms.
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(
            [2, 2]
        )
        with col1:
            soc_weights = weight_configuration_card(
                title="SOC Profile Weight",
                subtitle="Prioritizes operational and defensive coverage.",
                key_prefix="soc",
                default_tasks=st.session_state.soc_weights["tasks"],
                default_skills=st.session_state.soc_weights["skills"],
            )

        with col2:

            grc_weights = weight_configuration_card(
                title="GRC Profile Weight",
                subtitle="Prioritizes governance, compliance and knowledge coverage.",
                key_prefix="grc",
                default_tasks=st.session_state.grc_weights["tasks"],
                default_skills=st.session_state.grc_weights["skills"],
            )

        st.session_state.soc_weights = soc_weights
        st.session_state.grc_weights = grc_weights    

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
            st.session_state.current_roles = DEFAULT_CURRENT_ROLES.copy()
        
        nodes = st.session_state.nodes

        current_cov = frameworkNice.calculate_coverage(st.session_state.current_roles, nodes, st.session_state.adj)

        if current_cov is not None and st.session_state.current_roles:

            num_roles           = len(st.session_state.current_roles)

            task_coverage       = len(current_cov["tasks"])
            skill_coverage      = len(current_cov["skills"])
            knowledge_coverage  = len(current_cov["knowledge"])
    
            work_roles      = len([n for n in nodes.values() if n.type == "work_role"])
            tasks           = len([n for n in nodes.values() if n.type == "task"])
            knowledges      = len([n for n in nodes.values() if n.type == "knowledge"])
            skills          = len([n for n in nodes.values() if n.type == "skill"])

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

            salary_scenario = st.session_state.get("salary_scenario", "AVERAGE")
            cost_model = st.session_state.cost_model

            current_team_cost = sum(
                    cost_model.cost(role_id, salary_scenario)
                    for role_id in st.session_state.current_roles
            )

            
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
                <div class="summary-item">
                    <span class="summary-label">Current team annual cost</span>
                    <span style="color:green; font-weight:700;">${current_team_cost:,.0f}</span>
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
            cov                 = frameworkNice.calculate_coverage([role], nodes, st.session_state.adj)
            role_labels[role]   = f"{role} - {nodes[role].title} (Tasks: {len(cov['tasks'])} Knowledge: {len(cov['knowledge'])} Skills: {len(cov['skills'])} Annual Cost: ${st.session_state.cost_model.cost(role, st.session_state.get('salary_scenario', 'AVERAGE')):,.0f} )"
        if "current_roles" not in st.session_state:
            st.session_state.current_roles = DEFAULT_CURRENT_ROLES.copy()

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
                            "Skills": len(cov["skills"]),
                            "Annual Cost": f"${st.session_state.cost_model.cost(role, st.session_state.get('salary_scenario', 'AVERAGE')):,.0f}"
                        })
                    st.dataframe(role_table, width='stretch')
                else:
                    st.info("No roles added yet. Selecciona un role y pulsa 'Add role'.")

                if current_cov is not None and st.session_state.current_roles:
                    ui.coverage_ui(st.session_state.current_roles, current_cov, nodes, st.session_state.adj)
   

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


##############################################################
def weight_configuration_card(title, subtitle, key_prefix, default_tasks, default_skills):

    with st.container(border=True):
        st.markdown(f"""
        <div class="weight-title">{title}</div>
        <div class="weight-subtitle">{subtitle}</div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1, 0.7])

        with col1:
            tasks = st.slider(
                "Tasks (%)",
                0, 100,
                default_tasks,
                5,
                key=f"{key_prefix}_tasks"
            )
            st.markdown(f"""
                <div style="
                display:flex;
                justify-content:space-between;
                margin-top:-38px;
                font-size:0.8rem;
                color:#9aa3b8;">
                <span>0%</span>
                <span>{100:.0f}%</span>
                </div>
                """, unsafe_allow_html=True)

        with col2:
            max_skills = 100 - tasks

            if max_skills > 0:
                skills = st.slider(
                    "Skills (%)",
                    0,
                    max_skills,
                    min(default_skills, max_skills),
                    5,
                    key=f"{key_prefix}_skills"
                )
                st.markdown(f"""
                    <div style="
                    display:flex;
                    justify-content:space-between;
                    margin-top:-38px;
                    font-size:0.8rem;
                    color:#9aa3b8;">
                    <span>0%</span>
                    <span>{100:.0f}%</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                skills = 0
                st.markdown(f"""
                    <div class="auto-weight">
                        <div class="auto-label">Skills (%) </div>
                        <div class="auto-value">{skills}</div>
                    </div>
                    """, unsafe_allow_html=True)

        knowledge = 100 - tasks - skills

        with col3:
            st.markdown(f"""
            <div class="auto-weight">
                <div class="auto-label">Knowledge (%)</div>
                <div class="auto-value">{knowledge}</div>
            </div>
            """, unsafe_allow_html=True)

    return {
        "tasks": tasks,
        "skills": skills,
        "knowledge": knowledge
    }
