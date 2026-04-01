from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, EmailStr
from app.database import get_db
from app.models.user import User, UserRole
from app.models.seller import Seller
from app.utils.security import hash_password, verify_password, create_access_token, create_refresh_token, decode_token
from datetime import timedelta

router = APIRouter(prefix="/auth", tags=["Auth"])


# ── Schemas ─────────────────────────────────────────────────────────────────

class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    role: UserRole = UserRole.buyer
    shop_name: str | None = None  # Required if role == seller


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str


class RefreshRequest(BaseModel):
    refresh_token: str


# ── Routes ───────────────────────────────────────────────────────────────────

@router.post(
    "/register", 
    response_model=TokenResponse, 
    status_code=status.HTTP_201_CREATED,
    summary="Register New User",
    description="Creates a new user account. If the role is 'seller', a corresponding seller profile is also created. Returns initial JWT tokens."
)
async def register(payload: RegisterRequest, db: AsyncSession = Depends(get_db)):
    # Check duplicate email
    existing = await db.execute(select(User).where(User.email == payload.email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    if payload.role == UserRole.seller and not payload.shop_name:
        raise HTTPException(status_code=400, detail="shop_name is required for seller accounts")

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
        role=payload.role,
    )
    db.add(user)
    await db.flush()  # Get user.id before commit

    if payload.role == UserRole.seller:
        # Ensure shop_name is unique
        existing_shop = await db.execute(select(Seller).where(Seller.shop_name == payload.shop_name))
        if existing_shop.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Shop name already taken")
        seller = Seller(user_id=user.id, shop_name=payload.shop_name)
        db.add(seller)

    await db.commit()
    await db.refresh(user)

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, role=user.role)


@router.post(
    "/login", 
    response_model=TokenResponse,
    summary="User Login",
    description="Authenticates a user via email and password (OAuth2 compatible) and returns access and refresh tokens."
)
async def login(form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == form_data.username))
    user = result.scalar_one_or_none()

    if not user or not verify_password(form_data.password, user.password_hash or ""):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    access_token = create_access_token({"sub": str(user.id)})
    refresh_token = create_refresh_token({"sub": str(user.id)})
    return TokenResponse(access_token=access_token, refresh_token=refresh_token, role=user.role)


@router.post(
    "/refresh", 
    response_model=TokenResponse,
    summary="Refresh Access Token",
    description="Issues a new access token and a new refresh token using a valid, non-expired refresh token."
)
async def refresh_token(payload: RefreshRequest, db: AsyncSession = Depends(get_db)):
    try:
        data = decode_token(payload.refresh_token)
        if data.get("type") != "refresh":
            raise ValueError()
        user_id = data.get("sub")
    except (ValueError, Exception):
        raise HTTPException(status_code=401, detail="Invalid refresh token")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    access_token = create_access_token({"sub": str(user.id)})
    new_refresh = create_refresh_token({"sub": str(user.id)})
    return TokenResponse(access_token=access_token, refresh_token=new_refresh, role=user.role)
