"""
Auth router — register, login, refresh, and /me endpoints.
"""
import uuid
from fastapi import APIRouter, HTTPException, status, Depends
from pydantic import BaseModel, EmailStr

from database import get_db_connection
from services.auth_service import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
)

router = APIRouter(prefix="/auth")


# ── Request / Response models ──────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class UserResponse(BaseModel):
    id: str
    username: str
    email: str


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest):
    """Create a new user account."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Check for existing email or username
    cursor.execute(
        "SELECT id FROM users WHERE email = %s OR username = %s",
        (req.email, req.username),
    )
    if cursor.fetchone():
        cursor.close()
        conn.close()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email or username already registered",
        )

    user_id = str(uuid.uuid4())
    password_hash = hash_password(req.password)

    cursor.execute(
        "INSERT INTO users (id, username, email, password_hash) VALUES (%s, %s, %s, %s)",
        (user_id, req.username, req.email, password_hash),
    )
    conn.commit()
    cursor.close()
    conn.close()

    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """Authenticate and return JWT tokens."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, password_hash FROM users WHERE email = %s",
        (req.email,),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row or not verify_password(req.password, row["password_hash"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    return TokenResponse(
        access_token=create_access_token(row["id"]),
        refresh_token=create_refresh_token(row["id"]),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(user_id: str = Depends(get_current_user)):
    """Return the current user's profile."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, username, email FROM users WHERE id = %s",
        (user_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    conn.close()

    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    return UserResponse(id=row["id"], username=row["username"], email=row["email"])


@router.post("/refresh", response_model=TokenResponse)
async def refresh(req: RefreshRequest):
    """Exchange a refresh token for a new access + refresh token pair."""
    payload = decode_token(req.refresh_token)

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    user_id = payload.get("sub")
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )
