from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Customer, Product, Sale


@dataclass(frozen=True)
class CustomerFilters:
    segment: str | None = None
    region: str | None = None
    status: str | None = None
    limit: int = 20


@dataclass(frozen=True)
class SalesFilters:
    customer_id: UUID | None = None
    region: str | None = None
    channel: str | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    limit: int | None = 20


class BusinessRepository(Protocol):
    def list_customers(self, limit: int = 20) -> Sequence[Customer]: ...

    def get_customer_by_id(self, customer_id: UUID) -> Customer | None: ...

    def search_customers(
        self,
        filters: CustomerFilters,
    ) -> Sequence[Customer]: ...

    def list_products(self) -> Sequence[Product]: ...

    def query_sales(self, filters: SalesFilters) -> Sequence[Sale]: ...


class SqlAlchemyBusinessRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_customers(self, limit: int = 20) -> Sequence[Customer]:
        statement = select(Customer).order_by(Customer.name).limit(limit)
        return self.session.scalars(statement).all()

    def get_customer_by_id(self, customer_id: UUID) -> Customer | None:
        return self.session.get(Customer, customer_id)

    def search_customers(
        self,
        filters: CustomerFilters,
    ) -> Sequence[Customer]:
        statement = select(Customer)
        if filters.segment is not None:
            statement = statement.where(Customer.segment == filters.segment)
        if filters.region is not None:
            statement = statement.where(Customer.region == filters.region)
        if filters.status is not None:
            statement = statement.where(Customer.status == filters.status)
        statement = statement.order_by(Customer.name).limit(filters.limit)
        return self.session.scalars(statement).all()

    def list_products(self) -> Sequence[Product]:
        statement = select(Product).order_by(Product.name)
        return self.session.scalars(statement).all()

    def query_sales(self, filters: SalesFilters) -> Sequence[Sale]:
        statement = select(Sale)
        if filters.customer_id is not None:
            statement = statement.where(Sale.customer_id == filters.customer_id)
        if filters.region is not None:
            statement = statement.where(Sale.region == filters.region)
        if filters.channel is not None:
            statement = statement.where(Sale.channel == filters.channel)
        if filters.start_date is not None:
            statement = statement.where(Sale.sold_at >= filters.start_date)
        if filters.end_date is not None:
            statement = statement.where(Sale.sold_at <= filters.end_date)
        statement = statement.order_by(Sale.sold_at.desc(), Sale.id)
        if filters.limit is not None:
            statement = statement.limit(filters.limit)
        return self.session.scalars(statement).all()
