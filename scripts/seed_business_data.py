from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.db.models import Customer, Product, Sale
from app.db.session import create_database_tables, engine


@dataclass(frozen=True)
class BusinessSeedData:
    customers: list[Customer]
    products: list[Product]
    sales: list[Sale]


def build_business_seed_data() -> BusinessSeedData:
    customer_specs = [
        (
            "10000000-0000-0000-0000-000000000001",
            "Northstar Retail",
            "mid-market",
            "north",
            "active",
        ),
        (
            "10000000-0000-0000-0000-000000000002",
            "Harbor Goods",
            "small-business",
            "east",
            "active",
        ),
        (
            "10000000-0000-0000-0000-000000000003",
            "Summit Supply",
            "enterprise",
            "west",
            "active",
        ),
        (
            "10000000-0000-0000-0000-000000000004",
            "Cedar Works",
            "mid-market",
            "south",
            "active",
        ),
        (
            "10000000-0000-0000-0000-000000000005",
            "Bluebird Market",
            "small-business",
            "north",
            "inactive",
        ),
        (
            "10000000-0000-0000-0000-000000000006",
            "Orchard Trading",
            "enterprise",
            "east",
            "active",
        ),
    ]
    product_specs = [
        (
            "20000000-0000-0000-0000-000000000001",
            "Analytics Starter",
            "software",
            "120.00",
        ),
        (
            "20000000-0000-0000-0000-000000000002",
            "Analytics Pro",
            "software",
            "350.00",
        ),
        (
            "20000000-0000-0000-0000-000000000003",
            "Data Connector",
            "integration",
            "80.00",
        ),
        (
            "20000000-0000-0000-0000-000000000004",
            "Support Pack",
            "service",
            "200.00",
        ),
        (
            "20000000-0000-0000-0000-000000000005",
            "Training Session",
            "service",
            "500.00",
        ),
    ]
    customers = [
        Customer(
            id=UUID(identifier),
            name=name,
            segment=segment,
            region=region,
            status=status,
        )
        for identifier, name, segment, region, status in customer_specs
    ]
    products = [
        Product(
            id=UUID(identifier),
            name=name,
            category=category,
            price=Decimal(price),
        )
        for identifier, name, category, price in product_specs
    ]
    base_date = datetime(2026, 1, 5, 12, tzinfo=UTC)
    channels = ["direct", "partner", "online"]
    sales = [
        Sale(
            id=UUID(f"30000000-0000-0000-0000-{index:012d}"),
            customer_id=customers[index % len(customers)].id,
            product_id=products[index % len(products)].id,
            amount=products[index % len(products)].price * ((index % 3) + 1),
            quantity=(index % 3) + 1,
            sold_at=base_date + timedelta(days=index * 4),
            channel=channels[index % len(channels)],
            region=customers[index % len(customers)].region,
        )
        for index in range(1, 25)
    ]
    return BusinessSeedData(customers=customers, products=products, sales=sales)


def seed() -> None:
    create_database_tables()
    data = build_business_seed_data()
    with Session(engine) as session:
        session.execute(delete(Sale))
        session.execute(delete(Product))
        session.execute(delete(Customer))
        session.add_all(data.customers)
        session.add_all(data.products)
        session.add_all(data.sales)
        session.commit()


if __name__ == "__main__":
    seed()
