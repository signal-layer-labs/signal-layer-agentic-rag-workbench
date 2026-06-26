from app.db.session import SessionLocal, create_database_tables
from app.evals.report import format_eval_report
from app.evals.service import build_eval_service
from app.providers.factory import get_llm_provider
from app.rag.retrieval import get_retrieval_service
from app.services.response_generator import ResponseGenerator


def main() -> int:
    create_database_tables()
    with SessionLocal() as session:
        service = build_eval_service(
            session=session,
            retrieval_service=get_retrieval_service(),
            response_generator=ResponseGenerator(get_llm_provider()),
        )
        report = service.run_builtin_cases()
    print(format_eval_report(report))
    return 0 if report.failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
