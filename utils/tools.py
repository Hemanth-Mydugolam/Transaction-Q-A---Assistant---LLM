import pandas as pd
from langchain_core.tools import tool
from typing import Optional


def make_tools(df_ref: dict) -> list:
    """
    Factory that returns 5 analysis tools closing over df_ref.
    df_ref is a mutable dict {"df": <DataFrame>} stored in st.session_state.
    Updating df_ref["df"] externally is immediately visible to all tools.
    """

    @tool
    def get_all_transactions() -> str:
        """Returns an overview of all transactions: total count, date range, and a sample of the first 5 rows."""
        df = df_ref["df"]
        if df is None:
            return "No data loaded."
        return (
            f"Total transactions: {len(df)}\n"
            f"Columns: {list(df.columns)}\n"
            f"Date range: {df['date'].min().date()} to {df['date'].max().date()}\n\n"
            f"Sample (first 5 rows):\n{df.head().to_string(index=False)}"
        )

    @tool
    def filter_by_month(month: str) -> str:
        """Returns all transactions for a given month.
        Args:
            month: Full month name, e.g. 'January', 'February', 'March'.
        """
        df = df_ref["df"]
        if df is None:
            return "No data loaded."
        filtered = df[df["date"].dt.month_name() == month]
        if filtered.empty:
            return f"No transactions found for {month}."
        return filtered[["date", "description", "amount", "type"]].to_string(index=False)

    @tool
    def summarize_by_type(month: Optional[str] = None) -> str:
        """Returns total debit and credit amounts with transaction counts, optionally filtered by month.
        Args:
            month: Full month name (e.g. 'January'). If omitted, summarizes all months.
        """
        df = df_ref["df"]
        if df is None:
            return "No data loaded."
        if month:
            df = df[df["date"].dt.month_name() == month]
            if df.empty:
                return f"No transactions found for {month}."
        summary = (
            df.groupby("type")["amount"]
            .agg(total="sum", count="count")
            .reset_index()
        )
        label = f"for {month}" if month else "across all months"
        return f"Summary {label}:\n{summary.to_string(index=False)}"

    @tool
    def top_expenses(n: int, month: Optional[str] = None) -> str:
        """Returns the top N highest debit transactions, optionally filtered by month.
        Args:
            n: Number of top expenses to return.
            month: Full month name (e.g. 'February'). If omitted, looks across all months.
        """
        df = df_ref["df"]
        if df is None:
            return "No data loaded."
        debits = df[df["type"] == "debit"]
        if month:
            debits = debits[debits["date"].dt.month_name() == month]
            if debits.empty:
                return f"No debit transactions found for {month}."
        top = debits.nlargest(n, "amount")[["date", "description", "amount"]]
        label = f"in {month}" if month else "overall"
        return f"Top {n} expenses {label}:\n{top.to_string(index=False)}"

    @tool
    def compare_months(month1: str, month2: str) -> str:
        """Returns a side-by-side debit and credit comparison between two months.
        Args:
            month1: First month name (e.g. 'January').
            month2: Second month name (e.g. 'February').
        """
        df = df_ref["df"]
        if df is None:
            return "No data loaded."
        rows = []
        for m in [month1, month2]:
            sub = df[df["date"].dt.month_name() == m]
            if sub.empty:
                rows.append({"Month": m, "Total Debit": "N/A", "Total Credit": "N/A", "Net (Credit - Debit)": "N/A"})
            else:
                debit  = sub[sub["type"] == "debit"]["amount"].sum()
                credit = sub[sub["type"] == "credit"]["amount"].sum()
                rows.append({
                    "Month":                 m,
                    "Total Debit":           f"{debit:.2f}",
                    "Total Credit":          f"{credit:.2f}",
                    "Net (Credit - Debit)":  f"{credit - debit:.2f}",
                })
        comparison = pd.DataFrame(rows)
        return f"Comparison between {month1} and {month2}:\n{comparison.to_string(index=False)}"

    return [get_all_transactions, filter_by_month, summarize_by_type, top_expenses, compare_months]
