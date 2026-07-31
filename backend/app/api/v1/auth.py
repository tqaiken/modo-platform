from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)
from app.models.user import User, UserRole
from app.schemas.user import (
    UserCreate,
    UserCreateByAdmin,
    UserLogin,
    UserRead,
    TokenResponse,
)


router = APIRouter(prefix="/auth")


@router.post("/register", status_code=status.HTTP_403_FORBIDDEN)
def register_disabled():
    """
    Public registration is disabled.

    Users must be created by SUPER_ADMIN.
    """
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Public registration is disabled. Users must be created by SUPER_ADMIN.",
    )


@router.post(
    "/bootstrap-super-admin",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
)
def bootstrap_super_admin(payload: UserCreate, db: Session = Depends(get_db)):
    """
    Create the first SUPER_ADMIN user.

    This endpoint works only when there are no users in the database.
    After the first user is created, this endpoint becomes unavailable.
    """
    existing_user = db.query(User).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Bootstrap is disabled because users already exist.",
        )

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=UserRole.SUPER_ADMIN,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.post(
    "/users",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
)
def create_user_by_super_admin(
    payload: UserCreateByAdmin,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a user.

    Only SUPER_ADMIN can create users.
    """
    if current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only SUPER_ADMIN can create users.",
        )

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered.",
        )

    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
        role=payload.role,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return UserRead.model_validate(user)


@router.post("/login", response_model=TokenResponse)
def login(payload: UserLogin, db: Session = Depends(get_db)):
    """
    Authenticate user and return JWT.

    SUPER_ADMIN, CURATOR, VERIFIER and DEVELOPER all sign in with email and password.
    """
    user = db.query(User).filter(User.email == payload.email).first()

    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials.",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account deactivated.",
        )

    token = create_access_token(data={"sub": str(user.id)})
    return TokenResponse(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
def get_me(user: User = Depends(get_current_user)):
    """
    Get current authenticated user.
    """
    return UserRead.model_validate(user)