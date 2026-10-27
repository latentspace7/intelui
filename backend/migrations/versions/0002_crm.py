from pathlib import Path

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade():
    for statement in Path(__file__).with_name("0002_crm.sql").read_text().split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade():
    op.execute("DROP SCHEMA crm CASCADE")
