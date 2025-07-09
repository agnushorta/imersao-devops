from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

import routers.auth as auth
import schemas
from database import get_db
from models import Aluno as UserModel

users_router = APIRouter()


@users_router.post("/users", response_model=schemas.Aluno, status_code=status.HTTP_201_CREATED)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = auth.get_user(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    hashed_password = auth.get_password_hash(user.password)
    user_data = user.dict(exclude={"password"})
    db_user = UserModel(**user_data, hashed_password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

