from dataclasses import dataclass

# DTO для создания продукта
@dataclass
class ProductCreate:
    name: str
    category: str
    price: float

# Базовый класс (в реальности здесь была бы логика хранения)
class BaseProduct:
    def __init__(self, name, category, unit, shelf_life, price):
        self.name = name
        self.category = category
        self.unit = unit
        self.shelf_life = shelf_life
        self.price = price

# Конкретные продукты
class GrainProduct(BaseProduct):
    def __init__(self, name, price):
        super().__init__(name, "Зерновые", "т", 365, price)

class VegetableProduct(BaseProduct):
    def __init__(self, name, price):
        super().__init__(name, "Овощи", "кг", 120, price)

class MilkProduct(BaseProduct):
    def __init__(self, name, price):
        super().__init__(name, "Молоко", "л", 10, price)

class MeatProduct(BaseProduct):
    def __init__(self, name, price):
        super().__init__(name, "Мясо", "кг", 5, price)

# --- САМ ПАТТЕРН FACTORY METHOD ---
class ProductFactory:
    """Создает продукт нужного типа на основе категории."""
    @staticmethod
    def create_product(data: ProductCreate) -> BaseProduct:
        if data.category == "Зерновые":
            return GrainProduct(data.name, data.price)
        elif data.category == "Овощи":
            return VegetableProduct(data.name, data.price)
        elif data.category == "Молоко":
            return MilkProduct(data.name, data.price)
        elif data.category == "Мясо":
            return MeatProduct(data.name, data.price)
        else:
            raise ValueError(f"Неизвестная категория продукта: {data.category}")