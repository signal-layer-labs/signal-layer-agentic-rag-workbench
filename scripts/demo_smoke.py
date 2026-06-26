"""Print a deterministic local demo sequence for the workbench."""


def main() -> None:
    steps = [
        "1. Start services: docker compose up --build",
        "2. Seed data: docker compose exec api python scripts/seed_business_data.py",
        (
            "3. Parse and ingest sample: POST /documents/parse-ingest with "
            "samples/commercial_policy.md"
        ),
        "4. Search policy rule: POST /documents/search",
        "5. Run deterministic orchestration: POST /agent/run",
        (
            "6. Run controlled response generation: POST /agent/run with "
            "generate_response=true"
        ),
        "7. Run optional Agno path: POST /agent/agno/run",
        "8. Run evals: python scripts/run_evals.py",
        (
            "9. Trigger structured error example: POST /documents/search with "
            "limit over budget"
        ),
    ]
    print("Signal Layer demo smoke checklist")
    for step in steps:
        print(step)


if __name__ == "__main__":
    main()
