# Authentication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add JWT-based authentication with HTTP-only cookies to protect all API endpoints, supporting 2 user accounts with invite-code-gated registration.

**Architecture:** New `users` table with email/password auth. JWT tokens stored in HTTP-only cookies (`SameSite=Strict`, `Secure` in prod). Backend `get_current_user` dependency protects all routes. Frontend `AuthContext` + `AuthGuard` wraps the app. Registration requires an invite code and is capped at 2 users.

**Tech Stack:** PyJWT, bcrypt, email-validator (backend); React Context + react-router-dom (frontend)

**Spec:** `docs/superpowers/specs/2026-03-21-authentication-design.md`

---

## File Structure

### New files
| File | Responsibility |
|------|---------------|
| `backend/app/auth.py` | Password hashing, JWT encode/decode, cookie helpers |
| `backend/app/routes/auth.py` | Register, login, logout, me, link-profile endpoints |
| `backend/tests/test_auth.py` | Auth endpoint tests |
| `frontend/src/contexts/AuthContext.tsx` | Auth state management, login/register/logout functions |
| `frontend/src/components/AuthGuard.tsx` | Route protection component |
| `frontend/src/pages/LoginPage.tsx` | Login form page |
| `frontend/src/pages/RegisterPage.tsx` | Registration form page |
| `frontend/src/test/LoginPage.test.tsx` | Login page tests |
| `frontend/src/test/RegisterPage.test.tsx` | Register page tests |

### Modified files
| File | Change |
|------|--------|
| `backend/requirements.txt` | Add PyJWT, bcrypt, email-validator |
| `backend/app/database.py` | Add `JWT_SECRET`, `INVITE_CODE` to Settings |
| `backend/app/models.py` | Add `User` model, add `user_id` FK to `Profile` |
| `backend/app/schemas.py` | Add auth-related Pydantic schemas |
| `backend/app/dependencies.py` | Add `get_current_user` dependency |
| `backend/app/main.py` | Register auth router |
| `backend/app/routes/profiles.py` | Add `get_current_user` dependency to all endpoints |
| `backend/app/routes/meal_plans.py` | Add `get_current_user` dependency to all endpoints |
| `backend/app/routes/shopping.py` | Add `get_current_user` dependency to all endpoints |
| `backend/app/routes/inventory.py` | Add `get_current_user` dependency to all endpoints |
| `backend/tests/conftest.py` | Add auth test fixtures (create_user, auth_client) |
| `frontend/src/types.ts` | Add `User`, `UserMe` types |
| `frontend/src/api/client.ts` | Add `credentials: "include"`, global 401 redirect |
| `frontend/src/App.tsx` | Wrap with AuthProvider, add AuthGuard, add login/register routes |
| `docker-compose.yml` | Add `JWT_SECRET`, `INVITE_CODE` to backend environment |
| `.github/workflows/deploy.yml` | Add `JWT_SECRET`, `INVITE_CODE` to .env creation |
| `.env.example` | Add `JWT_SECRET`, `INVITE_CODE` entries |

---

## Task 1: Backend Dependencies & Configuration

**Files:**
- Modify: `backend/requirements.txt`
- Modify: `backend/app/database.py:10-20` (Settings class)
- Modify: `.env.example`

- [ ] **Step 1: Add new Python dependencies**

Add to `backend/requirements.txt`:

```
PyJWT>=2.8.0
bcrypt>=4.0.0
email-validator>=2.1.0
```

- [ ] **Step 2: Add auth settings to Settings class**

In `backend/app/database.py`, add two fields to the `Settings` class after `OPENAI_MODEL`:

```python
    JWT_SECRET: str  # Required — no default. App won't start without it.
    INVITE_CODE: str  # Required — no default. App won't start without it.
```

- [ ] **Step 3: Update .env.example**

Add to `.env.example`:

```
JWT_SECRET=change-me-to-a-random-64-char-string
INVITE_CODE=your-secret-invite-code
```

- [ ] **Step 4: Install dependencies**

Run: `cd backend && uv pip install -r requirements.txt`
Expected: All packages install successfully

- [ ] **Step 5: Commit**

```bash
git add backend/requirements.txt backend/app/database.py .env.example
git commit -m "feat(auth): add auth dependencies and settings"
```

---

## Task 2: User Model & Profile FK

**Files:**
- Modify: `backend/app/models.py`

- [ ] **Step 1: Add User model**

Add at the top of models.py, after the existing imports and before the `Profile` class:

```python
class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=datetime.utcnow
    )

    profile: Mapped["Profile | None"] = relationship(back_populates="user")
```

- [ ] **Step 2: Add user_id FK to Profile model**

Add to the `Profile` class, after `created_at` and before `meal_portions`:

```python
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=True, unique=True
    )

    user: Mapped["User | None"] = relationship(back_populates="profile")
```

- [ ] **Step 3: Verify models load correctly**

Run: `cd backend && uv run python -c "from app.models import User, Profile; print('OK')"`
Expected: `OK`

- [ ] **Step 4: Commit**

```bash
git add backend/app/models.py
git commit -m "feat(auth): add User model and user_id FK on Profile"
```

---

## Task 2B: Alembic Migration

**Files:**
- Create: `backend/alembic/versions/<auto>_add_users_table_and_user_id_to_profiles.py`

- [ ] **Step 1: Generate Alembic migration**

Run: `cd backend && uv run alembic revision --autogenerate -m "add users table and user_id to profiles"`
Expected: A new migration file is created in `backend/alembic/versions/`

- [ ] **Step 2: Review the generated migration**

Open the generated file and verify it:
1. Creates the `users` table with columns: `id`, `email`, `hashed_password`, `created_at`
2. Adds `user_id` column to `profiles` table with FK to `users.id`
3. Adds unique constraint on `profiles.user_id`

- [ ] **Step 3: Commit**

```bash
git add backend/alembic/versions/
git commit -m "feat(auth): add migration for users table and profile user_id FK"
```

---

## Task 3: Auth Utilities Module

**Files:**
- Create: `backend/app/auth.py`

- [ ] **Step 1: Write the auth utilities module**

Create `backend/app/auth.py`:

```python
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Response

from app.database import settings

COOKIE_NAME = "mealmate_auth"
TOKEN_EXPIRY_DAYS = 30
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())


def create_jwt(user_id: str, email: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "email": email,
        "iat": now,
        "exp": now + timedelta(days=TOKEN_EXPIRY_DAYS),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_jwt(token: str) -> dict:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[ALGORITHM])


def _is_production() -> bool:
    """Detect production by checking if any CORS origin uses HTTPS."""
    return any(o.strip().startswith("https://") for o in settings.CORS_ORIGINS.split(","))


def set_auth_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="strict",
        secure=_is_production(),
        max_age=TOKEN_EXPIRY_DAYS * 24 * 60 * 60,
        path="/",
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(key=COOKIE_NAME, path="/")
```

- [ ] **Step 2: Verify module imports**

Run: `cd backend && uv run python -c "from app.auth import hash_password, verify_password, create_jwt, decode_jwt; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/auth.py
git commit -m "feat(auth): add auth utilities (JWT, bcrypt, cookies)"
```

---

## Task 4: Auth Pydantic Schemas

**Files:**
- Modify: `backend/app/schemas.py`

- [ ] **Step 1: Add auth schemas**

Add at the top of the imports in `backend/app/schemas.py`:

```python
from pydantic import EmailStr
```

Then add a new section at the end of the file, before the `MessageResponse` class:

```python
# ---------------------------------------------------------------------------
# Auth schemas
# ---------------------------------------------------------------------------


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8)
    invite_code: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserResponse(BaseModel):
    id: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class UserMeResponse(BaseModel):
    id: str
    email: str
    profile_id: str | None = None
    profile_name: str | None = None
```

- [ ] **Step 2: Verify schemas load**

Run: `cd backend && uv run python -c "from app.schemas import UserRegister, UserLogin, UserResponse, UserMeResponse; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/schemas.py
git commit -m "feat(auth): add auth Pydantic schemas"
```

---

## Task 5: Auth Dependency (get_current_user)

**Files:**
- Modify: `backend/app/dependencies.py`

- [ ] **Step 1: Add get_current_user dependency**

Replace the entire content of `backend/app/dependencies.py`:

```python
from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import COOKIE_NAME, decode_jwt
from app.database import get_db
from app.models import User


async def get_current_user(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_jwt(token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token payload")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user


__all__ = ["get_db", "get_current_user"]
```

- [ ] **Step 2: Verify dependency imports**

Run: `cd backend && uv run python -c "from app.dependencies import get_current_user; print('OK')"`
Expected: `OK`

- [ ] **Step 3: Commit**

```bash
git add backend/app/dependencies.py
git commit -m "feat(auth): add get_current_user dependency"
```

---

## Task 6: Auth Test Fixtures

**Files:**
- Modify: `backend/tests/conftest.py`

- [ ] **Step 1: Add auth helpers to conftest.py**

Add these imports at the top of `backend/tests/conftest.py`:

```python
from app.auth import create_jwt, hash_password
from app.models import User
```

Add this autouse fixture **before** the existing `setup_db` fixture to override settings for the test environment:

```python
@pytest_asyncio.fixture(autouse=True, scope="session")
def override_settings():
    """Provide required settings for tests so they don't need a .env file."""
    import app.database as db_module
    db_module.settings.JWT_SECRET = "test-secret-key-for-testing-only"
    db_module.settings.INVITE_CODE = "test-invite"
    yield
```

Add these fixtures after the existing `client` fixture:

```python
@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user and return it."""
    user = User(
        email="test@example.com",
        hashed_password=hash_password("testpassword123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def auth_client(
    db_session: AsyncSession, test_user: User
) -> AsyncGenerator[AsyncClient, None]:
    """AsyncClient with a valid auth cookie."""

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    token = create_jwt(test_user.id, test_user.email)
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://test",
        cookies={"mealmate_auth": token},
    ) as ac:
        yield ac
    app.dependency_overrides.clear()
```

Also add `User` to the import from `app.models` if not already imported (the existing conftest doesn't import models directly, so add it).

- [ ] **Step 2: Verify fixtures load**

Run: `cd backend && uv run python -m pytest tests/test_health.py -v --co`
Expected: Shows collected tests without errors

- [ ] **Step 3: Commit**

```bash
git add backend/tests/conftest.py
git commit -m "feat(auth): add test fixtures for authenticated requests"
```

---

## Task 7: Auth Routes (TDD)

**Files:**
- Create: `backend/tests/test_auth.py`
- Create: `backend/app/routes/auth.py`
- Modify: `backend/app/main.py`

- [ ] **Step 1: Write the auth route tests**

Create `backend/tests/test_auth.py`:

```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import hash_password
from app.models import User


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "user1@example.com",
            "password": "securepass123",
            "invite_code": "test-invite",  # matches override_settings fixture
        },
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["email"] == "user1@example.com"
    assert "id" in body
    assert "mealmate_auth" in resp.cookies


@pytest.mark.asyncio
async def test_register_bad_invite_code(client: AsyncClient):
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "user1@example.com",
            "password": "securepass123",
            "invite_code": "wrong-code",
        },
    )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient):
    data = {
        "email": "dup@example.com",
        "password": "securepass123",
        "invite_code": "test-invite",
    }
    resp1 = await client.post("/api/auth/register", json=data)
    assert resp1.status_code == 201
    resp2 = await client.post("/api/auth/register", json=data)
    assert resp2.status_code == 409


@pytest.mark.asyncio
async def test_register_max_users(client: AsyncClient, db_session: AsyncSession):
    # Create 2 users directly in DB
    for i in range(2):
        user = User(
            email=f"existing{i}@example.com",
            hashed_password=hash_password("password123"),
        )
        db_session.add(user)
    await db_session.commit()

    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "third@example.com",
            "password": "securepass123",
            "invite_code": "test-invite",
        },
    )
    assert resp.status_code == 403
    assert "closed" in resp.json()["detail"].lower()


@pytest.mark.asyncio
async def test_register_short_password(client: AsyncClient):
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "user1@example.com",
            "password": "short",
            "invite_code": "test-invite",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_register_invalid_email(client: AsyncClient):
    resp = await client.post(
        "/api/auth/register",
        json={
            "email": "not-an-email",
            "password": "securepass123",
            "invite_code": "test-invite",
        },
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, db_session: AsyncSession):
    user = User(
        email="login@example.com",
        hashed_password=hash_password("mypassword123"),
    )
    db_session.add(user)
    await db_session.commit()

    resp = await client.post(
        "/api/auth/login",
        json={"email": "login@example.com", "password": "mypassword123"},
    )
    assert resp.status_code == 200
    assert "mealmate_auth" in resp.cookies
    assert resp.json()["email"] == "login@example.com"


@pytest.mark.asyncio
async def test_login_case_insensitive_email(client: AsyncClient, db_session: AsyncSession):
    user = User(
        email="case@example.com",
        hashed_password=hash_password("mypassword123"),
    )
    db_session.add(user)
    await db_session.commit()

    resp = await client.post(
        "/api/auth/login",
        json={"email": "CASE@Example.com", "password": "mypassword123"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, db_session: AsyncSession):
    user = User(
        email="wrong@example.com",
        hashed_password=hash_password("correctpassword"),
    )
    db_session.add(user)
    await db_session.commit()

    resp = await client.post(
        "/api/auth/login",
        json={"email": "wrong@example.com", "password": "wrongpassword"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    resp = await client.post(
        "/api/auth/login",
        json={"email": "nobody@example.com", "password": "password123"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_authenticated(auth_client: AsyncClient):
    resp = await auth_client.get("/api/auth/me")
    assert resp.status_code == 200
    body = resp.json()
    assert body["email"] == "test@example.com"
    assert "id" in body


@pytest.mark.asyncio
async def test_me_unauthenticated(client: AsyncClient):
    resp = await client.get("/api/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_logout(auth_client: AsyncClient):
    resp = await auth_client.post("/api/auth/logout")
    assert resp.status_code == 200
    # Cookie should be cleared (set to empty/expired)
    assert "mealmate_auth" in resp.headers.get("set-cookie", "")


@pytest.mark.asyncio
async def test_link_profile(auth_client: AsyncClient, test_user):
    # Create a profile first
    profile_resp = await auth_client.post(
        "/api/profiles",
        json={"name": "Alonso", "goal": "muscle_gain"},
    )
    profile_id = profile_resp.json()["id"]

    resp = await auth_client.put(f"/api/auth/link-profile/{profile_id}")
    assert resp.status_code == 200
    assert resp.json()["user_id"] == test_user.id


@pytest.mark.asyncio
async def test_link_profile_already_taken(
    auth_client: AsyncClient, db_session: AsyncSession
):
    # Create another user and a profile linked to them
    other_user = User(
        email="other@example.com",
        hashed_password=hash_password("password123"),
    )
    db_session.add(other_user)
    await db_session.commit()
    await db_session.refresh(other_user)

    profile_resp = await auth_client.post(
        "/api/profiles",
        json={"name": "Maria", "goal": "fat_loss"},
    )
    profile_id = profile_resp.json()["id"]

    # Link to other user directly in DB
    from app.models import Profile
    from sqlalchemy import select

    result = await db_session.execute(
        select(Profile).where(Profile.id == profile_id)
    )
    profile = result.scalar_one()
    profile.user_id = other_user.id
    await db_session.commit()

    # Try to link to our user — should fail
    resp = await auth_client.put(f"/api/auth/link-profile/{profile_id}")
    assert resp.status_code == 409
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run python -m pytest tests/test_auth.py -v`
Expected: All tests FAIL (routes don't exist yet)

- [ ] **Step 3: Create the auth routes**

Create `backend/app/routes/auth.py`:

```python
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
from app.schemas import UserLogin, UserMeResponse, UserRegister, UserResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])

MAX_USERS = 2


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(
    body: UserRegister,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    # Check user cap
    count = await db.scalar(select(func.count()).select_from(User))
    if count >= MAX_USERS:
        raise HTTPException(status_code=403, detail="Registration closed")

    # Validate invite code
    if body.invite_code != settings.INVITE_CODE:
        raise HTTPException(status_code=403, detail="Invalid invite code")

    # Normalize email
    email = body.email.lower()

    # Check for duplicate
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


@router.post("/logout")
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


@router.put("/link-profile/{profile_id}")
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
```

- [ ] **Step 4: Register auth router in main.py**

In `backend/app/main.py`, add the import:

```python
from app.routes.auth import router as auth_router
```

And add below the existing `include_router` calls:

```python
app.include_router(auth_router)
```

- [ ] **Step 5: Run auth tests**

Run: `cd backend && uv run python -m pytest tests/test_auth.py -v`
Expected: All tests PASS

- [ ] **Step 6: Run all backend tests to check nothing broke**

Run: `cd backend && uv run python -m pytest tests/ -v`
Expected: All tests PASS (existing tests still use unauthenticated `client` fixture and routes aren't protected yet)

- [ ] **Step 7: Commit**

```bash
git add backend/app/routes/auth.py backend/tests/test_auth.py backend/app/main.py
git commit -m "feat(auth): add auth routes (register, login, logout, me, link-profile)"
```

---

## Task 8: Protect Existing Routes

**Files:**
- Modify: `backend/app/routes/profiles.py`
- Modify: `backend/app/routes/meal_plans.py`
- Modify: `backend/app/routes/shopping.py`
- Modify: `backend/app/routes/inventory.py`

- [ ] **Step 1: Add auth dependency to profiles routes**

In `backend/app/routes/profiles.py`, add import:

```python
from app.dependencies import get_current_user
from app.models import Profile, User
```

Remove the old `from app.models import Profile` import.

Add `_: User = Depends(get_current_user)` as a parameter to every route function. For example:

```python
@router.get("", response_model=list[ProfileResponse])
async def list_profiles(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
```

Apply the same pattern to `create_profile`, `get_profile`, `update_profile`, `delete_profile`.

- [ ] **Step 2: Add auth dependency to meal_plans routes**

In `backend/app/routes/meal_plans.py`, add import:

```python
from app.dependencies import get_current_user
from app.models import User
```

Add `_: User = Depends(get_current_user)` as a parameter to every route function: `generate_meal_plan`, `list_meal_plans`, `get_meal_plan`, `regenerate_meal`, `delete_meal_plan`.

- [ ] **Step 3: Add auth dependency to shopping routes**

In `backend/app/routes/shopping.py`, add import:

```python
from app.dependencies import get_current_user
from app.models import User
```

Add `_: User = Depends(get_current_user)` to the `get_shopping_list` function.

- [ ] **Step 4: Add auth dependency to inventory routes**

In `backend/app/routes/inventory.py`, add import:

```python
from app.dependencies import get_current_user
from app.models import User
```

Add `_: User = Depends(get_current_user)` to every route function: `list_inventory`, `create_item`, `update_item`, `delete_item`.

- [ ] **Step 5: Update existing tests to use auth_client**

In all existing test files (`test_profiles.py`, `test_meal_plans.py`, `test_shopping.py`, `test_inventory.py`), replace `client: AsyncClient` with `auth_client: AsyncClient` in every test function parameter. The `auth_client` fixture provides a valid auth cookie.

For example, in `test_profiles.py`:

```python
@pytest.mark.asyncio
async def test_list_profiles_empty(auth_client: AsyncClient):
    resp = await auth_client.get("/api/profiles")
    assert resp.status_code == 200
    assert resp.json() == []
```

Do NOT change `test_health.py` — the health endpoint stays unauthenticated.

- [ ] **Step 6: Add a test for unauthenticated access**

Add to `backend/tests/test_auth.py`:

```python
@pytest.mark.asyncio
async def test_protected_route_without_auth(client: AsyncClient):
    resp = await client.get("/api/profiles")
    assert resp.status_code == 401
```

- [ ] **Step 7: Run all backend tests**

Run: `cd backend && uv run python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 8: Commit**

```bash
git add backend/app/routes/ backend/tests/
git commit -m "feat(auth): protect all API routes with authentication"
```

---

## Task 9: Infrastructure Updates

**Files:**
- Modify: `docker-compose.yml`
- Modify: `.github/workflows/deploy.yml`

- [ ] **Step 1: Add env vars to docker-compose.yml**

In `docker-compose.yml`, add to the backend `environment` list, after `CORS_ORIGINS`:

```yaml
      - JWT_SECRET=${JWT_SECRET}
      - INVITE_CODE=${INVITE_CODE}
```

- [ ] **Step 2: Add secrets to deploy.yml**

In `.github/workflows/deploy.yml`, in the "Create .env file" step, add before the `EOF`:

```
          JWT_SECRET=${{ secrets.JWT_SECRET }}
          INVITE_CODE=${{ secrets.INVITE_CODE }}
```

- [ ] **Step 3: Commit**

```bash
git add docker-compose.yml .github/workflows/deploy.yml
git commit -m "feat(auth): add auth env vars to docker and deploy config"
```

---

## Task 10: Frontend Types & API Client Updates

**Files:**
- Modify: `frontend/src/types.ts`
- Modify: `frontend/src/api/client.ts`

- [ ] **Step 1: Add auth types**

Add to `frontend/src/types.ts`, before the `STORAGE_LABELS` constant:

```typescript
export interface User {
  id: string;
  email: string;
  created_at: string;
}

export interface UserMe {
  id: string;
  email: string;
  profile_id: string | null;
  profile_name: string | null;
}
```

- [ ] **Step 2: Update API client with credentials and 401 handling**

In `frontend/src/api/client.ts`, update the `apiRequest` function. Add `credentials: "include"` to the config and add 401 redirect logic:

```typescript
async function apiRequest<T>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const { body, headers: customHeaders, ...rest } = options;
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(customHeaders as Record<string, string>),
  };
  const config: RequestInit = { ...rest, headers, credentials: "include" };
  if (body !== undefined) {
    config.body = typeof body === "string" ? body : JSON.stringify(body);
  }
  const response = await fetch(`${BASE_URL}${endpoint}`, config);
  if (!response.ok) {
    // Redirect to login on 401, except for auth endpoints (including /auth/me
    // which is called on mount — without this exclusion, unauthenticated users
    // would hit an infinite reload loop)
    if (response.status === 401 && !endpoint.startsWith("/auth/")) {
      window.location.href = "/login";
      return undefined as T;
    }
    const errorBody = await response.json().catch(() => null);
    const message =
      errorBody?.detail ?? errorBody?.message ?? response.statusText;
    throw new ApiError(response.status, message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types.ts frontend/src/api/client.ts
git commit -m "feat(auth): add frontend auth types and API client credentials"
```

---

## Task 11: AuthContext

**Files:**
- Create: `frontend/src/contexts/AuthContext.tsx`

- [ ] **Step 1: Create the AuthContext**

Create `frontend/src/contexts/AuthContext.tsx`:

```typescript
import {
  createContext,
  useContext,
  useEffect,
  useState,
  useCallback,
  type ReactNode,
} from "react";
import { api, ApiError } from "@/api/client";
import type { UserMe } from "@/types";

interface AuthContextType {
  user: UserMe | null;
  isLoading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, inviteCode: string) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserMe | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    api
      .get<UserMe>("/auth/me")
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    await api.post("/auth/login", { email, password });
    const me = await api.get<UserMe>("/auth/me");
    setUser(me);
  }, []);

  const register = useCallback(
    async (email: string, password: string, inviteCode: string) => {
      await api.post("/auth/register", {
        email,
        password,
        invite_code: inviteCode,
      });
      const me = await api.get<UserMe>("/auth/me");
      setUser(me);
    },
    [],
  );

  const logout = useCallback(async () => {
    await api.post("/auth/logout");
    setUser(null);
  }, []);

  return (
    <AuthContext.Provider value={{ user, isLoading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/contexts/AuthContext.tsx
git commit -m "feat(auth): add AuthContext and AuthProvider"
```

---

## Task 12: Login Page

**Files:**
- Create: `frontend/src/pages/LoginPage.tsx`

- [ ] **Step 1: Create the Login page**

Create `frontend/src/pages/LoginPage.tsx`:

```typescript
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Loader2, UtensilsCrossed } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { ApiError } from "@/api/client";

export default function LoginPage() {
  const navigate = useNavigate();
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      navigate("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Something went wrong");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <UtensilsCrossed className="mx-auto h-10 w-10 text-primary" />
          <h1 className="mt-4 text-2xl font-bold">MealMate</h1>
          <p className="text-muted-foreground">Sign in to your account</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
          )}
          <div>
            <label htmlFor="email" className="block text-sm font-medium">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            Sign in
          </button>
        </form>
        <p className="text-center text-sm text-muted-foreground">
          Don't have an account?{" "}
          <Link to="/register" className="text-primary hover:underline">
            Register
          </Link>
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/LoginPage.tsx
git commit -m "feat(auth): add login page"
```

---

## Task 13: Register Page

**Files:**
- Create: `frontend/src/pages/RegisterPage.tsx`

- [ ] **Step 1: Create the Register page**

Create `frontend/src/pages/RegisterPage.tsx`:

```typescript
import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Loader2, UtensilsCrossed } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import { ApiError } from "@/api/client";

export default function RegisterPage() {
  const navigate = useNavigate();
  const { register } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [inviteCode, setInviteCode] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await register(email, password, inviteCode);
      navigate("/dashboard");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Something went wrong");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center px-4">
      <div className="w-full max-w-sm space-y-6">
        <div className="text-center">
          <UtensilsCrossed className="mx-auto h-10 w-10 text-primary" />
          <h1 className="mt-4 text-2xl font-bold">MealMate</h1>
          <p className="text-muted-foreground">Create your account</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          {error && (
            <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
          )}
          <div>
            <label htmlFor="email" className="block text-sm font-medium">
              Email
            </label>
            <input
              id="email"
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2"
            />
          </div>
          <div>
            <label htmlFor="password" className="block text-sm font-medium">
              Password
            </label>
            <input
              id="password"
              type="password"
              required
              minLength={8}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2"
            />
            <p className="mt-1 text-xs text-muted-foreground">
              Minimum 8 characters
            </p>
          </div>
          <div>
            <label htmlFor="invite-code" className="block text-sm font-medium">
              Invite Code
            </label>
            <input
              id="invite-code"
              type="text"
              required
              value={inviteCode}
              onChange={(e) => setInviteCode(e.target.value)}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2"
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="flex w-full items-center justify-center gap-2 rounded-md bg-primary px-4 py-2 text-primary-foreground hover:bg-primary/90 disabled:opacity-50"
          >
            {loading && <Loader2 className="h-4 w-4 animate-spin" />}
            Create account
          </button>
        </form>
        <p className="text-center text-sm text-muted-foreground">
          Already have an account?{" "}
          <Link to="/login" className="text-primary hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/RegisterPage.tsx
git commit -m "feat(auth): add register page"
```

---

## Task 14: AuthGuard & App Routing

**Files:**
- Create: `frontend/src/components/AuthGuard.tsx`
- Modify: `frontend/src/App.tsx`

- [ ] **Step 1: Create AuthGuard component**

Create `frontend/src/components/AuthGuard.tsx`:

```typescript
import { Navigate } from "react-router-dom";
import { Loader2 } from "lucide-react";
import { useAuth } from "@/contexts/AuthContext";
import type { ReactNode } from "react";

export default function AuthGuard({ children }: { children: ReactNode }) {
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  return <>{children}</>;
}
```

- [ ] **Step 2: Update App.tsx with AuthProvider and route guards**

Replace `frontend/src/App.tsx` with:

```typescript
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { AuthProvider } from "./contexts/AuthContext";
import AuthGuard from "./components/AuthGuard";
import BottomNav from "./components/BottomNav";
import Dashboard from "./pages/Dashboard";
import MealPlanPage from "./pages/MealPlanPage";
import ShoppingListPage from "./pages/ShoppingListPage";
import ProfilesPage from "./pages/ProfilesPage";
import InventoryPage from "./pages/InventoryPage";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";

function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route
        path="/*"
        element={
          <AuthGuard>
            <div className="min-h-screen pb-20 bg-background">
              <Routes>
                <Route path="/" element={<Navigate to="/dashboard" replace />} />
                <Route path="/dashboard" element={<Dashboard />} />
                <Route path="/meal-plans/:id" element={<MealPlanPage />} />
                <Route path="/shopping/:id" element={<ShoppingListPage />} />
                <Route path="/profiles" element={<ProfilesPage />} />
                <Route path="/inventory" element={<InventoryPage />} />
              </Routes>
              <BottomNav />
            </div>
          </AuthGuard>
        }
      />
    </Routes>
  );
}

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
```

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/AuthGuard.tsx frontend/src/App.tsx
git commit -m "feat(auth): add AuthGuard and protect frontend routes"
```

---

## Task 15: Profile Linking UX

**Files:**
- Modify: `frontend/src/pages/Dashboard.tsx`

- [ ] **Step 1: Add profile linking prompt to Dashboard**

In `frontend/src/pages/Dashboard.tsx`, add imports:

```typescript
import { useAuth } from "@/contexts/AuthContext";
import { api } from "@/api/client";
```

Inside the `Dashboard` component, after the existing state declarations, add:

```typescript
  const { user } = useAuth();
  const [linkingProfile, setLinkingProfile] = useState(false);
```

Then, in the JSX return, add a banner at the top (before the existing content) that shows when the user has no linked profile:

```typescript
  {user && !user.profile_id && profiles.length > 0 && (
    <div className="mx-4 mt-4 rounded-lg border bg-card p-4">
      <p className="text-sm font-medium">Which profile is yours?</p>
      <div className="mt-2 flex flex-wrap gap-2">
        {profiles.map((p) => (
          <button
            key={p.id}
            disabled={linkingProfile}
            onClick={async () => {
              setLinkingProfile(true);
              try {
                await api.put(`/auth/link-profile/${p.id}`);
                window.location.reload();
              } catch {
                setLinkingProfile(false);
              }
            }}
            className="rounded-md border px-3 py-1.5 text-sm hover:bg-accent"
          >
            {p.name} ({p.goal.replace("_", " ")})
          </button>
        ))}
      </div>
    </div>
  )}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/pages/Dashboard.tsx
git commit -m "feat(auth): add profile linking prompt on dashboard"
```

---

## Task 16: Frontend Tests

**Files:**
- Create: `frontend/src/test/LoginPage.test.tsx`
- Create: `frontend/src/test/RegisterPage.test.tsx`
- Modify: existing frontend tests to mock auth

- [ ] **Step 1: Create login page test**

Create `frontend/src/test/LoginPage.test.tsx`:

```typescript
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
      this.name = "ApiError";
    }
  },
}));

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: vi.fn(),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { useAuth } from "@/contexts/AuthContext";
import LoginPage from "@/pages/LoginPage";

const mockedUseAuth = vi.mocked(useAuth);

function renderLogin() {
  return render(
    <MemoryRouter initialEntries={["/login"]}>
      <LoginPage />
    </MemoryRouter>,
  );
}

describe("LoginPage", () => {
  const mockLogin = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockedUseAuth.mockReturnValue({
      user: null,
      isLoading: false,
      login: mockLogin,
      register: vi.fn(),
      logout: vi.fn(),
    });
  });

  it("renders login form", () => {
    renderLogin();
    expect(screen.getByLabelText("Email")).toBeTruthy();
    expect(screen.getByLabelText("Password")).toBeTruthy();
    expect(screen.getByText("Sign in")).toBeTruthy();
  });

  it("calls login on form submit", async () => {
    mockLogin.mockResolvedValue(undefined);
    renderLogin();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "password123");
    await user.click(screen.getByText("Sign in"));

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith("test@example.com", "password123");
    });
  });

  it("shows error on failed login", async () => {
    const { ApiError } = await import("@/api/client");
    mockLogin.mockRejectedValue(new ApiError(401, "Invalid email or password"));
    renderLogin();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Email"), "test@example.com");
    await user.type(screen.getByLabelText("Password"), "wrongpass");
    await user.click(screen.getByText("Sign in"));

    await waitFor(() => {
      expect(screen.getByText("Invalid email or password")).toBeTruthy();
    });
  });

  it("has link to register page", () => {
    renderLogin();
    expect(screen.getByText("Register")).toBeTruthy();
  });
});
```

- [ ] **Step 2: Create register page test**

Create `frontend/src/test/RegisterPage.test.tsx`:

```typescript
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  api: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    status: number;
    constructor(status: number, message: string) {
      super(message);
      this.status = status;
      this.name = "ApiError";
    }
  },
}));

vi.mock("@/contexts/AuthContext", () => ({
  useAuth: vi.fn(),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));

import { useAuth } from "@/contexts/AuthContext";
import RegisterPage from "@/pages/RegisterPage";

const mockedUseAuth = vi.mocked(useAuth);

function renderRegister() {
  return render(
    <MemoryRouter initialEntries={["/register"]}>
      <RegisterPage />
    </MemoryRouter>,
  );
}

describe("RegisterPage", () => {
  const mockRegister = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    mockedUseAuth.mockReturnValue({
      user: null,
      isLoading: false,
      login: vi.fn(),
      register: mockRegister,
      logout: vi.fn(),
    });
  });

  it("renders register form with invite code field", () => {
    renderRegister();
    expect(screen.getByLabelText("Email")).toBeTruthy();
    expect(screen.getByLabelText("Password")).toBeTruthy();
    expect(screen.getByLabelText("Invite Code")).toBeTruthy();
    expect(screen.getByText("Create account")).toBeTruthy();
  });

  it("calls register on form submit", async () => {
    mockRegister.mockResolvedValue(undefined);
    renderRegister();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Email"), "new@example.com");
    await user.type(screen.getByLabelText("Password"), "securepass123");
    await user.type(screen.getByLabelText("Invite Code"), "my-secret");
    await user.click(screen.getByText("Create account"));

    await waitFor(() => {
      expect(mockRegister).toHaveBeenCalledWith(
        "new@example.com",
        "securepass123",
        "my-secret",
      );
    });
  });

  it("shows error on failed registration", async () => {
    const { ApiError } = await import("@/api/client");
    mockRegister.mockRejectedValue(new ApiError(403, "Invalid invite code"));
    renderRegister();

    const user = userEvent.setup();
    await user.type(screen.getByLabelText("Email"), "new@example.com");
    await user.type(screen.getByLabelText("Password"), "securepass123");
    await user.type(screen.getByLabelText("Invite Code"), "wrong");
    await user.click(screen.getByText("Create account"));

    await waitFor(() => {
      expect(screen.getByText("Invalid invite code")).toBeTruthy();
    });
  });

  it("has link to login page", () => {
    renderRegister();
    expect(screen.getByText("Sign in")).toBeTruthy();
  });
});
```

- [ ] **Step 3: Update existing frontend tests for auth mock**

In each existing test file (`Dashboard.test.tsx`, `ProfilesPage.test.tsx`, `InventoryPage.test.tsx`, `ShoppingListPage.test.tsx`), add this mock block after the existing `vi.mock("@/api/client")`:

```typescript
vi.mock("@/contexts/AuthContext", () => ({
  useAuth: () => ({
    user: { id: "1", email: "test@example.com", profile_id: "p1", profile_name: "Test" },
    isLoading: false,
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
  }),
  AuthProvider: ({ children }: { children: React.ReactNode }) => <>{children}</>,
}));
```

- [ ] **Step 4: Run all frontend tests**

Run: `cd frontend && npm run test`
Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/test/
git commit -m "feat(auth): add frontend auth tests and update existing test mocks"
```

---

## Task 17: Final Verification

- [ ] **Step 1: Run all backend tests**

Run: `cd backend && uv run python -m pytest tests/ -v`
Expected: All tests PASS

- [ ] **Step 2: Run all frontend tests**

Run: `cd frontend && npm run test`
Expected: All tests PASS

- [ ] **Step 3: Verify frontend builds**

Run: `cd frontend && npm run build`
Expected: Build succeeds with no TypeScript errors

- [ ] **Step 4: Final commit if any remaining changes**

```bash
git status
# If clean, nothing to do. If there are changes, stage and commit.
```
