"""
Analytics routes: summary, overview, agent metrics.
"""
from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timedelta, timezone
from typing import Optional
import io
import csv
import json
import logging

from database import (
    tickets_collection, users_collection, teams_collection,
    csat_responses_collection,
)
from dependencies import get_current_user
from utils import serialize_doc, serialize_for_export, generate_json_export, generate_csv_export
from pymongo import ASCENDING, DESCENDING

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["analytics"])


@router.get("/analytics/summary")
async def get_analytics_summary(current_user: dict = Depends(get_current_user)):
    pipeline = [
        {"$facet": {
            "by_status": [
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ],
            "by_assignee": [
                {"$match": {"assignee_id": {"$ne": None}}},
                {"$group": {"_id": "$assignee_id", "count": {"$sum": 1}}}
            ],
            "my_tickets": [
                {"$match": {"assignee_id": current_user["user_id"]}},
                {"$count": "count"}
            ],
            "total": [
                {"$count": "count"}
            ]
        }}
    ]
    result = list(tickets_collection.aggregate(pipeline))
    facets = result[0] if result else {}

    status_counts = {s: 0 for s in ["todo", "in_progress", "waiting", "review", "resolved"]}
    for item in facets.get("by_status", []):
        if item["_id"] in status_counts:
            status_counts[item["_id"]] = item["count"]

    my_count = facets.get("my_tickets", [{}])
    my_tickets_count = my_count[0].get("count", 0) if my_count else 0

    total_list = facets.get("total", [{}])
    total = total_list[0].get("count", 0) if total_list else 0

    return {
        "by_status": status_counts,
        "by_assignee": [{"assignee_id": item["_id"], "count": item["count"]} for item in facets.get("by_assignee", [])],
        "my_tickets": my_tickets_count,
        "total": total
    }


@router.get("/export")
async def export_tickets(
    format: str = "json",
    current_user: dict = Depends(get_current_user)
):
    from starlette.responses import StreamingResponse

    fieldnames = ["ticket_id", "title", "description", "status", "assignee_id", "priority", "order", "created_at", "updated_at"]

    if format == "csv":
        def csv_generator():
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
            writer.writeheader()
            yield output.getvalue()
            for ticket in tickets_collection.find({}, {"_id": 0}).batch_size(500):
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction='ignore')
                writer.writerow(serialize_doc(ticket))
                yield output.getvalue()
        return StreamingResponse(
            csv_generator(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=tickets.csv"}
        )
    else:
        def json_generator():
            yield "[\n"
            first = True
            for ticket in tickets_collection.find({}, {"_id": 0}).batch_size(500):
                if not first:
                    yield ",\n"
                first = False
                yield json.dumps(serialize_doc(ticket))
            yield "\n]"
        return StreamingResponse(
            json_generator(),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=tickets.json"}
        )


@router.get("/analytics/overview")
async def get_analytics_overview(
    period: str = Query("7d", description="Time period: 24h, 7d, 30d, 90d"),
    current_user: dict = Depends(get_current_user)
):
    """Get comprehensive analytics overview"""
    period_map = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
    days = period_map.get(period, 7)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    pipeline = [
        {"$facet": {
            "total_tickets": [{"$count": "count"}],
            "period_tickets": [
                {"$match": {"created_at": {"$gte": cutoff}}},
                {"$count": "count"}
            ],
            "by_status": [
                {"$match": {"status": {"$nin": ["merged"]}}},
                {"$group": {"_id": "$status", "count": {"$sum": 1}}}
            ],
            "by_priority": [
                {"$group": {"_id": "$priority", "count": {"$sum": 1}}}
            ],
            "by_source": [
                {"$group": {"_id": {"$ifNull": ["$source", "unknown"]}, "count": {"$sum": 1}}}
            ],
            "resolved_in_period": [
                {"$match": {"status": {"$in": ["resolved", "closed"]}, "updated_at": {"$gte": cutoff}}},
                {"$count": "count"}
            ],
            "avg_resolution_time": [
                {"$match": {"resolved_at": {"$exists": True}, "resolved_at": {"$gte": cutoff}}},
                {"$project": {
                    "resolution_time": {
                        "$subtract": ["$resolved_at", "$created_at"]
                    }
                }},
                {"$group": {
                    "_id": None,
                    "avg_time": {"$avg": "$resolution_time"},
                    "min_time": {"$min": "$resolution_time"},
                    "max_time": {"$max": "$resolution_time"}
                }}
            ],
            "daily_created": [
                {"$match": {"created_at": {"$gte": cutoff}}},
                {"$group": {
                    "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                    "count": {"$sum": 1}
                }},
                {"$sort": {"_id": 1}}
            ],
            "by_escalation": [
                {"$match": {"status": {"$nin": ["merged", "resolved", "closed"]}}},
                {"$group": {"_id": {"$ifNull": ["$escalation_level", "L1"]}, "count": {"$sum": 1}}}
            ],
            "sla_breached": [
                {"$match": {"sla_breached": True, "created_at": {"$gte": cutoff}}},
                {"$count": "count"}
            ]
        }}
    ]

    result = list(tickets_collection.aggregate(pipeline))
    facets = result[0] if result else {}

    total = facets.get("total_tickets", [{}])
    total_count = total[0].get("count", 0) if total else 0

    period_total = facets.get("period_tickets", [{}])
    period_count = period_total[0].get("count", 0) if period_total else 0

    resolved = facets.get("resolved_in_period", [{}])
    resolved_count = resolved[0].get("count", 0) if resolved else 0

    avg_res = facets.get("avg_resolution_time", [{}])
    avg_resolution = None
    if avg_res and avg_res[0].get("avg_time"):
        avg_ms = avg_res[0]["avg_time"]
        avg_resolution = {
            "hours": round(avg_ms / (1000 * 60 * 60), 1),
            "minutes": round(avg_ms / (1000 * 60), 0)
        }

    sla_data = facets.get("sla_breached", [{}])
    sla_breached = sla_data[0].get("count", 0) if sla_data else 0

    csat_pipeline = [
        {"$match": {"created_at": {"$gte": cutoff}}},
        {"$group": {
            "_id": None,
            "avg_rating": {"$avg": "$rating"},
            "total_responses": {"$sum": 1},
            "by_rating": {"$push": "$rating"}
        }}
    ]
    csat_result = list(csat_responses_collection.aggregate(csat_pipeline))
    csat_metrics = serialize_for_export(csat_result[0]) if csat_result else None

    return {
        "period": period,
        "total_tickets": total_count,
        "tickets_in_period": period_count,
        "resolved_in_period": resolved_count,
        "resolution_rate": round(resolved_count / period_count * 100, 1) if period_count > 0 else 0,
        "by_status": {item["_id"]: item["count"] for item in facets.get("by_status", [])},
        "by_priority": {item["_id"]: item["count"] for item in facets.get("by_priority", [])},
        "by_source": {item["_id"]: item["count"] for item in facets.get("by_source", [])},
        "by_escalation": {item["_id"]: item["count"] for item in facets.get("by_escalation", [])},
        "avg_resolution_time": avg_resolution,
        "daily_trend": [{"date": d["_id"], "count": d["count"]} for d in facets.get("daily_created", [])],
        "sla_breached": sla_breached,
        "csat": csat_metrics
    }


@router.get("/analytics/agents")
async def get_agent_analytics(
    period: str = Query("7d"),
    current_user: dict = Depends(get_current_user)
):
    """Get per-agent performance analytics"""
    period_map = {"24h": 1, "7d": 7, "30d": 30, "90d": 90}
    days = period_map.get(period, 7)
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    agents = list(users_collection.find(
        {"role": {"$in": ["agent", "admin", "lead"]}},
        {"_id": 0, "user_id": 1, "name": 1, "email": 1, "role": 1}
    ))

    agent_stats = []
    for agent in agents:
        uid = agent["user_id"]
        pipeline = [
            {"$match": {"assignee_id": uid}},
            {"$facet": {
                "total": [{"$count": "count"}],
                "open": [
                    {"$match": {"status": {"$nin": ["resolved", "closed", "merged"]}}},
                    {"$count": "count"}
                ],
                "resolved_period": [
                    {"$match": {"status": {"$in": ["resolved", "closed"]}, "updated_at": {"$gte": cutoff}}},
                    {"$count": "count"}
                ],
                "avg_resolution": [
                    {"$match": {"resolved_at": {"$exists": True}}},
                    {"$project": {"resolution_time": {"$subtract": ["$resolved_at", "$created_at"]}}},
                    {"$group": {"_id": None, "avg_time": {"$avg": "$resolution_time"}}}
                ]
            }}
        ]
        result = list(tickets_collection.aggregate(pipeline))
        facets = result[0] if result else {}

        total = facets.get("total", [{}])
        open_count = facets.get("open", [{}])
        resolved = facets.get("resolved_period", [{}])
        avg_res = facets.get("avg_resolution", [{}])

        avg_hours = None
        if avg_res and avg_res[0].get("avg_time"):
            avg_hours = round(avg_res[0]["avg_time"] / (1000 * 60 * 60), 1)

        agent_stats.append({
            "user_id": uid,
            "name": agent.get("name", ""),
            "email": agent.get("email", ""),
            "role": agent.get("role", ""),
            "total_tickets": total[0].get("count", 0) if total else 0,
            "open_tickets": open_count[0].get("count", 0) if open_count else 0,
            "resolved_in_period": resolved[0].get("count", 0) if resolved else 0,
            "avg_resolution_hours": avg_hours
        })

    agent_stats.sort(key=lambda x: x["resolved_in_period"], reverse=True)
    return {"period": period, "agents": agent_stats}
