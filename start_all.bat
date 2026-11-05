@echo off
start cmd /k ".\venv\Scripts\activate && uvicorn identity_service.main:app --port 8005 --reload"
start cmd /k ".\venv\Scripts\activate && uvicorn product_service.main:app --port 8001 --reload"
start cmd /k ".\venv\Scripts\activate && uvicorn counterparty_service.main:app --port 8002 --reload"
start cmd /k ".\venv\Scripts\activate && uvicorn order_service.main:app --port 8003 --reload"
start cmd /k ".\venv\Scripts\activate && uvicorn finance_service.main:app --port 8004 --reload"
start cmd /k ".\venv\Scripts\activate && uvicorn api_gateway.main:app --port 8000 --reload"