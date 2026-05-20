"""Initial schema

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────
    op.create_table(
        'users',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('email', sa.String(255), nullable=False, unique=True),
        sa.Column('username', sa.String(50), nullable=False, unique=True),
        sa.Column('hashed_password', sa.String(255), nullable=False),
        sa.Column('full_name', sa.String(100)),
        sa.Column('avatar_url', sa.String(500)),
        sa.Column('role', sa.String(20), server_default='user'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('is_verified', sa.Boolean, server_default='false'),
        sa.Column('telegram_chat_id', sa.String(50)),
        sa.Column('telegram_alerts_enabled', sa.Boolean, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('last_login_at', sa.DateTime(timezone=True)),
    )
    op.create_index('ix_users_email', 'users', ['email'])
    op.create_index('ix_users_username', 'users', ['username'])

    # ── exchanges ──────────────────────────────────────────────────────────
    op.create_table(
        'exchanges',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(30), nullable=False),
        sa.Column('label', sa.String(100), nullable=False),
        sa.Column('encrypted_api_key', sa.Text, nullable=False),
        sa.Column('encrypted_api_secret', sa.Text, nullable=False),
        sa.Column('encrypted_passphrase', sa.Text),
        sa.Column('is_paper_trading', sa.Boolean, server_default='true'),
        sa.Column('is_active', sa.Boolean, server_default='true'),
        sa.Column('last_sync_at', sa.DateTime(timezone=True)),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── strategies ────────────────────────────────────────────────────────
    op.create_table(
        'strategies',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('strategy_type', sa.String(30), nullable=False),
        sa.Column('description', sa.Text),
        sa.Column('parameters', sa.JSON, server_default='{}'),
        sa.Column('is_public', sa.Boolean, server_default='false'),
        sa.Column('created_by', UUID(as_uuid=False), sa.ForeignKey('users.id')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── bots ──────────────────────────────────────────────────────────────
    op.create_table(
        'bots',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('exchange_id', UUID(as_uuid=False), sa.ForeignKey('exchanges.id', ondelete='CASCADE'), nullable=False),
        sa.Column('strategy_id', UUID(as_uuid=False), sa.ForeignKey('strategies.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('timeframe', sa.String(10), server_default='1h'),
        sa.Column('status', sa.String(20), server_default='stopped'),
        sa.Column('position_size_usdt', sa.Float, server_default='100'),
        sa.Column('max_open_trades', sa.Integer, server_default='1'),
        sa.Column('stop_loss_pct', sa.Float),
        sa.Column('take_profit_pct', sa.Float),
        sa.Column('trailing_stop_pct', sa.Float),
        sa.Column('max_daily_loss_usdt', sa.Float),
        sa.Column('total_trades', sa.Integer, server_default='0'),
        sa.Column('winning_trades', sa.Integer, server_default='0'),
        sa.Column('total_pnl_usdt', sa.Float, server_default='0'),
        sa.Column('paper_balance_usdt', sa.Float, server_default='10000'),
        sa.Column('last_tick_at', sa.DateTime(timezone=True)),
        sa.Column('error_message', sa.Text),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── trades ────────────────────────────────────────────────────────────
    op.create_table(
        'trades',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('bot_id', UUID(as_uuid=False), sa.ForeignKey('bots.id', ondelete='SET NULL')),
        sa.Column('exchange_id', UUID(as_uuid=False), sa.ForeignKey('exchanges.id'), nullable=False),
        sa.Column('symbol', sa.String(20), nullable=False),
        sa.Column('side', sa.String(10), nullable=False),
        sa.Column('order_type', sa.String(20), server_default='market'),
        sa.Column('status', sa.String(20), server_default='open'),
        sa.Column('entry_price', sa.Float, nullable=False),
        sa.Column('exit_price', sa.Float),
        sa.Column('quantity', sa.Float, nullable=False),
        sa.Column('stop_loss_price', sa.Float),
        sa.Column('take_profit_price', sa.Float),
        sa.Column('pnl_usdt', sa.Float),
        sa.Column('pnl_pct', sa.Float),
        sa.Column('commission_usdt', sa.Float, server_default='0'),
        sa.Column('exchange_order_id', sa.String(100)),
        sa.Column('is_paper_trade', sa.Boolean, server_default='true'),
        sa.Column('entry_reason', sa.Text),
        sa.Column('exit_reason', sa.Text),
        sa.Column('opened_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('closed_at', sa.DateTime(timezone=True)),
    )

    # ── journal_entries ───────────────────────────────────────────────────
    op.create_table(
        'journal_entries',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('trade_id', UUID(as_uuid=False), sa.ForeignKey('trades.id', ondelete='SET NULL')),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('notes', sa.Text),
        sa.Column('emotion', sa.String(50)),
        sa.Column('mistakes', sa.Text),
        sa.Column('lessons', sa.Text),
        sa.Column('setup_quality', sa.Integer),
        sa.Column('tags', sa.JSON, server_default='[]'),
        sa.Column('screenshot_urls', sa.JSON, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── alerts ────────────────────────────────────────────────────────────
    op.create_table(
        'alerts',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('alert_type', sa.String(50), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('message', sa.Text, nullable=False),
        sa.Column('is_read', sa.Boolean, server_default='false'),
        sa.Column('metadata', sa.JSON, server_default='{}'),
        sa.Column('sent_via_telegram', sa.Boolean, server_default='false'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # ── user_settings ─────────────────────────────────────────────────────
    op.create_table(
        'user_settings',
        sa.Column('id', UUID(as_uuid=False), primary_key=True),
        sa.Column('user_id', UUID(as_uuid=False), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('theme', sa.String(20), server_default='dark'),
        sa.Column('currency', sa.String(10), server_default='USD'),
        sa.Column('timezone', sa.String(50), server_default='UTC'),
        sa.Column('notify_trade_open', sa.Boolean, server_default='true'),
        sa.Column('notify_trade_close', sa.Boolean, server_default='true'),
        sa.Column('notify_stop_loss', sa.Boolean, server_default='true'),
        sa.Column('notify_take_profit', sa.Boolean, server_default='true'),
        sa.Column('notify_daily_summary', sa.Boolean, server_default='true'),
        sa.Column('daily_summary_time', sa.String(10), server_default='08:00'),
        sa.Column('default_risk_pct', sa.Float, server_default='1.0'),
        sa.Column('default_stop_loss_pct', sa.Float, server_default='2.0'),
        sa.Column('default_take_profit_pct', sa.Float, server_default='4.0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    for table in ['user_settings','alerts','journal_entries','trades','bots','strategies','exchanges','users']:
        op.drop_table(table)
