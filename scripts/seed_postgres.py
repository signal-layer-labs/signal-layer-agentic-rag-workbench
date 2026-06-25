from sqlalchemy.orm import Session

from app.db.repositories import SqlAlchemyAgentRunRepository
from app.db.session import create_database_tables, engine
from app.services.run_service import MOCK_RUN_SUMMARY


def seed() -> None:
    create_database_tables()
    with Session(engine) as session:
        repository = SqlAlchemyAgentRunRepository(session)
        repository.create(
            business_question=(
                "Analyze last quarter sales and summarize risks and opportunities."
            ),
            summary=MOCK_RUN_SUMMARY,
        )


if __name__ == "__main__":
    seed()
