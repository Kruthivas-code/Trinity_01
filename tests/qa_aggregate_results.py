"""
QA Results Aggregator - Collects all batch results into a final report.
"""
import json
import os
import glob
from datetime import datetime, timezone

REPORT_DIR = "/app/test_reports/qa_run"

def aggregate():
    files = sorted(glob.glob(os.path.join(REPORT_DIR, "batch*.json")))
    if not files:
        print("No batch results found!")
        return

    total = passed = failed = errors = skipped = 0
    all_results = []
    batch_summaries = []

    for f in files:
        with open(f) as fh:
            report = json.load(fh)
        s = report["summary"]
        total += s["total"]
        passed += s["passed"]
        failed += s["failed"]
        errors += s["errors"]
        skipped += s["skipped"]
        all_results.extend(report["results"])
        batch_summaries.append({
            "batch": report["batch"],
            "total": s["total"],
            "passed": s["passed"],
            "failed": s["failed"],
            "errors": s["errors"],
            "skipped": s["skipped"],
            "pass_rate": s["pass_rate"],
            "duration_seconds": report["duration_seconds"],
        })

    executed = total - skipped
    pass_rate = f"{(passed / max(executed, 1)) * 100:.1f}%"

    # Print summary
    print("=" * 70)
    print("QA TEST EXECUTION REPORT - AGGREGATE RESULTS")
    print("=" * 70)
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Batches: {len(files)}")
    print()

    print("BATCH BREAKDOWN:")
    print(f"{'Batch':<50} {'Total':>6} {'Pass':>6} {'Fail':>6} {'Err':>5} {'Skip':>5} {'Rate':>8}")
    print("-" * 87)
    for bs in batch_summaries:
        print(f"{bs['batch']:<50} {bs['total']:>6} {bs['passed']:>6} {bs['failed']:>6} {bs['errors']:>5} {bs['skipped']:>5} {bs['pass_rate']:>8}")
    print("-" * 87)
    print(f"{'TOTAL':<50} {total:>6} {passed:>6} {failed:>6} {errors:>5} {skipped:>5} {pass_rate:>8}")
    print()

    # Failed tests
    failed_tests = [r for r in all_results if r["status"] == "FAIL"]
    error_tests = [r for r in all_results if r["status"] == "ERROR"]

    if failed_tests:
        print(f"\nFAILED TESTS ({len(failed_tests)}):")
        print("-" * 70)
        for t in failed_tests:
            print(f"  [{t['test_id']}] {t['description']}")
            print(f"    -> {t['detail'][:200]}")
    
    if error_tests:
        print(f"\nERROR TESTS ({len(error_tests)}):")
        print("-" * 70)
        for t in error_tests:
            print(f"  [{t['test_id']}] {t['description']}")
            print(f"    -> {t['detail'][:200]}")

    if not failed_tests and not error_tests:
        print("ALL TESTS PASSED!")

    # Save aggregate
    aggregate_report = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "total": total,
            "passed": passed,
            "failed": failed,
            "errors": errors,
            "skipped": skipped,
            "pass_rate": pass_rate,
        },
        "batch_summaries": batch_summaries,
        "failed_tests": failed_tests,
        "error_tests": error_tests,
        "all_results": all_results,
    }
    outpath = os.path.join(REPORT_DIR, "AGGREGATE_REPORT.json")
    with open(outpath, "w") as f:
        json.dump(aggregate_report, f, indent=2)
    print(f"\nFull report saved to: {outpath}")

if __name__ == "__main__":
    aggregate()
