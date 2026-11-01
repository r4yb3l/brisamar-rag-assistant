import logging

from pydantic import ValidationError

from app.llm.chat import ChatModel, timed_complete
from app.llm.prompt import PromptSource, build_messages, build_repair_message
from app.llm.schemas import ModelAnswer
from app.observability.tracing import tracer

logger = logging.getLogger(__name__)


class InvalidModelOutputError(RuntimeError):
    """The model broke the output schema twice (original call plus one repair attempt)."""


def _strip_code_fence(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = stripped.split("\n", 1)[-1]
        stripped = stripped.rsplit("```", 1)[0]
    return stripped.strip()


def generate_answer(model: ChatModel, question: str, sources: list[PromptSource]) -> ModelAnswer:
    messages = build_messages(question, sources)
    with tracer.start_as_current_span("llm.generate") as span:
        span.set_attribute("gen_ai.request.model", model.name)
        span.set_attribute("rag.source_count", len(sources))
        span.set_attribute("rag.flagged_source_count", sum(s.flagged for s in sources))
        last_error = ""
        for attempt in range(2):
            completion, latency_ms = timed_complete(model, messages)
            span.add_event(
                "llm.completion",
                {
                    "attempt": attempt,
                    "latency_ms": round(latency_ms, 1),
                    "gen_ai.usage.input_tokens": completion.input_tokens or 0,
                    "gen_ai.usage.output_tokens": completion.output_tokens or 0,
                },
            )
            try:
                answer = ModelAnswer.model_validate_json(_strip_code_fence(completion.text))
                span.set_attribute("llm.repair_attempted", attempt > 0)
                return answer
            except ValidationError as error:
                last_error = str(error)
                logger.warning(
                    "model output failed schema validation",
                    extra={"attempt": attempt, "model": model.name},
                )
                messages = messages + build_repair_message(completion.text, last_error)
        span.set_attribute("llm.repair_attempted", True)
        raise InvalidModelOutputError(last_error)
