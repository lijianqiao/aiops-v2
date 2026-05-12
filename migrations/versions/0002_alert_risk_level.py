"""Add Alert.risk_level column distinct from upstream severity.

Revision ID: 0002_alert_risk_level
Revises: 0001_initial
Create Date: 2026-05-12 12:00:00

``severity`` stores the upstream alert severity reported by Zabbix
(warning / high / disaster). ``risk_level`` records the platform-derived
execution risk floor (L1 / L2 / L3) so SQL queries can distinguish source
data from derived decisions without unpacking JSON.
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "0002_alert_risk_level"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add a dedicated risk_level column to alerts."""
    op.add_column("alerts", sa.Column("risk_level", sa.String(length=8), nullable=True))
    op.create_index("ix_alerts_risk_level", "alerts", ["risk_level"], unique=False)


def downgrade() -> None:
    """Drop the risk_level column."""
    op.drop_index("ix_alerts_risk_level", table_name="alerts")
    op.drop_column("alerts", "risk_level")
