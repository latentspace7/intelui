from pathlib import Path

from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    sql = Path(__file__).with_name("0001_schema.sql").read_text()
    for statement in sql.split(";"):
        if statement.strip():
            op.execute(statement)


def downgrade():
    op.execute("DROP SCHEMA app CASCADE")
    op.execute("DROP SCHEMA airline CASCADE")
