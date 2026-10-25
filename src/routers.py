from fastapi import APIRouter, FastAPI

from payment_api.router import router as PaymentRouter


def get_routers() -> list[APIRouter]:
    """
    Возвращает список маршрутов для подключения к приложению
    """
    return [PaymentRouter]


def setup_routers(app: FastAPI) -> None:
    """
    Подключает все маршруты к приложению и логирует их инициализацию
    """
    for router in get_routers():
        app.include_router(router)
