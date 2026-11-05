from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import datetime, timedelta
import jwt

from shared.database import engine, get_db, Base
from shared.errors import DomainException, domain_exception_handler

# Секретный ключ (тот же, что в shared/auth.py и api_gateway/config.py)
SECRET_KEY = "SUPER_SECRET_KEY_AGRI_SALES"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# --- Модель БД ---
class DBUser(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    password = Column(String) # В реальности тут должен быть хеш!
    role = Column(String)     # "Администратор", "Менеджер по продажам" и т.д.

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Identity Service")
app.add_exception_handler(DomainException, domain_exception_handler)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- Схемы ---
class UserCreate(BaseModel):
    username: str
    password: str
    role: str

# --- Вспомогательные функции ---
def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# --- ЭНДПОИНТЫ ---

# 1. Регистрация (для тестов, чтобы создать первого пользователя)
@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(DBUser).filter(DBUser.username == user.username).first():
        raise DomainException("Пользователь уже существует")
    
    db_user = DBUser(username=user.username, password=user.password, role=user.role)
    db.add(db_user)
    db.commit()
    return {"status": "created", "username": user.username, "role": user.role}

# 2. Логин (выдает JWT токен)
@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(DBUser).filter(DBUser.username == form_data.username).first()
    
    # Простая проверка пароля (в реальности compare_hash)
    if not user or user.password != form_data.password:
        raise HTTPException(status_code=401, detail="Неверный логин или пароль")
    
    # Генерируем токен
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role, "user_id": user.id}
    )
    return {"access_token": access_token, "token_type": "bearer"}

# 3. Получить информацию о себе (проверка токена)
@app.get("/users/me")
def read_users_me(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return {"username": payload.get("sub"), "role": payload.get("role")}
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Неверный токен")