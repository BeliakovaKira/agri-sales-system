from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from shared.database import engine, get_db, Base
from shared.errors import DomainException, domain_exception_handler
from order_service.models import DBOrder, DBOrderItem
from order_service.facade import OrderFacade

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Order Service")
app.add_exception_handler(DomainException, domain_exception_handler)

# Схемы
class OrderItemCreate(BaseModel):
    product_id: int
    quantity: float
    price: float

class OrderCreate(BaseModel):
    counterparty_id: int
    contract_id: int
    items: List[OrderItemCreate]

class OrderResponse(BaseModel):
    id: int
    status: str
    counterparty_id: int
    contract_id: int
    class Config:
        from_attributes = True

# ЭНДПОИНТ СОЗДАНИЯ ЗАКАЗА (Паттерн Facade)
@app.post("/orders", response_model=OrderResponse)
async def create_order(order_data: OrderCreate, db: Session = Depends(get_db)):
    # 1. Проверяем договор (межсервисный вызов)
    await OrderFacade.validate_contract(order_data.contract_id)

    # 2. Проверяем и резервируем каждый товар
    for item in order_data.items:
        await OrderFacade.check_and_reserve_stock(item.product_id, item.quantity)

    # 3. Создаем заказ в БД (если все проверки прошли)
    db_order = DBOrder(
        counterparty_id=order_data.counterparty_id,
        contract_id=order_data.contract_id,
        status="CREATED" # Начальное состояние (паттерн State)
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # 4. Добавляем позиции
    for item in order_data.items:
        db_item = DBOrderItem(
            order_id=db_order.id,
            product_id=item.product_id,
            quantity=item.quantity,
            price=item.price
        )
        db.add(db_item)
    
    db.commit()
    return db_order

# ЭНДПОИНТ ПОДТВЕРЖДЕНИЯ (Смена статуса)
@app.post("/orders/{order_id}/confirm")
def confirm_order(order_id: int, db: Session = Depends(get_db)):
    order = db.query(DBOrder).filter(DBOrder.id == order_id).first()
    if not order:
        raise DomainException("Заказ не найден")
    
    if order.status != "CREATED":
        raise DomainException(f"Нельзя подтвердить заказ в статусе {order.status}")
    
    order.status = "CONFIRMED"
    db.commit()
    return {"status": "confirmed", "order_id": order.id}

# Просмотр заказов
@app.get("/orders", response_model=List[OrderResponse])
def get_orders(db: Session = Depends(get_db)):
    return db.query(DBOrder).all()