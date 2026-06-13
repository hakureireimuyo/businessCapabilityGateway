"""SQLAlchemy ORM models for the amazon_db plugin.

Maps directly to the real SQLite database schema.
No relationships are defined — each repository method constructs
its own queries, which avoids cross-thread ORM state issues.
"""

from datetime import date, datetime
from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


# =========================================================
# Product main table
# =========================================================

class Product(Base):
    __tablename__ = "product"

    id: Mapped[int] = mapped_column(primary_key=True)
    asin: Mapped[str] = mapped_column(String(20), unique=True, index=True)
    url: Mapped[str] = mapped_column(String(1000), default="")
    title: Mapped[str] = mapped_column(String(1000), default="")
    price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    image_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    review_count: Mapped[int] = mapped_column(Integer, default=0)
    monthly_sales_file_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    monthly_sales_file_downloaded: Mapped[bool] = mapped_column(Boolean, default=False)
    parent_category: Mapped[str] = mapped_column(String(255), default="")
    parent_category_rank: Mapped[int] = mapped_column(Integer, default=0)
    sub_category: Mapped[str] = mapped_column(String(255), default="")
    sub_category_rank: Mapped[int] = mapped_column(Integer, default=0)
    monthly_sales: Mapped[int] = mapped_column(Integer, default=0)
    sales_amount: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    fba_fee: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    gross_margin: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    rating: Mapped[float | None] = mapped_column(Numeric(3, 2), nullable=True)
    launch_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    launch_days: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# =========================================================
# Product–keyword association table
# =========================================================

class ProductKeyword(Base):
    __tablename__ = "product_keyword"

    __table_args__ = (
        UniqueConstraint("asin", "sheet_name", "keyword", name="uq_product_keyword"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    asin: Mapped[str] = mapped_column(String(20), index=True)
    sheet_name: Mapped[str] = mapped_column(String(255))
    category: Mapped[str] = mapped_column(String(255), default="")
    keyword: Mapped[str] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# =========================================================
# Product variant table
# =========================================================

class ProductVariant(Base):
    __tablename__ = "product_variant"

    __table_args__ = (
        UniqueConstraint("parent_asin", "child_asin", name="uq_product_variant"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    parent_asin: Mapped[str] = mapped_column(String(20), index=True)
    child_asin: Mapped[str] = mapped_column(String(20), index=True)
    sku: Mapped[str | None] = mapped_column(String(255), nullable=True)
    variant: Mapped[str | None] = mapped_column(String(500), nullable=True)
    price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    monthly_sales: Mapped[int] = mapped_column(Integer, default=0)
    best_seller: Mapped[bool] = mapped_column(Boolean, default=False)
    crawl_count: Mapped[int] = mapped_column(Integer, default=0)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# =========================================================
# Keyword–product relevance score table
# =========================================================

class ProductKeywordRelevance(Base):
    __tablename__ = "product_keyword_relevance"

    __table_args__ = (
        UniqueConstraint("keyword", "asin", name="uq_keyword_asin_relevance"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    keyword: Mapped[str] = mapped_column(String(500))
    asin: Mapped[str] = mapped_column(String(20), index=True)
    relevance_score: Mapped[int] = mapped_column(Integer, default=0)


# =========================================================
# Monthly sales table
# =========================================================

class MonthlySales(Base):
    __tablename__ = "monthly_sales"

    __table_args__ = (
        UniqueConstraint("asin", "month", name="uq_monthly_sales"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    asin: Mapped[str] = mapped_column(String(20), index=True)
    month: Mapped[str] = mapped_column(String(7), index=True)
    sales: Mapped[int] = mapped_column(Integer, default=0)
    revenue: Mapped[float | None] = mapped_column(Numeric(14, 2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
