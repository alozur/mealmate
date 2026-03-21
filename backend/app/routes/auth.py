from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    clear_auth_cookie,
    create_jwt,
    hash_password,
    set_auth_cookie,
    verify_password,
)
from app.database import get_db, settings
from app.dependencies import get_current_user
from app.models import Profile, User
from app.schemas import MessageResponse, ProfileLinkResponse, UserLogin, UserMeResponse, UserRegister, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

MAX_USERS = 2


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    body: UserRegister,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    # Validate invite code first — don't reveal capacity info to invalid callers
    if body.invite_code != settings.INVITE_CODE:
        raise HTTPException(status_code=403, detail="Invalid invite code")

    # Hard cap for the 2-person household model
    count = await db.scalar(select(func.count()).select_from(User))
    if count >= MAX_USERS:
        raise HTTPException(status_code=403, detail="Registration closed")

    email = body.email.lower()

    existing = await db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    user = User(
        email=email,
        hashed_password=hash_password(body.password),
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = create_jwt(user.id, user.email)
    set_auth_cookie(response, token)
    return user


@router.post("/login", response_model=UserResponse)
async def login(
    body: UserLogin,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    email = body.email.lower()
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_jwt(user.id, user.email)
    set_auth_cookie(response, token)
    return user


@router.post("/logout", response_model=MessageResponse)
async def logout(
    response: Response,
    _: User = Depends(get_current_user),
):
    clear_auth_cookie(response)
    return {"message": "Logged out"}


@router.get("/me", response_model=UserMeResponse)
async def me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Profile).where(Profile.user_id == current_user.id)
    )
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
        raise HTTPException(status_code=409, detail="Profile already linked to another user")
    profile.user_id = current_user.id
    await db.commit()
    await db.refresh(profile)
    return {
        "id": profile.id,
        "name": profile.name,
        "user_id": profile.user_id,
    }
