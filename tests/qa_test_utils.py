"""
QA Test Utilities - Shared test framework for TickFlow/Trinity QA testing.
"""
import requests
import json
import time
import os
from datetime import datetime, timezone

BASE_URL = "http://localhost:8001"
REPORT_DIR = "/app/test_reports/qa_run"

ADMIN_TOKEN = "qa_test_admin_session_token_2026"
LEAD_TOKEN = "qa_test_lead_session_token_2026"
AGENT_TOKEN = "qa_test_agent_session_token_2026"

class QATestRunner:
    def __init__(self, batch_name):
        self.batch_name = batch_name
        self.results = []
        self.passed = 0
        self.failed = 0
        self.skipped = 0
        self.errors = 0
        self.start_time = time.time()

    def _session(self, token=ADMIN_TOKEN):
        s = requests.Session()
        s.cookies.set("session_token", token)
        s.headers.update({"Content-Type": "application/json"})
        return s

    def admin_session(self):
        return self._session(ADMIN_TOKEN)

    def lead_session(self):
        return self._session(LEAD_TOKEN)

    def agent_session(self):
        return self._session(AGENT_TOKEN)

    def no_auth_session(self):
        s = requests.Session()
        s.headers.update({"Content-Type": "application/json"})
        return s

    def run_test(self, test_id, description, test_fn, priority="P0"):
        """Execute a single test case and record the result."""
        result = {
            "test_id": test_id,
            "description": description,
            "priority": priority,
            "status": "unknown",
            "detail": "",
            "duration_ms": 0,
        }
        start = time.time()
        try:
            passed, detail = test_fn()
            result["duration_ms"] = round((time.time() - start) * 1000, 1)
            if passed:
                result["status"] = "PASS"
                self.passed += 1
            else:
                result["status"] = "FAIL"
                self.failed += 1
            result["detail"] = str(detail)[:500]
        except Exception as e:
            result["duration_ms"] = round((time.time() - start) * 1000, 1)
            result["status"] = "ERROR"
            result["detail"] = f"{type(e).__name__}: {str(e)[:400]}"
            self.errors += 1

        self.results.append(result)
        status_icon = {"PASS": "PASS", "FAIL": "FAIL", "ERROR": "ERR ", "SKIP": "SKIP"}.get(result["status"], "????")
        print(f"  [{status_icon}] {test_id}: {description} ({result['duration_ms']}ms)")
        if result["status"] in ("FAIL", "ERROR"):
            print(f"         -> {result['detail'][:200]}")
        return result

    def skip_test(self, test_id, description, reason="", priority="P0"):
        result = {
            "test_id": test_id,
            "description": description,
            "priority": priority,
            "status": "SKIP",
            "detail": reason,
            "duration_ms": 0,
        }
        self.results.append(result)
        self.skipped += 1
        print(f"  [SKIP] {test_id}: {description} -- {reason}")

    def save_report(self):
        """Save test results to JSON file."""
        os.makedirs(REPORT_DIR, exist_ok=True)
        elapsed = round(time.time() - self.start_time, 1)
        report = {
            "batch": self.batch_name,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "duration_seconds": elapsed,
            "summary": {
                "total": len(self.results),
                "passed": self.passed,
                "failed": self.failed,
                "errors": self.errors,
                "skipped": self.skipped,
                "pass_rate": f"{(self.passed / max(len(self.results) - self.skipped, 1)) * 100:.1f}%",
            },
            "results": self.results,
        }
        filepath = os.path.join(REPORT_DIR, f"{self.batch_name}.json")
        with open(filepath, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n{'='*60}")
        print(f"BATCH: {self.batch_name}")
        print(f"Total: {report['summary']['total']} | Pass: {self.passed} | Fail: {self.failed} | Error: {self.errors} | Skip: {self.skipped}")
        print(f"Pass Rate: {report['summary']['pass_rate']} | Duration: {elapsed}s")
        print(f"Report: {filepath}")
        print(f"{'='*60}")
        return filepath


def api_get(session, path, **kwargs):
    return session.get(f"{BASE_URL}{path}", timeout=15, **kwargs)

def api_post(session, path, data=None, **kwargs):
    return session.post(f"{BASE_URL}{path}", json=data, timeout=15, **kwargs)

def api_put(session, path, data=None, **kwargs):
    return session.put(f"{BASE_URL}{path}", json=data, timeout=15, **kwargs)

def api_delete(session, path, **kwargs):
    return session.delete(f"{BASE_URL}{path}", timeout=15, **kwargs)

def api_patch(session, path, data=None, **kwargs):
    return session.patch(f"{BASE_URL}{path}", json=data, timeout=15, **kwargs)
