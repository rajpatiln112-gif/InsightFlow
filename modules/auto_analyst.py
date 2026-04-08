"""
Auto-Analyst Module
Implements the 10-step automated analytics pipeline + 14 advanced smart features.
"""
import streamlit as st
import pandas as pd
import plotly.express as px
import numpy as np
import json
from query_service import save_query

# ── Helper Functions ─────────────────────────────────────────────────────────

def _get_auto_metadata(df, groq_client):
    """Detect business type and dashboard title using AI."""
    cols = ", ".join(df.columns[:15])
    prompt = f"""Analyze these columns: {cols}.
    1. Classify the dataset type (e.g. Sales, Finance, Student, Healthcare).
    2. Generate a professional dashboard title (max 5 words).
    Return ONLY a JSON object: {{"type": "...", "title": "..."}}"""
    try:
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except:
        return {"type": "General Data", "title": "Autonomous Data Intelligence Report"}


def _calculate_quality_score(df):
    """Calculate data quality score based on nulls and duplicates."""
    total_cells = df.size
    null_cells = df.isnull().sum().sum()
    dup_rows = df.duplicated().sum()
    null_pct = (null_cells / total_cells) * 100 if total_cells > 0 else 0
    dup_pct  = (dup_rows / len(df)) * 100 if len(df) > 0 else 0
    score = 100 - (null_pct * 2) - (dup_pct * 1)
    return max(0, min(100, score)), null_pct, dup_pct


def _detect_anomalies(df, col):
    """Detect unusual spikes in numeric data using IQR."""
    try:
        Q1, Q3 = df[col].quantile(0.25), df[col].quantile(0.75)
        IQR = Q3 - Q1
        outliers = df[(df[col] < (Q1 - 1.5 * IQR)) | (df[col] > (Q3 + 1.5 * IQR))]
        return len(outliers) > 0, len(outliers)
    except:
        return False, 0


def _ask_data_question(question, df, groq_client):
    """Convert a user question to a pandas expression and return answer + insight."""
    cols_info = df.dtypes.to_string()
    sample    = df.head(3).to_string()
    prompt    = f"""You are a data analyst. Given this dataframe info:
Columns & types:\n{cols_info}
Sample rows:\n{sample}

User question: "{question}"

Instructions:
1. Write a single Python pandas expression using `df` to answer it.
2. Provide a 1-sentence plain English insight about the result.
Return ONLY JSON: {{"expression": "...", "insight": "..."}}"""
    try:
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"}
        )
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {"expression": None, "insight": f"Error: {e}"}


# ── Main Render ──────────────────────────────────────────────────────────────

def render_auto_flow():
    st.markdown("## ⚡ Auto Flow")
    st.markdown("---")

    # ─── MULTI-DATASET COMPARISON (Feature 14) ───────────────────────────────
    with st.expander("📂 MULTI-DATASET COMPARISON (Upload 2 Files)"):
        mf1, mf2 = st.columns(2)
        if "multi_df_a" in st.session_state:
            mf1.success("Dataset A loaded.")
            if mf1.button("🗑️ Clear Dataset A", use_container_width=True):
                del st.session_state["multi_df_a"]
                st.rerun()
        else:
            file_a = mf1.file_uploader("Dataset A", type=["csv"], key="mf_a")
            if file_a:
                st.session_state.multi_df_a = pd.read_csv(file_a).dropna().drop_duplicates()
                st.rerun()

        if "multi_df_b" in st.session_state:
            mf2.success("Dataset B loaded.")
            if mf2.button("🗑️ Clear Dataset B", use_container_width=True):
                del st.session_state["multi_df_b"]
                st.rerun()
        else:
            file_b = mf2.file_uploader("Dataset B", type=["csv"], key="mf_b")
            if file_b:
                st.session_state.multi_df_b = pd.read_csv(file_b).dropna().drop_duplicates()
                st.rerun()

        df_a = st.session_state.get("multi_df_a")
        df_b = st.session_state.get("multi_df_b")

        if df_a is not None and df_b is not None:
            common_num = list(set(df_a.select_dtypes('number').columns) &
                              set(df_b.select_dtypes('number').columns))
            if common_num:
                col_pick = st.selectbox("Compare Metric", common_num, key="mf_pick")
                cmp_df = pd.DataFrame({
                    "Dataset A": [df_a[col_pick].mean()],
                    "Dataset B": [df_b[col_pick].mean()],
                }, index=["Mean"])
                fig_cmp = px.bar(cmp_df.T.reset_index(), x="index", y="Mean",
                                 labels={"index": "Dataset", "Mean": col_pick},
                                 title=f"Comparison: {col_pick}",
                                 color="index",
                                 color_discrete_sequence=px.colors.qualitative.Set1)
                fig_cmp.update_layout(template="plotly_dark",
                                      paper_bgcolor="rgba(0,0,0,0)",
                                      plot_bgcolor="rgba(0,0,0,0)")
                st.plotly_chart(fig_cmp, use_container_width=True)
            else:
                st.warning("No common numeric columns found between datasets.")

    st.markdown("---")

    # 🔹 STEP 1: File Upload or Global Dataset
    df = st.session_state.get("df")
    file_name = st.session_state.get("dataset_name", "dataset")

    if df is None:
        file = st.file_uploader("Upload CSV or Excel to Begin Auto Flow", type=["csv", "xlsx"])
        if file:
            from modules.data_handler import load_data
            st.session_state.df = load_data(file)
            st.session_state.dataset_name = file.name
            st.rerun()

    if df is not None:
        # 🔹 DATA HEALTH & QUALITY (Feature 3)
        score, n_pct, d_pct = _calculate_quality_score(df)

        # 🔹 BUSINESS INTELLIGENCE — Type detection & Auto Title (Features 7 & 8)
        if "auto_meta" not in st.session_state or st.session_state.get("_last_file") != file_name:
            st.session_state.auto_meta = _get_auto_metadata(df, st.session_state.groq_client)
            st.session_state._last_file = file_name

        meta = st.session_state.auto_meta
        st.markdown(f"### 🛡️ {meta['title']}")
        st.caption(f"Domain: **{meta['type']}** | Health Score: **{score:.1f}%**")

        # 🔹 STEP 2: Data Cleaning
        df_clean = df.dropna().drop_duplicates()

        col_q1, col_q2, col_q3 = st.columns(3)
        col_q1.metric("Cleanliness Score", f"{score:.0f}%")
        col_q2.metric("Null Density",       f"{n_pct:.1f}%")
        col_q3.metric("Duplicate Ratio",    f"{d_pct:.1f}%")

        # 🔹 STEP 3: Detect Column Types
        num_cols = df_clean.select_dtypes(include=['number']).columns.tolist()
        cat_cols = df_clean.select_dtypes(include=['object']).columns.tolist()

        # 🔹 STEP 4: Add Filters
        if cat_cols:
            pivot    = st.selectbox("Select Dimension Filter", cat_cols)
            selected = st.selectbox(f"Filter by {pivot}", ["All"] + list(df_clean[pivot].unique()))
            df_filtered = df_clean[df_clean[pivot] == selected] if selected != "All" else df_clean
        else:
            df_filtered = df_clean

        # 🔹 ANOMALY ALERTS (Feature 12)
        if num_cols:
            has_anomaly, a_count = _detect_anomalies(df_filtered, num_cols[0])
            if has_anomaly:
                st.error(f"🚨 **ANOMALY ALERT**: {a_count} unusual variance points in `{num_cols[0]}`.")

        # 🔹 STEP 5: Key Metrics
        if num_cols:
            col_m1, col_m2 = st.columns(2)
            col_m1.metric(f"Total {num_cols[0]}",   f"{df_filtered[num_cols[0]].sum():,.2f}")
            col_m2.metric(f"Average {num_cols[0]}", f"{df_filtered[num_cols[0]].mean():,.2f}")

        # 🔹 STEP 6: Top 10 Selection
        df_top = (df_filtered.sort_values(by=num_cols[0], ascending=False).head(10)
                  if num_cols else df_filtered.head(10))

        # 🔹 STEP 7: Auto Chart Logic
        fig = None
        date_cols = [c for c in df_filtered.columns if 'date' in c.lower() or 'time' in c.lower()]
        if date_cols and num_cols:
            fig = px.line(df_filtered.sort_values(date_cols[0]), x=date_cols[0], y=num_cols[0],
                          color=cat_cols[0] if cat_cols else None,
                          color_discrete_sequence=px.colors.qualitative.Set2)
        elif cat_cols and num_cols:
            fig = px.bar(df_top, x=cat_cols[0], y=num_cols[0],
                         color=cat_cols[0],
                         color_discrete_sequence=px.colors.qualitative.Set3)
        elif len(num_cols) >= 2:
            fig = px.scatter(df_filtered, x=num_cols[0], y=num_cols[1],
                             color=cat_cols[0] if cat_cols else None,
                             color_discrete_sequence=px.colors.qualitative.Set1)
        elif len(num_cols) == 1:
            fig = px.histogram(df_filtered, x=num_cols[0],
                               color=cat_cols[0] if cat_cols else None,
                               color_discrete_sequence=px.colors.qualitative.Pastel)

        if fig:
            # 🔹 STEP 8: Chart Design
            fig.update_layout(
                title=f"{meta['type']} Analysis — Primary Axis",
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )

            # 🔹 STEP 9: Dashboard Layout
            st.markdown("---")
            col1, col2 = st.columns([2, 1])

            with col1:
                st.plotly_chart(fig, use_container_width=True)
                # Feature 5: Auto Chart Explanation
                chart_type = fig.data[0].type
                x_lbl = fig.layout.xaxis.title.text or (cat_cols[0] if cat_cols else "X")
                y_lbl = fig.layout.yaxis.title.text or (num_cols[0] if num_cols else "Y")
                st.info(f"💡 **Auto Insight**: This **{chart_type}** chart shows the distribution of `{y_lbl}` across `{x_lbl}`. "
                        f"Patterns here reveal dominant trends in the **{meta['type']}** domain.")

            with col2:
                # 🔹 STEP 10: AI Story & Recommendations
                st.markdown("### 🧠 AI Engine")
                if not df_top.empty and num_cols:
                    top_row = df_top.iloc[0]
                    bot_row = df_top.iloc[-1]
                    cat_val = top_row[cat_cols[0]] if cat_cols else "Top Record"
                    bot_val = bot_row[cat_cols[0]] if cat_cols else "Bottom Record"
                    st.write(f"📈 **{cat_val}** leads with the highest {num_cols[0]}.")
                    st.write(f"📉 **{bot_val}** shows lowest performance in this segment.")
                    st.write(f"🔬 Data reliability: **{score:.0f}%** post-refinement.")
                    st.markdown("---")
                    st.markdown("**🚀 Recommendations**")
                    if score < 90:
                        st.warning(f"⚠️ Data quality below threshold. Re-upload a cleaner dataset.")
                    st.success(f"✅ Double down on **{cat_val}** — it drives peak value.")
                    st.error(f"❌ Review **{bot_val}** for optimization or removal.")
                else:
                    st.write("Insufficient data for insight generation.")

            # Save to Dashboard (Feature 9)
            if "dashboard_charts" not in st.session_state:
                st.session_state.dashboard_charts = []
            if st.button("📥 Save Chart to Dashboard", key="af_save"):
                st.session_state.dashboard_charts.append(fig)
                st.success(f"Chart saved! Dashboard now has {len(st.session_state.dashboard_charts)} visualization(s).")

            # Feature 6: Compare Two Columns
            if len(num_cols) >= 2:
                with st.expander("🔄 AUTO COLUMN COMPARISON"):
                    col_x = st.selectbox("Column A", num_cols, key="cmp_x")
                    col_y = st.selectbox("Column B", [c for c in num_cols if c != col_x], key="cmp_y")
                    fig_cmp = px.scatter(df_filtered, x=col_x, y=col_y, trendline="ols",
                                         title=f"{col_x} vs {col_y}",
                                         color_discrete_sequence=px.colors.qualitative.Set2)
                    fig_cmp.update_layout(template="plotly_dark",
                                          paper_bgcolor="rgba(0,0,0,0)",
                                          plot_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_cmp, use_container_width=True)
                    diff = df_filtered[col_x].mean() - df_filtered[col_y].mean()
                    st.info(f"💡 Mean difference between `{col_x}` and `{col_y}` is **{diff:,.2f}**.")

        # ─── FEATURE 1: ASK QUESTIONS TO DATA ────────────────────────────────
        st.markdown("---")
        st.markdown("### 💬 Ask Questions About Your Data")
        question = st.text_input("Type your question (e.g. 'Which category has highest sales?')",
                                 key="af_question")
        if question and st.button("🔍 Get Answer", key="af_ask"):
            with st.spinner("Analyzing..."):
                result = _ask_data_question(question, df_filtered, st.session_state.groq_client)
            if result.get("expression"):
                try:
                    answer = eval(result["expression"], {"df": df_filtered, "pd": pd, "np": np})
                    st.success(f"**Answer:** {answer}")
                    st.info(f"💡 **Insight:** {result['insight']}")
                    # Save query to persistent history
                    save_query(question, str(answer) + " | " + result['insight'])
                except Exception as e:
                    st.error(f"Could not evaluate: {e}")
            else:
                st.error(result.get("insight", "Unable to process question."))

        # ─── HTML EXPORT (Feature 10) ─────────────────────────────────────────
        if fig:
            st.markdown("---")
            st.markdown("### 📤 Export Report")
            html_out = f"""<html><head><title>{meta['title']}</title>
            <link href='https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap' rel='stylesheet'>
            <style>body{{font-family:'Inter',sans-serif;background:#0e1117;color:#e0e0e0;padding:20px}}</style></head>
            <body>
            <h1>🛡️ {meta['title']}</h1>
            <p>Domain: {meta['type']} | Health Score: {score:.1f}%</p>
            <hr>
            {fig.to_html(include_plotlyjs='cdn', full_html=False)}
            <hr><h3>Strategic Summary</h3>
            <ul><li>Data Rows: {len(df_filtered)}</li>
            <li>Null Density: {n_pct:.1f}%</li>
            <li>Duplicate Ratio: {d_pct:.1f}%</li></ul>
            </body></html>"""
            st.download_button("📥 Download Full Report (HTML)", data=html_out,
                               file_name=f"{meta['title'].replace(' ','_')}_report.html",
                               mime="text/html", use_container_width=True)

    else:
        st.info("Ready for autonomous stream. Please upload a CSV file.")


