# Адреса сервисов (порты должны совпадать с теми, на которых вы их запускаете)
SERVICES = {
    "products": "http://localhost:8001",
    "counterparties": "http://localhost:8002",
    "orders": "http://localhost:8003",
    "finance": "http://localhost:8004",
    "identity": "http://localhost:8005"
}

# Секретный ключ для проверки JWT (должен совпадать с тем, что в Identity Service)
JWT_SECRET = "SUPER_SECRET_KEY_AGRI_SALES"
JWT_ALGORITHM = "HS256"