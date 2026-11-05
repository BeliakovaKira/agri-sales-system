import httpx
from shared.errors import DomainException
from fastapi import HTTPException

# Адреса наших сервисов
PRODUCT_SERVICE_URL = "http://localhost:8001"
COUNTERPARTY_SERVICE_URL = "http://localhost:8002"

class OrderFacade:
    """Скрывает сложность проверки договора и резервирования товара."""
    
    @staticmethod
    async def validate_contract(contract_id: int):
        """Проверяет договор в Counterparty Service."""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{COUNTERPARTY_SERVICE_URL}/contracts/{contract_id}/check", timeout=5.0)
                if resp.status_code != 200:
                    # Передаем ошибку от другого сервиса дальше
                    raise DomainException(resp.json().get("error", "Договор не действует"))
        except httpx.RequestError:
            # Устойчивость к отказам
            raise HTTPException(status_code=503, detail="Сервис контрагентов временно недоступен")

    @staticmethod
    async def check_and_reserve_stock(product_id: int, quantity: float):
        """Проверяет остатки и резервирует товар в Product Service."""
        try:
            async with httpx.AsyncClient() as client:
                # 1. Проверяем остатки
                resp = await client.get(f"{PRODUCT_SERVICE_URL}/stock/{product_id}", timeout=5.0)
                if resp.status_code != 200:
                    raise DomainException("Продукт не найден")
                
                stock_data = resp.json()
                if stock_data["available"] < quantity:
                    raise DomainException(f"Недостаточно товара. Доступно: {stock_data['available']}")

                # 2. Резервируем
                reserve_resp = await client.post(
                    f"{PRODUCT_SERVICE_URL}/reserve", 
                    params={"product_id": product_id, "quantity": quantity},
                    timeout=5.0
                )
                if reserve_resp.status_code != 200:
                    raise DomainException(reserve_resp.json().get("error", "Ошибка резервирования"))
                    
        except httpx.RequestError:
            # Устойчивость к отказам
            raise HTTPException(status_code=503, detail="Сервис продукции временно недоступен")