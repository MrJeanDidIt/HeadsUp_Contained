from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    source: str
    kind: str
    title: str
    url: str | None
    sender: str | None
    context: str | None
    due_at: datetime | None
    score: int


class RuleIn(BaseModel):
    name: str
    field: str
    match_type: str
    value: str
    weight: int = 5
    active: bool = True


class RuleOut(RuleIn):
    model_config = ConfigDict(from_attributes=True)

    id: int


class PipelineOut(BaseModel):
    fetched: int
    new_items: int
    notified: int
