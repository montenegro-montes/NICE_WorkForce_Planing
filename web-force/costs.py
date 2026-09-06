from dataclasses import dataclass
import pandas as pd
import random


@dataclass
class RoleCost:
    role_id: str
    role_name: str
    mapped_job: str
    salary_model: str
    min_salary: float
    avg_salary: float
    max_salary: float
    overhead: float
    confidence: str
    source_id: str


class CostModel:

    def __init__(self, csv_file):

        df = pd.read_csv(csv_file)

        self.roles = {}

        for _, row in df.iterrows():

            self.roles[row["role_id"]] = RoleCost(
                role_id=row["role_id"],
                role_name=row["role_name"],
                mapped_job=row["mapped_job"],
                salary_model=row["salary_model"],
                min_salary=row["min_salary"],
                avg_salary=row["avg_salary"],
                max_salary=row["max_salary"],
                overhead=row["overhead"],
                confidence=row["confidence"],
                source_id=row["source_id"]
            )

    

    def cost(self, role_id, scenario="AVERAGE"):

        role = self.roles[role_id]

        if scenario == "MINIMUM":
            salary = role.min_salary

        elif scenario == "AVERAGE":
            salary = role.avg_salary

        elif scenario == "MAXIMUM":
            salary = role.max_salary

        elif scenario == "PERT":
            salary = (
                role.min_salary
                + 4 * role.avg_salary
                + role.max_salary
            ) / 6

        elif scenario == "MONTE_CARLO":
            import random
            salary = random.triangular(
                role.min_salary,
                role.max_salary,
                role.avg_salary
            )

        else:
            raise ValueError(f"Unknown scenario: {scenario}")

        return salary * (1 + role.overhead)


