"""
Team management routes: CRUD, member management, on-shift queries, schedule.
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import List
import uuid
import logging

from database import (
    users_collection, teams_collection, shifts_collection,
    user_shifts_collection, SYSTEM_TIMEZONE,
)
from dependencies import get_current_user, require_lead_or_admin, require_admin
from models.schemas import TeamCreate, TeamUpdate, TeamMemberAdd
from utils import serialize_doc, get_ist_now, parse_time_str

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["teams"])


@router.post("/teams")
async def create_team(
    team_data: TeamCreate,
    current_user: dict = Depends(require_lead_or_admin)
):
    """Create a new team"""
    team_id = f"team_{uuid.uuid4().hex[:12]}"

    team_doc = {
        "team_id": team_id,
        "name": team_data.name,
        "escalation_level": team_data.escalation_level,
        "description": team_data.description,
        "members": [],
        "lead_id": None,
        "last_assigned_idx": -1,
        "timezone": SYSTEM_TIMEZONE,
        "created_by": current_user["user_id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }

    teams_collection.insert_one(team_doc)
    return serialize_doc(team_doc)


@router.get("/teams")
async def get_teams(current_user: dict = Depends(get_current_user)):
    """List all teams - optimized to avoid N+1 queries"""
    teams = list(teams_collection.find({}, {"_id": 0}))

    all_member_ids = set()
    for team in teams:
        all_member_ids.update(team.get("members", []))

    all_users = {}
    if all_member_ids:
        users_list = list(users_collection.find(
            {"user_id": {"$in": list(all_member_ids)}},
            {"_id": 0, "user_id": 1, "name": 1, "email": 1, "role": 1}
        ))
        all_users = {u["user_id"]: u for u in users_list}

    all_shifts = {}
    user_shift_docs = list(user_shifts_collection.find(
        {"user_id": {"$in": list(all_member_ids)}},
        {"_id": 0}
    ))
    for us in user_shift_docs:
        if us["user_id"] not in all_shifts:
            all_shifts[us["user_id"]] = []
        all_shifts[us["user_id"]].append(us)

    shift_ids = set(us.get("shift_id") for us in user_shift_docs)
    active_shifts = {}
    if shift_ids:
        shifts_list = list(shifts_collection.find(
            {"shift_id": {"$in": list(shift_ids)}, "is_active": True},
            {"_id": 0}
        ))
        active_shifts = {s["shift_id"]: s for s in shifts_list}

    now = get_ist_now()
    current_weekday = now.isoweekday()
    current_time = now.time()

    def is_user_on_shift_cached(user_id: str, team_id: str) -> bool:
        user_shifts_list = all_shifts.get(user_id, [])
        for us in user_shifts_list:
            if us.get("team_id") != team_id:
                continue
            shift = active_shifts.get(us.get("shift_id"))
            if not shift:
                continue
            if current_weekday not in shift.get("days_of_week", []):
                continue
            start = parse_time_str(shift.get("start_time", "00:00"))
            end = parse_time_str(shift.get("end_time", "23:59"))
            if start <= end:
                if start <= current_time <= end:
                    return True
            else:
                if current_time >= start or current_time <= end:
                    return True
        return False

    for team in teams:
        team["member_count"] = len(team.get("members", []))
        members = []
        on_shift_count = 0

        for member_id in team.get("members", []):
            user = all_users.get(member_id)
            if user:
                member = user.copy()
                member["is_on_shift"] = is_user_on_shift_cached(member_id, team.get("team_id"))
                if member["is_on_shift"]:
                    on_shift_count += 1
                members.append(member)

        team["member_details"] = members
        team["on_shift_count"] = on_shift_count

    return [serialize_doc(team) for team in teams]


@router.get("/teams/{team_id}")
async def get_team(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get team details"""
    team = teams_collection.find_one({"team_id": team_id}, {"_id": 0})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    if team.get("members"):
        members = list(users_collection.find(
            {"user_id": {"$in": team["members"]}},
            {"_id": 0}
        ))
        team["member_details"] = [serialize_doc(m) for m in members]

    return serialize_doc(team)


@router.put("/teams/{team_id}")
async def update_team(
    team_id: str,
    team_data: TeamUpdate,
    current_user: dict = Depends(require_lead_or_admin)
):
    """Update team details"""
    update_data = {k: v for k, v in team_data.dict().items() if v is not None}
    update_data["updated_at"] = datetime.now(timezone.utc)

    result = teams_collection.update_one(
        {"team_id": team_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Team not found")

    return teams_collection.find_one({"team_id": team_id}, {"_id": 0})


@router.delete("/teams/{team_id}")
async def delete_team(
    team_id: str,
    current_user: dict = Depends(require_lead_or_admin)
):
    """Delete a team - requires lead or admin role"""
    users_collection.update_many(
        {"team_id": team_id},
        {"$unset": {"team_id": ""}}
    )

    result = teams_collection.delete_one({"team_id": team_id})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Team not found")

    logger.info(f"Team {team_id} deleted by user {current_user.get('user_id')}")
    return {"message": "Team deleted"}


@router.post("/teams/{team_id}/members")
async def add_team_member(
    team_id: str,
    member: TeamMemberAdd,
    current_user: dict = Depends(require_lead_or_admin)
):
    """Add a member to a team"""
    team = teams_collection.find_one({"team_id": team_id})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    user = users_collection.find_one({"user_id": member.user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    teams_collection.update_one(
        {"team_id": team_id},
        {
            "$addToSet": {"members": member.user_id},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )

    users_collection.update_one(
        {"user_id": member.user_id},
        {"$set": {"team_id": team_id, "updated_at": datetime.now(timezone.utc)}}
    )

    return {"message": "Member added", "team_id": team_id, "user_id": member.user_id}


@router.delete("/teams/{team_id}/members/{user_id}")
async def remove_team_member(
    team_id: str,
    user_id: str,
    current_user: dict = Depends(require_lead_or_admin)
):
    """Remove a member from a team"""
    result = teams_collection.update_one(
        {"team_id": team_id},
        {
            "$pull": {"members": user_id},
            "$set": {"updated_at": datetime.now(timezone.utc)}
        }
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Team not found")

    users_collection.update_one(
        {"user_id": user_id},
        {"$unset": {"team_id": ""}, "$set": {"updated_at": datetime.now(timezone.utc)}}
    )

    return {"message": "Member removed"}
