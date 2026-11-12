"""
Unified CLI for GuardSLM Benchmark V2 infrastructure.
Usage:
  python -m tools.benchmark.cli generate [--output DIR]
  python -m tools.benchmark.cli validate [--dir DIR]
  python -m tools.benchmark.cli stats [--dir DIR]
"""
import sys
import argparse
import json
from pathlib import Path

from .capture.package_builder import PackageBuilder
from .validation.validator import BenchmarkValidator

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BENCHMARK_DIR = str(REPO_ROOT / "research_snapshots_2000")


def main():
    parser = argparse.ArgumentParser(description="GuardSLM Benchmark V2 CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Generate
    gen_parser = subparsers.add_parser("generate", help="Generate and package ~2,000 benchmark cases")
    gen_parser.add_argument("--output", default=DEFAULT_BENCHMARK_DIR, help="Output directory")

    # Validate
    val_parser = subparsers.add_parser("validate", help="Run 20-point validation suite on benchmark")
    val_parser.add_argument("--dir", default=DEFAULT_BENCHMARK_DIR, help="Benchmark directory")

    # Stats
    stat_parser = subparsers.add_parser("stats", help="Show summary statistics of generated benchmark")
    stat_parser.add_argument("--dir", default=DEFAULT_BENCHMARK_DIR, help="Benchmark directory")

    args = parser.parse_args()

    if args.command == "generate":
        print(f"=== GuardSLM Benchmark V2: Generating Dataset in {args.output} ===")
        builder = PackageBuilder(base_dir=args.output)
        res = builder.build_dataset()
        print(f"✓ Successfully generated and packaged {res['total_cases']} benchmark cases.")
        print(f"✓ Manifest written to: {res['manifest_path']}")
        print(f"✓ Ground truth isolated at: {res['ground_truth_path']}")
        print(f"✓ Reports written to: {res['reports_dir']}")
        print("\nSummary Statistics:")
        print(json.dumps(res['stats'], indent=2))

    elif args.command == "validate":
        print(f"=== GuardSLM Benchmark V2: Running 20-Point Validation Suite on {args.dir} ===")
        validator = BenchmarkValidator(base_dir=args.dir)
        passed, results = validator.run_all_checks()
        for r in results:
            mark = "✓" if r["passed"] else "✗"
            print(f"[{mark}] Check {r['check_num']:02d}: {r['name']} — {r['detail']}")

        if passed:
            print("\n🎉 ALL 20 VALIDATION CHECKS PASSED PERFECTLY!")
            sys.exit(0)
        else:
            print("\n❌ SOME VALIDATION CHECKS FAILED.")
            sys.exit(1)

    elif args.command == "stats":
        validator = BenchmarkValidator(base_dir=args.dir)
        import os
        stats_file = os.path.join(validator.reports_dir, "distribution_stats.json")
        if os.path.exists(stats_file):
            with open(stats_file, "r", encoding="utf-8") as f:
                print(f.read())
        else:
            print(f"No stats file found at {stats_file}. Run generate first.")


if __name__ == "__main__":
    main()
