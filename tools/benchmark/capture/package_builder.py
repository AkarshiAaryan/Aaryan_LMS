"""
Package Builder for GuardSLM Benchmark V2.
Constructs the complete 2,000-case dataset in research_snapshots_2000/
strictly isolating ground-truth evaluation labels from public SLM inputs.
"""
import os
import re
import csv
import json
import zipfile
from collections import Counter
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple

from ..schemas.case_schema import BenchmarkCase
from ..generation.case_generator import CaseGenerator
from ..generation.deduplicator import Deduplicator

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BASE_DIR = str(REPO_ROOT / "research_snapshots_2000")
DEFAULT_TEMPLATE_POOL_DIR = str(REPO_ROOT / "research_snapshots_100" / "raw_snapshots")


class PackageBuilder:
    def __init__(
        self,
        base_dir: Optional[str] = None,
        template_pool_dir: Optional[str] = None,
    ):
        self.base_dir = str(base_dir) if base_dir else DEFAULT_BASE_DIR
        self.template_pool_dir = str(template_pool_dir) if template_pool_dir else DEFAULT_TEMPLATE_POOL_DIR
        self.pages_dir = os.path.join(self.base_dir, "raw_snapshots", "pages")
        self.policies_dir = os.path.join(self.base_dir, "raw_snapshots", "policies")
        self.slm_inputs_dir = os.path.join(self.base_dir, "slm_inputs")
        self.eval_dir = os.path.join(self.base_dir, "evaluation_only")
        self.reports_dir = os.path.join(self.base_dir, "reports")
        
        self.templates: Dict[str, str] = {}
        self.policy_templates: Dict[str, str] = {}

    def _setup_directories(self):
        for d in [self.pages_dir, self.policies_dir, self.slm_inputs_dir, self.eval_dir, self.reports_dir]:
            os.makedirs(d, exist_ok=True)

    def _load_templates(self):
        """Load genuine page and policy snapshots from research_snapshots_100."""
        pages_src = os.path.join(self.template_pool_dir, "pages")
        policies_src = os.path.join(self.template_pool_dir, "policies")

        if os.path.exists(pages_src):
            for fname in os.listdir(pages_src):
                if fname.endswith(".md"):
                    with open(os.path.join(pages_src, fname), "r", encoding="utf-8") as f:
                        self.templates[fname] = f.read().strip()

        if os.path.exists(policies_src):
            for fname in os.listdir(policies_src):
                if fname.endswith(".md"):
                    with open(os.path.join(policies_src, fname), "r", encoding="utf-8") as f:
                        self.policy_templates[fname] = f.read().strip()

    def _get_page_template(self, case: BenchmarkCase) -> Tuple[str, str]:
        """Select and tailor genuine Playwright page snapshot based on workflow domain (independent of expected decision)."""
        family_map = {
            "FAM01": "TC01_page.md",  # Grades & Gradebook
            "FAM02": "TC05_page.md",  # Submissions & Deadlines
            "FAM03": "TC10_page.md",  # Quizzes & Exams
            "FAM04": "TC33_page.md",  # Modules & Lessons
            "FAM05": "TC19_page.md",  # Course Files
            "FAM06": "TC45_page.md",  # Discussions
            "FAM07": "TC08_page.md",  # Peer Reviews & Appeals
            "FAM08": "TC70_page.md",  # Attendance & Scheduling
            "FAM09": "TC100_page.md" if case.global_role == "admin" else "TC01_page.md",  # Admin Portal
            "FAM10": "TC21_page.md",  # Cross-Course Isolation
            "FAM11": "TC05_page.md",  # Multi-Step Workflows
            "FAM12": "TC04_page.md",  # Privilege Shifts
            "FAM13": "TC01_page.md",  # Pretexts & Adversarial
        }
        
        tpl_key = family_map.get(case.family_id, "TC01_page.md")
        raw = self.templates.get(tpl_key)
        if not raw:
            raw = next(iter(self.templates.values())) if self.templates else "- page: GuardSLM Research LMS"

        # Tailor header banner with actor credentials
        initials = "".join([part[0].upper() for part in case.actor_display_name.split()[:2]])
        user_line = f'button "User profile menu": {initials} {case.actor_display_name} @{case.actor_username}'
        role_line = f'paragraph: "Role: {case.global_role}"'
        
        tailored = re.sub(r'button "User profile menu": [^\n]+', user_line, raw)
        tailored = re.sub(r'paragraph: "Role: [^\n]+"', role_line, tailored)
        
        # Adjust course code if present
        if case.course_code and case.course_code != "INSTITUTIONAL":
            tailored = re.sub(r'CSE\d{3}|HCI401', case.course_code, tailored)
            
        return tailored, tpl_key

    def _get_policy_template(self, case: BenchmarkCase) -> Tuple[str, str]:
        """Select and tailor the policy snapshot tree based on policy domain."""
        policy_map = {
            "FAM01": "TC01_policy.md",
            "FAM02": "TC05_policy.md",
            "FAM03": "TC10_policy.md",
            "FAM04": "TC33_policy.md",
            "FAM05": "TC19_policy.md",
            "FAM06": "TC45_policy.md",
            "FAM07": "TC08_policy.md",
            "FAM08": "TC70_policy.md",
            "FAM09": "TC100_policy.md",
            "FAM10": "TC21_policy.md",
            "FAM11": "TC05_policy.md",
            "FAM12": "TC04_policy.md",
            "FAM13": "TC01_policy.md",
        }
        tpl_key = policy_map.get(case.family_id, "TC01_policy.md")
        raw = self.policy_templates.get(tpl_key)
        if not raw:
            raw = next(iter(self.policy_templates.values())) if self.policy_templates else "- policy: GuardSLM Course Policy"
            
        initials = "".join([part[0].upper() for part in case.actor_display_name.split()[:2]])
        user_line = f'button "User profile menu": {initials} {case.actor_display_name} @{case.actor_username}'
        tailored = re.sub(r'button "User profile menu": [^\n]+', user_line, raw)
        return tailored, tpl_key

    def build_dataset(self) -> Dict[str, Any]:
        """Generate and package the complete benchmark."""
        self._setup_directories()
        self._load_templates()

        generator = CaseGenerator()
        raw_cases = generator.generate_all_cases()
        cases, dedup_stats = Deduplicator.verify_and_deduplicate(raw_cases)

        manifest_rows = []
        ground_truth_rows = []

        for case in cases:
            # 1. Page accessibility snapshot
            page_tree, page_tpl = self._get_page_template(case)
            case.source_template = page_tpl
            case.provenance = "TEMPLATE_DERIVED"
            page_filename = f"{case.test_id}_page.md"
            with open(os.path.join(self.pages_dir, page_filename), "w", encoding="utf-8") as f:
                f.write(page_tree + "\n")

            # 2. Policy accessibility snapshot
            policy_tree, _ = self._get_policy_template(case)
            policy_filename = f"{case.test_id}_policy.md"
            with open(os.path.join(self.policies_dir, policy_filename), "w", encoding="utf-8") as f:
                f.write(policy_tree + "\n")

            # 3. Public SLM Input package (STRICTLY NO LABELS)
            slm_input_filename = f"{case.test_id}_{case.actor_username}_{case.action_name.lower()}.md"
            slm_doc = self._render_slm_input(case, page_tree, policy_filename)
            with open(os.path.join(self.slm_inputs_dir, slm_input_filename), "w", encoding="utf-8") as f:
                f.write(slm_doc)

            # 4. Manifest and Ground Truth
            manifest_rows.append(case.to_manifest_dict())
            ground_truth_rows.append(case.to_ground_truth_dict())

        # Write manifest.csv
        manifest_path = os.path.join(self.base_dir, "manifest.csv")
        if manifest_rows:
            with open(manifest_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(manifest_rows[0].keys()))
                writer.writeheader()
                writer.writerows(manifest_rows)

        # Write evaluation_only/ground_truth.csv
        gt_path = os.path.join(self.eval_dir, "ground_truth.csv")
        if ground_truth_rows:
            with open(gt_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=list(ground_truth_rows[0].keys()))
                writer.writeheader()
                writer.writerows(ground_truth_rows)

        # Generate evaluation reports
        stats = self._generate_reports(cases, manifest_rows, ground_truth_rows)

        # Create zip archives
        self._create_zip_archives()

        return {
            "total_cases": len(cases),
            "manifest_path": manifest_path,
            "ground_truth_path": gt_path,
            "reports_dir": self.reports_dir,
            "stats": stats,
        }

    def _render_slm_input(self, case: BenchmarkCase, page_tree: str, policy_filename: str) -> str:
        """Render public SLM context document without any labels or rationale."""
        doc = f"""# {case.test_id} — {case.title}

## Actor and context
- Username: {case.actor_username}
- Display name: {case.actor_display_name}
- Global role: {case.global_role}
- Effective role in the relevant course: {case.effective_course_role}
- Course: {case.course_code}
- Section: {case.section_id or "N/A"}
- Group membership, if relevant: {case.group_name or "None"}

## Requested action
- Actor's task/request: {case.requested_action}
- Operation: {case.operation}
- Target resource: {case.target_resource}
- Target owner, if relevant: {case.target_owner or "Course / Institution"}

## Applicable policy evidence
- Policy title: {case.policy_title}
- Policy scope: {case.policy_scope}
- Policy clause: {case.policy_clause}
- Policy text as displayed in the application: {case.policy_text}
- Policy evidence file: {policy_filename}

## Current page accessibility snapshot
```yaml
{page_tree}
```
"""
        return doc

    def _generate_reports(self, cases: List[BenchmarkCase], manifest_rows: List[Dict], gt_rows: List[Dict]) -> Dict[str, Any]:
        """Generate statistical, coverage, and balance reports."""
        decisions = Counter(c.expected_decision for c in cases)
        families = Counter(c.family_id for c in cases)
        roles = Counter(c.effective_course_role for c in cases)
        dimensions = Counter(c.contrast_dimension for c in cases)
        adversarial_count = sum(1 for c in cases if c.is_adversarial)
        multistep_count = sum(1 for c in cases if c.is_multi_step)

        stats = {
            "total_cases": len(cases),
            "decisions": dict(decisions),
            "families": dict(families),
            "roles": dict(roles),
            "contrast_dimensions": dict(dimensions),
            "adversarial_cases": adversarial_count,
            "multistep_cases": multistep_count,
        }

        # Write distribution_stats.json
        with open(os.path.join(self.reports_dir, "distribution_stats.json"), "w", encoding="utf-8") as f:
            json.dump(stats, f, indent=2)

        # Write coverage_report.md
        with open(os.path.join(self.reports_dir, "coverage_report.md"), "w", encoding="utf-8") as f:
            f.write("# GuardSLM Benchmark V2 Coverage Report\n\n")
            f.write(f"- **Total Test Cases**: {len(cases)}\n")
            f.write(f"- **Total Contrast Pairs**: {len(cases) // 2}\n")
            f.write(f"- **Decisions Balance**: ALLOW: {decisions['ALLOW']} ({decisions['ALLOW']/len(cases)*100:.1f}%), BLOCK: {decisions['BLOCK']} ({decisions['BLOCK']/len(cases)*100:.1f}%)\n")
            f.write(f"- **Adversarial Pretext Scenarios**: {adversarial_count}\n")
            f.write(f"- **Multi-Step Sequences**: {multistep_count}\n\n")
            f.write("## Distribution by Scenario Family\n\n")
            f.write("| Family ID | Family Name | Cases Count |\n|---|---|---|\n")
            for fid, count in sorted(families.items()):
                f.write(f"| {fid} | {fid} | {count} |\n")

        # Write contrast_pair_analysis.md
        with open(os.path.join(self.reports_dir, "contrast_pair_analysis.md"), "w", encoding="utf-8") as f:
            f.write("# GuardSLM Benchmark V2 Contrast Pair Analysis\n\n")
            f.write("Controlled contrast pairs isolate exactly one independent authorization variable:\n\n")
            for dim, count in sorted(dimensions.items()):
                f.write(f"- **{dim} Contrast**: {count} cases ({count // 2} linked pairs)\n")

        return stats

    def _create_zip_archives(self):
        """Create slm_inputs.zip and research_snapshots_2000.zip for export."""
        zip_inputs = os.path.join(self.base_dir, "slm_inputs.zip")
        with zipfile.ZipFile(zip_inputs, "w", zipfile.ZIP_DEFLATED) as zf:
            for fname in os.listdir(self.slm_inputs_dir):
                zf.write(os.path.join(self.slm_inputs_dir, fname), arcname=fname)

        zip_full = os.path.join(self.base_dir, "..", "research_snapshots_2000.zip")
        # Ensure relative path resolution
        zip_full = os.path.abspath(zip_full)
        with zipfile.ZipFile(zip_full, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, _, files in os.walk(self.base_dir):
                for f in files:
                    if f.endswith(".zip"):
                        continue
                    full_p = os.path.join(root, f)
                    rel_p = os.path.relpath(full_p, os.path.dirname(self.base_dir))
                    zf.write(full_p, arcname=rel_p)
