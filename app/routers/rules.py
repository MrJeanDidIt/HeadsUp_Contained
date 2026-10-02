from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import current_principal
from app.db import get_session
from app.models import Rule
from app.schemas import RuleIn, RuleOut

router = APIRouter(prefix="/rules", tags=["rules"], dependencies=[Depends(current_principal)])

VALID_FIELDS = {"title", "body", "sender", "context", "kind"}
VALID_MATCHES = {"contains", "equals", "prefix", "domain"}


def _validate(payload: RuleIn) -> None:
    if payload.field not in VALID_FIELDS:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"field must be one of {VALID_FIELDS}")
    if payload.match_type not in VALID_MATCHES:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, f"match_type must be one of {VALID_MATCHES}")


@router.get("", response_model=list[RuleOut])
async def list_rules(session: AsyncSession = Depends(get_session)) -> list[Rule]:
    return list(await session.scalars(select(Rule).order_by(Rule.weight.desc())))


@router.post("", response_model=RuleOut, status_code=status.HTTP_201_CREATED)
async def create_rule(payload: RuleIn, session: AsyncSession = Depends(get_session)) -> Rule:
    _validate(payload)
    rule = Rule(**payload.model_dump())
    session.add(rule)
    await session.commit()
    await session.refresh(rule)
    return rule


@router.delete("/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(rule_id: int, session: AsyncSession = Depends(get_session)) -> None:
    rule = await session.get(Rule, rule_id)
    if rule is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Rule not found")
    await session.delete(rule)
    await session.commit()
