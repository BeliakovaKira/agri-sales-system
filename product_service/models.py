from sqlalchemy import Column, Integer, String, Float, ForeignKey
from sqlalchemy.orm import relationship
from shared.database import Base

class DBProduct(Base):
    __tablename__ = "products"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    category = Column(String, index=True) # Зерновые, Овощи, Молоко, Мясо
    unit = Column(String)                 # т, кг, л
    shelf_life_days = Column(Integer)     # срок хранения
    price = Column(Float)                 # базовая цена

    # Связь со складскими остатками
    stock = relationship("DBStock", back_populates="product", uselist=False)

class DBStock(Base):
    __tablename__ = "stock"
    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), unique=True)
    quantity = Column(Float, default=0.0) # сколько сейчас на складе
    reserved = Column(Float, default=0.0) # сколько зарезервировано под заказы

    product = relationship("DBProduct", back_populates="stock")