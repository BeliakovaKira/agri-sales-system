from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from shared.database import engine, get_db, Base
from shared.errors import DomainException, domain_exception_handler
from product_service.models import DBProduct, DBStock
from product_service.factory import ProductFactory, ProductCreate

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Product Service")
app.add_exception_handler(DomainException, domain_exception_handler)

# Схемы для ответа API
class ProductResponse(BaseModel):
    id: int
    name: str
    category: str
    unit: str
    price: float
    class Config:
        from_attributes = True

# 1. Получить список продукции
@app.get("/products", response_model=List[ProductResponse])
def get_products(db: Session = Depends(get_db)):
    return db.query(DBProduct).all()

# 2. Создать продукт (Используем Factory Method)
@app.post("/products")
def create_product(data: ProductCreate, db: Session = Depends(get_db)):
    try:
        # Фабрика сама решает, какой класс создать (Grain, Milk и т.д.)
        product_logic = ProductFactory.create_product(data)
    except ValueError as e:
        raise DomainException(str(e))

    # Сохраняем в базу
    db_product = DBProduct(
        name=product_logic.name,
        category=product_logic.category,
        unit=product_logic.unit,
        shelf_life_days=product_logic.shelf_life,
        price=product_logic.price
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)

    # Сразу создаем складскую запись для этого продукта
    db_stock = DBStock(product_id=db_product.id, quantity=0.0, reserved=0.0)
    db.add(db_stock)
    db.commit()

    return {"status": "created", "product_id": db_product.id}

# 3. Получить остатки по продукту (для Order Service)
@app.get("/stock/{product_id}")
def get_stock(product_id: int, db: Session = Depends(get_db)):
    stock = db.query(DBStock).filter(DBStock.product_id == product_id).first()
    if not stock:
        raise DomainException("Продукт или складская запись не найдены")
    
    # Доступно = всего - зарезервировано
    available = stock.quantity - stock.reserved
    return {"product_id": product_id, "available": available, "reserved": stock.reserved}

# 4. Резервирование товара (вызывает Order Service)
@app.post("/reserve")
def reserve_stock(product_id: int, quantity: float, db: Session = Depends(get_db)):
    stock = db.query(DBStock).filter(DBStock.product_id == product_id).first()
    if not stock:
        raise DomainException("Продукт не найден на складе")
    
    available = stock.quantity - stock.reserved
    if available < quantity:
        raise DomainException(f"Недостаточно остатков. Доступно: {available}")
    
    stock.reserved += quantity
    db.commit()
    return {"status": "reserved", "reserved_now": quantity}

# 5. Пополнение склада (приход)
@app.post("/income")
def add_stock(product_id: int, quantity: float, db: Session = Depends(get_db)):
    stock = db.query(DBStock).filter(DBStock.product_id == product_id).first()
    if not stock:
        raise DomainException("Продукт не найден")
    
    stock.quantity += quantity
    db.commit()
    return {"status": "income_added", "new_total": stock.quantity}