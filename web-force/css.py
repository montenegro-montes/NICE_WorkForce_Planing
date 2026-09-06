import streamlit as st

def load_css():
    st.markdown("""
    <style>

    :root{
        --bg:#0f1117;
        --surface:#1a1d2e;
        --border:#2d3148;
        --accent:#2563eb;
        --accent2:#00d4ff;
        --green:#00e676;
        --red:#ff5252;
        --yellow:#ffd740;
        --text:#e8eaf6;
        --muted:#8892b0;
    }

    .stApp{
        background-color: var(--bg);
        color: var(--text);
    }

    .chart-container{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1.5rem;
        margin-bottom: 2rem;
    }

    .chart-title{
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 1rem;
        color: var(--accent2);
    }

    .metric-card{
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 1.2rem;
    }

    .metric-title{
        color: var(--muted);
        font-size: .8rem;
        text-transform: uppercase;
    }

    .metric-value{
        font-size: 2rem;
        font-weight: 700;
        color: var(--text);
    }

    h2{
        font-size:1.2rem;
        font-weight:700;
        margin-bottom:1.5rem;
        color:var(--accent2);
    }

    .cards{
        display:grid;
        grid-template-columns:repeat(auto-fit,minmax(200px,1fr));
        gap:1rem;
        margin-top:1.5rem;      
        margin-bottom:0.4rem;
    }
                
    .section-card{
        border:1px solid var(--border);
        border-top:4px solid var(--accent);
        border-radius:16px;
        padding:1.5rem;
        position:relative;
        overflow:hidden;
        background:var(--surface);
        margin-bottom:1.5rem;
    }

    

    .card{
        border:1px solid var(--border);
        border-radius:12px;
        padding:1.2rem;
        position:relative;
        overflow:hidden;
    }

    .card::before{
        content:'';
        position:absolute;
        top:0;
        left:0;
        right:0;
        height:3px;
        background:var(--accent);
    }

    .card.green::before{
        background:var(--green);
    }

    .card.red::before{
        background:var(--red);
    }

    .card.yellow::before{
        background:var(--yellow);
    }

    .card-label{
        font-size:.75rem;
        color:var(--muted);
        text-transform:uppercase;
        letter-spacing:.08em;
        font-weight:700;
    }
    
    .card-icon{
        font-size:1.1rem;
        opacity:.75;
    }

    .card-section{
        font-size:1.75rem;
        color:var(--muted);
        text-transform:uppercase;
        letter-spacing:.08em;
        margin-bottom:1rem;
    }

    .card-section-subtitle{
        color:var(--muted);
        font-size:.85rem;
        margin-top:-0.4rem;
        margin-left:0.4rem;
        margin-bottom:1.2rem;
    }
    
    .card-section-info{
        color:var(--muted);
        font-size:1.5rem;
        margin-top:-0.4rem;
        margin-left:0.4rem;
        margin-bottom:1.2rem;
    }
                
    .card-value{
        font-size:2rem;
        font-weight:700;
        color:var(--text);
    }

    .card-sub{
        font-size:.8rem;
        color:var(--muted);
        margin-top:.3rem;
    }

    .chart-container{
        background:var(--surface);
        border:1px solid var(--border);
        border-radius:12px;
        padding:1.5rem;
        margin-bottom:2rem;
    }

    .chart-container h3{
        font-size:.95rem;
        font-weight:600;
        margin-bottom:1rem;
        color:var(--muted);
    }

    /* Side-by-side embedding coverage charts card. */
    .st-key-plot-container {
        background: var(--surface);
        border: 1px solid var(--border);
        border-top: 4px solid var(--accent);
        border-radius: 14px;
        padding: 1.35rem 1.5rem 1.5rem;
        margin-top: 2rem;
        margin-bottom: 2rem;
        overflow: hidden;
        box-shadow: 0 10px 28px rgba(0, 0, 0, 0.18);
    }

    .st-key-plot-container .card-section-info {
        color: var(--accent2);
        margin: 0 0 1rem;
    }

    .st-key-optimization-execution-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 14px;
        padding: 1.15rem 1.5rem 1.35rem;
        margin-bottom: 1.5rem;
    }

    .st-key-optimization-execution-card h4 {
        color: var(--accent2) !important;
        margin-top: 0 !important;
    }

    .st-key-optimization-results-card,
    .st-key-optimization-agreement-card,
    .st-key-optimization-roles-card,
    .st-key-optimization-gaps-card,
    .st-key-budget-selected-roles-card,
    .st-key-budget-nice-tasks-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-top: 4px solid var(--accent);
        border-radius: 14px;
        padding: 1.25rem 1.5rem 1.5rem;
        margin-bottom: 1.5rem;
        overflow: hidden;
        box-shadow: 0 10px 28px rgba(0, 0, 0, 0.16);
    }

    .st-key-optimization-results-card .card-section-info,
    .st-key-optimization-agreement-card .card-section-info,
    .st-key-optimization-roles-card .card-section-info,
    .st-key-optimization-gaps-card .card-section-info,
    .st-key-budget-selected-roles-card .card-section-info,
    .st-key-budget-nice-tasks-card .card-section-info {
        color: var(--accent2);
        margin-top: 0;
    }

    /* Streamlit tab styling */
    div[role="tablist"] > button[role="tab"] {
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: var(--text) !important;
        border: 1px solid transparent !important;
        border-radius: 0px !important;
        padding: 0.75rem 1rem !important;
        margin: 0 0.25rem !important;
    }

    div[role="tablist"] > button[role="tab"][aria-selected="true"] {
        background-color: var(--accent) !important;
        color: #ffffff !important;
        border-color: var(--accent) !important;
    }

    div[role="tablist"] > button[role="tab"]:hover {
        background-color: rgba(255, 255, 255, 0.12) !important;
    }

    /* Keep expanders readable in every interaction state. */
    div[data-testid="stExpander"] {
        background-color: var(--surface) !important;
        border: 1px solid var(--border) !important;
        border-radius: 10px !important;
        overflow: hidden;
    }

    div[data-testid="stExpander"] details,
    div[data-testid="stExpander"] details > summary {
        background-color: var(--surface) !important;
        color: var(--text) !important;
    }

    div[data-testid="stExpander"] details > summary:hover,
    div[data-testid="stExpander"] details > summary:focus,
    div[data-testid="stExpander"] details > summary:focus-visible,
    div[data-testid="stExpander"] details[open] > summary {
        background-color: #232840 !important;
        color: #ffffff !important;
        outline: none !important;
    }

    div[data-testid="stExpander"] details > summary p,
    div[data-testid="stExpander"] details > summary svg {
        color: inherit !important;
        fill: currentColor !important;
    }

    /* Mejorar visibilidad de labels en selectbox y multiselect */
    label {
        color: var(--accent2) !important;
        font-weight: 600 !important;
    }

    div[data-testid="stTextInput"] label,
    div[data-testid="stNumberInput"] label,
    div[data-testid="stSelectbox"] label,
    div[data-testid="stMultiSelect"] label,
    div[data-testid="stFileUploader"] label {
        color: var(--accent2) !important;
        font-weight: 600 !important;
    }

    /* Checkbox label and control contrast on the dark theme. */
    div[data-testid="stCheckbox"] label,
    div[data-testid="stCheckbox"] label p,
    div[data-testid="stCheckbox"] label span {
        color: var(--text) !important;
        opacity: 1 !important;
        font-weight: 600 !important;
    }

    div[data-testid="stCheckbox"] [role="checkbox"] {
        background-color: var(--bg) !important;
        border-color: var(--accent2) !important;
    }

    div[data-testid="stCheckbox"] [role="checkbox"][aria-checked="true"] {
        background-color: var(--accent) !important;
        border-color: var(--accent) !important;
    }

    /* Streamlit alerts, including st.info, on the dark theme. */
    div[data-testid="stAlert"] {
        background-color: #16243a !important;
        color: var(--text) !important;
        border: 1px solid var(--accent) !important;
        border-radius: 10px !important;
    }

    div[data-testid="stAlert"] p,
    div[data-testid="stAlert"] span,
    div[data-testid="stAlert"] div {
        color: var(--text) !important;
        opacity: 1 !important;
    }

    div[data-testid="stAlert"] svg {
        color: var(--accent2) !important;
        fill: currentColor !important;
    }

    /* Help icons and their portal-rendered tooltips. */
    span[data-testid="stTooltipIcon"],
    div[data-testid="stTooltipIcon"],
    [data-testid="stTooltipIcon"] svg {
        color: var(--accent2) !important;
        fill: currentColor !important;
        opacity: 1 !important;
    }

    div[role="tooltip"],
    div[data-baseweb="tooltip"],
    div[data-baseweb="popover"] {
        background-color: #232840 !important;
        color: #ffffff !important;
        border: 1px solid var(--accent2) !important;
        border-radius: 8px !important;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45) !important;
    }

    div[role="tooltip"] p,
    div[role="tooltip"] span,
    div[role="tooltip"] div,
    div[data-baseweb="tooltip"] p,
    div[data-baseweb="tooltip"] span,
    div[data-baseweb="tooltip"] div,
    div[data-baseweb="popover"] > div,
    div[data-baseweb="popover"] [data-testid="stMarkdownContainer"],
    div[data-baseweb="popover"] p,
    div[data-baseweb="popover"] span {
        background-color: #232840 !important;
        color: #ffffff !important;
        opacity: 1 !important;
    }

    div[role="tooltip"] > div,
    div[data-baseweb="tooltip"] > div {
        background-color: #232840 !important;
    }

                          
    /* Mejorar visibilidad de botones */
    .stButton > button {
        background-color: var(--accent) !important;
        color: #ffffff !important;
        border: 2px solid var(--accent) !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.2rem !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
    }

    .stButton > button:hover {
        background-color: var(--accent2) !important;
        border-color: var(--accent2) !important;
        transform: scale(1.02) !important;
    }

    .stButton > button:active {
        background-color: var(--accent) !important;
        box-shadow: 0 0 12px rgba(108, 99, 255, 0.5) !important;
    }

    /* Form Submit Buttons */
    .stForm button {
        background-color: var(--accent) !important;
        color: #ffffff !important;
        border: 2px solid var(--accent) !important;
        font-weight: 600 !important;
        padding: 0.6rem 1.2rem !important;
        border-radius: 8px !important;
        transition: all 0.3s ease !important;
    }

    .weight-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 1rem;
        margin-bottom: 1rem;
    }

    .weight-card h3 {
        color: var(--accent2);
        margin: 0;
        font-size: 1rem;
        font-weight: 600;
    }
    /* Coverage cards */

    .cov-cards{
        display:grid;
        grid-template-columns:repeat(auto-fit,minmax(280px,1fr));
        gap:1rem;
        margin-top:1rem;
        margin-bottom:2rem;
    }

    .cov-card{
        background:var(--surface);
        border:1px solid var(--border);
        border-radius:12px;
        padding:1.2rem;
        position:relative;
        overflow:hidden;
    }

    .cov-card::before{
        content:'';
        position:absolute;
        top:0;
        left:0;
        right:0;
        height:4px;
        background:var(--yellow);
    }

    .cov-card-label{
        font-size:.75rem;
        color:var(--muted);
        text-transform:uppercase;
        letter-spacing:.08em;
        margin-bottom:1rem;
    }
    
    .card-header{
        display:flex;
        justify-content:space-between;
        align-items:center;
        margin-bottom:0.1rem;
    }

    .cov-metric-main{
        font-size:2rem;
        font-weight:700;
        color:var(--text);
        margin-bottom:.5rem;
    }

    .cov-metric-sub{
        font-size:.85rem;
        color:var(--muted);
        margin-bottom:1rem;
    }

    .coverage-header{
        display:flex;
        justify-content:space-between;
        align-items:center;
        color:var(--text);
        font-size:.85rem;
        margin-bottom:.4rem;
    }

    .progress-bg{
        width:100%;
        height:10px;
        background:var(--border);
        border-radius:999px;
        overflow:hidden;
    }

    .progress-fill{
        height:100%;
        border-radius:999px;
    }

    .cat-card{
        background:var(--surface);
        border:1px solid var(--border);
        border-radius:12px;
        padding:1.2rem;
        border-top:4px solid var(--accent);
        margin-bottom:2rem;
    }

    .cat-row{
        margin-bottom:0.9rem;
    }

    .cat-header{
        display:flex;
        justify-content:space-between;
        align-items:center;
        margin-bottom:0.35rem;
    }

    .cat-name{
        color:var(--text);
        font-weight:700;
    }

    .cat-value{
        color:var(--muted);
        font-size:0.85rem;
    }
    
    .cat-mini-grid{
        display:grid;
        grid-template-columns:repeat(auto-fit,minmax(170px,1fr));
        gap:1rem;
        margin-bottom:2rem;
    }

    .cat-mini-card{
        background:var(--surface);
        border:1px solid var(--border);
        border-radius:12px;
        padding:1rem;
        min-height:105px;
        position:relative;
        overflow:hidden;
    }

    .cat-mini-card::before{
        content:'';
        position:absolute;
        top:0;
        left:0;
        right:0;
        height:4px;
        background:var(--border);
    }

    .cat-mini-card.active::before{
        background:var(--accent);
    }

    .cat-mini-card.empty{
        opacity:0.55;
    }

    .cat-mini-code{
        font-size:.8rem;
        color:var(--muted);
        font-weight:700;
        letter-spacing:.08em;
    }

    .cat-mini-value{
        font-size:2rem;
        font-weight:800;
        color:var(--text);
        margin-top:.3rem;
    }

    .cat-mini-name{
        font-size:.75rem;
        color:var(--muted);
        margin-top:.2rem;
        line-height:1.2;
    }

    /* Company profile card */
    .st-key-weight_configuration_box,
    .st-key-current_workforce_analysis_box,
    .st-key-configuration_management_box,
    .st-key-company_workforce_status_box,
    .st-key-company_profile_box,
    .st-key-current_workforce_box{
        background:var(--surface);
        border:1px solid var(--border);
        border-radius:12px;
        padding:1.5rem;
        margin-bottom:1.5rem;
        position:relative;
        overflow:hidden;
    }
                
    . st-key-weight_configuration_box::before,
    .st-key-current_workforce_analysis_box::before,       
    .st-key-configuration_management_box::before,
    .st-key-company_workforce_status_box::before,
    .st-key-company_profile_box::before,
    .st-key-current_workforce_box::before{
        content:'';
        position:absolute;
        top:0;
        left:0;
        right:0;
        height:4px;
        background:var(--accent);
    }
                
    .nice-summary{
        display:flex;
        justify-content:space-between;
        align-items:center;
        gap:2rem;
        padding:0.2rem ;
    }

    .nice-stat{
        text-align:center;
        flex:1;
        border-right:2px solid var(--border);
    }
 
    .nice-stat:last-child{
        border-right:none;
    }
                
    .nice-label{
        display:block;
        color:var(--muted);
        font-size:.85rem;
        font-weight:600;
        text-transform:uppercase;
        letter-spacing:.08em;
        margin-bottom:.3rem;
    }

    .nice-value{
        color:var(--text);
        font-size:2rem;
        font-weight:700;
    }
    
    .nice-value.roles{
        color:#ffd740;
    }
    
    .nice-value.tasks{
        color:#ff4081;
    }
                
    .nice-value.knowledge{
        color:#64b5f6;
    }

    .nice-value.skills{
        color:#00e676;
    }
    .nice-value.graph{
        font-size:1.5rem;
    }
                
    .summary-box{
        display:flex;
        flex-wrap:wrap;
        gap:2rem;
        padding:0.75rem 1.25rem;
        margin-bottom:1.5rem;

        background:var(--surface);
        border:1px solid var(--border);
        border-radius:12px;
    }

    .summary-item{
        display:flex;
        flex-direction:column;
        min-width:180px;
    }

    .summary-label{
        font-size:.75rem;
        text-transform:uppercase;
        letter-spacing:.08em;
        color:var(--muted);
        margin-bottom:.3rem;
    }

    .summary-value{
        font-size:1rem;
        font-weight:700;
        color:var(--text);
    }

    .summary-value.threat-summary-value-large{
        font-size:2rem;
        line-height:1.1;
    }

    .summary-value.threat-summary-value-medium{
        font-size:1.6rem;
        line-height:1.1;
    }

    .budget-proposal-summary{
        flex-wrap:nowrap;
        gap:.75rem;
    }

    .budget-proposal-summary .summary-item{
        flex:1 1 0;
        min-width:0;
    }

    .budget-proposal-summary .summary-value.threat-summary-value-large{
        font-size:1.3rem;
        white-space:nowrap;
    }

    .budget-workforce-summary,
    .budget-nice-summary{
        flex-wrap:nowrap;
        gap:.75rem;
    }

    .budget-workforce-summary .summary-item,
    .budget-nice-summary .summary-item{
        flex:1 1 0;
        min-width:0;
    }

    .budget-workforce-summary .summary-value.threat-summary-value-large{
        font-size:1.3rem;
        white-space:nowrap;
    }

    .budget-nice-summary .summary-value.threat-summary-value-large{
        font-size:2rem;
        white-space:nowrap;
    }

    .threat-summary-value-row{
        display:flex;
        align-items:baseline;
        gap:.65rem;
        flex-wrap:wrap;
    }

    .threat-summary-card .summary-item{
        min-width:0;
        width:100%;
    }

    .threat-summary-help{
        display:inline-flex;
        position:relative;
        align-items:center;
        justify-content:center;
        width:1rem;
        height:1rem;
        margin-left:.2rem;
        border:1px solid var(--accent2);
        border-radius:50%;
        color:var(--accent2);
        font-size:.7rem;
        font-weight:800;
        line-height:1;
        cursor:help;
        text-transform:none;
    }

    .threat-summary-help::after{
        content:attr(data-help);
        display:none;
        position:absolute;
        right:0;
        bottom:calc(100% + .55rem);
        z-index:1000;
        width:260px;
        padding:.65rem .75rem;
        background:#232840;
        border:1px solid var(--accent2);
        border-radius:8px;
        color:#ffffff;
        box-shadow:0 8px 24px rgba(0, 0, 0, .45);
        font-size:.78rem;
        font-weight:500;
        line-height:1.4;
        letter-spacing:normal;
        text-align:left;
        text-transform:none;
        white-space:normal;
    }

    .threat-summary-help:hover::after,
    .threat-summary-help:focus::after{
        display:block;
    }

    .st-key-optimization-agreement-card{
        overflow:visible;
    }

    .threat-summary-value-row .card-sub{
        font-size:1rem;
        line-height:1.2;
        margin-top:0;
    }

    .threat-summary-value-row .threat-summary-detail{
        color:var(--green);
        background:rgba(0, 230, 118, 0.14);
        border:1px solid rgba(0, 230, 118, 0.32);
        border-radius:999px;
        padding:.2rem .55rem;
        font-weight:700;
        opacity:1;
    }

    .summary-value.domains{
        color:var(--accent2);
    }

    .summary-value.neutral{
        color: var(--muted);
        font-style: italic;
    }
                
    .summary-value.danger{
        color:#ff5252;
    }

    .summary-value.warning{
        color:#ffc107;
    }

    .summary-value.success{
        color:#00e676;
    }

    .summary-value.excellent{
        color:#64b5f6;
        font-weight:700;
    }

    .summary-value.maturity{
        color:var(--yellow);
    }

    .summary-value.tasks{
        color:var(--yellow);
    }
                       
    .nice-badge{
        padding: 0.35rem 0.75rem;
        font-size: 0.85rem;
        font-weight: 700;
        border-radius: 999px;        
        display:inline-block;
        margin-right:6px;
        letter-spacing:.05em;
    }

    .nice-badge.covered{
        background:rgba(0,230,118,.15);
        color:#00e676;
        border:1px solid rgba(0,230,118,.35);
    }

    .nice-badge.missing{
        background:rgba(255,82,82,.15);
        color:#ff5252;
        border:1px solid rgba(255,82,82,.35);
    }

    .insight-box{
        margin-top:1rem;
        padding:1rem 1.25rem;
        border:1px solid var(--border);
        border-radius:12px;
        background:rgba(255,255,255,0.03);
    }

    .insight-title{
        display:block;
        font-size:.75rem;
        text-transform:uppercase;
        letter-spacing:.08em;
        color:var(--muted);
        margin-bottom:.4rem;
    }

    .insight-text{
        color:var(--text);
        font-weight:600;
    }

    .maturity-badge{
        display:inline-block;
        padding:0.15rem 0.45rem;
        border-radius:999px;
        font-size:0.75rem;
        font-weight:700;
        width:auto;
        min-width:auto;
        line-height:1.2;
        text-align:center;
    }
    
    .delta-badge{
        display:inline-block;
        padding:.28rem .65rem;
        margin-right:.35rem;
        margin-bottom:.35rem;
        border-radius:999px;
        font-size:.78rem;
        font-weight:700;
        white-space:nowrap;
    }

    .delta-badge.maintained{
        background:rgba(100,181,246,.12);
        color:#64b5f6;
        border:1px solid rgba(100,181,246,.35);
    }

    .delta-badge.added{
        background:rgba(0,230,118,.14);
        color:#00e676;
        border:1px solid rgba(0,230,118,.35);
    }

    .delta-badge.removed{
        background:rgba(255,82,82,.14);
        color:#ff5252;
        border:1px solid rgba(255,82,82,.35);
    }

    .delta-badge.neutral{
        background:rgba(255,255,255,.06);
        color:var(--muted);
        border:1px solid var(--border);
    }

    .transition-bg{
        position:relative;
        width:100%;
        height:10px;
        background:var(--border);
        border-radius:999px;
        overflow:hidden;
    }

    .transition-target{
        position:absolute;
        height:100%;
        background:#ff9800;
        opacity:.75;
        border-radius:999px;
    }

    .transition-current{
        position:absolute;
        height:100%;
        background:#ff4b4b;
        border-radius:999px;
    }

    .transition-gain{
        margin-top:.35rem;
        font-size:.8rem;
        color:var(--muted);
    }

    .cov-metric-sub {
        min-height: 1.4rem;
    }

    .cov-metric-sub.two-lines {
        min-height: 2.8rem;
    }
    .capability-gain-box{
        background:var(--surface);
        text-align:left;
    }

    .capability-gain-title{
        color:var(--muted);
        font-size:.75rem;
        text-transform:uppercase;
        letter-spacing:.08em;
        font-weight:700;
        margin-bottom:.7rem;
    }

    .capability-gain-values{
        display:flex;
        justify-content:center;
        gap:1rem;
        flex-wrap:wrap;
    }

    .capability-gain-item{
        display:inline-block;
        padding:.35rem .85rem;
        border-radius:999px;
        font-size:.85rem;
        font-weight:700;
    }

    .capability-gain-item.tasks{
        background:rgba(255,215,64,.15);
        color:#ffd740;
        border:1px solid rgba(255,215,64,.35);
    }

    .capability-gain-item.knowledge{
        background:rgba(100,181,246,.15);
        color:#64b5f6;
        border:1px solid rgba(100,181,246,.35);
    }

    .capability-gain-item.skills{
        background:rgba(0,230,118,.15);
        color:#00e676;
        border:1px solid rgba(0,230,118,.35);
    }

    /* Texto de los radio buttons */
    div[role="radiogroup"] label p {
        color: #e8eaf0 !important;
        font-weight: 600 !important;
    }

    /* Texto del radio seleccionado */
    div[role="radiogroup"] label:has(input:checked) p {
        color: #ffffff !important;
    }

    /* Título del radio */
    .stRadio > label {
        color: #00d9ff !important;
        font-weight: 700 !important;
    }
   
 
    /* Valor */
    .stSlider [data-testid="stThumbValue"]{
        color:#ffffff !important;
        font-weight:700 !important;
    }

                            
    .weight-card {
        background: #181b22;
        border: 1px solid #2a2f3a;
        border-radius: 16px;
        padding: 22px 24px;
        margin-bottom: 22px;
        border-top: 4px solid #6c63ff;
    }

    .weight-title {
        font-size: 1.35rem;
        font-weight: 800;
        margin-bottom: 4px;
        color: #f2f4ff;
    }

    .weight-subtitle {
        font-size: 0.9rem;
        color: #9aa3b8;
        margin-bottom: 20px;
    }

    .auto-weight{
        width:120px;
        margin:auto;
        background:#11141a;
        border:1px solid #2a2f3a;
        border-radius:14px;
        padding: 10px 12px;
        text-align:center;
    }
                
    .auto-label {
        color: #00d9ff;
        font-size: 0.85rem;
        font-weight: 700;
    }

    .auto-value {
        font-size: 1.6rem;
        font-weight: 800;
        color: #f2f4ff;
    }
    
    .recommendation-card {
        position: relative;
        display: flex;
        gap: 1.2rem;
        padding: 1rem 1.2rem;
        margin-bottom: 0.8rem;
        border: 1px solid rgba(120, 130, 180, 0.25);
        border-top: 4px solid #2f6df6;
        border-radius: 14px;
        background: rgba(15, 18, 30, 0.95);
    }
                    
    .rec-rank {
        min-width: 44px;
        height: 44px;
        border-radius: 50%;
        background: rgba(47, 109, 246, 0.18);
        border: 1px solid rgba(47, 109, 246, 0.55);
        color: #dbe4ff;
        font-weight: 800;
        font-size: 1rem;
        display: flex;
        align-items: center;
        justify-content: center;
    }

    .rec-content {
        width: 100%;
    }

    .rec-title {
        font-size: 1rem;
        font-weight: 700;
        color: #f1f5ff;
        margin-bottom: 0.2rem;
    }

    .rec-meta {
        color: #a7b0c8;
        font-weight: 600;
        margin-bottom: 0.8rem;
        font-size: 0.9rem;
    }

    .rec-metrics {
        display: flex;
        justify-content: center;   /* centra toda la fila */
        gap: 0.8rem;
        flex-wrap: wrap;
    }
                    
    .rec-metric {
        width: 220px;
        min-height: 72px;
        padding: 0.75rem;
        text-align: center;
        border: 1px solid rgba(120, 130, 180, 0.20);
        border-radius: 12px;
        background: rgba(20, 24, 36, 0.85);
    }

    .rec-metric span {
        display: block;
        color: #9fa8c0;
        font-size: 0.85rem;
        font-weight: 700;
        margin-bottom: 0.7rem;
        text-transform: uppercase;
        letter-spacing: .08em;
    }

    .rec-metric strong {
        color: #eef2ff;
        display: block;
        margin-top: .2rem;
        font-size: 1.45rem;
        font-weight: 800;
    }

    .rec-metric.score strong {
        color: #ffffff;
        font-size: 2rem;
    }
    
    .rec-metric.score {
        border-color: rgba(47, 109, 246, 0.65);
        background: rgba(47, 109, 246, 0.12);
    }
    
    .rec-metric.coverage {
        width: 220px;
        background: linear-gradient(
            180deg,
            rgba(30,70,170,.35),
            rgba(20,24,36,.95)
        );
        border: 2px solid #2f6df6;
        box-shadow: 0 0 18px rgba(47,109,246,.25);
        padding: 0.75rem;
    }
    
    .rec-metric.coverage strong {
        display: block;
        margin-top: .2rem;
        font-size: 1.5rem;
        color: #ffffff;
        font-weight: 800;
    }

    .rec-metric.coverage span {
        color: #b8d2ff;
        font-size: .85rem;
        text-transform: uppercase;
        letter-spacing: .08em;
    }
    .coverage-values{
        display:flex;
        justify-content:center;
        align-items:center;
        gap:.5rem;
        margin-top:.5rem;
    }

    .coverage-current{
        color:#b0b8d0;
        font-size:1rem;
    }

    .coverage-arrow{
        font-size:1.2rem;
        color:#5b8cff;
    }

    .coverage-new{
        color:#ffffff;
        font-size:1.45rem;
        font-weight:700;
    }

    .coverage-gain{
        margin-top:.45rem;
        color:#55d26a;
        font-size:1.5rem;
        font-weight:700;
    }            
    .rec-badge {
        display: inline-block;
        margin-left: 10px;
        padding: 4px 12px;
        background: rgba(47,109,246,.15);
        color: #9fc1ff;
        font-size: 0.8rem;
        font-weight: 600;
    }

    .metric-evolution {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: .45rem;
        margin-top: .5rem;
        font-size: 1.2rem;
        color: #b0b8d0;
        font-weight: 700;
    }

    .metric-arrow {
        color: #5b8cff;
    }

    .metric-new {
        color: #ffffff;
        font-size: 1.75rem;
        font-weight: 800;
    }

    .metric-gain {
        margin-top: .45rem;
        color: #55d26a;
        font-size: 1.5rem;
        font-weight: 800;
    }
   
    .score-bar {
        width: 100%;
        height: 6px;
        margin-top: .95rem;
        border-radius: 999px;
        background: rgba(120, 130, 180, 0.20);
        overflow: hidden;
    }

    .score-fill {
        height: 100%;
        border-radius: 999px;
        background: #2f6df6;
    }     

    .rec-metric.cost strong{
        color:#7dd3fc;   /* azul claro */
        font-size:2rem;
        font-weight:700;
        margin-bottom: .25rem;
    }
                                         
    </style>
    """, unsafe_allow_html=True)
