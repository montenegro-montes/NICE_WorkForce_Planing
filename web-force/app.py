import os
import tempfile
import streamlit as st

import configuration_ui
import transicion_ui
import frameworkNice
import recommendation_ui
import threat_ui
import budget_ui
import css
import costs
from configuration import PATH_DATA, NICE_json, NICE_URL, ROLES_CSV, ROLES_CSV_PATH, NICE_JSON_PATH, COMPANY_JSON_PATH

st.set_page_config(
    page_title="CISO DSS | Cybersecurity Workforce Planning",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "About": """
        **CISO Decision Support System**

        Decision-support platform for cybersecurity workforce planning,
        threat coverage analysis, and budget optimization using the
        NICE Workforce Framework, MITRE ATT&CK, and ENISA threat data.
        """
    }
)
st.title("🛡️ Cybersecurity Workforce Planning")
st.caption(
    "Threat-driven and cost-aware cybersecurity workforce planning"
)

if "configured" not in st.session_state:
    st.session_state.configured = False

tabs = st.tabs([
    "Configuration",
    "Workforce Transition Analysis",
    "Recommendations",
    "Budget",
    "Threat Scenarios"
])

css.load_css()


with tabs[0]:
    st.header("Initial Configuration")
    local_path   = os.path.join(PATH_DATA, NICE_json)
    local_exists = os.path.exists(local_path)
    framework_data = None
    if local_exists:
        try:
            framework_data = frameworkNice.load_framework_data(url=NICE_JSON_PATH, local_path=local_path)
            location_status = "local file"
        except Exception as exc:
            st.warning(f"Could not load the local NICE Framework: {exc}")

    if framework_data is None:
        try:
            with st.spinner("Loading NICE Framework from URL, please wait..."):
                framework_data = frameworkNice.load_framework_data(url=NICE_JSON_PATH)
            location_status = "remote URL"
        except Exception as exc:
            st.warning(f"Could not load the NICE Framework from URL: {exc}")

    if framework_data is None:
        manual_json = st.text_area("Paste NICE Framework JSON", key="manual_nice_json", height=250)
        if not manual_json.strip():
            st.info("Provide NICE Framework JSON to continue.")
            st.stop()
        try:
            with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", encoding="utf-8") as manual_file:
                manual_file.write(manual_json)
                manual_file.flush()
                framework_data = frameworkNice.load_framework_data(
                    url=NICE_JSON_PATH, local_path=manual_file.name
                )
            if not framework_data[0]:
                raise ValueError("The JSON must contain NICE Framework elements.")
            location_status = "manual JSON input"
        except Exception as exc:
            st.error(f"Could not load the supplied NICE Framework JSON: {exc}")
            st.stop()

    nodes, edges, adj, doc_meta = framework_data
    st.session_state.cost_model = costs.CostModel(ROLES_CSV_PATH)

    framework_name      = doc_meta.get("name", "unknown")
    framework_version   = doc_meta.get("version", "unknown")
    framework_info = (
        f" {framework_name} "
        f"- version {framework_version} "
        f"- {location_status}" 
    )
    if doc_meta:
        configuration_ui.nice_information(nodes,edges,framework_info)
        
    # Guardar en session_state para que sea accesible en otras tabs
    st.session_state.nodes = nodes
    st.session_state.edges = edges
    st.session_state.adj   = adj

    configuration_ui.apply_loaded_company_state();
    configuration_ui.company_profile();
    configuration_ui.weigth_configuration();
    configuration_ui.currentWorkforceStatus();
    configuration_ui.currentWorkforce(nodes);
    configuration_ui.configurationManagement();

   
def require_configuration():
    if not st.session_state.configured:
        st.warning("Please complete the Configuration tab before accessing this section.")
        st.stop()

with tabs[1]:
    #require_configuration()
    st.header("Workforce Transition Analysis")
    transicion_ui.WorkforceGapAnalysis(nodes);
    
with tabs[2]:
    #require_configuration()
    st.header("Recommendations")
    recommendation_ui.render_recommendations(nodes)

with tabs[3]:
    #require_configuration()
    st.header("Budget")
    budget_ui.render_budget(nodes)

with tabs[4]:
    #require_configuration()
    st.header("Threat Scenarios")
    threat_ui.render_threat_scenarios(nodes)
    
