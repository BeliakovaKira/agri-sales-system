from fastapi import FastAPI, Depends
from sqlalchemy import Column, Integer, Float, Date, String
from sqlalchemy.orm import Session
from pydantic import BaseModel
from datetime import date
from typing import List

from shared.database import engine, get_db, Base
from shared.errors import DomainException, domain_exception_handler

class DBPayment(Base):
    __tablename__ = "payments"
    id = Column(Integer, primary_key=True, index=True)
    counterparty_id = Column(Integer, index=True)
    order_id = Column(Integer, nullable=True) # Может быть привязка к заказу
    amount = Column(Float)
    date = Column(Date, default=date.today)
    method = Column(String, default="bank_transfer")

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Finance Service")
app.add_exception_handler(DomainException, domain_exception_handler)

class PaymentCreate(BaseModel):
    counterparty_id: int
    order_id: int | None = None
    amount: float

class PaymentResponse(PaymentCreate):
    id: int
    date: date
    class Config:
        from_attributes = True

@app.post("/payments", response_model=PaymentResponse)
def create_payment(payment: PaymentCreate, db: Session = Depends(get_db)):
    if payment.amount <= 0:
        raise DomainException("Сумма платежа должна быть больше нуля")
    
    db_payment = DBPayment(
        counterparty_id=payment.counterparty_id,
        order_id=payment.order_id,
        amount=payment.amount
    )
    db.add(db_payment)
    db.commit()
    db.refresh(db_payment)
    return db_payment

@app.get("/payments", response_model=List[PaymentResponse])
def get_payments(db: Session = Depends(get_db)):
    return db.query(DBPayment).all()

@app.get("/debts/{counterparty_id}")
def get_debt(counterparty_id: int, db: Session = Depends(get_db)):
    """Заглушка для получения задолженности"""
    payments = db.query(DBPayment).filter(DBPayment.counterparty_id == counterparty_id).all()
    total_paid = sum(p.amount for p in payments)
    return {"counterparty_id": counterparty_id, "total_paid": total_paid}