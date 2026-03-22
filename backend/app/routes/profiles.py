import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Profile, User
from app.schemas import ProfileCreate, ProfileResponse, ProfileUpdate

router = APIRouter(prefix="/api/profiles", tags=["profiles"])


@router.get("", response_model=list[ProfileResponse])
async def list_profiles(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Profile).order_by(Profile.created_at))
    return result.scalars().all()


@router.post("", response_model=ProfileResponse, status_code=201)
async def create_profile(
    body: ProfileCreate,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = Profile(
        name=body.name,
        goal=body.goal,
        restrictions=json.dumps(body.restrictions),
        calorie_target=body.calorie_target,
        protein_target=body.protein_target,
        carbs_target=body.carbs_target,
        fat_target=body.fat_target,
    )
    db.add(profile)
    await db.commit()
    await db.refresh(profile)
    return profile


@router.get("/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.put("/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: str,
    body: ProfileUpdate,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    update_data = body.model_dump(exclude_unset=True)
    if "restrictions" in update_data:
        update_data["restrictions"] = json.dumps(update_data["restrictions"])

    for key, value in update_data.items():
        setattr(profile, key, value)

    await db.commit()
    await db.refresh(profile)
    return profile


@router.delete("/{profile_id}", status_code=204)
async def delete_profile(
    profile_id: str,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    profile = await db.get(Profile, profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    await db.delete(profile)
    await db.commit()
