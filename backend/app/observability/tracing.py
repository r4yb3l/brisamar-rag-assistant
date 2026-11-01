from opentelemetry import trace
from opentelemetry.instrumentation.psycopg import PsycopgInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (
    BatchSpanProcessor,
    ConsoleSpanExporter,
    SimpleSpanProcessor,
)

from app.core.config import get_settings

_configured = False


def configure_tracing(component: str) -> None:
    global _configured
    if _configured:
        return
    settings = get_settings()
    provider = TracerProvider(
        resource=Resource.create({"service.name": f"{settings.otel_service_name}-{component}"})
    )
    if settings.otel_exporter == "console":
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    elif settings.otel_exporter == "otlp":
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

        endpoint = settings.otel_exporter_otlp_endpoint
        exporter = OTLPSpanExporter(endpoint=f"{endpoint}/v1/traces" if endpoint else None)
        provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    PsycopgInstrumentor().instrument(enable_commenter=False)
    _configured = True


def current_trace_id() -> str | None:
    span_context = trace.get_current_span().get_span_context()
    return format(span_context.trace_id, "032x") if span_context.is_valid else None


tracer = trace.get_tracer("brisamar.rag")
