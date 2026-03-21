# MealMate Authentication Design

**Date:** 2026-03-21
**Status:** Draft
**Author:** Claude + Alonso

## Problem

MealMate has no authentication. All API endpoints are publicly accessible, including those that call the OpenAI API (meal plan generation, meal regeneration). The app is deployed on a Synology NAS and will be exposed to the internet via reverse proxy. Without auth, anyone who discovers the URL can consume OpenAI credits, delete data, or view personal meal plans.

## Goals

- Protect all API endpoints behind authentication
- Support two user accounts (Alonso + girlfriend), each linked to their own profile
- Allow registration only with a secret invite code
- Keep users logged in for 30 days for convenience
- Share all app data (meal plans, shopping lists, inventory) between both users

## Non-Goals

- Multi-tenancy / household isolation (only 2 users, all data shared)
- OAuth / social login (overkill for 2 users)
- Role-based permissions (no admin vs regular user distinction)
- Email verification or password reset flows (can be added later)

## Approach

JWT tokens stored in HTTP-only cookies. Chosen over localStorage JWT (XSS-vulnerable) and server-side sessions (unnecessary DB lookups per request for 2 users).

## Database Changes

### New table: `users`

Schema: `mealmate`

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | String(36) | Primary key, default uuid4 (matches existing ID pattern) |
| `email` | String(255) | Unique, not null, stored lowercase |
| `hashed_password` | String(255) | Not null |
| `created_at` | DateTime | Default now(), not null |

### Modified table: `profiles`

Add column:

| Column | Type | Constraints |
|--------|------|-------------|
| `user_id` | String(36) | FK to users.id, nullable, unique |

Nullable to avoid breaking existing profiles during migration. Unique because each user links to exactly one profile.

### Migration

Alembic migration that:
1. Creates `users` table
2. Adds `user_id` column to `profiles` table

No data migration needed — users will link to profiles after registration.

## Auth Endpoints

New route file: `backend/app/routes/auth.py`, mounted at `/api/auth`.

### POST `/api/auth/register`

**Auth required:** No

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword",
  "invite_code": "the-secret-code"
}
```

**Behavior:**
1. Check user count — if already 2 users registered → 403 "Registration closed"
2. Validate invite code matches `INVITE_CODE` env var → 403 if wrong
3. Normalize email to lowercase
4. Check email not already registered → 409 if exists
5. Validate password meets minimum length (8 chars)
6. Hash password with bcrypt
7. Create user record
8. Generate JWT, set HTTP-only cookie
9. Return user info (id, email)

### POST `/api/auth/login`

**Auth required:** No

**Request body:**
```json
{
  "email": "user@example.com",
  "password": "securepassword"
}
```

**Behavior:**
1. Normalize email to lowercase, find user by email → 401 if not found
2. Verify password against hash → 401 if wrong
3. Generate JWT, set HTTP-only cookie
4. Return user info (id, email, linked profile id)

### POST `/api/auth/logout`

**Auth required:** Yes

**Behavior:**
1. Clear the auth cookie (set expired cookie)
2. Return 200

### GET `/api/auth/me`

**Auth required:** Yes

**Behavior:**
1. Return current user info (id, email, linked profile id, profile name)

## Token Strategy

**Single JWT token** with 30-day expiry. No access/refresh token split.

**Rationale:** For a 2-user app with HTTP-only cookies (immune to XSS theft), the complexity of token refresh is not justified. To force-logout all users, change the `JWT_SECRET` env var and restart.

**JWT payload:**
```json
{
  "sub": "user-uuid-string",
  "email": "user@example.com",
  "iat": 1234567890,
  "exp": 1234567890
}
```

**Cookie configuration:**

| Attribute | Value | Reason |
|-----------|-------|--------|
| `HttpOnly` | `True` | Prevents JavaScript access (XSS protection) |
| `SameSite` | `Strict` | Prevents CSRF (cookie only sent from same site) |
| `Secure` | `True` in prod, `False` in dev | Only sent over HTTPS in production. Backend checks `X-Forwarded-Proto` header to detect HTTPS behind reverse proxy. |
| `Max-Age` | `2592000` (30 days) | Matches JWT expiry |
| `Path` | `/` | Sent to all routes. `SameSite=Strict` already limits scope to same-origin. Using `/` avoids issues if endpoints are added outside `/api`. |

## Backend Auth Layer

### New module: `backend/app/auth.py`

Responsibilities:
- `hash_password(password: str) -> str` — bcrypt hash
- `verify_password(plain: str, hashed: str) -> bool` — bcrypt verify
- `create_jwt(user_id: str, email: str) -> str` — encode JWT with PyJWT, includes sub, email, iat, exp
- `decode_jwt(token: str) -> dict` — decode and validate JWT with PyJWT
- `set_auth_cookie(response: Response, token: str)` — set HTTP-only cookie on response
- `clear_auth_cookie(response: Response)` — expire the cookie

### New dependency: `get_current_user`

Added to `backend/app/dependencies.py`:
1. Extract JWT from cookie named `mealmate_auth`
2. Decode and validate → raise 401 if invalid or expired
3. Look up user in DB → raise 401 if not found
4. Return user object

### Route protection

Apply `get_current_user` dependency to all route files:
- `routes/profiles.py` — all endpoints
- `routes/meal_plans.py` — all endpoints
- `routes/shopping.py` — all endpoints
- `routes/inventory.py` — all endpoints

**Unprotected endpoints:**
- `GET /health`
- `POST /api/auth/register`
- `POST /api/auth/login`

## Backend Schemas

New Pydantic models in `backend/app/schemas.py`:

- `UserRegister` — email (EmailStr), password (min_length=8), invite_code
- `UserLogin` — email (EmailStr), password
- `UserResponse` — id, email, created_at
- `UserMeResponse` — id, email, profile_id (nullable), profile_name (nullable)

## Frontend Changes

### New pages

**`LoginPage.tsx`**
- Email + password form
- "Don't have an account? Register" link
- On submit: POST `/api/auth/login` with `credentials: "include"`
- On success: redirect to `/dashboard`
- On error: show error message

**`RegisterPage.tsx`**
- Email + password + invite code form
- "Already have an account? Login" link
- On submit: POST `/api/auth/register` with `credentials: "include"`
- On success: redirect to `/dashboard`
- On error: show error message

### Auth context: `AuthContext.tsx`

```
AuthProvider wraps the entire app.

State:
- user: UserMeResponse | null
- isLoading: boolean

On mount:
- Call GET /api/auth/me
- If 200: set user
- If 401: set user to null

Exposes:
- user, isLoading
- login(email, password) → calls API, sets user
- register(email, password, inviteCode) → calls API, sets user
- logout() → calls API, clears user
```

### Route protection: `AuthGuard.tsx`

- Wraps all routes except `/login` and `/register`
- If `isLoading`: show loading spinner
- If `user` is null: redirect to `/login`
- Otherwise: render children

### API client changes (`client.ts`)

- Add `credentials: "include"` to the `config` object in `apiRequest()` so cookies are sent with every request
- Add global 401 handling: if any API call returns 401, redirect to `/login` — **except** for `/api/auth/login` and `/api/auth/register` endpoints (otherwise a failed login would cause an infinite redirect loop)

### Profile linking UX

After registration, if the user's `profile_id` is null:
- Show a one-time prompt on the dashboard: "Which profile is yours?"
- List existing profiles to choose from, or option to create new
- POST to a new endpoint: `PUT /api/auth/link-profile/{profile_id}`
- This sets `user_id` on the selected profile

## New endpoint for profile linking

### PUT `/api/auth/link-profile/{profile_id}`

**Auth required:** Yes

**Behavior:**
1. Check profile exists → 404 if not
2. Check profile not already linked to another user → 409 if taken
3. Set `user_id` on profile to current user's id
4. Return updated profile

## Configuration

### New environment variables

| Variable | Required | Example | Purpose |
|----------|----------|---------|---------|
| `JWT_SECRET` | Yes | 64-char random string | Signs JWT tokens |
| `INVITE_CODE` | Yes | `mealmate-family-2026` | Required for registration |

### New Python dependencies

| Package | Purpose |
|---------|---------|
| `PyJWT>=2.8.0` | JWT encode/decode (actively maintained, replaces unmaintained python-jose) |
| `bcrypt>=4.0.0` | Password hashing (used directly, replaces unmaintained passlib) |
| `python-multipart` | Form data parsing (FastAPI requirement) |
| `email-validator` | Email format validation via Pydantic `EmailStr` |

### Infrastructure changes

**`docker-compose.yml`** — add `JWT_SECRET` and `INVITE_CODE` to the backend service environment block:
```yaml
backend:
  environment:
    - JWT_SECRET=${JWT_SECRET}
    - INVITE_CODE=${INVITE_CODE}
```

**`.github/workflows/deploy.yml`** — add to the `.env` file construction step:
```
JWT_SECRET=${{ secrets.JWT_SECRET }}
INVITE_CODE=${{ secrets.INVITE_CODE }}
```

**`backend/app/database.py`** — add `JWT_SECRET: str` and `INVITE_CODE: str` to the `Settings` class so they are validated at startup via pydantic-settings.

**`.env.example`** — add `JWT_SECRET` and `INVITE_CODE` entries.

### No changes needed to

- `frontend/nginx.conf` — proxy already forwards headers correctly, cookies pass through transparently
- CI pipeline config — pipeline itself unchanged

## Testing Strategy

### Test fixture strategy

Existing route tests will break because all routes now require authentication. Create a shared test helper that:
- Creates a test user in the DB
- Generates a valid JWT cookie
- Provides an authenticated `AsyncClient` fixture that includes the cookie

This lets existing tests add auth with minimal changes (use the authenticated client fixture instead of the plain one).

### Backend tests
- Auth registration with valid/invalid invite codes
- Registration blocked after 2 users exist
- Login with correct/incorrect credentials
- Login with mixed-case email works (normalization)
- Protected routes return 401 without cookie
- Protected routes work with valid cookie
- Profile linking
- Password minimum length enforcement

### Frontend tests
- Login form submission and redirect
- Register form with invite code
- AuthGuard redirects unauthenticated users
- Logout clears state

## Security Considerations

- Passwords hashed with bcrypt (slow hash, resistant to brute force)
- JWT secret must be a strong random string (not a guessable word)
- HTTP-only cookies prevent XSS token theft
- SameSite=Strict prevents CSRF attacks
- Secure flag ensures cookies only sent over HTTPS in production
- Invite code prevents unauthorized registration
- No password stored in JWT payload
- Hard cap of 2 registered users prevents abuse even if invite code leaks
- Emails normalized to lowercase to prevent duplicate accounts via case variations
- Rate limiting on login/register is NOT included (acceptable for 2-user app, can add later)
