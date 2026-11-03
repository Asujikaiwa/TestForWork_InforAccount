from fastapi import FastAPI

from app.errors import register_error_handlers
from app.routers import groups


def create_app() -> FastAPI:
    app = FastAPI(title="SplitBill API", version="0.1.0")
    register_error_handlers(app)
    app.include_router(groups.router)

    @app.get("/health", include_in_schema=False)
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
