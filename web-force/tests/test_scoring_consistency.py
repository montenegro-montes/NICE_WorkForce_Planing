import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import frameworkNice


class ScoringConsistencyTests(unittest.TestCase):
    def test_recommendation_score_has_true_zero_to_hundred_range(self):
        metrics = frameworkNice.adaptive_role_score(
            cov={"tasks": {"t"}, "skills": {"s"}, "knowledge": {"k"}},
            tasks_gain=1,
            skills_gain=1,
            knowledge_gain=1,
            covered_tasks=set(),
            covered_skills=set(),
            covered_knowledge=set(),
            total_tasks=1,
            total_skills=1,
            total_knowledge=1,
            category="PD",
            current_categories=set(),
            preferred_categories={"PD"},
            weights={"tasks": 1, "skills": 1, "knowledge": 1},
        )
        self.assertAlmostEqual(metrics["score"], 100.0)

    def test_redundancy_is_not_penalized_twice(self):
        metrics = frameworkNice.adaptive_role_score(
            cov={"tasks": {"old"}, "skills": set(), "knowledge": set()},
            tasks_gain=0,
            skills_gain=0,
            knowledge_gain=0,
            covered_tasks={"old"},
            covered_skills=set(),
            covered_knowledge=set(),
            total_tasks=1,
            total_skills=1,
            total_knowledge=1,
            category="PD",
            current_categories={"PD"},
            preferred_categories={"PD"},
            weights={"tasks": 1, "skills": 1, "knowledge": 1},
        )
        self.assertEqual(metrics["novelty"], 0)
        self.assertEqual(metrics["score"], 0)

    def test_recommendation_score_uses_configurable_coefficients(self):
        common = dict(
            cov={"tasks": {"new", "old"}, "skills": set(), "knowledge": set()},
            tasks_gain=1,
            skills_gain=0,
            knowledge_gain=0,
            covered_tasks={"old"},
            covered_skills=set(),
            covered_knowledge=set(),
            total_tasks=2,
            total_skills=0,
            total_knowledge=0,
            category="PD",
            current_categories=set(),
            preferred_categories={"PD"},
            weights={"tasks": 1, "skills": 0, "knowledge": 0},
        )

        coverage_only = frameworkNice.adaptive_role_score(
            **common,
            score_weights={"F": 1, "N": 0, "G": 0, "B": 0},
        )
        category_only = frameworkNice.adaptive_role_score(
            **common,
            score_weights={"F": 0, "N": 0, "G": 1, "B": 0},
        )

        self.assertAlmostEqual(coverage_only["score"], 50.0)
        self.assertAlmostEqual(category_only["score"], 100.0)

    def test_recommendation_coefficients_are_normalized_to_keep_range(self):
        metrics = frameworkNice.adaptive_role_score(
            cov={"tasks": {"t"}, "skills": {"s"}, "knowledge": {"k"}},
            tasks_gain=1,
            skills_gain=1,
            knowledge_gain=1,
            covered_tasks=set(),
            covered_skills=set(),
            covered_knowledge=set(),
            total_tasks=1,
            total_skills=1,
            total_knowledge=1,
            category="PD",
            current_categories=set(),
            preferred_categories={"PD"},
            weights={"tasks": 1, "skills": 1, "knowledge": 1},
            score_weights={"F": 50, "N": 25, "G": 20, "B": 5},
        )
        self.assertAlmostEqual(metrics["score"], 100.0)

    def test_balance_uses_normalized_dimension_gains(self):
        balance = frameworkNice.compute_capability_balance(
            tasks_gain=10,
            skills_gain=1,
            knowledge_gain=2,
            total_tasks=100,
            total_skills=10,
            total_knowledge=20,
            weights={"tasks": 1, "skills": 1, "knowledge": 1},
        )
        self.assertAlmostEqual(balance, 1.0)

    def test_budget_coverage_uses_profile_weights(self):
        coverage = {"tasks": {"t"}, "skills": set(), "knowledge": set()}
        pct = frameworkNice.calculate_weighted_coverage_pct(
            coverage,
            total_tasks=1,
            total_knowledge=1,
            total_skills=1,
            weights={"tasks": 60, "skills": 25, "knowledge": 15},
        )
        self.assertAlmostEqual(pct, 60.0)


if __name__ == "__main__":
    unittest.main()
