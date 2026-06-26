from app.schemas.evals import EvalRunReport


def format_eval_report(report: EvalRunReport) -> str:
    lines = [
        "Eval report summary:",
        f"total={report.total}",
        f"passed={report.passed}",
        f"failed={report.failed}",
    ]
    if report.failed > 0:
        lines.append("warning=one or more eval cases failed")
    for result in report.results:
        status = "PASS" if result.passed else "FAIL"
        lines.append(f"- {result.case_id}: {status}")
        lines.append(
            f"  retrieval={result.retrieval.passed} "
            f"response={result.response.passed} trace={result.trace.passed}"
        )
        if not result.passed:
            lines.append(f"  failed_case={result.name}")
    return "\n".join(lines)
