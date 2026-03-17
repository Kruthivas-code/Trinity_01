#!/usr/bin/env python3
"""
Performance Test - Run async tests for API endpoints
"""

import asyncio
import aiohttp
import json
import time
from datetime import datetime
import statistics
import sys
import os

PREVIEW_URL = "https://backend-refresh-3.preview.emergentagent.com"
CADDY_URL = "https://sync-engine-fixes.internal.emergent.host"
CLOUDFLARE_URL = "https://sync-engine-fixes.internal.emergent.host"

# Comprehensive GET routes list
TEST_ROUTES = [
    ("/api/health", "Health Check"),
    ("/api/admin/custom-fields", "Admin Custom Fields"),
    ("/api/admin/settings", "Admin Settings"),
    ("/api/admin/routing-rules", "Admin Routing Rules"),
    ("/api/admin/sla-policies", "Admin SLA Policies"),
    ("/api/admin/sla-escalation-rules", "Admin SLA Escalation Rules"),
    ("/api/admin/auto-close-status", "Admin Auto Close Status"),
    ("/api/analytics/summary", "Analytics Summary"),
    ("/api/analytics/overview", "Analytics Overview"),
    ("/api/analytics/agents", "Analytics Agents"),
    ("/api/users", "List Users"),
    ("/api/users/me", "Current User"),
    ("/api/auth/me", "Auth Me"),
    ("/api/auth/api-keys", "API Keys"),
    ("/api/teams", "List Teams"),
    ("/api/shifts", "List Shifts"),
    ("/api/tickets", "List Tickets"),
    ("/api/tickets/escalation-counts", "Ticket Escalation Counts"),
    ("/api/tickets/starred", "Starred Tickets"),
    ("/api/filter/fields", "Filter Fields"),
    ("/api/customers", "List Customers"),
    ("/api/customers/b2b-prospects", "B2B Prospects"),
    ("/api/csat/analytics", "CSAT Analytics"),
    ("/api/canned-responses", "Canned Responses"),
    ("/api/feature-requests", "Feature Requests"),
    ("/api/leaves", "Leaves"),
    ("/api/knowledge-base", "Knowledge Base"),
    ("/api/knowledge-base-search", "KB Search"),
    ("/api/kb/articles", "KB Articles"),
    ("/api/kb/navigation", "KB Navigation"),
    ("/api/kb/public-data", "KB Public Data"),
    ("/api/kb/search", "KB Search"),
    ("/api/kb/admin/articles", "KB Admin Articles"),
    ("/api/kb/admin/images", "KB Admin Images"),
    ("/api/kb/social-links", "KB Social Links"),
    ("/api/kb/admin/docs-settings", "KB Docs Settings"),
    ("/api/kb/admin/design-config", "KB Design Config"),
    ("/api/portal/categories", "Portal Categories"),
    ("/api/portal/help-topics", "Portal Help Topics"),
    ("/api/portal/engineer-plans", "Engineer Plans"),
    ("/api/portal/tickets", "Portal Tickets"),
    ("/api/portal/admin/kb-nav-groups", "Portal KB Nav Groups"),
    ("/api/portal/admin/kb-articles-list", "Portal KB Articles List"),
    ("/api/portal/admin/engineer-plans", "Portal Admin Engineer Plans"),
    ("/api/webhooks", "List Webhooks"),
    ("/api/webhooks/events", "Webhook Events"),
    ("/api/webhooks/logs", "Webhook Logs"),
    ("/api/search", "Search"),
    ("/api/search/suggestions", "Search Suggestions"),
    ("/api/presence/stats", "Presence Stats"),
    ("/api/admin/atlas/backfill/status", "Atlas Backfill Status"),
    ("/api/admin/atlas/sync/status", "Atlas Sync Status"),
    ("/api/attachments/status", "Attachments Status"),
    ("/api/export", "Export"),
    ("/api/admin/export/analytics", "Admin Export Analytics"),
    ("/api/admin/export/customers", "Admin Export Customers"),
]

async def measure_latency(url, iterations=10):
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
                # Skip on error, don't retry
                pass
    
    if not latencies:
        return None
    
    return {
        "min": min(latencies),
        "max": max(latencies),
        "avg": statistics.mean(latencies),
    }

async def test_endpoint(route, description, base_urls, iterations=10):
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

async def run_tests(iterations=10):
    """Run performance tests for all routes"""
    base_urls = {
        "preview": PREVIEW_URL,
        "caddy": CADDY_URL,
        "cloudflare": CLOUDFLARE_URL
    }
    
    results = []
    total = len(TEST_ROUTES)
    
    print(f"\nStarting performance tests for {total} endpoints")
    print(f"Iterations per endpoint: {iterations}\n")
    
    for idx, (route, description) in enumerate(TEST_ROUTES, 1):
        try:
            result = await test_endpoint(route, description, base_urls, iterations)
            if result["backend_perf_result"]:
                results.append(result)
                status = "✓"
            else:
                status = "✗"
            
            print(f"[{idx:2d}/{total}] {status} {description:45s} {route}")
        except Exception as e:
            print(f"[{idx:2d}/{total}] ✗ {description:45s} ERROR: {e}")
        
        # Small delay between requests
        await asyncio.sleep(0.1)
    
    return results

async def main():
    """Main test execution"""
    print("="*80)
    print("API Performance Test Suite")
    print("="*80)
    print(f"Preview:    {PREVIEW_URL}")
    print(f"Caddy:      {CADDY_URL}")
    print(f"Cloudflare: {CLOUDFLARE_URL}")
    
    results = await run_tests(iterations=10)
    
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
    print(f"Test date: {report['testDate']}")
    
    # Calculate averages
    if results:
        all_preview_latencies = []
        all_caddy_latencies = []
        all_cloudflare_latencies = []
        
        for result in results:
            for perf in result['backend_perf_result']:
                if perf['provider'] == 'preview':
                    all_preview_latencies.append(perf['latencyInMs'])
                elif perf['provider'] == 'caddy':
                    all_caddy_latencies.append(perf['latencyInMs'])
                elif perf['provider'] == 'cloudflare':
                    all_cloudflare_latencies.append(perf['latencyInMs'])
        
        print("\nOverall Performance Metrics:")
        if all_preview_latencies:
            print(f"  Preview:    Avg {statistics.mean(all_preview_latencies):.2f}ms (Min: {min(all_preview_latencies):.2f}ms, Max: {max(all_preview_latencies):.2f}ms)")
        if all_caddy_latencies:
            print(f"  Caddy:      Avg {statistics.mean(all_caddy_latencies):.2f}ms (Min: {min(all_caddy_latencies):.2f}ms, Max: {max(all_caddy_latencies):.2f}ms)")
        if all_cloudflare_latencies:
            print(f"  Cloudflare: Avg {statistics.mean(all_cloudflare_latencies):.2f}ms (Min: {min(all_cloudflare_latencies):.2f}ms, Max: {max(all_cloudflare_latencies):.2f}ms)")
    
    # Save results to file
    output_file = "/tmp/performance_results.json"
    with open(output_file, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"\nResults saved to {output_file}")
    
    return report

if __name__ == "__main__":
    report = asyncio.run(main())
    
    # Also print the JSON for submission
    print("\n" + "="*80)
    print("FINAL REPORT (JSON)")
    print("="*80)
    print(json.dumps(report, indent=2))
    
    # Save to a separate JSON file for easy submission
    with open("/tmp/final_perf_report.json", 'w') as f:
        json.dump(report, f, indent=2)
