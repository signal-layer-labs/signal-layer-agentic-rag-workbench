from app.schemas.evals import EvalRunReport


def format_eval_report(report: EvalRunReport) -> str:
    lines = [f"Eval report: {report.passed}/{report.total} passed"]
    for result in report.results:
        lines.append(
            f"- {result.case_id}: {'PASS' if result.passed else 'FAIL'} "
            f"(retrieval={result.retrieval.passed}, "
            f"response={result.response.passed}, trace={result.trace.passed})"
        )
    return "\n".join(lines)
