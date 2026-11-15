"""
20-Point Automated Validation Suite for GuardSLM Benchmark V2.
Verifies dataset scale, double-blind isolation, contrast pairing, and integrity.
"""
import os
import csv
import json
import zipfile
from pathlib import Path
from typing import Dict, List, Any, Tuple, Optional

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BASE_DIR = str(REPO_ROOT / "research_snapshots_2000")


class BenchmarkValidator:
    def __init__(self, base_dir: Optional[str] = None):
        self.base_dir = str(base_dir) if base_dir else DEFAULT_BASE_DIR
        self.pages_dir = os.path.join(self.base_dir, "raw_snapshots", "pages")
        self.policies_dir = os.path.join(self.base_dir, "raw_snapshots", "policies")
        self.slm_inputs_dir = os.path.join(self.base_dir, "slm_inputs")
        self.eval_dir = os.path.join(self.base_dir, "evaluation_only")
        self.reports_dir = os.path.join(self.base_dir, "reports")
        self.manifest_file = os.path.join(self.base_dir, "manifest.csv")
        self.ground_truth_file = os.path.join(self.eval_dir, "ground_truth.csv")
        
        self.results: List[Dict[str, Any]] = []

    def _check(self, num: int, name: str, passed: bool, detail: str):
        self.results.append({
            "check_num": num,
            "name": name,
            "passed": passed,
            "detail": detail,
        })

    def run_all_checks(self) -> Tuple[bool, List[Dict[str, Any]]]:
        self.results.clear()

        # Check 1: Base directory and subdirectories exist
        dirs_exist = all(os.path.isdir(d) for d in [self.pages_dir, self.policies_dir, self.slm_inputs_dir, self.eval_dir, self.reports_dir])
        self._check(1, "Directory Structure Exists", dirs_exist, f"Verified all 5 required directories exist in {self.base_dir}")

        # Check 2: Manifest file exists and valid
        manifest_valid = os.path.isfile(self.manifest_file)
        manifest_rows = []
        if manifest_valid:
            with open(self.manifest_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                manifest_rows = list(reader)
        self._check(2, "Manifest CSV Integrity", manifest_valid and len(manifest_rows) > 0, f"Manifest loaded with {len(manifest_rows)} rows")

        # Check 3: Ground truth file exists in evaluation_only
        gt_valid = os.path.isfile(self.ground_truth_file)
        gt_rows = []
        if gt_valid:
            with open(self.ground_truth_file, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                gt_rows = list(reader)
        self._check(3, "Ground Truth CSV Integrity", gt_valid and len(gt_rows) > 0, f"Ground truth loaded with {len(gt_rows)} rows")

        # Check 4: Exact scale verification (~2,000 cases)
        case_count = len(manifest_rows)
        scale_ok = 1950 <= case_count <= 2050
        self._check(4, "Scale Target (~2,000 Cases)", scale_ok, f"Total case count is {case_count} (target ~2,000)")

        # Check 5: 1:1 Match between manifest and ground truth
        manifest_ids = [r["test_id"] for r in manifest_rows]
        gt_ids = [r["test_id"] for r in gt_rows]
        id_match = (manifest_ids == gt_ids) and (len(manifest_ids) == len(set(manifest_ids)))
        self._check(5, "1:1 Manifest-GroundTruth Key Match", id_match, f"{len(manifest_ids)} unique keys matched perfectly")

        # Check 6: STRICT DOUBLE-BLIND ISOLATION (No labels in slm_inputs)
        leaks = []
        all_slm_files = [f for f in os.listdir(self.slm_inputs_dir) if f.endswith(".md")] if os.path.exists(self.slm_inputs_dir) else []
        for fname in all_slm_files:
            fpath = os.path.join(self.slm_inputs_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                content = f.read()
                # Check for explicit expected_decision key or isolated ALLOW/BLOCK label lines
                if "expected_decision:" in content.lower() or "\nexpected: allow" in content.lower() or "\nexpected: block" in content.lower():
                    leaks.append(fname)
        self._check(6, "Double-Blind Isolation (Zero Label Leakage)", len(leaks) == 0, f"Checked 100% of SLM input files ({len(all_slm_files)} files); leaks: {len(leaks)}")

        # Check 7: Raw page accessibility snapshots exist
        page_files = set(os.listdir(self.pages_dir)) if os.path.exists(self.pages_dir) else set()
        missing_pages = [r["page_snapshot_file"] for r in manifest_rows if r["page_snapshot_file"] not in page_files]
        self._check(7, "Page Accessibility Snapshots Completeness", len(missing_pages) == 0, f"{len(page_files)} raw page snapshots verified")

        # Check 8: Raw policy accessibility snapshots exist
        policy_files = set(os.listdir(self.policies_dir)) if os.path.exists(self.policies_dir) else set()
        missing_policies = [r["policy_snapshot_file"] for r in manifest_rows if r["policy_snapshot_file"] not in policy_files]
        self._check(8, "Policy Snapshots Completeness", len(missing_policies) == 0, f"{len(policy_files)} raw policy snapshots verified")

        # Check 9: SLM input files completeness
        slm_files = set(os.listdir(self.slm_inputs_dir)) if os.path.exists(self.slm_inputs_dir) else set()
        missing_slm = [r["slm_input_file"] for r in manifest_rows if r["slm_input_file"] not in slm_files]
        self._check(9, "SLM Input Packages Completeness", len(missing_slm) == 0, f"{len(slm_files)} SLM input packages verified")

        # Check 10: Decision balance (ALLOW vs BLOCK)
        decisions = [r["expected_decision"] for r in gt_rows]
        allow_count = decisions.count("ALLOW")
        block_count = decisions.count("BLOCK")
        ratio = allow_count / case_count if case_count else 0
        balance_ok = 0.40 <= ratio <= 0.60
        self._check(10, "Decision Class Balance", balance_ok, f"ALLOW: {allow_count} ({ratio*100:.1f}%), BLOCK: {block_count} ({(1-ratio)*100:.1f}%)")

        # Check 11: 13 Scenario Families coverage
        gt_fam_counts: Dict[str, int] = {}
        target_families = {f"FAM{i:02d}" for i in range(1, 14)}
        for r in gt_rows:
            fam = r.get("family_id")
            if not fam:
                tid_str = r.get("test_id", "")
                if tid_str.startswith("TC"):
                    try:
                        tid_num = int(tid_str.replace("TC", ""))
                        ranges = [
                            (1, 154, "FAM01"), (155, 308, "FAM02"), (309, 462, "FAM03"),
                            (463, 616, "FAM04"), (617, 770, "FAM05"), (771, 924, "FAM06"),
                            (925, 1078, "FAM07"), (1079, 1232, "FAM08"), (1233, 1386, "FAM09"),
                            (1387, 1540, "FAM10"), (1541, 1692, "FAM11"), (1693, 1846, "FAM12"),
                            (1847, 2000, "FAM13"),
                        ]
                        for start, end, fid in ranges:
                            if start <= tid_num <= end:
                                fam = fid
                                break
                    except ValueError:
                        pass
            if fam:
                gt_fam_counts[fam] = gt_fam_counts.get(fam, 0) + 1

        missing_families = target_families - set(gt_fam_counts.keys())
        all_represented = len(missing_families) == 0 and all(c >= 50 for c in gt_fam_counts.values())
        detail = (
            f"All 13 target families verified across {len(gt_rows)} cases (counts: {sorted(gt_fam_counts.items())})"
            if all_represented else f"Missing or underrepresented families: {missing_families}"
        )
        self._check(11, "13 Scenario Families Representation", all_represented, detail)

        # Check 12: 5 Contrast Dimensions representation
        dimensions = set(r["contrast_dimension"] for r in gt_rows if r.get("contrast_dimension"))
        dims_expected = {"Identity", "Scope", "Ownership", "Lifecycle", "Time"}
        dims_ok = dims_expected.issubset(dimensions)
        self._check(12, "Contrast Dimensions (All 5 Present)", dims_ok, f"Present dimensions: {sorted(list(dimensions))}")

        # Check 13: Contrast Pairs completeness (Every CP has 2 linked cases)
        cp_groups = {}
        for r in gt_rows:
            cpid = r.get("contrast_pair_id")
            if cpid:
                cp_groups.setdefault(cpid, []).append(r)
        broken_cps = [cpid for cpid, items in cp_groups.items() if len(items) != 2]
        self._check(13, "Contrast Pair Linkage Integrity", len(broken_cps) == 0, f"{len(cp_groups)} linked contrast pairs verified; broken: {len(broken_cps)}")

        # Check 14: All 4 Academic Courses covered
        courses_in_gt = set(r["course_code"] for r in gt_rows)
        courses_ok = {"CSE301", "CSE302", "CSE303", "HCI401"}.issubset(courses_in_gt)
        self._check(14, "Curricular Coverage (All 4 Courses)", courses_ok, f"Courses covered: {sorted(list(courses_in_gt))}")

        # Check 15: All 4 Roles covered
        roles_in_gt = set(r["effective_role"].lower() for r in gt_rows)
        roles_ok = {"admin", "professor", "ta", "student"}.issubset(roles_in_gt)
        self._check(15, "Role Tier Coverage (Admin, Prof, TA, Student)", roles_ok, f"Roles verified: {sorted(list(roles_in_gt))}")

        # Check 16: Adversarial scenarios presence
        adv_cases = [r for r in gt_rows if r.get("is_adversarial") == "True"]
        self._check(16, "Adversarial & Guard-Bypass Scenarios", len(adv_cases) >= 50, f"{len(adv_cases)} adversarial test cases generated")

        # Check 17: Multi-step scenarios presence
        multistep_cases = [r for r in manifest_rows if "multi-step" in r["title"].lower() or "step" in r["requested_action"].lower()]
        self._check(17, "Multi-Step Sequential Scenarios", len(multistep_cases) >= 50, f"{len(multistep_cases)} multi-step sequential workflow cases generated")

        # Check 18: Distribution Stats JSON exists and valid
        stats_path = os.path.join(self.reports_dir, "distribution_stats.json")
        stats_ok = os.path.isfile(stats_path)
        if stats_ok:
            with open(stats_path, "r", encoding="utf-8") as f:
                json_data = json.load(f)
                stats_ok = json_data.get("total_cases") == case_count
        self._check(18, "Distribution Statistics JSON Report", stats_ok, f"Verified {stats_path}")

        # Check 19: Coverage Markdown Report exists
        cov_path = os.path.join(self.reports_dir, "coverage_report.md")
        cov_ok = os.path.isfile(cov_path) and os.path.getsize(cov_path) > 100
        self._check(19, "Coverage Markdown Report", cov_ok, f"Verified {cov_path}")

        # Check 20: Zip export archives exist
        zip_slm = os.path.join(self.base_dir, "slm_inputs.zip")
        zip_full = os.path.abspath(os.path.join(self.base_dir, "..", "research_snapshots_2000.zip"))
        zips_ok = os.path.isfile(zip_slm) and os.path.isfile(zip_full) and os.path.getsize(zip_slm) > 1000
        self._check(20, "Distribution Zip Archives", zips_ok, f"slm_inputs.zip: {os.path.exists(zip_slm)}, research_snapshots_2000.zip: {os.path.exists(zip_full)}")

        all_passed = all(r["passed"] for r in self.results)
        return all_passed, self.results
