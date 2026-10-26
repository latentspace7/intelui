import re

import sqlglot
from sqlglot import exp
from sqlglot.errors import OptimizeError, ParseError
from sqlglot.optimizer.qualify import qualify
from sqlglot.optimizer.scope import traverse_scope

from app.errors import AppError
from app.models import AIRLINE_TABLES

SAFE_FUNCTIONS = {
    "AND",
    "OR",
    "EXISTS",
    "COUNT",
    "SUM",
    "AVG",
    "MIN",
    "MAX",
    "COALESCE",
    "NULLIF",
    "ROUND",
    "ABS",
    "GREATEST",
    "LEAST",
    "CAST",
    "TRY_CAST",
    "EXTRACT",
    "DATE_TRUNC",
    "TIMESTAMP_TRUNC",
    "DATE",
    "TS_OR_DS_TO_DATE",
    "TO_CHAR",
    "TIME_TO_STR",
    "LOWER",
    "UPPER",
    "LENGTH",
    "CONCAT",
    "CONCAT_WS",
    "ROW_NUMBER",
    "RANK",
    "DENSE_RANK",
    "LAG",
    "LEAD",
    "FIRST_VALUE",
    "LAST_VALUE",
    "CEIL",
    "FLOOR",
    "POWER",
    "SQRT",
    "STDDEV",
    "STDDEV_SAMP",
    "STDDEV_POP",
    "VARIANCE",
    "PERCENTILE_CONT",
    "PERCENTILE_DISC",
    "FILTER",
    "IF",
    "CASE",
    "CURRENT_DATE",
    "CURRENT_TIMESTAMP",
    "DATE_PART",
}
FORBIDDEN_NODES = {
    "Insert",
    "Update",
    "Delete",
    "Drop",
    "Alter",
    "Create",
    "Merge",
    "Copy",
    "Command",
    "Into",
    "Lock",
    "Transaction",
    "Commit",
    "Rollback",
    "Set",
    "Use",
    "Grant",
    "Revoke",
    "Execute",
    "Analyze",
    "TruncateTable",
    "Parameter",
    "Placeholder",
    "Lateral",
}


def schema_for_model() -> str:
    lines = []
    for name, table in AIRLINE_TABLES.items():
        fields = []
        for column in table.columns:
            target = ", ".join(str(fk.target_fullname) for fk in column.foreign_keys)
            fields.append(f"{column.name} {column.type}" + (f" -> {target}" if target else ""))
        lines.append(f"airline.{name}({'; '.join(fields)})")
    return "\n".join(lines)


def validate_sql(sql: str) -> str:
    if not sql.strip() or len(sql) > 12000:
        raise AppError("unsafe_sql", "The query is empty or exceeds the size limit.")
    try:
        statements = sqlglot.parse(sql, read="postgres")
    except ParseError as exc:
        raise AppError("invalid_sql", "The generated SQL could not be parsed.") from exc
    if len(statements) != 1 or not isinstance(statements[0], (exp.Select, exp.Union)):
        raise AppError("unsafe_sql", "Only one read-only SELECT query is permitted.")
    tree = statements[0]
    nodes = list(tree.walk())
    if len(nodes) > 700 or len(list(tree.find_all(exp.Join))) > 6:
        raise AppError("unsafe_sql", "The query is too complex for this demo.")
    if any(type(node).__name__ in FORBIDDEN_NODES for node in nodes):
        raise AppError(
            "unsafe_sql", "Modifying operations, locks, and external operations are not permitted."
        )
    if any(node.args.get("recursive") for node in tree.find_all(exp.With)):
        raise AppError("unsafe_sql", "Recursive queries are not permitted.")
    for join in tree.find_all(exp.Join):
        if join.kind == "CROSS" or (not join.args.get("on") and not join.args.get("using")):
            raise AppError("unsafe_sql", "Joins must use an explicit relationship.")
    for node in nodes:
        if isinstance(node, exp.Func):
            name = node.name if isinstance(node, exp.Anonymous) else node.sql_name()
            if name.upper() not in SAFE_FUNCTIONS:
                raise AppError(
                    "unsafe_sql", f"Function {name[:50]} is not in the analytics allowlist."
                )
        if isinstance(node, exp.Dot):
            raise AppError("unsafe_sql", "Qualified function calls are not permitted.")
        if isinstance(node, exp.Cast):
            data_type = node.args["to"].sql(dialect="postgres").upper()
            if not re.fullmatch(
                r"(?:SMALLINT|INT|INTEGER|BIGINT|DECIMAL|NUMERIC|REAL|FLOAT|DOUBLE PRECISION|TEXT|VARCHAR|BOOLEAN|DATE|TIMESTAMP|TIMESTAMPTZ)(?:\([0-9, ]+\))?(?: WITH TIME ZONE)?",
                data_type,
            ):
                raise AppError("unsafe_sql", "This type conversion is not permitted.")
    physical_tables = 0
    for scope in traverse_scope(tree):
        for source in scope.sources.values():
            if isinstance(source, exp.Table):
                if (
                    source.catalog
                    or source.db not in ("", "airline")
                    or source.name not in AIRLINE_TABLES
                ):
                    raise AppError("unsafe_sql", "Only approved airline tables are accessible.")
                if not isinstance(source.this, exp.Identifier):
                    raise AppError("unsafe_sql", "Table-valued functions are not permitted.")
                physical_tables += 1
                source.set("db", exp.to_identifier("airline"))
    if not physical_tables:
        raise AppError("unsafe_sql", "An analytical query must read the airline dataset.")
    schema = {
        "airline": {
            name: {column.name: str(column.type) for column in table.columns}
            for name, table in AIRLINE_TABLES.items()
        }
    }
    try:
        tree = qualify(tree, dialect="postgres", schema=schema, validate_qualify_columns=True)
    except (OptimizeError, sqlglot.errors.SchemaError) as exc:
        raise AppError(
            "invalid_sql",
            "The query uses an unknown or ambiguous column; check the permitted schema.",
        ) from exc
    if any(not selection.alias_or_name for selection in tree.selects):
        raise AppError("invalid_sql", "Computed columns must have descriptive aliases.")
    return tree.sql(dialect="postgres")
