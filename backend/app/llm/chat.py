import json
import re
import time
from dataclasses import dataclass
from typing import Protocol

from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import Settings, get_settings
from app.llm.errors import LLMUnavailableError, is_transient_llm_error
from app.llm.text import content_terms

Message = dict[str, str]


@dataclass(frozen=True)
class Completion:
    text: str
    input_tokens: int | None = None
    output_tokens: int | None = None


class ChatModel(Protocol):
    name: str

    def complete(self, messages: list[Message]) -> Completion: ...


class LiteLLMChatModel:
    def __init__(self, settings: Settings) -> None:
        self.name = settings.llm_model
        self._timeout = settings.llm_timeout_seconds
        self._max_attempts = settings.llm_max_attempts

    def complete(self, messages: list[Message]) -> Completion:
        import litellm

        @retry(
            retry=retry_if_exception(is_transient_llm_error),
            wait=wait_exponential(multiplier=0.5, max=8),
            stop=stop_after_attempt(self._max_attempts),
            reraise=True,
        )
        def call() -> Completion:
            response = litellm.completion(
                model=self.name,
                messages=messages,
                temperature=0.0,
                timeout=self._timeout,
                num_retries=0,
                response_format={"type": "json_object"},
            )
            usage = getattr(response, "usage", None)
            return Completion(
                text=response.choices[0].message.content or "",
                input_tokens=getattr(usage, "prompt_tokens", None),
                output_tokens=getattr(usage, "completion_tokens", None),
            )

        try:
            return call()
        except Exception as error:
            if is_transient_llm_error(error):
                raise LLMUnavailableError(f"LLM provider unavailable: {error}") from error
            raise


class FakeChatModel:
    """Offline model: answers extractively with the sentences that best overlap the question.

    It reads the same JSON payload the real model receives, so the whole prompt and validation
    pipeline is exercised without network access.
    """

    name = "fake/extractive-v1"
    max_sentences = 2
    secondary_ratio = 0.75

    def complete(self, messages: list[Message]) -> Completion:
        payload = json.loads(next(m["content"] for m in messages if m["role"] == "user"))
        question_terms = set(content_terms(payload["question"]))
        scored: list[tuple[float, str, str]] = []
        for source in payload["sources"]:
            for sentence in _sentences(source["text"]):
                overlap = question_terms & set(content_terms(sentence))
                if overlap:
                    scored.append((len(overlap) / len(question_terms), source["id"], sentence))
        scored.sort(key=lambda item: item[0], reverse=True)
        best = [
            item
            for item in scored[: self.max_sentences]
            if item[0] >= self.secondary_ratio * scored[0][0] and len(item[2]) >= 30
        ]
        if not best or best[0][0] < 0.34:
            answer = {
                "answer": "",
                "citations": [],
                "confidence": 0.0,
                "insufficient_evidence": True,
            }
        else:
            answer = {
                "answer": " ".join(f"{sentence} [{source_id}]" for _, source_id, sentence in best),
                "citations": [
                    {"source_id": source_id, "quote": sentence} for _, source_id, sentence in best
                ],
                "confidence": round(min(1.0, best[0][0]), 2),
                "insufficient_evidence": False,
            }
        return Completion(text=json.dumps(answer, ensure_ascii=False))


_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")


def _sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_BOUNDARY.split(text) if part.strip()]


def get_chat_model(settings: Settings | None = None) -> ChatModel:
    settings = settings or get_settings()
    if settings.llm_provider == "litellm":
        return LiteLLMChatModel(settings)
    return FakeChatModel()


def timed_complete(model: ChatModel, messages: list[Message]) -> tuple[Completion, float]:
    started = time.perf_counter()
    completion = model.complete(messages)
    return completion, (time.perf_counter() - started) * 1000
