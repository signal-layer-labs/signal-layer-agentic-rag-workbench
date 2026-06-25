from app.db.business_repositories import CustomerFilters, SalesFilters
from app.db.models import Customer, Sale
from app.schemas.business import SalesSummary
from app.services.business_service import BusinessService

QUERY_CUSTOMERS_DESCRIPTION = "Query customers using approved structured filters."
QUERY_SALES_DESCRIPTION = "Query sales records using approved structured filters."
SUMMARIZE_SALES_DESCRIPTION = "Summarize sales using deterministic aggregates."


def query_customers_tool(
    service: BusinessService,
    filters: CustomerFilters,
) -> list[Customer]:
    return service.query_customers(filters)


def query_sales_tool(
    service: BusinessService,
    filters: SalesFilters,
) -> list[Sale]:
    return service.query_sales(filters)


def summarize_sales_tool(
    service: BusinessService,
    filters: SalesFilters,
) -> SalesSummary:
    return service.summarize_sales(filters)
