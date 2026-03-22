from contextlib import asynccontextmanager
from datetime import datetime
import os

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict, field_validator
from sqlalchemy import Column, DateTime, Integer, String, create_engine
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, declarative_base, sessionmaker
import uvicorn

load_dotenv()


def get_required_env(name: str, default: str | None = None) -> str:
    value = os.getenv(name, default)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


DATABASE_URL = get_required_env(
    "DATABASE_URL",
    "postgresql://postgres:password@localhost:5432/color_platform"
)
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5500")
PORT = int(os.getenv("PORT", "8000"))

engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    age = Column(Integer, nullable=False)
    designation = Column(String(255), nullable=False)
    location = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)


class UserLogin(BaseModel):
    name: str
    age: int
    designation: str
    location: str
    email: str

    @field_validator("name", "designation", "location", "email")
    @classmethod
    def validate_strings(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Field cannot be empty")
        return cleaned

    @field_validator("age")
    @classmethod
    def validate_age(cls, value: int) -> int:
        if value < 1 or value > 150:
            raise ValueError("Age must be between 1 and 150")
        return value

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = value.strip().lower()
        if "@" not in cleaned or "." not in cleaned:
            raise ValueError("Invalid email format")
        return cleaned

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "name": "John Doe",
                "age": 20,
                "designation": "Student",
                "location": "New York",
                "email": "john@example.com",
            }
        }
    )


class UserResponse(BaseModel):
    id: int
    name: str
    age: int
    designation: str
    location: str
    email: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class LoginResponse(BaseModel):
    success: bool
    message: str
    user_id: int


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    print("Database initialized successfully")
    yield


app = FastAPI(
    title="Color Educational Platform API",
    description="Backend API for Color Fusion login and user storage",
    version="1.1.0",
    lifespan=lifespan,
)

allowed_origins = [
    "http://localhost:3000",
    "http://localhost:5500",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:5500",
    FRONTEND_URL,
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(dict.fromkeys(allowed_origins)),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {
        "service": "Color Educational Platform API",
        "version": "1.1.0",
        "status": "running",
        "endpoints": {
            "health": "/health",
            "login": "POST /login",
            "users": "GET /users",
            "user_by_id": "GET /users/{user_id}",
        },
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "Color Educational Platform API",
    }


@app.post("/login", response_model=LoginResponse)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == user_data.email).first()

    if existing_user:
        return LoginResponse(
            success=True,
            message="Welcome back!",
            user_id=existing_user.id,
        )

    new_user = User(
        name=user_data.name,
        age=user_data.age,
        designation=user_data.designation,
        location=user_data.location,
        email=user_data.email,
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except IntegrityError:
        db.rollback()
        existing_user = db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            return LoginResponse(
                success=True,
                message="Welcome back!",
                user_id=existing_user.id,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )
    except SQLAlchemyError as exc:
        db.rollback()
        print(f"Database error during login: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process login. Please try again.",
        )

    return LoginResponse(
        success=True,
        message="Registration successful!",
        user_id=new_user.id,
    )


@app.get("/users", response_model=list[UserResponse])
async def get_users(db: Session = Depends(get_db)):
    try:
        return db.query(User).order_by(User.created_at.desc()).all()
    except SQLAlchemyError as exc:
        print(f"Database error while fetching users: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch users.",
        )


@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int, db: Session = Depends(get_db)):
    try:
        user = db.query(User).filter(User.id == user_id).first()
    except SQLAlchemyError as exc:
        print(f"Database error while fetching user {user_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user.",
        )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", port=PORT, reload=False)
