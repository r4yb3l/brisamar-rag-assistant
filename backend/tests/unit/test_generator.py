import json

import pytest

from app.answering.generator import InvalidModelOutputError, generate_answer
from app.llm.chat import Completion, FakeChatModel
from tests.unit.helpers import make_sources

VALID = json.dumps(
    {
        "answer": "Cinco días hábiles [S1].",
        "citations": [{"source_id": "S1", "quote": "5 días hábiles"}],
        "confidence": 0.8,
        "insufficient_evidence": False,
    }
)
SOURCES = make_sources("El plazo es de 5 días hábiles.")


class ScriptedChatModel:
    name = "scripted"

    def __init__(self, *outputs: str) -> None:
        self.outputs = list(outputs)
        self.calls: list[list[dict[str, str]]] = []

    def complete(self, messages: list[dict[str, str]]) -> Completion:
        self.calls.append(messages)
        return Completion(text=self.outputs.pop(0))


def test_valid_output_in_code_fence_is_accepted_without_repair() -> None:
    model = ScriptedChatModel(f"```json\n{VALID}\n```")
    answer = generate_answer(model, "¿Plazo?", SOURCES)
    assert answer.confidence == 0.8
    assert len(model.calls) == 1


def test_schema_violation_triggers_exactly_one_repair() -> None:
    model = ScriptedChatModel('{"answer": "x", "confidence": 7}', VALID)
    answer = generate_answer(model, "¿Plazo?", SOURCES)
    assert answer.answer.startswith("Cinco")
    assert len(model.calls) == 2
    assert "esquema JSON" in model.calls[1][-1]["content"]


def test_two_invalid_outputs_raise() -> None:
    model = ScriptedChatModel("not json", "still not json")
    with pytest.raises(InvalidModelOutputError):
        generate_answer(model, "¿Plazo?", SOURCES)


def test_fake_model_answers_extractively_and_cites_the_source() -> None:
    sources = make_sources(
        "La franquicia de lunas es de 60 euros por siniestro.",
        "El vehículo de sustitución se concede durante 15 días.",
    )
    answer = generate_answer(FakeChatModel(), "¿Cuál es la franquicia de lunas?", sources)
    assert not answer.insufficient_evidence
    assert answer.citations[0].source_id == "S1"
    assert "60 euros" in answer.citations[0].quote


def test_fake_model_declares_insufficient_evidence_for_unrelated_question() -> None:
    answer = generate_answer(FakeChatModel(), "¿Quién ganó el mundial de fútbol?", SOURCES)
    assert answer.insufficient_evidence
    assert answer.citations == []
