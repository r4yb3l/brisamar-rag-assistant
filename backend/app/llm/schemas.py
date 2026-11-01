from pydantic import BaseModel, Field


class ModelCitation(BaseModel):
    source_id: str = Field(min_length=1, max_length=16)
    quote: str = Field(min_length=1, max_length=1000)


class ModelAnswer(BaseModel):
    """Structured output the model must return; validated before anything reaches the user."""

    answer: str = Field(max_length=6000)
    citations: list[ModelCitation] = Field(default_factory=list, max_length=12)
    confidence: float = Field(ge=0.0, le=1.0)
    insufficient_evidence: bool
