from app.contracts import Presentation, QueryResult, Section, SQLPlan


class FakeProvider:
    def __init__(self):
        self.plans = 0
        self.fail = False

    def plan(self, question, context, repair=None):
        self.plans += 1
        sql = "SELECT COUNT(*) AS bookings FROM airline.bookings"
        return SQLPlan(
            status="ready", message="Counts all synthetic bookings.", sql=sql, title="Booking count"
        )

    def present(self, question: str, result: QueryResult) -> Presentation:
        if self.fail:
            from app.errors import AppError

            raise AppError("model_error", "Test provider unavailable", 502)
        return Presentation(
            title="Booking count",
            summary=f"The query returned {result.rows[0]['bookings']} bookings.",
            sections=[
                Section(
                    kind="metric",
                    title="Bookings",
                    description="All synthetic bookings",
                    columns=[],
                    x=None,
                    y=[],
                    value_column="bookings",
                    row_index=0,
                    format="number",
                )
            ],
        )
