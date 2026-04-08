"""
Data Handler Module
Handles file loading, validation, and summary generation.
"""
import pandas as pd
import streamlit as st
import io


def load_data(uploaded_file):
    """Load a CSV or Excel file into a pandas DataFrame."""
    try:
        file_name = uploaded_file.name.lower()
        if file_name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif file_name.endswith((".xlsx", ".xls")):
            df = pd.read_excel(uploaded_file, engine="openpyxl")
        else:
            st.error("❌ Unsupported file format. Please upload a CSV or Excel file.")
            return None

        if df.empty:
            st.warning("⚠️ The uploaded file is empty.")
            return None

        return df
    except Exception as e:
        st.error(f"❌ Error loading file: {str(e)}")
        return None


def get_data_summary(df):
    """Generate a comprehensive summary dictionary of the DataFrame."""
    summary = {}
    summary["shape"] = df.shape
    summary["columns"] = list(df.columns)
    summary["dtypes"] = df.dtypes.astype(str).to_dict()
    summary["missing"] = df.isnull().sum().to_dict()
    summary["missing_pct"] = (df.isnull().sum() / len(df) * 100).round(2).to_dict()
    summary["numeric_cols"] = list(df.select_dtypes(include=["number"]).columns)
    summary["categorical_cols"] = list(df.select_dtypes(include=["object", "category"]).columns)
    summary["datetime_cols"] = list(df.select_dtypes(include=["datetime64"]).columns)
    summary["duplicates"] = int(df.duplicated().sum())
    summary["memory_mb"] = round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2)

    if summary["numeric_cols"]:
        summary["describe_numeric"] = df[summary["numeric_cols"]].describe().round(2)
    if summary["categorical_cols"]:
        summary["describe_categorical"] = df[summary["categorical_cols"]].describe()

    return summary


def get_schema_string(df, max_rows=5):
    """Return a concise string representation of the DataFrame schema for AI context."""
    buf = io.StringIO()
    buf.write(f"Dataset: {df.shape[0]} rows × {df.shape[1]} columns\n\n")
    buf.write("Columns & Types:\n")
    for col in df.columns:
        non_null = df[col].notna().sum()
        buf.write(f"  - {col} ({df[col].dtype}, {non_null}/{len(df)} non-null)\n")
    buf.write(f"\nFirst {max_rows} rows:\n")
    buf.write(df.head(max_rows).to_string(index=False))
    buf.write("\n\nBasic Statistics:\n")
    buf.write(df.describe(include="all").to_string())
    return buf.getvalue()
