"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None

data_quality_enum = sa.Enum("LIVE", "DELAYED", "STALE", "UNAVAILABLE", name="dataquality")
severity_enum = sa.Enum("NORMAL", "LOW", "MODERATE", "HIGH", "CRITICAL", name="severity")


def upgrade() -> None:
    bind = op.get_bind()

    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("display_name", sa.String(120), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("onboarded", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "sessions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("token", sa.String(128), nullable=False, unique=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default=sa.false()),
    )
    op.create_index("ix_sessions_token", "sessions", ["token"])
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])

    op.create_table(
        "instruments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("symbol", sa.String(32), nullable=False, unique=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("exchange", sa.String(16), nullable=False, server_default="NSE"),
        sa.Column("sector", sa.String(64), nullable=False, server_default=""),
        sa.Column("base_price", sa.Float, nullable=False),
    )
    op.create_index("ix_instruments_symbol", "instruments", ["symbol"])
    op.create_index("ix_instruments_symbol_exchange", "instruments", ["symbol", "exchange"])

    op.create_table(
        "watchlists",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(120), nullable=False, server_default="My Watchlist"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_watchlists_user_id", "watchlists", ["user_id"])

    op.create_table(
        "watchlist_items",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("watchlist_id", sa.String(36), sa.ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("instrument_id", sa.String(36), sa.ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("added_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("price_threshold_pct", sa.Float, nullable=True),
        sa.UniqueConstraint("watchlist_id", "instrument_id", name="uq_watchlist_instrument"),
    )
    op.create_index("ix_watchlist_items_watchlist_id", "watchlist_items", ["watchlist_id"])
    op.create_index("ix_watchlist_items_instrument_id", "watchlist_items", ["instrument_id"])

    op.create_table(
        "market_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("instrument_id", sa.String(36), sa.ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("price", sa.Float, nullable=False),
        sa.Column("volume", sa.Integer, nullable=False),
        sa.Column("avg_volume", sa.Float, nullable=False),
        sa.Column("benchmark_change_pct", sa.Float, nullable=False),
        sa.Column("volatility", sa.Float, nullable=False),
        sa.Column("source", sa.String(64), nullable=False, server_default="mock"),
        sa.Column("quality", data_quality_enum, nullable=False, server_default="LIVE"),
        sa.Column("market_timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_snapshots_instrument_time", "market_snapshots", ["instrument_id", "market_timestamp"])

    op.create_table(
        "user_checkpoints",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("watchlist_id", sa.String(36), sa.ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("snapshot_refs", sa.JSON, nullable=False),
        sa.Column("checked_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_checkpoint_watchlist_time", "user_checkpoints", ["watchlist_id", "checked_at"])
    op.create_index("ix_user_checkpoints_user_id", "user_checkpoints", ["user_id"])

    op.create_table(
        "change_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("watchlist_id", sa.String(36), sa.ForeignKey("watchlists.id", ondelete="CASCADE"), nullable=False),
        sa.Column("instrument_id", sa.String(36), sa.ForeignKey("instruments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("checkpoint_id", sa.String(36), sa.ForeignKey("user_checkpoints.id", ondelete="CASCADE"), nullable=False),
        sa.Column("previous_snapshot_id", sa.String(36), sa.ForeignKey("market_snapshots.id"), nullable=True),
        sa.Column("current_snapshot_id", sa.String(36), sa.ForeignKey("market_snapshots.id"), nullable=False),
        sa.Column("price_change_abs", sa.Float, nullable=False, server_default="0"),
        sa.Column("price_change_pct", sa.Float, nullable=False, server_default="0"),
        sa.Column("volume_ratio", sa.Float, nullable=False, server_default="1"),
        sa.Column("benchmark_divergence_pct", sa.Float, nullable=False, server_default="0"),
        sa.Column("volatility_delta", sa.Float, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("ix_change_events_watchlist_created", "change_events", ["watchlist_id", "created_at"])
    op.create_index("ix_change_events_instrument_id", "change_events", ["instrument_id"])
    op.create_index("ix_change_events_checkpoint_id", "change_events", ["checkpoint_id"])

    op.create_table(
        "attention_scores",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("change_event_id", sa.String(36), sa.ForeignKey("change_events.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("price_component", sa.Float, nullable=False, server_default="0"),
        sa.Column("volume_component", sa.Float, nullable=False, server_default="0"),
        sa.Column("benchmark_component", sa.Float, nullable=False, server_default="0"),
        sa.Column("volatility_component", sa.Float, nullable=False, server_default="0"),
        sa.Column("total_score", sa.Float, nullable=False, server_default="0"),
        sa.Column("severity", severity_enum, nullable=False, server_default="NORMAL"),
        sa.Column("reasons", sa.JSON, nullable=False),
    )
    op.create_index("ix_attention_severity_score", "attention_scores", ["severity", "total_score"])

    op.create_table(
        "user_preferences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("price_threshold_pct", sa.Float, nullable=False, server_default="2.0"),
        sa.Column("volume_spike_multiplier", sa.Float, nullable=False, server_default="2.0"),
        sa.Column("benchmark_divergence_threshold_pct", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("notify_on_critical_only", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("theme", sa.String(16), nullable=False, server_default="light"),
    )


def downgrade() -> None:
    op.drop_table("user_preferences")
    op.drop_table("attention_scores")
    op.drop_table("change_events")
    op.drop_table("user_checkpoints")
    op.drop_table("market_snapshots")
    op.drop_table("watchlist_items")
    op.drop_table("watchlists")
    op.drop_table("instruments")
    op.drop_table("sessions")
    op.drop_table("users")
    severity_enum.drop(op.get_bind(), checkfirst=True)
    data_quality_enum.drop(op.get_bind(), checkfirst=True)
