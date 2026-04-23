import os
import pandas as pd
import pdfplumber
import streamlit as st


@st.cache_data
def list_pdfs_for_user(data_dir: str, prefix: str) -> list:
    return sorted([
        f for f in os.listdir(data_dir)
        if f.endswith(".pdf") and f.startswith(prefix)
    ])


@st.cache_data
def extract_transactions_from_pdf(pdf_path: str) -> pd.DataFrame:
    rows    = []
    headers = None

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            table = page.extract_table()
            if not table or len(table) < 2:
                continue
            if headers is None:
                headers = table[0]
            for row in table[1:]:
                if not any(cell is not None for cell in row):
                    continue
                # skip repeated header rows that appear on new pages
                normalized_row = [str(c).strip() if c else "" for c in row]
                normalized_hdr = [str(h).strip() if h else "" for h in headers]
                if normalized_row == normalized_hdr:
                    continue
                rows.append(row)

    return pd.DataFrame(rows, columns=headers)


def clean_transactions(df: pd.DataFrame) -> pd.DataFrame:
    df.columns = [c.strip().lower() for c in df.columns]

    column_map = {
        "transaction date": "date",
        "date":             "date",
        "description":      "description",
        "details":          "description",
        "amount":           "amount",
        "debit/credit":     "type",
        "type":             "type",
        "balance":          "balance",
    }
    df.rename(columns=column_map, inplace=True)

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["amount"] = (
        df["amount"].astype(str)
        .str.replace(",", "", regex=False)
        .str.replace("$", "", regex=False)
        .astype(float)
    )
    df["type"] = df["type"].str.lower()

    return df
