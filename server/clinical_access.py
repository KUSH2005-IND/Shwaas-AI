from fastapi import HTTPException
from sqlalchemy import select
from server.db import User, Screening

def screening_scope(user):
    if user.role == "doctor":
        if not user.phc_center:
            raise HTTPException(403, "No facility assigned.")
        return Screening.user_id.in_(select(User.id).where(User.phc_center == user.phc_center))
    return Screening.user_id == user.id

def visible_screenings(db, user):
    return db.query(Screening).filter(screening_scope(user))

def require_screening(db, user, screening_id):
    item = visible_screenings(db, user).filter(Screening.id == screening_id).first()
    if item is None:
        raise HTTPException(404, "Case not found or not assigned to your facility.")
    return item

