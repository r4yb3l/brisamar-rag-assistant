from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from app.api.routes import router
from app.core.config import get_settings
from app.db.session import close_pool
from app.observability.context import new_request_id, request_id_var
from app.observability.logging import configure_logging
from app.observability.tracing import configure_tracing

REQUEST_ID_HEADER = "X-Request-ID"


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    close_pool()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging()
    configure_tracing("api")
    CeleryInstrumentor().instrument()

    app = FastAPI(title="Brisamar RAG Assistant", version="0.1.0", lifespan=lifespan)

    @app.middleware("http")
    async def correlation_id(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get(REQUEST_ID_HEADER, "")
        request_id = incoming if incoming.isalnum() and len(incoming) <= 64 else new_request_id()
        token = request_id_var.set(request_id)
        try:
            response = await call_next(request)
        finally:
            request_id_var.reset(token)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Authorization", "Content-Type", REQUEST_ID_HEADER],
        expose_headers=[REQUEST_ID_HEADER],
    )
    app.include_router(router)
    FastAPIInstrumentor.instrument_app(app, excluded_urls="api/health")
    return app


app = create_app()
