# ==============================================================================
# LOGIC OVERVIEW:
# This module provides user authentication and session management.
#
# KEY RESPONSIBILITIES:
# 1. JWT & Cookie Dual Auth: Accepts JWT tokens either from Authorization Bearer
#    headers (for programmatic API use) or HttpOnly cookies (for the Next.js web app).
# 2. Secure Password Hashing: Uses Argon2/bcrypt for safe credential verification.
# 3. User Identity Dependency (get_current_user): Injected across protected routes
#    to enforce authentication and retrieve the active User object.
# ==============================================================================

from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, decode_access_token
from app.models.models import User
from app.schemas.schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["Auth"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login", auto_error=False)

# ------------------------------------------------------------------------------
# CORE CODE: Current User Resolver Dependency
# LOGIC:
# 1. Inspects the HTTP Authorization header or 'pace_session' HttpOnly cookie.
# 2. Decodes and cryptographically validates the signed JWT access token.
# 3. Fetches the active User entity from the DB; rejects inactive or deleted accounts.
# ------------------------------------------------------------------------------
async def get_current_user(
    request: Request,
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db)
) -> User:
    # Try token from Authorization header or cookie
    auth_token = token
    if not auth_token:
        auth_token = request.cookies.get("pace_session")
    
    if not auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = decode_access_token(auth_token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    
    return user

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="User with this email already exists")
    
    user = User(
        email=req.email,
        password_hash=get_password_hash(req.password),
        full_name=req.full_name
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user

@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == req.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(req.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    
    token = create_access_token(user.id)
    # Set HttpOnly signed cookie for web application
    response.set_cookie(
        key="pace_session",
        value=token,
        httponly=True,
        samesite="lax",
        secure=False  # Allow local HTTP testing; toggle via settings in prod
    )
    return TokenResponse(access_token=token)

@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("pace_session")
    return {"message": "Logged out successfully"}

@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    return current_user
