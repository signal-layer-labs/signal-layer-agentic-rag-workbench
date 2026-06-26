from app.evals.metrics import evaluate_response, evaluate_retrieval, evaluate_trace
from app.rag.retrieval import RetrievalService
from app.schemas.agent import AgentRunRequest
from app.schemas.evals import EvalCase, EvalRunReport, OverallEvalResult
from app.services.agent_orchestrator import AgentOrchestrator


class EvalRunner:
    def __init__(
        self,
        retrieval_service: RetrievalService,
        orchestrator: AgentOrchestrator,
    ) -> None:
        self.retrieval_service = retrieval_service
        self.orchestrator = orchestrator

    def run_cases(self, cases: list[EvalCase]) -> EvalRunReport:
        results: list[OverallEvalResult] = []
        for case in cases:
            for document in case.documents:
                self.retrieval_service.ingest(
                    title=document.title,
                    source=document.source,
                    content=document.content,
                    metadata=document.metadata,
                )

            retrieval_results = (
                self.retrieval_service.search(case.retrieval_query, limit=5)
                if case.retrieval_query is not None
                else []
            )
            orchestration_response = self.orchestrator.run(
                AgentRunRequest(
                    business_question=case.business_question,
                    retrieval_query=case.retrieval_query,
                    sales_region=case.sales_region,
                    sales_channel=case.sales_channel,
                    customer_segment=case.customer_segment,
                    generate_response=case.generate_response,
                )
            )
            retrieval_eval = evaluate_retrieval(case, retrieval_results)
            response_eval = evaluate_response(case, orchestration_response)
            trace_eval = evaluate_trace(case, orchestration_response)
            passed = (
                retrieval_eval.passed
                and response_eval.passed
                and trace_eval.passed
            )
            results.append(
                OverallEvalResult(
                    case_id=case.id,
                    name=case.name,
                    retrieval=retrieval_eval,
                    response=response_eval,
                    trace=trace_eval,
                    passed=passed,
                )
            )

        passed_count = sum(1 for result in results if result.passed)
        return EvalRunReport(
            total=len(results),
            passed=passed_count,
            failed=len(results) - passed_count,
            results=results,
        )
