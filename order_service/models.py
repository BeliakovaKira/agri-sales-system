from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime
from shared.database import Base

class DBOrder(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    counterparty_id = Column(Integer, index=True)
    contract_id = Column(Integer)
    status = Column(String, default="CREATED") # CREATED, CONFIRMED, SHIPPED, PAID, CLOSED
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связь с позициями
    items = relationship("DBOrderItem", back_populates="order")

class DBOrderItem(Base):
    __tablename__ = "order_items"
    id = Column(Integer, primary_key=True, index=True)
    order_id = Column(Integer, ForeignKey("orders.id"))
    product_id = Column(Integer)
    quantity = Column(Float)
    price = Column(Float) # цена на момент заказа
    
    order = relationship("DBOrder", back_populates="items")