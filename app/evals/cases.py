from app.schemas.evals import EvalCase


def get_builtin_eval_cases() -> list[EvalCase]:
    return [
        EvalCase(
            id="discount-approval-policy",
            name="Discount approval policy retrieval",
            business_question=(
                "Find the relevant discount approval policy and summarize the "
                "linked online sales context."
            ),
            documents=[
                {
                    "title": "Commercial Policy",
                    "source": "eval_discount_policy.md",
                    "content": (
                        "Discount approval rules require manager review for "
                        "enterprise deals above standard thresholds."
                    ),
                    "metadata": {
                        "department": "growth",
                        "document_type": "policy",
                    },
                }
            ],
            retrieval_query="discount approval rules",
            expected_keywords=["discount", "approval", "manager", "review"],
            expected_source="eval_discount_policy.md",
            sales_region="east",
            sales_channel="online",
            customer_segment="enterprise",
            generate_response=True,
        ),
        EvalCase(
            id="online-sales-summary",
            name="Online sales summary with policy context",
            business_question=(
                "Analyze online sales performance and include any relevant "
                "commercial policy context."
            ),
            documents=[
                {
                    "title": "Sales Channel Notes",
                    "source": "eval_online_sales_notes.md",
                    "content": (
                        "Online sales follow the standard channel policy and "
                        "escalate discount exceptions for manual review."
                    ),
                    "metadata": {
                        "department": "sales",
                        "document_type": "notes",
                    },
                }
            ],
            retrieval_query="online sales discount exceptions",
            expected_keywords=["online sales", "discount", "manual review"],
            expected_source="eval_online_sales_notes.md",
            sales_region="east",
            sales_channel="online",
            customer_segment="enterprise",
            generate_response=True,
        ),
        EvalCase(
            id="structured-only-workflow",
            name="Structured-only workflow without retrieval",
            business_question=(
                "Summarize the current east region online sales activity "
                "without document retrieval."
            ),
            documents=[],
            expected_keywords=[],
            sales_region="east",
            sales_channel="online",
            customer_segment="enterprise",
            generate_response=True,
        ),
    ]
