import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# Секретный ключ (в реальности должен совпадать с Identity Service)
SECRET_KEY = "SUPER_SECRET_KEY_AGRI_SALES"
ALGORITHM = "HS256"

security = HTTPBearer()

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Проверяет токен и возвращает данные пользователя."""
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Токен истек")
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный токен")

def require_role(required_role: str):
    """Декоратор для проверки роли пользователя."""
    def role_checker(user: dict = Depends(get_current_user)):
        if user.get("role") != required_role and user.get("role") != "Администратор":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN, 
                detail="Недостаточно прав"
            )
        return user
    return role_checker