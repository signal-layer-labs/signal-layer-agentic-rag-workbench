from typing import Annotated

from fastapi import APIRouter, Depends

from app.evals.service import EvalService, get_eval_service
from app.schemas.evals import EvalRunReport

router = APIRouter(prefix="/evals", tags=["evals"])
EvalServiceDependency = Annotated[EvalService, Depends(get_eval_service)]


@router.post("/run", response_model=EvalRunReport)
def run_evals(service: EvalServiceDependency) -> EvalRunReport:
    return service.run_builtin_cases()
