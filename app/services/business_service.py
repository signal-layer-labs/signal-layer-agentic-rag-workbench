from collections import Counter
from decimal import Decimal

from app.db.business_repositories import (
    BusinessRepository,
    CustomerFilters,
    SalesFilters,
)
from app.db.models import Customer, Sale
from app.schemas.business import SalesSummary


class BusinessService:
    def __init__(self, repository: BusinessRepository) -> None:
        self.repository = repository

    def query_customers(self, filters: CustomerFilters) -> list[Customer]:
        return list(self.repository.search_customers(filters))

    def query_sales(self, filters: SalesFilters) -> list[Sale]:
        return list(self.repository.query_sales(filters))

    def summarize_sales(self, filters: SalesFilters) -> SalesSummary:
        sales = self.query_sales(
            SalesFilters(
                customer_id=filters.customer_id,
                region=filters.region,
                channel=filters.channel,
                start_date=filters.start_date,
                end_date=filters.end_date,
                limit=None,
            )
        )
        region_counts = Counter(sale.region for sale in sales)
        channel_counts = Counter(sale.channel for sale in sales)
        return SalesSummary(
            total_revenue=sum(
                (sale.amount for sale in sales),
                start=Decimal("0.00"),
            ),
            total_quantity=sum(sale.quantity for sale in sales),
            number_of_sales=len(sales),
            unique_customers=len({sale.customer_id for sale in sales}),
            top_region=_top_value(region_counts),
            top_channel=_top_value(channel_counts),
        )


def _top_value(counts: Counter[str]) -> str | None:
    if not counts:
        return None
    return min(
        counts,
        key=lambda value: (-counts[value], value),
    )
