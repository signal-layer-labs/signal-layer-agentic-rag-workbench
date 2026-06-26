from importlib import import_module
from typing import Any

from app.mcp.schemas import MCPErrorEnvelope
from app.mcp.tools import (
    execute_mcp_tool,
    query_customers,
    run_traceable_workflow,
    summarize_sales,
)


def load_fastmcp() -> Any:
    try:
        module = import_module("mcp.server.fastmcp")
    except ImportError as error:  # pragma: no cover - exercised by runtime only
        raise RuntimeError(
            "MCP server support requires the mcp package to be installed."
        ) from error
    return module.FastMCP


def create_mcp_server() -> Any:
    FastMCP = load_fastmcp()
    server = FastMCP("signal-layer-agentic-rag-workbench")

    def mcp_query_customers(
        segment: str | None = None,
        region: str | None = None,
        status: str | None = None,
        limit: int = 20,
    ) -> list[dict[str, object]] | dict[str, object]:
        """Return structured customer matches using approved deterministic filters only.

        This tool reuses service-layer customer queries, does not accept raw SQL,
        and does not execute shell commands.
        """
        result = execute_mcp_tool(
            lambda: query_customers(
                {
                    "segment": segment,
                    "region": region,
                    "status": status,
                    "limit": limit,
                }
            )
        )
        if isinstance(result, MCPErrorEnvelope):
            return result.model_dump(mode="json")
        if isinstance(result, list):
            return [item.model_dump(mode="json") for item in result]
        return result.model_dump(mode="json")
    server.tool()(mcp_query_customers)

    def mcp_summarize_sales(
        region: str | None = None,
        channel: str | None = None,
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> dict[str, object]:
        """Return a deterministic sales summary from approved service-layer filters.

        This tool reuses existing summary logic, does not accept raw SQL, and
        does not execute shell commands.
        """
        result = execute_mcp_tool(
            lambda: summarize_sales(
                {
                    "region": region,
                    "channel": channel,
                    "start_date": start_date,
                    "end_date": end_date,
                }
            )
        )
        if isinstance(result, MCPErrorEnvelope):
            return result.model_dump(mode="json")
        return result.model_dump(mode="json")
    server.tool()(mcp_summarize_sales)

    def mcp_run_traceable_workflow(
        business_question: str,
        retrieval_query: str | None = None,
        sales_region: str | None = None,
        sales_channel: str | None = None,
        customer_segment: str | None = None,
        generate_response: bool = False,
    ) -> dict[str, object]:
        """Run the deterministic workflow and return a traceable run result.

        This tool reuses approved service-layer orchestration, does not accept
        raw SQL, does not execute shell commands, and may record
        retrieval_events and tool_calls.
        """
        result = execute_mcp_tool(
            lambda: run_traceable_workflow(
                {
                    "business_question": business_question,
                    "retrieval_query": retrieval_query,
                    "sales_region": sales_region,
                    "sales_channel": sales_channel,
                    "customer_segment": customer_segment,
                    "generate_response": generate_response,
                }
            )
        )
        if isinstance(result, MCPErrorEnvelope):
            return result.model_dump(mode="json")
        return result.model_dump(mode="json")
    server.tool()(mcp_run_traceable_workflow)

    return server


def main() -> None:
    create_mcp_server().run(transport="stdio")


if __name__ == "__main__":
    main()
