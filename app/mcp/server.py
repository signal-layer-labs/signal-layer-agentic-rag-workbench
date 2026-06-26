from typing import Any

from app.mcp.tools import query_customers, run_traceable_workflow, summarize_sales

try:
    from mcp.server.fastmcp import FastMCP  # type: ignore[import-not-found]
except ImportError as exc:  # pragma: no cover - exercised by runtime only
    FastMCP = None
    MCP_IMPORT_ERROR: ImportError | None = exc
else:
    MCP_IMPORT_ERROR = None


def create_mcp_server() -> Any:
    if FastMCP is None:
        raise RuntimeError(
            "The MCP SDK is not installed. Add the 'mcp' dependency to run the "
            "local MCP server entrypoint."
        ) from MCP_IMPORT_ERROR

    server = FastMCP("signal-layer-agentic-rag-workbench")

    @server.tool()  # type: ignore[untyped-decorator]
    def mcp_query_customers(
        segment: str | None = None,
        region: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, object]]:
        results = query_customers(
            {
                "segment": segment,
                "region": region,
                "status": status,
                "limit": limit,
            }
        )
        return [result.model_dump(mode="json") for result in results]

    @server.tool()  # type: ignore[untyped-decorator]
    def mcp_summarize_sales(
        region: str | None = None,
        channel: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, object]:
        summary = summarize_sales(
            {
                "region": region,
                "channel": channel,
                "start_date": start_date,
                "end_date": end_date,
            }
        )
        return summary.model_dump(mode="json")

    @server.tool()  # type: ignore[untyped-decorator]
    def mcp_run_traceable_workflow(
        business_question: str,
        retrieval_query: str | None = None,
        sales_region: str | None = None,
        sales_channel: str | None = None,
        customer_segment: str | None = None,
        generate_response: bool = False,
    ) -> dict[str, object]:
        response = run_traceable_workflow(
            {
                "business_question": business_question,
                "retrieval_query": retrieval_query,
                "sales_region": sales_region,
                "sales_channel": sales_channel,
                "customer_segment": customer_segment,
                "generate_response": generate_response,
            }
        )
        return response.model_dump(mode="json")

    return server


def main() -> None:
    create_mcp_server().run(transport="stdio")


if __name__ == "__main__":
    main()
