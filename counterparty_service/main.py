from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy import Column, Integer, String, Boolean, Date, ForeignKey
from sqlalchemy.orm import Session, relationship
from pydantic import BaseModel
from datetime import date
from typing import List

from shared.database import engine, get_db, Base
from shared.errors import DomainException, domain_exception_handler

# --- МОДЕЛИ БД (SQLAlchemy) ---

class DBCounterparty(Base):
    __tablename__ = "counterparties"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    inn = Column(String, unique=True, index=True)
    address = Column(String, nullable=True)
    
    # Связь один-ко-многим: у контрагента много договоров
    contracts = relationship("DBContract", back_populates="counterparty")

class DBContract(Base):
    __tablename__ = "contracts"
    id = Column(Integer, primary_key=True, index=True)
    counterparty_id = Column(Integer, ForeignKey("counterparties.id"))
    number = Column(String, index=True)
    date = Column(Date)
    is_active = Column(Boolean, default=True) # Действует ли договор
    
    counterparty = relationship("DBCounterparty", back_populates="contracts")

# Создаем таблицы в БД
Base.metadata.create_all(bind=engine)


class ContractCreate(BaseModel):
    number: str
    date: date

class CounterpartyCreate(BaseModel):
    name: str
    inn: str
    address: str = ""
    contracts: List[ContractCreate] = []

class CounterpartyResponse(CounterpartyCreate):
    id: int
    class Config:
        from_attributes = True # Позволяет FastAPI читать данные из SQLAlchemy моделей


# --- ПРИЛОЖЕНИЕ FASTAPI ---
app = FastAPI(title="Counterparty Service")
app.add_exception_handler(DomainException, domain_exception_handler)


# --- ЭНДПОИНТЫ ---

@app.get("/counterparties", response_model=List[CounterpartyResponse])
def get_counterparties(db: Session = Depends(get_db)):
    return db.query(DBCounterparty).all()

@app.get("/counterparties/{id}", response_model=CounterpartyResponse)
def get_counterparty(id: int, db: Session = Depends(get_db)):
    cp = db.query(DBCounterparty).filter(DBCounterparty.id == id).first()
    if not cp:
        raise DomainException("Контрагент не найден")
    return cp

@app.post("/counterparties")
def create_counterparty(cp: CounterpartyCreate, db: Session = Depends(get_db)):
    # Проверка ИНН
    if len(cp.inn) not in (10, 12):
        raise DomainException("ИНН должен быть длиной 10 или 12 цифр")
    
    # Проверка, что такой ИНН уже есть
    if db.query(DBCounterparty).filter(DBCounterparty.inn == cp.inn).first():
        raise DomainException("Контрагент с таким ИНН уже существует")

    db_cp = DBCounterparty(name=cp.name, inn=cp.inn, address=cp.address)
    db.add(db_cp)
    db.commit()
    db.refresh(db_cp)

    # Добавляем договоры (если переданы)
    for c in cp.contracts:
        db_contract = DBContract(counterparty_id=db_cp.id, number=c.number, date=c.date)
        db.add(db_contract)
    
    db.commit()
    return {"status": "created", "counterparty_id": db_cp.id}


# --- ЭНДПОИНТ ДЛЯ ДРУГИХ СЕРВИСОВ (Order Service) ---
@app.get("/contracts/{id}/check")
def check_contract(id: int, db: Session = Depends(get_db)):
    """
    Проверяет, действует ли договор.
    Этот эндпоинт будет вызывать Order Service перед созданием заказа.
    """
    contract = db.query(DBContract).filter(DBContract.id == id).first()
    if not contract:
        raise DomainException("Договор не найден")
    if not contract.is_active:
        raise DomainException("Договор расторгнут или не действует")
    
    return {"contract_id": contract.id, "is_active": True, "counterparty_id": contract.counterparty_id}


# --- ПАТТЕРН ADAPTER (Заглушка для 1С) ---
@app.post("/sync/1c")
def sync_from_1c(inn: str):
    """
    Имитация адаптера к 1С. Принимает ИНН, возвращает 'спарсенные' данные.
    """
    # В реальности тут был бы вызов OneCClient.getContragentXml(inn)
    mock_1c_data = {
        "name": "ООО АгроПром (из 1С)",
        "inn": inn,
        "address": "г. Москва, ул. Полевая, д. 1"
    }
    return {"source": "1C", "data": mock_1c_data}