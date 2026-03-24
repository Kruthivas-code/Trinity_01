#!/usr/bin/env python3
"""
Quick Performance Test - Streamlined for faster completion
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
import statistics

PREVIEW_URL = "https://docs-sync-test.preview.emergentagent.com"
CADDY_URL = "https://sync-engine-fixes.internal.emergent.host"
CLOUDFLARE_URL = "https://sync-engine-fixes.internal.emergent.host"

# Essential GET routes (representative sample)
TEST_ROUTES = [
    ("/api/health", "Health Check"),
    ("/api/admin/settings", "Admin Settings"),
    ("/api/analytics/summary", "Analytics Summary"),
    ("/api/users", "List Users"),
    ("/api/teams", "List Teams"),
    ("/api/tickets", "List Tickets"),
    ("/api/customers", "List Customers"),
    ("/api/shifts", "List Shifts"),
    ("/api/leaves", "Leaves"),
    ("/api/canned-responses", "Canned Responses"),
    ("/api/feature-requests", "Feature Requests"),
    ("/api/knowledge-base", "Knowledge Base"),
    ("/api/kb/articles", "KB Articles"),
    ("/api/kb/navigation", "KB Navigation"),
    ("/api/kb/search", "KB Search"),
    ("/api/portal/categories", "Portal Categories"),
    ("/api/portal/help-topics", "Portal Help Topics"),
    ("/api/webhooks", "List Webhooks"),
    ("/api/search", "Search"),
    ("/api/presence/stats", "Presence Stats"),
    ("/api/admin/custom-fields", "Admin Custom Fields"),
    ("/api/admin/routing-rules", "Admin Routing Rules"),
    ("/api/admin/sla-policies", "Admin SLA Policies"),
    ("/api/admin/auto-close-status", "Admin Auto Close Status"),
    ("/api/analytics/overview", "Analytics Overview"),
    ("/api/analytics/agents", "Analytics Agents"),
    ("/api/auth/me", "Auth Me"),
    ("/api/filter/fields", "Filter Fields"),
    ("/api/customers/b2b-prospects", "B2B Prospects"),
    ("/api/csat/analytics", "CSAT Analytics"),
    ("/api/tickets/escalation-counts", "Ticket Escalation Counts"),
    ("/api/tickets/starred", "Starred Tickets"),
    ("/api/kb/admin/articles", "KB Admin Articles"),
    ("/api/kb/social-links", "KB Social Links"),
    ("/api/export", "Export"),
    ("/api/admin/export/analytics", "Admin Export Analytics"),
    ("/api/attachments/status", "Attachments Status"),
    ("/api/webhooks/events", "Webhook Events"),
    ("/api/search/suggestions", "Search Suggestions"),
    ("/api/knowledge-base-search", "KB Search API"),
]

async def measure_latency(url, iterations=5):
    """Measure latency for a single endpoint"""
    latencies = []
    async with aiohttp.ClientSession(connector=aiohttp.TCPConnector(ssl=False)) as session:
        for i in range(iterations):
            try:
                start = time.time()
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    await resp.read()
                    latency = (time.time() - start) * 1000
                    latencies.append(latency)
            except Exception as e:
                pass
    
    if not latencies:
        return None
    
    return {
        "min": min(latencies),
        "max": max(latencies),
        "avg": statistics.mean(latencies),
    }

async def test_endpoint(route, description, base_urls, iterations=5):
    """Test a single endpoint across all providers"""
    result = {
        "description": description,
        "route": route,
        "iterations": iterations,
        "backend_perf_result": []
    }
    
    for provider_name, base_url in base_urls.items():
        full_url = base_url + route
        latency_data = await measure_latency(full_url, iterations)
        
        if latency_data:
            result["backend_perf_result"].append({
                "provider": provider_name,
                "latencyInMs": round(latency_data["avg"], 2),
                "minLatencyInMs": round(latency_data["min"], 2),
                "maxLatencyInMs": round(latency_data["max"], 2)
            })
    
    return result

async def run_tests(iterations=5):
    """Run performance tests for all routes"""
    base_urls = {
        "preview": PREVIEW_URL,
        "caddy": CADDY_URL,
        "cloudflare": CLOUDFLARE_URL
    }
    
    results = []
    total = len(TEST_ROUTES)
    
    print(f"\nTesting {total} endpoints with {iterations} iterations per endpoint\n")
    
    for idx, (route, description) in enumerate(TEST_ROUTES, 1):
        try:
            result = await test_endpoint(route, description, base_urls, iterations)
            if result["backend_perf_result"]:
                results.append(result)
                print(f"[{idx:2d}/{total}] ✓ {description:40s}")
        except Exception as e:
            print(f"[{idx:2d}/{total}] ✗ {description:40s} ERROR")
        
        await asyncio.sleep(0.05)
    
    return results

async def main():
    """Main test execution"""
    print("="*80)
    print("API Performance Test - Quick Run")
    print("="*80)
    
    results = await run_tests(iterations=5)
    
    # Generate report
    report = {
        "appName": "audit-engine-13",
        "testDate": datetime.utcnow().isoformat() + "Z",
        "previewUrl": PREVIEW_URL,
        "deployedUrl": CADDY_URL,
        "result": results
    }
    
    # Print summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    print(f"Total endpoints tested: {len(results)}")
    
    # Calculate averages
    if results:
        all_preview = [p['latencyInMs'] for r in results for p in r['backend_perf_result'] if p['provider'] == 'preview']
        all_caddy = [p['latencyInMs'] for r in results for p in r['backend_perf_result'] if p['provider'] == 'caddy']
        all_cloudflare = [p['latencyInMs'] for r in results for p in r['backend_perf_result'] if p['provider'] == 'cloudflare']
        
        if all_preview:
            print(f"Preview:    Avg {statistics.mean(all_preview):.2f}ms")
        if all_caddy:
            print(f"Caddy:      Avg {statistics.mean(all_caddy):.2f}ms")
        if all_cloudflare:
            print(f"Cloudflare: Avg {statistics.mean(all_cloudflare):.2f}ms")
    
    # Save results
    with open("/tmp/final_perf_report.json", 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nResults saved to /tmp/final_perf_report.json")
    
    return report

if __name__ == "__main__":
    report = asyncio.run(main())
    
    # Print JSON
    print("\n" + "="*80)
    print("REPORT JSON")
    print("="*80)
    print(json.dumps(report, indent=2))
