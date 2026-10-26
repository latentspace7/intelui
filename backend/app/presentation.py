from app.contracts import Presentation, QueryResult
from app.errors import AppError

CATALOG_ID = "aerovista://analytics/v1"


def compile_ui(plan: Presentation, result: QueryResult) -> list[dict]:
    components: list[dict] = []
    data_sections = 0
    for index, section in enumerate(plan.sections):
        node = {
            "id": f"section-{index}",
            "title": section.title,
            "description": section.description,
        }
        known = set(result.columns)
        references = (
            section.columns
            + section.y
            + ([section.x] if section.x else [])
            + ([section.value_column] if section.value_column else [])
        )
        if not set(references).issubset(known):
            raise AppError(
                "invalid_ui", "The report references a column that is not in the query result.", 502
            )
        if section.kind == "metric":
            if (
                section.value_column is None
                or section.row_index is None
                or section.row_index >= len(result.rows)
            ):
                raise AppError("invalid_ui", "A KPI does not reference a valid result row.", 502)
            value = result.rows[section.row_index][section.value_column]
            if section.format != "text" and (
                not isinstance(value, (int, float)) or isinstance(value, bool)
            ):
                raise AppError("invalid_ui", "A numeric KPI references a nonnumeric value.", 502)
            node.update(component="Metric", value=value, format=section.format)
            data_sections += 1
        elif section.kind == "table":
            if not section.columns:
                raise AppError("invalid_ui", "A table needs at least one result column.", 502)
            node.update(component="DataTable", columns=section.columns, rows=result.rows)
            data_sections += 1
        elif section.kind in ("bar", "line", "donut"):
            if not section.x or not section.y or len(result.rows) > 60:
                raise AppError(
                    "invalid_ui", "A chart needs valid axes and no more than 60 result rows.", 502
                )
            for key in section.y:
                if any(
                    row[key] is not None
                    and (not isinstance(row[key], (int, float)) or isinstance(row[key], bool))
                    for row in result.rows
                ):
                    raise AppError("invalid_ui", "Chart values must be numeric.", 502)
            if section.kind == "donut" and (
                len(section.y) != 1
                or len(result.rows) > 12
                or any((row[section.y[0]] or 0) < 0 for row in result.rows)
            ):
                raise AppError(
                    "invalid_ui",
                    "A donut chart requires one nonnegative series and at most 12 categories.",
                    502,
                )
            node.update(
                component="Chart",
                chartType=section.kind,
                x=section.x,
                y=section.y,
                rows=result.rows,
                format=section.format,
            )
            data_sections += 1
        else:
            node.update(component="Narrative")
        components.append(node)
    if not data_sections:
        raise AppError("invalid_ui", "The report must include a chart, KPI, or table.", 502)
    root = {"id": "root", "component": "Stack", "items": [item["id"] for item in components]}
    return [
        {"version": "v0.9", "createSurface": {"surfaceId": "report", "catalogId": CATALOG_ID}},
        {
            "version": "v0.9",
            "updateComponents": {"surfaceId": "report", "components": [root, *components]},
        },
    ]
