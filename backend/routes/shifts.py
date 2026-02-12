"""
Shift management routes: CRUD, user-shift assignments, on-shift queries, schedule.
"""
from fastapi import APIRouter, HTTPException, Depends
from datetime import datetime, timezone
from typing import Optional, List
import uuid
import logging

from database import (
    users_collection, teams_collection, shifts_collection,
    user_shifts_collection,
)
from dependencies import get_current_user, require_lead_or_admin
from models.schemas import ShiftCreate, ShiftUpdate, UserShiftAssign
from utils import serialize_doc, get_ist_now, parse_time_str

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["shifts"])


def get_on_shift_members(team_id: str) -> List[dict]:
    """Get all team members currently on shift"""
    team = teams_collection.find_one({"team_id": team_id}, {"_id": 0})
    if not team:
        return []

    ist_now = get_ist_now()
    current_weekday = ist_now.isoweekday()
    current_time = ist_now.time()

    on_shift = []
    for member_id in team.get("members", []):
        user_shift_docs = list(user_shifts_collection.find(
            {"user_id": member_id, "team_id": team_id}, {"_id": 0}
        ))
        for us_doc in user_shift_docs:
            shift = shifts_collection.find_one(
                {"shift_id": us_doc.get("shift_id"), "is_active": True}, {"_id": 0}
            )
            if not shift:
                continue
            if current_weekday not in shift.get("days_of_week", []):
                continue
            start = parse_time_str(shift.get("start_time", "00:00"))
            end = parse_time_str(shift.get("end_time", "23:59"))
            is_on = False
            if start <= end:
                is_on = start <= current_time <= end
            else:
                is_on = current_time >= start or current_time <= end
            if is_on:
                user = users_collection.find_one(
                    {"user_id": member_id},
                    {"_id": 0, "user_id": 1, "name": 1, "email": 1}
                )
                if user:
                    on_shift.append(serialize_doc(user))
                break
    return on_shift


def is_user_on_shift(user_id: str, team_id: str) -> bool:
    """Check if a specific user is currently on shift for a team"""
    ist_now = get_ist_now()
    current_weekday = ist_now.isoweekday()
    current_time = ist_now.time()

    user_shift_docs = list(user_shifts_collection.find(
        {"user_id": user_id, "team_id": team_id}, {"_id": 0}
    ))
    for us_doc in user_shift_docs:
        shift = shifts_collection.find_one(
            {"shift_id": us_doc.get("shift_id"), "is_active": True}, {"_id": 0}
        )
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


@router.post("/shifts")
async def create_shift(
    shift_data: ShiftCreate,
    current_user: dict = Depends(require_lead_or_admin)
):
    """Create a new shift for a team - requires lead or admin role"""
    team = teams_collection.find_one({"team_id": shift_data.team_id})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    shift_id = f"shift_{uuid.uuid4().hex[:12]}"

    shift_doc = {
        "shift_id": shift_id,
        "team_id": shift_data.team_id,
        "name": shift_data.name,
        "start_time": shift_data.start_time,
        "end_time": shift_data.end_time,
        "days_of_week": shift_data.days_of_week,
        "is_active": True,
        "created_by": current_user["user_id"],
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)
    }

    shifts_collection.insert_one(shift_doc)
    return serialize_doc(shift_doc)


@router.get("/shifts")
async def get_all_shifts(current_user: dict = Depends(get_current_user)):
    """Get all shifts"""
    shifts = list(shifts_collection.find({}, {"_id": 0}))

    for shift in shifts:
        team = teams_collection.find_one({"team_id": shift.get("team_id")}, {"_id": 0, "name": 1, "escalation_level": 1})
        if team:
            shift["team_name"] = team.get("name")
            shift["team_escalation_level"] = team.get("escalation_level")

        user_shift_docs = list(user_shifts_collection.find({"shift_id": shift.get("shift_id")}, {"_id": 0}))
        user_ids = [us["user_id"] for us in user_shift_docs]

        shift["assigned_users_count"] = len(user_ids)

        if user_ids:
            users = list(users_collection.find(
                {"user_id": {"$in": user_ids}},
                {"_id": 0, "user_id": 1, "name": 1, "email": 1}
            ))
            shift["assigned_users"] = [serialize_doc(u) for u in users]
        else:
            shift["assigned_users"] = []

    return [serialize_doc(s) for s in shifts]


@router.get("/shifts/team/{team_id}")
async def get_team_shifts(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all shifts for a specific team"""
    shifts = list(shifts_collection.find({"team_id": team_id}, {"_id": 0}))

    for shift in shifts:
        user_shift_docs = list(user_shifts_collection.find({"shift_id": shift.get("shift_id")}, {"_id": 0}))
        user_ids = [us["user_id"] for us in user_shift_docs]

        if user_ids:
            users = list(users_collection.find(
                {"user_id": {"$in": user_ids}},
                {"_id": 0, "user_id": 1, "name": 1, "email": 1}
            ))
            shift["assigned_users"] = [serialize_doc(u) for u in users]
        else:
            shift["assigned_users"] = []

    return [serialize_doc(s) for s in shifts]


@router.put("/shifts/{shift_id}")
async def update_shift(
    shift_id: str,
    shift_data: ShiftUpdate,
    current_user: dict = Depends(require_lead_or_admin)
):
    """Update a shift - requires lead or admin role"""
    update_data = {"updated_at": datetime.now(timezone.utc)}

    if shift_data.name is not None:
        update_data["name"] = shift_data.name
    if shift_data.start_time is not None:
        update_data["start_time"] = shift_data.start_time
    if shift_data.end_time is not None:
        update_data["end_time"] = shift_data.end_time
    if shift_data.days_of_week is not None:
        update_data["days_of_week"] = shift_data.days_of_week
    if shift_data.is_active is not None:
        update_data["is_active"] = shift_data.is_active

    result = shifts_collection.update_one(
        {"shift_id": shift_id},
        {"$set": update_data}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Shift not found")

    shift = shifts_collection.find_one({"shift_id": shift_id}, {"_id": 0})
    return serialize_doc(shift)


@router.delete("/shifts/{shift_id}")
async def delete_shift(
    shift_id: str,
    current_user: dict = Depends(require_lead_or_admin)
):
    """Delete a shift - requires lead or admin role"""
    result = shifts_collection.delete_one({"shift_id": shift_id})

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Shift not found")

    user_shifts_collection.delete_many({"shift_id": shift_id})

    return {"message": "Shift deleted successfully"}


@router.post("/users/{user_id}/shifts")
async def assign_user_to_shift(
    user_id: str,
    assignment: UserShiftAssign,
    current_user: dict = Depends(get_current_user)
):
    """Assign a user to a shift"""
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    shift = shifts_collection.find_one({"shift_id": assignment.shift_id})
    if not shift:
        raise HTTPException(status_code=404, detail="Shift not found")

    existing = user_shifts_collection.find_one({
        "user_id": user_id,
        "shift_id": assignment.shift_id
    })
    if existing:
        raise HTTPException(status_code=400, detail="User already assigned to this shift")

    user_shift_id = f"us_{uuid.uuid4().hex[:12]}"

    user_shift_doc = {
        "user_shift_id": user_shift_id,
        "user_id": user_id,
        "team_id": shift.get("team_id"),
        "shift_id": assignment.shift_id,
        "is_primary": assignment.is_primary,
        "effective_from": assignment.effective_from or datetime.now(timezone.utc).isoformat(),
        "effective_to": None,
        "created_at": datetime.now(timezone.utc)
    }

    user_shifts_collection.insert_one(user_shift_doc)
    return serialize_doc(user_shift_doc)


@router.get("/users/{user_id}/shifts")
async def get_user_shifts(
    user_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all shifts assigned to a user"""
    user_shift_docs = list(user_shifts_collection.find({"user_id": user_id}, {"_id": 0}))

    for us_doc in user_shift_docs:
        shift = shifts_collection.find_one({"shift_id": us_doc.get("shift_id")}, {"_id": 0})
        if shift:
            us_doc["shift_details"] = serialize_doc(shift)
            team = teams_collection.find_one({"team_id": shift.get("team_id")}, {"_id": 0, "name": 1})
            if team:
                us_doc["team_name"] = team.get("name")

    return [serialize_doc(us) for us in user_shift_docs]


@router.delete("/users/{user_id}/shifts/{shift_id}")
async def remove_user_from_shift(
    user_id: str,
    shift_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a user from a shift"""
    result = user_shifts_collection.delete_one({
        "user_id": user_id,
        "shift_id": shift_id
    })

    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User shift assignment not found")

    return {"message": "User removed from shift successfully"}


@router.get("/teams/{team_id}/on-shift")
async def get_team_on_shift_members(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get all team members currently on shift"""
    team = teams_collection.find_one({"team_id": team_id}, {"_id": 0})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    on_shift = get_on_shift_members(team_id)
    ist_now = get_ist_now()

    return {
        "team_id": team_id,
        "team_name": team.get("name"),
        "current_time_ist": ist_now.strftime("%Y-%m-%d %H:%M:%S"),
        "on_shift_count": len(on_shift),
        "on_shift_members": on_shift
    }


@router.get("/teams/{team_id}/schedule")
async def get_team_schedule(
    team_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Get complete team schedule overview"""
    team = teams_collection.find_one({"team_id": team_id}, {"_id": 0})
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    shifts = list(shifts_collection.find({"team_id": team_id, "is_active": True}, {"_id": 0}))

    schedule = []
    for shift in shifts:
        shift_data = serialize_doc(shift)
        user_shift_docs = list(user_shifts_collection.find({"shift_id": shift.get("shift_id")}, {"_id": 0}))
        user_ids = [us["user_id"] for us in user_shift_docs]

        if user_ids:
            users = list(users_collection.find(
                {"user_id": {"$in": user_ids}},
                {"_id": 0, "user_id": 1, "name": 1, "email": 1}
            ))
            shift_data["members"] = [serialize_doc(u) for u in users]
        else:
            shift_data["members"] = []

        schedule.append(shift_data)

    ist_now = get_ist_now()

    return {
        "team_id": team_id,
        "team_name": team.get("name"),
        "escalation_level": team.get("escalation_level"),
        "current_time_ist": ist_now.strftime("%Y-%m-%d %H:%M:%S"),
        "current_day": ist_now.strftime("%A"),
        "total_members": len(team.get("members", [])),
        "on_shift_now": len(get_on_shift_members(team_id)),
        "shifts": schedule
    }
