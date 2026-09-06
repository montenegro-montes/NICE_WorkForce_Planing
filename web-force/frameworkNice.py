import re
import os
import json
from collections import Counter
from urllib.request import Request, urlopen
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass

# -------------------------- Data model --------------------------
@dataclass(frozen=True)
class Node:
    id: str                 # element_identifier
    type: str               # element_type
    title: str              # title
    text: str               # text

@dataclass(frozen=True)
class RoleCost:
    role_id: str
    hiring_cost: float
    training_cost: float
    outsourcing_cost: float
    time_to_hire_months: int
    certification_cost: float
    criticality_score: float
    risk_impact: float


# -------------------------- Load --------------------------

def load_local(local_path: str) -> Dict[str, Any]:
    with open(local_path, "r", encoding="utf-8") as f:
        return json.load(f)

def load_url(url: str) -> Dict[str, Any]:
    req = Request(url, headers={"User-Agent": "Mozilla/5.0 (NICE-Toolkit)"})
    with urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode("utf-8"))

def load_nice(url: str, local_path: Optional[str] = None) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    if local_path and os.path.exists(local_path):
        data = load_local(local_path)
    else:
        data = load_url(url)

    if isinstance(data, dict) and "response" in data:
        root = data["response"].get("elements", {})
        elems = root.get("elements", [])
    else:
        root = data
        elems = data.get("elements", [])

    if not isinstance(elems, list):
        raise ValueError("Expected elements to be a list")
    return elems, root

########################################
## Load NICE Framework Data
########################################

def load_framework_data(url: str, local_path: Optional[str] = None):
    """Load and cache NICE Framework data from local file"""
    # Use provided url; call load_nice with or without local_path to avoid passing None
    if local_path:
        elements, root = load_nice(url, local_path)
    else:
        elements, root = load_nice(url)
    
    nodes = build_node_index(elements)
    edges = build_edges(root, nodes)
    adj = build_adjacency(edges)

    doc_meta: Dict[str, Any] = {}
    if isinstance(root, dict) and "documents" in root and isinstance(root["documents"], list) and root["documents"]:
        first_doc = root["documents"][0]
        if isinstance(first_doc, dict):
            doc_meta = {
                "doc_identifier": first_doc.get("doc_identifier", ""),
                "name": first_doc.get("name", ""),
                "version": first_doc.get("version", "")
            }
    
    return nodes, edges, adj, doc_meta

#####################################

def get_role_list(nodes: Dict[str, Node]) -> List[str]:
    """Extract all work roles from nodes"""
    import re
    return sorted([nid for nid, n in nodes.items() 
                   if n.type == "work_role" and re.match(r"^[A-Z]{2}-WRL-\d{3}$", nid)])

#########
def getCategory(role_id: str) -> str:
    """Extract category from role ID (e.g., 'DD' from 'DD-WRL-002')"""
    match = re.match(r"^([A-Z]{2})-WRL-\d{3}$", role_id)
    if not match:
        return "Unknown"

    category = match.group(1)
    return {
        "OG": "Oversight and Governance (OG)",
        "DD": "Design and Development (DD)",
        "IO": "Implementation and Operation (IO)",
        "PD": "Protection and Defense (PD)",
        "IN": "Investigation (IN)"
    }.get(category, "Unknown")



#################

def calculate_overall_coverage(num_roles, work_roles,
                               task_coverage, tasks,
                               knowledge_coverage, knowledges,
                               skill_coverage, skills):

    role_pct = (num_roles / work_roles * 100) if work_roles else 0
    task_pct = (task_coverage / tasks * 100) if tasks else 0
    knowledge_pct = (knowledge_coverage / knowledges * 100) if knowledges else 0
    skill_pct = (skill_coverage / skills * 100) if skills else 0

    overall = (
        role_pct * 0.20 +
        task_pct * 0.30 +
        knowledge_pct * 0.25 +
        skill_pct * 0.25
    )

    return overall

def baseline_maturity(overall):
    if overall < 20:
        return "Initial", "#ff4b4b"
    elif overall < 40:
        return "Developing", "#ff9800"
    elif overall < 60:
        return "Defined", "#ffc107"
    elif overall < 80:
        return "Managed", "#8bc34a"
    else:
        return "Optimized", "#4caf50"
    
########

from collections import Counter

category_names = {
    "OG": "Oversight and Governance ",
    "DD": "Design and Development",
    "IO": "Implementation and Operation",
    "PD": "Protection and Defense",
    "IN": "Investigation"
}
 
def get_category_distribution(role_list, nodes=None):
    counts = Counter()

    for role_id in role_list:
        cat = role_id.split("-")[0].strip()
        counts[cat] += 1

    return counts


category_names = {
        "OG": "Oversight and Governance ",
        "DD": "Design and Development",
        "IO": "Implementation and Operation",
        "PD": "Protection and Defense",
        "IN": "Investigation"
    }

categories = ["OG", "DD", "IO", "PD", "IN"]



#################

def calculate_coverage(role_set, nodes: Dict[str, Node], adj: Dict[str, Set[str]]) -> Dict[str, Set[str]]:
    """Calculate task, skill, and knowledge coverage for a set of roles."""
    role_set = set(role_set) if not isinstance(role_set, set) else role_set
    T, S, K = set(), set(), set()
    for r in role_set:
        if r in nodes:
            c = role_coverage(r, adj, nodes, depth=5)
            T |= c["tasks"]
            S |= c["skills"]
            K |= c["knowledge"]
    return {"tasks": T, "skills": S, "knowledge": K}


##############################################################

def calculate_unique_and_duplicates(role_list, current_cov, nodes, adj):
    """Calcula items únicos y duplicados entre roles"""

    # Contador de apariciones de cada item
    task_count = {}
    skill_count = {}
    knowledge_count = {}
    
    # Para cada rol, contar sus items
    for role in role_list:
        role_cov = role_coverage(role, adj, nodes, depth=5)
        
        for task in role_cov.get("tasks", []):
            task_count[task] = task_count.get(task, 0) + 1
        for skill in role_cov.get("skills", []):
            skill_count[skill] = skill_count.get(skill, 0) + 1
        for knowledge in role_cov.get("knowledge", []):
            knowledge_count[knowledge] = knowledge_count.get(knowledge, 0) + 1
    
    # Calcular únicos vs duplicados
    tasks_unique        = len([t for t, c in task_count.items() if c == 1])
    tasks_duplicated    = len([t for t, c in task_count.items() if c > 1])
    tasks_efficiency    = (tasks_unique / len(current_cov["tasks"]) * 100) if len(current_cov["tasks"]) > 0 else 0
    
    skills_unique       = len([s for s, c in skill_count.items() if c == 1])
    skills_duplicated   = len([s for s, c in skill_count.items() if c > 1])
    skills_efficiency   = (skills_unique / len(current_cov["skills"]) * 100) if len(current_cov["skills"]) > 0 else 0
    
    knowledge_unique     = len([k for k, c in knowledge_count.items() if c == 1])
    knowledge_duplicated = len([k for k, c in knowledge_count.items() if c > 1])
    knowledge_efficiency = (knowledge_unique / len(current_cov["knowledge"]) * 100) if len(current_cov["knowledge"]) > 0 else 0
    
    return {
        "tasks": {"unique": tasks_unique, "duplicated": tasks_duplicated, "efficiency": tasks_efficiency},
        "skills": {"unique": skills_unique, "duplicated": skills_duplicated, "efficiency": skills_efficiency},
        "knowledge": {"unique": knowledge_unique, "duplicated": knowledge_duplicated, "efficiency": knowledge_efficiency}
    }

def calculate_efficiency(role_list, nodes, adj):
    if not role_list:
        return 0

    cov = calculate_coverage(role_list, nodes, adj)

    total_covered = (
        len(cov["tasks"]) +
        len(cov["knowledge"]) +
        len(cov["skills"])
    )

    return total_covered / len(role_list)


def compare_categories(current_roles, target_roles):
    current_categories = {
        role_id.split("-")[0]
        for role_id in current_roles
    }

    target_categories = {
        role_id.split("-")[0]
        for role_id in target_roles
    }

    return {
        "add": target_categories - current_categories,
        "remove": current_categories - target_categories,
        "keep": current_categories & target_categories
    }

##########################################
#
#########################################
def calculate_impact(
    coverage_gain,
    cat_gap,
    target_cov,
    current_cov,
    tasks_total,
    knowledge_total,
    skills_total,
    current_efficiency,
    target_efficiency
):
    coverage_score = min(coverage_gain / 20 * 40, 40)

    new_categories = len(cat_gap["add"])
    category_score = min(new_categories / 5 * 25, 25)

    tasks_gain = len(target_cov["tasks"]) - len(current_cov["tasks"])
    knowledge_gain = len(target_cov["knowledge"]) - len(current_cov["knowledge"])
    skills_gain = len(target_cov["skills"]) - len(current_cov["skills"])

    capability_score = (
        tasks_gain / tasks_total +
        knowledge_gain / knowledge_total +
        skills_gain / skills_total
    ) / 3 * 25

    efficiency_delta = current_efficiency - target_efficiency
    penalty = max(0, efficiency_delta)

    impact = (
        coverage_score
        + category_score
        + capability_score
        - penalty
    )


    return max(0, min(100, impact))


##############################################################
#
#
##############################################################

def compute_score(
    current_cov,
    new_cov,current_roles,
    candidate_role,
    nodes,adj,
    profile,
    total_tasks,
    total_skills,
    total_knowledge,
):
    """
    Multi-criteria recommendation score (0-100)
    """

    # ----------------------------------------------------
    # Coverage Gain
    # ----------------------------------------------------
    tasks_gain = len(new_cov["tasks"]) - len(current_cov["tasks"])
    skills_gain = len(new_cov["skills"]) - len(current_cov["skills"])
    knowledge_gain = len(new_cov["knowledge"]) - len(current_cov["knowledge"])

    coverage_gain = (
        tasks_gain / total_tasks +
        skills_gain / total_skills +
        knowledge_gain / total_knowledge
    ) / 3


    # ----------------------------------------------------
    # Novelty
    # ----------------------------------------------------
    role_cov = role_coverage(candidate_role, adj, nodes)

    total_items = (
        len(role_cov["tasks"])
        + len(role_cov["skills"])
        + len(role_cov["knowledge"])
    )

    new_items = (
        tasks_gain +
        skills_gain +
        knowledge_gain
    )

    novelty = new_items / total_items if total_items else 0


    # ----------------------------------------------------
    # Category Gap Reduction
    # ----------------------------------------------------
    current_categories = set(r.split("-")[0] for r in current_roles)

    candidate_category = candidate_role.split("-")[0]

    category_gain = 1 if candidate_category not in current_categories else 0


    # ----------------------------------------------------
    # Profile Alignment
    # ----------------------------------------------------
    if profile == "SOC":

        preferred = {"PD", "IN", "IO"}

    elif profile == "GRC":

        preferred = {"OG", "DD"}

    else:

        preferred = {"PD", "IN", "IO", "OG", "DD"}

    profile_alignment = 1 if candidate_category in preferred else 0


    # ----------------------------------------------------
    # Redundancy
    # ----------------------------------------------------
    redundancy = 1 - novelty


    # ----------------------------------------------------
    # Final score
    # ----------------------------------------------------
    score = (
        0.45 * coverage_gain +
        0.20 * novelty +
        0.15 * category_gain +
        0.10 * profile_alignment -
        0.10 * redundancy
    ) * 100

    return {
        "score": score,
        "coverage": coverage_gain,
        "novelty": novelty,
        "category_gain": category_gain,
        "profile_alignment": profile_alignment,
        "redundancy": redundancy,
    }



############
#
############


def normalize_weights(weights: Dict[str, float]) -> Dict[str, float]:
    total = (
        weights.get("tasks", 0)
        + weights.get("skills", 0)
        + weights.get("knowledge", 0)
    )

    if total == 0:
        return {
            "tasks": 1 / 3,
            "skills": 1 / 3,
            "knowledge": 1 / 3,
        }

    return {
        "tasks": weights.get("tasks", 0) / total,
        "skills": weights.get("skills", 0) / total,
        "knowledge": weights.get("knowledge", 0) / total,
    }

###############
#
##############




###############
#
##############


def compute_weighted_coverage_gain(
    tasks_gain: int,
    skills_gain: int,
    knowledge_gain: int,
    total_tasks: int,
    total_skills: int,
    total_knowledge: int,
    weights: Dict[str, float],
) -> float:
    w = normalize_weights(weights)

    return (
        w["tasks"] * (tasks_gain / total_tasks if total_tasks else 0)
        + w["skills"] * (skills_gain / total_skills if total_skills else 0)
        + w["knowledge"] * (knowledge_gain / total_knowledge if total_knowledge else 0)
    )


def calculate_weighted_coverage_pct(
    cov: Dict[str, Set[str]],
    total_tasks: int,
    total_skills: int,
    total_knowledge: int,
    weights: Dict[str, float],
) -> float:
    """Return weighted objective coverage as percentage points."""
    return 100 * compute_weighted_coverage_gain(
        len(cov["tasks"]),
        len(cov["skills"]),
        len(cov["knowledge"]),
        total_tasks,
        total_skills,
        total_knowledge,
        weights,
    )

###############
#
##############

def compute_capability_balance(
    tasks_gain: int,
    skills_gain: int,
    knowledge_gain: int,
    total_tasks: int,
    total_skills: int,
    total_knowledge: int,
    weights: Dict[str, float],
) -> float:
    """Return balance across comparable, normalized capability gains."""
    gains = {
        "tasks": tasks_gain / total_tasks if total_tasks else 0,
        "skills": skills_gain / total_skills if total_skills else 0,
        "knowledge": knowledge_gain / total_knowledge if total_knowledge else 0,
    }

    normalized_weights = normalize_weights(weights)
    active = [k for k, v in normalized_weights.items() if v > 0]

    if not active:
        return 0

    selected_gains = [gains[k] for k in active]

    total_gain = sum(selected_gains)

    if total_gain == 0:
        return 0

    max_gain = max(selected_gains)
    min_gain = min(selected_gains)

    return 1 - ((max_gain - min_gain) / total_gain)

######################################################
# Recommendation:
# coverage + novelty + category_gap + balance
######################################################
def adaptive_role_score(
    cov: Dict[str, Set[str]],
    tasks_gain: int,
    skills_gain: int,
    knowledge_gain: int,
    covered_tasks: Set[str],
    covered_skills: Set[str],
    covered_knowledge: Set[str],
    total_tasks: int,
    total_skills: int,
    total_knowledge: int,
    category: str,
    current_categories: Set[str],
    preferred_categories: Set[str],
    weights: Dict[str, float],
    score_weights: Dict[str, float] | None = None,
) -> Dict:

    default_score_weights = {
        "F": 0.50,
        "N": 0.25,
        "G": 0.20,
        "B": 0.05,
    }
    configured_score_weights = default_score_weights.copy()
    if score_weights is not None:
        configured_score_weights.update(score_weights)

    if any(value < 0 for value in configured_score_weights.values()):
        raise ValueError("Recommendation score coefficients must be non-negative")

    coefficient_total = sum(configured_score_weights.values())
    if coefficient_total <= 0:
        raise ValueError("At least one recommendation score coefficient must be positive")

    normalized_score_weights = {
        component: value / coefficient_total
        for component, value in configured_score_weights.items()
    }

    coverage_gain = compute_weighted_coverage_gain(
        tasks_gain,
        skills_gain,
        knowledge_gain,
        total_tasks,
        total_skills,
        total_knowledge,
        weights,
    )

    overlap = (
        len(cov["tasks"] & covered_tasks)
        + len(cov["skills"] & covered_skills)
        + len(cov["knowledge"] & covered_knowledge)
    )

    total_items = (
        len(cov["tasks"])
        + len(cov["skills"])
        + len(cov["knowledge"])
    )

    redundancy = overlap / total_items if total_items else 0
    novelty = 1 - redundancy

    category_gap = 1 if category not in current_categories else 0
    profile_alignment = 1 if category in preferred_categories else 0

    balance = compute_capability_balance(
        tasks_gain,
        skills_gain,
        knowledge_gain,
        total_tasks,
        total_skills,
        total_knowledge,
        weights,
    )

    # Profile alignment is an eligibility condition in the recommenders, not
    # a score component. Novelty already equals 1 - redundancy, so applying a
    # second redundancy penalty would count the same effect twice.
    score = 100 * (
        normalized_score_weights["F"] * coverage_gain
        + normalized_score_weights["N"] * novelty
        + normalized_score_weights["G"] * category_gap
        + normalized_score_weights["B"] * balance
    )

    return {
        "score": max(0, min(100, score)),
        "coverage_gain": coverage_gain * 100,
        "novelty": novelty * 100,
        "redundancy": redundancy * 100,
        "category_gap": category_gap,
        "profile_alignment": profile_alignment,
        "balance": balance * 100,
        "tasks_gain": tasks_gain,
        "skills_gain": skills_gain,
        "knowledge_gain": knowledge_gain,
        "score_weights": normalized_score_weights,
    }

################


def build_node_index(elements: List[Dict[str, Any]]) -> Dict[str, Node]:
    idx: Dict[str, Node] = {}
    for e in elements:
        if not isinstance(e, dict):
            continue
        eid = e.get("element_identifier")
        etype = e.get("element_type")
        if not isinstance(eid, str) or not isinstance(etype, str):
            continue
        idx[eid] = Node(
            id=eid,
            type=etype,
            title=e.get("title", "") if isinstance(e.get("title"), str) else "",
            text=e.get("text", "") if isinstance(e.get("text"), str) else "",
        )
    return idx


# -------------------------- Relationship extraction (semantic) --------------------------

def looks_like_id(s: str) -> bool:
    # Work role IDs like OG-WRL-001, PD-WRL-007; others like T0001, S0001, K0001, etc.
    return bool(re.match(r"^[A-Z]{2}-WRL-\d{3}$", s) or re.match(r"^[A-Z]\d{3,6}$", s))

def find_relationship_lists(obj: Any) -> List[List[Dict[str, Any]]]:
    """
    Search the whole JSON subtree (root) for list-of-dicts that look like relationships:
    dicts containing (source, target) IDs.
    """
    candidates: List[List[Dict[str, Any]]] = []

    def walk(x: Any):
        if isinstance(x, dict):
            for v in x.values():
                walk(v)
        elif isinstance(x, list):
            # relationship list heuristic: list of dicts with 2+ id-like fields
            if x and all(isinstance(it, dict) for it in x):
                # check first few items
                sample = x[:5]
                score = 0
                for it in sample:
                    vals = [vv for vv in it.values() if isinstance(vv, str) and looks_like_id(vv)]
                    if len(vals) >= 2:
                        score += 1
                if score >= max(1, len(sample)//2):
                    candidates.append(x)  # type: ignore
            for it in x:
                walk(it)

    walk(obj)
    return candidates

def build_edges(root: Dict[str, Any], node_index: Dict[str, Node]) -> Set[Tuple[str, str]]:
    """
    Build directed edges (src_id, dst_id) using *actual relationship objects* discovered in JSON.
    We only accept edges where both ends are known node identifiers.
    """
    rel_lists: List[List[Dict[str, Any]]] = []
    if isinstance(root, dict) and "relationships" in root and isinstance(root["relationships"], list):
        rel_lists.append(root["relationships"])
    else:
        rel_lists = find_relationship_lists(root)

    edges: Set[Tuple[str, str]] = set()

    def extract_pairs(rel: Dict[str, Any]) -> List[Tuple[str, str]]:
        # try common field names
        keys_src = ["source", "source_id", "source_identifier", "source_element_identifier", "from", "from_id"]
        keys_dst = ["target", "target_id", "target_identifier", "target_element_identifier", "dest_element_identifier", "destination_element_identifier", "to", "to_id"]

        srcs = [rel.get(k) for k in keys_src if isinstance(rel.get(k), str)]
        dsts = [rel.get(k) for k in keys_dst if isinstance(rel.get(k), str)]

        pairs: List[Tuple[str, str]] = []
        for s in srcs:
            for t in dsts:
                if s in node_index and t in node_index:
                    pairs.append((s, t))
        # fallback: take any two known node ids in dict values
        if not pairs:
            ids = [v for v in rel.values() if isinstance(v, str) and v in node_index]
            if len(ids) >= 2:
                pairs.append((ids[0], ids[1]))
        return pairs

    for rel_list in rel_lists:
        for rel in rel_list:
            if not isinstance(rel, dict):
                continue
            for (s, t) in extract_pairs(rel):
                edges.add((s, t))

    return edges

def build_adjacency(edges: Set[Tuple[str, str]]) -> Dict[str, Set[str]]:
    adj: Dict[str, Set[str]] = {}
    for s, t in edges:
        adj.setdefault(s, set()).add(t)
    return adj


# -------------------------- Traversal: Role → Task → Skill → Knowledge --------------------------

def bfs_to_types(start: str, adj: Dict[str, Set[str]], nodes: Dict[str, Node], want_types: Set[str], max_depth: int = 4) -> Set[str]:
    out: Set[str] = set()
    seen: Set[str] = {start}
    q: List[Tuple[str, int]] = [(start, 0)]
    while q:
        cur, d = q.pop(0)
        if d >= max_depth:
            continue
        for nxt in adj.get(cur, set()):
            if nxt in seen:
                continue
            seen.add(nxt)
            n = nodes.get(nxt)
            if n and n.type in want_types:
                out.add(nxt)
            q.append((nxt, d + 1))
    return out

def role_coverage(role_id: str, adj: Dict[str, Set[str]], nodes: Dict[str, Node], depth: int = 5) -> Dict[str, Set[str]]:
    return {
        "tasks": bfs_to_types(role_id, adj, nodes, {"task"}, max_depth=depth),
        "skills": bfs_to_types(role_id, adj, nodes, {"skill"}, max_depth=depth),
        "knowledge": bfs_to_types(role_id, adj, nodes, {"knowledge"}, max_depth=depth),
    }


def run_optimization(nice_json, budget, focus):
    # 1. Parsear NICE JSON
    #roles = parse_nice_roles(nice_json)

    # 2. Calcular gaps
    #gap = compute_gap(roles)

    # 3. Ejecutar recomendador / set cover / greedy
    #plan = optimize_team(
    #    roles=roles,
    #    budget=budget,
    #    focus=focus
    #)


    # 4. Construir DATA para el dashboard
    DATA = {
        "focus": "soc",
        "budget": 300000,
        "current_roles": ["IO-001", "OG-002"],
        "target_roles": ["IO-001", "OG-002", "PD-001"],
        "coverage": {
            "current": {"tasks": 20, "skills": 15, "knowledge": 18},
            "target": {"tasks": 45, "skills": 35, "knowledge": 40}
        },
        "gap": {
            "missing_tasks": 25,
            "missing_skills": 20,
            "missing_knowledge": 22,
            "weighted_gap_soc": 78.5,
            "weighted_gap_grc": 65.2
        },
        "role_info": {
            "IO-001": {"title": "Systems Administrator"},
            "OG-002": {"title": "Cyber Policy Analyst"},
            "PD-001": {"title": "Cyber Defense Analyst"}
        },
        "plan": [
            {
                "role_id": "PD-001",
                "title": "Cyber Defense Analyst",
                "action": "hire",
                "new_tasks": 12,
                "new_skills": 8,
                "new_knowledge": 10,
                "weighted_gain_soc": 35.0,
                "weighted_gain_grc": 20.0,
                "cost_2yr": 120000,
                "risk_impact_pct": 25
            }
        ],
        "scenarios": [
            {
                "name": "Ransomware Attack",
                "total": 20,
                "before": 6,
                "after": 15,
                "before_pct": 30,
                "after_pct": 75
            }
        ]
    }

    return DATA
