from dataclasses import dataclass
from datetime import date
from math import isfinite

from app.config import settings
from app.contracts import ColumnBinding, Presentation, QueryResult, Section, Snapshot
from app.errors import AppError
from app.models import utcnow


@dataclass(frozen=True)
class ComponentSpec:
    name: str
    title: str
    description: str
    fields: tuple[str, ...]
    numeric: tuple[str, ...] = ()


CRM_COMPONENTS = {
    "record_overview": ComponentSpec(
        "RecordOverview",
        "Account overview",
        "Search accounts, inspect ownership, and explore company details.",
        ("id", "label", "status", "owner", "description", "amount"),
        ("amount",),
    ),
    "checklist": ComponentSpec(
        "Checklist",
        "Work checklist",
        "Filter outstanding tasks, inspect due dates, and update task status.",
        ("id", "label", "status", "owner", "date"),
    ),
    "document_review": ComponentSpec(
        "DocumentReview",
        "Document review",
        "Compare declared and extracted fields against a synthetic source document and record a review.",
        ("id", "label", "field", "expected", "actual", "source", "status"),
    ),
    "quote_simulator": ComponentSpec(
        "QuoteSimulator",
        "Quote simulator",
        "Adjust seats, term, and discount to compare subscription costs with a saved quote.",
        ("id", "label", "unit_price", "quantity", "months", "discount", "setup_fee"),
        ("unit_price", "quantity", "months", "discount", "setup_fee"),
    ),
    "budget_planner": ComponentSpec(
        "BudgetPlanner",
        "Budget planner",
        "Explore changes in monthly income, expenses, and a proposed recurring spend.",
        ("id", "label", "income", "expenses", "budget"),
        ("income", "expenses", "budget"),
    ),
    "comparison": ComponentSpec(
        "Comparison",
        "Option comparison",
        "Select options to compare contract totals, terms, and service details side by side.",
        ("id", "label", "amount", "category", "description"),
        ("amount",),
    ),
    "cash_flow": ComponentSpec(
        "CashFlow",
        "Cash-flow explorer",
        "Filter recorded inflows and outflows, inspect monthly totals, and drill into entries.",
        ("id", "label", "date", "amount", "category", "direction"),
        ("amount",),
    ),
    "activity_timeline": ComponentSpec(
        "ActivityTimeline",
        "Activity timeline",
        "Filter emails, calls, meetings, and notes and expand their source details.",
        ("id", "label", "date", "description", "category", "owner"),
    ),
    "rule_assessment": ComponentSpec(
        "RuleAssessment",
        "Business-rule checks",
        "Inspect versioned demo rules, their recorded inputs, and deterministic comparison results.",
        ("id", "label", "observed", "threshold", "operator", "description"),
        ("observed", "threshold"),
    ),
    "relationship_graph": ComponentSpec(
        "RelationshipGraph",
        "Relationship explorer",
        "Select a company or contact to inspect its immediate connections and relationship types.",
        ("source", "target", "relationship"),
    ),
    "milestone_tracker": ComponentSpec(
        "MilestoneTracker",
        "Delivery milestones",
        "Follow onboarding milestones by account, with owners, due dates, and blockers.",
        ("id", "label", "status", "date", "owner", "group"),
    ),
    "pipeline": ComponentSpec(
        "Pipeline",
        "Deal pipeline",
        "Filter opportunities by owner, inspect stage totals, and open deal details.",
        ("id", "label", "status", "amount", "owner", "date"),
        ("amount",),
    ),
}


def component_instructions() -> str:
    return "\n".join(
        f"{kind}: {spec.description} Required binding fields: {', '.join(spec.fields)}."
        for kind, spec in CRM_COMPONENTS.items()
    )


def bind_component(
    section: Section, result: QueryResult, reference_date: str | None = None
) -> dict:
    spec = CRM_COMPONENTS[section.kind]
    bindings = {binding.field: binding.column for binding in section.bindings}
    if len(bindings) != len(section.bindings) or set(bindings) != set(spec.fields):
        raise AppError(
            "invalid_ui",
            f"{spec.title} requires exactly these bindings: {', '.join(spec.fields)}.",
            502,
        )
    if not set(bindings.values()).issubset(result.columns):
        raise AppError(
            "invalid_ui", "An analytics component references a missing result column.", 502
        )
    rows = [{field: row[column] for field, column in bindings.items()} for row in result.rows]
    if len(rows) > 200:
        raise AppError(
            "invalid_ui", "Analytics components support at most 200 rows; narrow the query.", 502
        )
    for row in rows:
        for field in set(spec.fields) - set(spec.numeric) - {"id"}:
            if not isinstance(row[field], str):
                raise AppError("invalid_ui", f"{spec.title}: {field} must contain text.", 502)
        if "date" in row:
            try:
                date.fromisoformat(row["date"][:10])
            except ValueError as exc:
                raise AppError(
                    "invalid_ui", "Component dates must use ISO date format.", 502
                ) from exc
        for field in spec.numeric:
            value = row[field]
            if field == "observed" and value is None:
                continue
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not isfinite(value)
            ):
                raise AppError(
                    "invalid_ui", f"{spec.title}: {field} must contain finite numbers.", 502
                )
        if "id" in row and (
            not isinstance(row["id"], int) or isinstance(row["id"], bool) or row["id"] < 1
        ):
            raise AppError("invalid_ui", "Record IDs must be positive integers.", 502)
        if section.kind == "quote_simulator" and (
            row["unit_price"] < 0
            or row["setup_fee"] < 0
            or not 1 <= row["quantity"] <= 10000
            or int(row["quantity"]) != row["quantity"]
            or not 1 <= row["months"] <= 120
            or int(row["months"]) != row["months"]
            or not 0 <= row["discount"] <= 100
        ):
            raise AppError("invalid_ui", "Quote values exceed the supported scenario bounds.", 502)
        if section.kind == "cash_flow" and (
            row["direction"] not in ("Inflow", "Outflow") or row["amount"] < 0
        ):
            raise AppError(
                "invalid_ui", "Cash-flow entries require a direction and nonnegative amount.", 502
            )
        if section.kind == "rule_assessment" and row["operator"] not in ("gte", "lte", "eq"):
            raise AppError("invalid_ui", "The rule comparison operator is unsupported.", 502)
        if section.kind == "budget_planner" and any(row[key] < 0 for key in spec.numeric):
            raise AppError("invalid_ui", "Budget inputs must be nonnegative.", 502)
    return {
        "component": spec.name,
        "rows": rows,
        "referenceDate": reference_date or str(settings.demo_reference_date),
    }


EXAMPLES = {
    "record_overview": (
        "Show an account overview of our companies.",
        "SELECT c.id, c.name AS label, c.status, s.name AS owner, c.description, c.annual_revenue AS amount FROM crm.companies c JOIN crm.staff s ON s.id=c.owner_id ORDER BY c.id LIMIT 48",
    ),
    "checklist": (
        "Show the work checklist for Northstar Labs.",
        "SELECT t.id, t.title AS label, t.status, s.name AS owner, t.due_date AS date FROM crm.tasks t JOIN crm.staff s ON s.id=t.owner_id JOIN crm.companies c ON c.id=t.company_id WHERE c.name='Northstar Labs' ORDER BY t.due_date, t.id",
    ),
    "document_review": (
        "Review the declared and extracted document fields for Northstar Labs.",
        "SELECT f.id, d.title AS label, f.field_name AS field, f.declared_value AS expected, f.extracted_value AS actual, d.body AS source, f.review_status AS status FROM crm.document_fields f JOIN crm.documents d ON d.id=f.document_id JOIN crm.companies c ON c.id=d.company_id WHERE c.name='Northstar Labs' ORDER BY d.id, f.id",
    ),
    "quote_simulator": (
        "Build an interactive quote simulator for Northstar Labs.",
        "SELECT q.id, p.name AS label, p.monthly_unit_price AS unit_price, q.quantity, q.months, q.discount_percent AS discount, p.setup_fee FROM crm.quotes q JOIN crm.products p ON p.id=q.product_id JOIN crm.companies c ON c.id=q.company_id WHERE c.name='Northstar Labs' ORDER BY p.monthly_unit_price",
    ),
    "budget_planner": (
        "Explore monthly budget scenarios for our accounts.",
        "SELECT id, name AS label, monthly_income AS income, monthly_expenses AS expenses, monthly_budget AS budget FROM crm.companies ORDER BY id LIMIT 48",
    ),
    "comparison": (
        "Compare Northstar Labs service quotes side by side by total contract cost.",
        "SELECT q.id, p.name AS label, ROUND(p.monthly_unit_price*q.quantity*q.months*(1-q.discount_percent/100)+p.setup_fee, 2) AS amount, p.category, CONCAT(p.description, ' Seats: ', q.quantity, '. Term: ', q.months, ' months. Discount: ', q.discount_percent, '%.') AS description FROM crm.quotes q JOIN crm.products p ON p.id=q.product_id JOIN crm.companies c ON c.id=q.company_id WHERE c.name='Northstar Labs' ORDER BY amount",
    ),
    "cash_flow": (
        "Explore Northstar Labs cash-flow entries over the last six months.",
        "SELECT e.id, e.description AS label, e.occurred_at AS date, e.amount, e.category, e.direction FROM crm.cash_entries e JOIN crm.companies c ON c.id=e.company_id WHERE c.name='Northstar Labs' ORDER BY e.occurred_at, e.id",
    ),
    "activity_timeline": (
        "Show Northstar Labs account activity as an interactive timeline.",
        "SELECT a.id, a.title AS label, a.occurred_at AS date, a.description, a.category, s.name AS owner FROM crm.activities a JOIN crm.staff s ON s.id=a.owner_id JOIN crm.companies c ON c.id=a.company_id WHERE c.name='Northstar Labs' ORDER BY a.occurred_at DESC",
    ),
    "rule_assessment": (
        "Explain the recorded onboarding and budget checks for Northstar Labs.",
        "SELECT r.id, r.name AS label, r.observed_value AS observed, r.threshold, r.operator, CONCAT(r.description, ' Rule version: ', r.rule_version, '. Evaluated: ', r.evaluated_at, '.') AS description FROM crm.rule_checks r JOIN crm.companies c ON c.id=r.company_id WHERE c.name='Northstar Labs' ORDER BY r.id",
    ),
    "relationship_graph": (
        "Show the company and contact relationships around Northstar Labs.",
        "SELECT a.name AS source, b.name AS target, r.relationship FROM crm.relationships r JOIN crm.companies a ON a.id=r.source_company_id JOIN crm.companies b ON b.id=r.target_company_id WHERE a.name='Northstar Labs' OR b.name='Northstar Labs' UNION ALL SELECT c.name AS source, p.name AS target, p.role AS relationship FROM crm.contacts p JOIN crm.companies c ON c.id=p.company_id WHERE c.name='Northstar Labs'",
    ),
    "milestone_tracker": (
        "Show delivery and onboarding milestones for our accounts.",
        "SELECT m.id, m.title AS label, m.status, m.due_date AS date, s.name AS owner, c.name AS group FROM crm.milestones m JOIN crm.staff s ON s.id=m.owner_id JOIN crm.companies c ON c.id=m.company_id ORDER BY c.id, m.sequence LIMIT 200",
    ),
    "pipeline": (
        "Show the deal pipeline grouped by stage with owners and close dates.",
        "SELECT d.id, d.name AS label, d.stage AS status, d.amount, s.name AS owner, d.expected_close AS date FROM crm.deals d JOIN crm.staff s ON s.id=d.owner_id ORDER BY d.expected_close, d.id LIMIT 200",
    ),
}


def example_snapshot(kind: str, reference_date: str | None = None) -> Snapshot:
    from app.executor import execute_query
    from app.presentation import compile_ui

    if kind not in EXAMPLES:
        raise AppError("example_not_found", "This catalog example was not found.", 404)
    spec = CRM_COMPONENTS[kind]
    question, sql = EXAMPLES[kind]
    result = execute_query(sql)
    plan = Presentation(
        title=spec.title,
        summary=f"{spec.description} Values come from the synthetic business database.",
        sections=[
            Section(
                kind=kind,
                title=spec.title,
                description=spec.description,
                columns=[],
                x=None,
                y=[],
                value_column=None,
                row_index=None,
                format="currency",
                bindings=[ColumnBinding(field=field, column=field) for field in spec.fields],
            )
        ],
    )
    return Snapshot(
        title=spec.title,
        question=question,
        summary=plan.summary,
        result=result,
        presentation=plan,
        ui=compile_ui(plan, result, reference_date=reference_date) if result.rows else [],
        generated_at=utcnow(),
        reference_date=reference_date or str(settings.demo_reference_date),
        model="Database example · no model call",
        catalog_example=kind,
    )
