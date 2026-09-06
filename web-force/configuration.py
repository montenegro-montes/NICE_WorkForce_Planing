import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PATH_DATA = str(PROJECT_ROOT / "data")
NICE_json = "v2-2-0_nf_components.json"
NICE_URL  = "https://csrc.nist.gov/csrc/media/Projects/cprt/documents/nice/"
ROLES_CSV = "role_costs.csv"
COMPANY_JSON = "company_state.json"

ROLES_CSV_PATH      = os.path.join(PATH_DATA, ROLES_CSV)
NICE_JSON_PATH      = os.path.join(PATH_DATA, NICE_json)
COMPANY_JSON_PATH   = os.path.join(PATH_DATA, COMPANY_JSON)

MODEL_PATH = os.path.join(PATH_DATA, "all_models")
YEAR_PATH  = 2024
ROLES_PATH = "roles"
TASKS_PATH = "tasks"

#SCENARIO_TASKS_CSV = "scenario_tasks_2024_A_attack_bert.csv"
#SCENARIO_ROLES_CSV = "enisa_roles_2024_A_attack_bert.csv"

#SCENARIO_TASKS_CSV  = "enisa_tasks_attackbert.csv"
#SCENARIO_ROLES_CSV  = "enisa_roles_attackbert.csv"    

#SCENARIO_TASKS_PATH = os.path.join(PATH_DATA, SCENARIO_TASKS_CSV)
#SCENARIO_ROLES_PATH = os.path.join(PATH_DATA, SCENARIO_ROLES_CSV)

def get_scenario_model_path(year, variant, model):
    """
    Constructs the path to the scenario model based on the year, model, and variant.
    
    Args:
        year (int): The year of the scenario.
        model (str): The model name.
        variant (str): The variant of the model.        
    """
    scenario_model_path = os.path.join(MODEL_PATH,  str(year), "tasks", "scenario_tasks_" + str(year)+"_" + variant+"_"+ model.lower()+".csv")
    #print(f"Scenario model path: {scenario_model_path}")
    roles_model_path = os.path.join(MODEL_PATH, str(year), "roles", "enisa_roles_" + str(year)+ "_" + variant+"_" + model.lower()+".csv")
    #print(f"Roles model path: {roles_model_path}")

    return scenario_model_path, roles_model_path