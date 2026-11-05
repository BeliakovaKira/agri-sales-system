from fastapi import FastAPI, Request, HTTPException, Depends, Form
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from typing import List, Optional
import httpx
import jwt
from datetime import date

# Импортируем настройки шлюза
from api_gateway.config import SERVICES, JWT_SECRET, JWT_ALGORITHM

app = FastAPI(title="API Gateway - Система учета сбыта")

security = HTTPBearer()

# --- Проверка JWT ---
def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        payload = jwt.decode(credentials.credentials, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Неверный или истекший токен")

# ==========================================
# СХЕМЫ ДЛЯ SWAGGER (Pydantic)
# ==========================================

class LoginData(BaseModel):
    username: str
    password: str

class ProductCreate(BaseModel):
    name: str
    category: str
    price: float

class ContractCreate(BaseModel):
    number: str
    date: date

class CounterpartyCreate(BaseModel):
    name: str
    inn: str
    address: Optional[str] = ""
    contracts: Optional[List[ContractCreate]] = []

class OrderItemCreate(BaseModel):
    product_id: int
    quantity: float
    price: float

class OrderCreate(BaseModel):
    counterparty_id: int
    contract_id: int
    items: List[OrderItemCreate]

class PaymentCreate(BaseModel):
    counterparty_id: int
    order_id: Optional[int] = None
    amount: float


# ==========================================
# 1. АУТЕНТИФИКАЦИЯ
# ==========================================
@app.post("/api/auth/login")
async def login_proxy(username: str = Form(...), password: str = Form(...)):
    """Логин (в Swagger нажмите Try it out и введите данные)."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SERVICES['identity']}/login", 
            data={"username": username, "password": password}
        )
        return JSONResponse(status_code=resp.status_code, content=resp.json())


# ==========================================
# 2. ПРОДУКЦИЯ И СКЛАД (Product Service)
# ==========================================
@app.get("/api/products")
async def get_products(user: dict = Depends(verify_token)):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SERVICES['products']}/products")
        return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.post("/api/products")
async def create_product(product: ProductCreate, user: dict = Depends(verify_token)):
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{SERVICES['products']}/products", json=product.model_dump())
        return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.get("/api/stock/{product_id}")
async def get_stock(product_id: int, user: dict = Depends(verify_token)):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SERVICES['products']}/stock/{product_id}")
        return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.post("/api/income")
async def add_income(product_id: int, quantity: float, user: dict = Depends(verify_token)):
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{SERVICES['products']}/income", 
            params={"product_id": product_id, "quantity": quantity}
        )
        return JSONResponse(status_code=resp.status_code, content=resp.json())


# ==========================================
# 3. КОНТРАГЕНТЫ (Counterparty Service)
# ==========================================
@app.get("/api/counterparties")
async def get_counterparties(user: dict = Depends(verify_token)):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SERVICES['counterparties']}/counterparties")
        return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.post("/api/counterparties")
async def create_counterparty(cp: CounterpartyCreate, user: dict = Depends(verify_token)):
    async with httpx.AsyncClient() as client:
        # model_dump(mode="json") автоматически превратит дату в строку для JSON
        resp = await client.post(
            f"{SERVICES['counterparties']}/counterparties", 
            json=cp.model_dump(mode="json")
        )
        return JSONResponse(status_code=resp.status_code, content=resp.json())


# ==========================================
# 4. ЗАКАЗЫ (Order Service)
# ==========================================
@app.post("/api/orders")
async def create_order(order: OrderCreate, user: dict = Depends(verify_token)):
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(
                f"{SERVICES['orders']}/orders", 
                json=order.model_dump(),
                timeout=10.0
            )
            return JSONResponse(status_code=resp.status_code, content=resp.json())
        except httpx.RequestError:
            return JSONResponse(status_code=503, content={"error": "Order Service недоступен"})

@app.post("/api/orders/{order_id}/confirm")
async def confirm_order(order_id: int, user: dict = Depends(verify_token)):
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{SERVICES['orders']}/orders/{order_id}/confirm")
        return JSONResponse(status_code=resp.status_code, content=resp.json())


# ==========================================
# 5. ФИНАНСЫ (Finance Service)
# ==========================================
@app.post("/api/payments")
async def create_payment(payment: PaymentCreate, user: dict = Depends(verify_token)):
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{SERVICES['finance']}/payments", json=payment.model_dump())
        return JSONResponse(status_code=resp.status_code, content=resp.json())

@app.get("/api/debts/{counterparty_id}")
async def get_debt(counterparty_id: int, user: dict = Depends(verify_token)):
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{SERVICES['finance']}/debts/{counterparty_id}")
        return JSONResponse(status_code=resp.status_code, content=resp.json())


# ==========================================
# 6. УНИВЕРСАЛЬНЫЙ РОУТ (запасной)
# ==========================================
@app.api_route("/api/{service_name}/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def gateway_router(
    service_name: str, 
    path: str, 
    request: Request,
    user_payload: dict = Depends(verify_token)
):
    if service_name not in SERVICES:
        raise HTTPException(status_code=404, detail=f"Сервис '{service_name}' не найден")
    
    target_url = f"{SERVICES[service_name]}/{path}"
    headers = dict(request.headers)
    headers.pop("host", None)
    body = await request.body()

    async with httpx.AsyncClient() as client:
        try:
            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params,
                timeout=10.0
            )
            return JSONResponse(
                status_code=response.status_code,
                content=response.json() if response.content else {}
            )
        except httpx.RequestError:
            return JSONResponse(status_code=503, content={"error": "Service Unavailable"})


# Корень
@app.get("/")
def root():
    return {"message": "API Gateway is running", "services": list(SERVICES.keys())}