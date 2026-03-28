from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Profile, User
from app.schemas import (
    MessageResponse,
    ProfileLinkResponse,
    UserMeResponse,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", status_code=410)
async def login_gone():
    raise HTTPException(
        status_code=410,
        detail="Login is now handled by Authelia at https://auth.zurera.cloud",
    )


@router.post("/register", status_code=410)
async def register_gone():
    raise HTTPException(
        status_code=410,
        detail="Registration is now handled by Authelia at https://auth.zurera.cloud",
    )


@router.post("/logout", response_model=MessageResponse)
async def logout():
    return {"message": "Logged out"}


@router.get("/me", response_model=UserMeResponse)
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Profile).where(Profile.user_id == current_user.id))
    profile = result.scalar_one_or_none()
    return UserMeResponse(
        id=current_user.id,
        email=current_user.email,
        profile_id=profile.id if profile else None,
        profile_name=profile.name if profile else None,
    )


@router.put("/link-profile/{profile_id}", response_model=ProfileLinkResponse)
async def link_profile(
    profile_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    if profile.user_id and profile.user_id != current_user.id:
        raise HTTPException(
            status_code=409, detail="Profile already linked to another user"
        )
    profile.user_id = current_user.id
    await db.commit()
    await db.refresh(profile)
    return {
        "id": profile.id,
        "name": profile.name,
        "user_id": profile.user_id,
    }
