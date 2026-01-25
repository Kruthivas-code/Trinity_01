"""
Trinity Leave Management System
- All team members can apply for leave
- Custom leave types (not fixed categories)
- Auto-approval with minimal friction
- No limits, just track usage
- Team calendar view + leave conflicts detection
"""

from datetime import datetime, timezone, date, timedelta
from typing import Optional, List
from pydantic import BaseModel
import uuid


# ============== Pydantic Models ==============

class LeaveRequest(BaseModel):
    """Request model for creating a leave entry"""
    user_id: str
    leave_type: str  # Custom - e.g., "Sick", "Vacation", "Personal", "WFH", etc.
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    reason: Optional[str] = None
    is_half_day: Optional[bool] = False
    half_day_type: Optional[str] = None  # "first_half" or "second_half"


class LeaveUpdate(BaseModel):
    """Request model for updating a leave entry"""
    leave_type: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    reason: Optional[str] = None
    status: Optional[str] = None  # "approved", "denied", "cancelled"
    is_half_day: Optional[bool] = None
    half_day_type: Optional[str] = None
    admin_note: Optional[str] = None


# ============== Leave Manager Class ==============

class LeaveManager:
    def __init__(self, db):
        self.db = db
        self.leaves_collection = db.leaves
        self.users_collection = db.users
        
    def _calculate_days(self, start_date: str, end_date: str, is_half_day: bool) -> float:
        """Calculate the number of leave days"""
        if is_half_day:
            return 0.5
        
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
        
        delta = end - start
        return max(1, delta.days + 1)

    async def create_leave(self, leave_data: LeaveRequest) -> dict:
        """Create a new leave entry (auto-approved)"""
        leave_id = f"leave_{uuid.uuid4().hex[:12]}"
        now = datetime.now(timezone.utc).isoformat()
        
        # Get user info
        user = self.users_collection.find_one({"user_id": leave_data.user_id})
        user_name = user.get("name", "Unknown") if user else "Unknown"
        user_email = user.get("email", "") if user else ""
        
        # Calculate days
        days_count = self._calculate_days(
            leave_data.start_date, 
            leave_data.end_date, 
            leave_data.is_half_day or False
        )
        
        leave_doc = {
            "id": leave_id,
            "user_id": leave_data.user_id,
            "user_name": user_name,
            "user_email": user_email,
            "leave_type": leave_data.leave_type,
            "start_date": leave_data.start_date,
            "end_date": leave_data.end_date,
            "reason": leave_data.reason,
            "status": "approved",  # Auto-approved
            "is_half_day": leave_data.is_half_day or False,
            "half_day_type": leave_data.half_day_type,
            "admin_note": None,
            "days_count": days_count,
            "created_at": now,
            "updated_at": now
        }
        
        self.leaves_collection.insert_one(leave_doc)
        return leave_doc

    async def get_leave(self, leave_id: str) -> Optional[dict]:
        """Get a single leave entry"""
        return self.leaves_collection.find_one({"id": leave_id})

    async def get_leaves(
        self, 
        user_id: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        status: Optional[str] = None,
        leave_type: Optional[str] = None
    ) -> List[dict]:
        """Get leaves with optional filters"""
        query = {}
        
        if user_id:
            query["user_id"] = user_id
        if status:
            query["status"] = status
        if leave_type:
            query["leave_type"] = leave_type
            
        # Date range filter - get leaves that overlap with the date range
        if start_date or end_date:
            if start_date and end_date:
                query["$or"] = [
                    {"start_date": {"$gte": start_date, "$lte": end_date}},
                    {"end_date": {"$gte": start_date, "$lte": end_date}},
                    {"$and": [{"start_date": {"$lte": start_date}}, {"end_date": {"$gte": end_date}}]}
                ]
            elif start_date:
                query["end_date"] = {"$gte": start_date}
            elif end_date:
                query["start_date"] = {"$lte": end_date}
        
        cursor = self.leaves_collection.find(query).sort("start_date", -1)
        return list(cursor)

    async def update_leave(self, leave_id: str, update_data: LeaveUpdate) -> Optional[dict]:
        """Update a leave entry (admin can edit/deny)"""
        update_dict = {k: v for k, v in update_data.dict().items() if v is not None}
        
        if not update_dict:
            return await self.get_leave(leave_id)
        
        # Recalculate days if dates changed
        if "start_date" in update_dict or "end_date" in update_dict or "is_half_day" in update_dict:
            existing = self.leaves_collection.find_one({"id": leave_id})
            if existing:
                start = update_dict.get("start_date", existing["start_date"])
                end = update_dict.get("end_date", existing["end_date"])
                is_half = update_dict.get("is_half_day", existing.get("is_half_day", False))
                update_dict["days_count"] = self._calculate_days(start, end, is_half)
        
        update_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        self.leaves_collection.update_one(
            {"id": leave_id},
            {"$set": update_dict}
        )
        
        return await self.get_leave(leave_id)

    async def delete_leave(self, leave_id: str) -> bool:
        """Delete a leave entry"""
        result = self.leaves_collection.delete_one({"id": leave_id})
        return result.deleted_count > 0

    async def get_team_calendar(self, year: int, month: int) -> List[dict]:
        """Get team calendar for a month showing who's on leave each day"""
        import calendar
        
        # Get first and last day of month
        _, last_day = calendar.monthrange(year, month)
        start_date = f"{year}-{month:02d}-01"
        end_date = f"{year}-{month:02d}-{last_day:02d}"
        
        # Get all approved leaves that overlap with this month
        leaves = list(self.leaves_collection.find({
            "status": "approved",
            "$or": [
                {"start_date": {"$lte": end_date, "$gte": start_date}},
                {"end_date": {"$lte": end_date, "$gte": start_date}},
                {"$and": [{"start_date": {"$lte": start_date}}, {"end_date": {"$gte": end_date}}]}
            ]
        }))
        
        # Build calendar
        calendar_days = []
        for day in range(1, last_day + 1):
            current_date = f"{year}-{month:02d}-{day:02d}"
            current = datetime.strptime(current_date, "%Y-%m-%d").date()
            
            # Find leaves for this day
            day_leaves = []
            for leave in leaves:
                leave_start = datetime.strptime(leave["start_date"], "%Y-%m-%d").date()
                leave_end = datetime.strptime(leave["end_date"], "%Y-%m-%d").date()
                
                if leave_start <= current <= leave_end:
                    day_leaves.append({
                        "id": leave["id"],
                        "user_id": leave["user_id"],
                        "user_name": leave.get("user_name", "Unknown"),
                        "leave_type": leave["leave_type"],
                        "is_half_day": leave.get("is_half_day", False),
                        "half_day_type": leave.get("half_day_type")
                    })
            
            # Determine conflict level
            people_out = len(day_leaves)
            if people_out == 0:
                conflict_level = "none"
            elif people_out == 1:
                conflict_level = "low"
            elif people_out == 2:
                conflict_level = "medium"
            else:
                conflict_level = "high"
            
            calendar_days.append({
                "date": current_date,
                "weekday": current.strftime("%a"),
                "is_weekend": current.weekday() >= 5,
                "leaves": day_leaves,
                "conflict_level": conflict_level,
                "people_out": people_out
            })
        
        return calendar_days

    async def check_conflicts(self, start_date: str, end_date: str, exclude_user_id: Optional[str] = None) -> dict:
        """Check for leave conflicts on given dates"""
        # Find approved leaves that overlap
        query = {
            "status": "approved",
            "$or": [
                {"start_date": {"$lte": end_date, "$gte": start_date}},
                {"end_date": {"$lte": end_date, "$gte": start_date}},
                {"$and": [{"start_date": {"$lte": start_date}}, {"end_date": {"$gte": end_date}}]}
            ]
        }
        
        # Exclude the requesting user if specified
        if exclude_user_id:
            query["user_id"] = {"$ne": exclude_user_id}
        
        leaves = list(self.leaves_collection.find(query))
        
        people_on_leave = [{
            "user_id": l["user_id"],
            "user_name": l.get("user_name", "Unknown"),
            "leave_type": l["leave_type"],
            "start_date": l["start_date"],
            "end_date": l["end_date"]
        } for l in leaves]
        
        count = len(people_on_leave)
        
        if count == 0:
            return {
                "has_conflict": False,
                "conflict_level": "none",
                "people_on_leave": [],
                "message": "No conflicts found"
            }
        elif count == 1:
            return {
                "has_conflict": False,
                "conflict_level": "low",
                "people_on_leave": people_on_leave,
                "message": f"1 person on leave during this period"
            }
        elif count == 2:
            return {
                "has_conflict": True,
                "conflict_level": "medium",
                "people_on_leave": people_on_leave,
                "message": f"{count} people on leave during this period"
            }
        else:
            return {
                "has_conflict": True,
                "conflict_level": "high",
                "people_on_leave": people_on_leave,
                "message": f"{count} people on leave - high conflict!"
            }

    async def get_user_leave_summary(self, user_id: str, year: Optional[int] = None) -> dict:
        """Get leave summary for a user"""
        if year is None:
            year = datetime.now().year
        
        start_date = f"{year}-01-01"
        end_date = f"{year}-12-31"
        
        leaves = list(self.leaves_collection.find({
            "user_id": user_id,
            "start_date": {"$gte": start_date, "$lte": end_date}
        }))
        
        # Group by type
        by_type = {}
        total_days = 0
        
        for leave in leaves:
            leave_type = leave["leave_type"]
            days = leave.get("days_count", 1)
            
            if leave_type not in by_type:
                by_type[leave_type] = {"count": 0, "days": 0}
            
            by_type[leave_type]["count"] += 1
            by_type[leave_type]["days"] += days
            total_days += days
        
        return {
            "user_id": user_id,
            "year": year,
            "total_leaves": len(leaves),
            "total_days": total_days,
            "by_type": by_type,
            "leaves": leaves
        }

    async def get_leave_types(self) -> List[str]:
        """Get all unique leave types used in the system"""
        types = self.leaves_collection.distinct("leave_type")
        
        # Add common defaults if none exist
        default_types = ["Sick Leave", "Vacation", "Personal", "Work from Home", "Other"]
        
        if not types:
            return default_types
        
        # Merge with defaults (keeping unique)
        all_types = list(set(types + default_types))
        return sorted(all_types)


# Singleton instance
_leave_manager = None

def get_leave_manager(db):
    global _leave_manager
    if _leave_manager is None:
        _leave_manager = LeaveManager(db)
    return _leave_manager
