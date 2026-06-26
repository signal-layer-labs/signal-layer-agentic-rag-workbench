from app.rag.vector_store import SearchResult
from app.schemas.agent import AgentRunResponse
from app.schemas.evals import (
    EvalCase,
    ResponseEvalResult,
    RetrievalEvalResult,
    TraceEvalResult,
)


def evaluate_retrieval(
    case: EvalCase,
    results: list[SearchResult],
) -> RetrievalEvalResult:
    if case.retrieval_query is None:
        return RetrievalEvalResult(
            retrieved_count=0,
            expected_source_found=True,
            expected_keywords_found=True,
            missing_keywords=[],
            passed=True,
        )

    combined_text = " ".join(
        " ".join(
            [
                result.document,
                str(result.metadata.get("title", "")),
                str(result.metadata.get("source", "")),
            ]
        ).lower()
        for result in results
    )
    missing_keywords = [
        keyword
        for keyword in case.expected_keywords
        if keyword.lower() not in combined_text
    ]
    expected_source_found = any(
        result.metadata.get("source") == case.expected_source for result in results
    )
    expected_keywords_found = not missing_keywords
    return RetrievalEvalResult(
        retrieved_count=len(results),
        expected_source_found=expected_source_found,
        expected_keywords_found=expected_keywords_found,
        missing_keywords=missing_keywords,
        passed=expected_source_found and expected_keywords_found and len(results) > 0,
    )


def evaluate_response(
    case: EvalCase,
    response: AgentRunResponse,
) -> ResponseEvalResult:
    generated = response.generated_response is not None
    generated_response = response.generated_response
    content = generated_response.content if generated_response is not None else ""
    unsupported_claim_flags: list[str] = []

    expected_documents_line = (
        "Documents retrieved: "
        f"{'yes' if response.trace.documents_retrieved > 0 else 'no'} "
        f"({response.trace.documents_retrieved})"
    )
    if generated and expected_documents_line not in content:
        unsupported_claim_flags.append("documents_retrieved_mismatch")

    expected_tool_calls_line = (
        f"Tool calls recorded: {len(response.trace.tool_call_ids)}"
    )
    if generated and expected_tool_calls_line not in content:
        unsupported_claim_flags.append("tool_call_count_mismatch")

    contains_business_question = generated and case.business_question in content
    contains_sales_summary = (
        generated
        and "Sales summary highlights:" in content
        and "revenue=" in content
    )

    return ResponseEvalResult(
        generated=generated,
        contains_business_question=contains_business_question,
        contains_sales_summary=contains_sales_summary,
        unsupported_claim_flags=unsupported_claim_flags,
        passed=(
            generated
            and contains_business_question
            and contains_sales_summary
            and not unsupported_claim_flags
        ),
    )


def evaluate_trace(
    case: EvalCase,
    response: AgentRunResponse,
) -> TraceEvalResult:
    run_created = response.run_id is not None and response.status == "completed"
    retrieval_event_created = response.trace.retrieval_event_id is not None
    tool_calls_created = len(response.trace.tool_call_ids) > 0
    expected_retrieval = case.retrieval_query is not None

    return TraceEvalResult(
        run_created=run_created,
        retrieval_event_created=retrieval_event_created,
        tool_calls_created=tool_calls_created,
        passed=(
            run_created
            and tool_calls_created
            and retrieval_event_created == expected_retrieval
        ),
    )
