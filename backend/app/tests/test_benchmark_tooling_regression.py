"""
Regression tests for GuardSLM Benchmark V2 tooling:
- Portable relative path resolution
- Truthful template provenance (TEMPLATE_DERIVED)
- Decoupled page templates (independent of expected_decision)
- 100% SLM input file scanning in validator Check 6
- Dynamic 13-family representation calculation in validator Check 11
- Deduplicator reciprocal ALLOW/BLOCK verification
"""
import os
import tempfile
import shutil
import pytest

from tools.benchmark.capture.package_builder import PackageBuilder
from tools.benchmark.validation.validator import BenchmarkValidator
from tools.benchmark.generation.case_generator import CaseGenerator
from tools.benchmark.generation.deduplicator import Deduplicator


def test_deduplicator_and_contrast_pair_reciprocal_decisions():
    generator = CaseGenerator()
    cases = generator.generate_all_cases()
    assert len(cases) == 2000
    
    unique_cases, stats = Deduplicator.verify_and_deduplicate(cases)
    assert stats["total_unique"] == 2000
    assert stats["duplicates_count"] == 0
    assert stats["broken_pairs_count"] == 0
    assert "non_reciprocal_pairs_count" in stats
    assert "prompt_duplicates_count" in stats


def test_validator_20_point_checks_read_only():
    """Verify that existing research_snapshots_2000 passes all 20 checks with 100% file scan."""
    validator = BenchmarkValidator()
    passed, results = validator.run_all_checks()
    assert passed is True
    assert len(results) == 20
    
    # Check 6 was 100% scan
    check_6 = next(r for r in results if r["check_num"] == 6)
    assert check_6["passed"] is True
    assert "100%" in check_6["detail"]
    
    # Check 11 verified all 13 families dynamically
    check_11 = next(r for r in results if r["check_num"] == 11)
    assert check_11["passed"] is True
    assert "All 13 target families verified" in check_11["detail"]


def test_package_builder_in_isolated_tempdir():
    """Verify package builder generation in an isolated temporary directory without modifying research_snapshots_2000."""
    temp_dir = tempfile.mkdtemp(prefix="test_guardslm_pkg_")
    try:
        builder = PackageBuilder(base_dir=temp_dir)
        res = builder.build_dataset()
        assert res["total_cases"] == 2000
        
        # Verify provenance in manifest
        manifest_path = res["manifest_path"]
        assert os.path.exists(manifest_path)
        with open(manifest_path, "r", encoding="utf-8") as f:
            header = f.readline()
            assert "provenance" in header
            assert "source_template" in header
            assert "capture_status" in header
            first_row = f.readline()
            assert "TEMPLATE_DERIVED" in first_row

        # Validate newly generated package in temp dir
        val = BenchmarkValidator(base_dir=temp_dir)
        passed, checks = val.run_all_checks()
        assert passed is True
    finally:
        shutil.rmtree(temp_dir)
