import logging
from typing import Any
from uuid import UUID

import psycopg
from celery import Celery, Task
from celery.signals import (
    before_task_publish,
    setup_logging,
    task_postrun,
    task_prerun,
    worker_process_init,
)

from app.core.config import get_settings
from app.ingestion.pipeline import ingest_document, mark_failed
from app.llm.embeddings import get_embedding_model
from app.llm.errors import LLMUnavailableError
from app.observability.context import request_id_var
from app.observability.logging import configure_logging
from app.observability.tracing import configure_tracing

REQUEST_ID_HEADER = "x_request_id"
logger = logging.getLogger(__name__)

settings = get_settings()
celery_app = Celery("brisamar", broker=settings.redis_url, backend=None)
celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_always_eager=settings.celery_task_always_eager,
    task_eager_propagates=True,
    broker_connection_retry_on_startup=True,
)


@setup_logging.connect
def _use_json_logging(**_: Any) -> None:
    configure_logging()


@worker_process_init.connect
def _init_worker_process(**_: Any) -> None:
    from opentelemetry.instrumentation.celery import CeleryInstrumentor

    configure_tracing("worker")
    CeleryInstrumentor().instrument()


@before_task_publish.connect
def _propagate_request_id(headers: dict[str, Any] | None = None, **_: Any) -> None:
    request_id = request_id_var.get()
    if headers is not None and request_id:
        headers.setdefault(REQUEST_ID_HEADER, request_id)


@task_prerun.connect
def _bind_request_id(task: Task | None = None, **_: Any) -> None:
    if task is not None:
        request_id = task.request.get(REQUEST_ID_HEADER)
        if request_id:
            task.request.request_id_token = request_id_var.set(request_id)


@task_postrun.connect
def _unbind_request_id(task: Task | None = None, **_: Any) -> None:
    token = getattr(task.request, "request_id_token", None) if task is not None else None
    if token is not None:
        request_id_var.reset(token)


TRANSIENT_ERRORS: tuple[type[Exception], ...] = (
    LLMUnavailableError,
    psycopg.OperationalError,
    ConnectionError,
    TimeoutError,
)


@celery_app.task(bind=True, name="ingest_document", max_retries=3)
def ingest_document_task(self: Task, document_id: str, business_line: str) -> str:
    try:
        return ingest_document(
            UUID(document_id), business_line, get_embedding_model(settings), settings
        )
    except TRANSIENT_ERRORS as error:
        if self.request.retries < self.max_retries:
            countdown = 2 ** (self.request.retries + 1)
            logger.warning(
                "transient ingestion failure; retrying",
                extra={"document_id": document_id, "countdown_s": countdown, "error": str(error)},
            )
            raise self.retry(exc=error, countdown=countdown) from error
        mark_failed(UUID(document_id), business_line, f"Gave up after retries: {error}")
        return "failed"
    except Exception as error:
        logger.exception("unexpected ingestion failure", extra={"document_id": document_id})
        mark_failed(UUID(document_id), business_line, f"Unexpected error: {type(error).__name__}")
        raise
