"""
Groq Brain Module
15 AI-powered Groq features for InsightFlow AUTO-FLOW.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import json

# ── Helper: Groq call wrapper ─────────────────────────────────────────────────

def _groq(groq_client, prompt: str, json_mode: bool = False) -> str:
    """Single-call wrapper for Groq completions."""
    kwargs = {"response_format": {"type": "json_object"}} if json_mode else {}
    resp = groq_client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile",
        **kwargs
    )
    return resp.choices[0].message.content


def _dark_layout():
    return dict(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")


# ── Feature helpers ───────────────────────────────────────────────────────────

def _nl_to_chart(query: str, df: pd.DataFrame, groq_client):
    """Feature 1: Natural Language → Chart config via Groq."""
    cols_info = {c: str(df[c].dtype) for c in df.columns}
    prompt = f"""Dataset columns (name: dtype): {json.dumps(cols_info)}
User wants: "{query}"
Pick the best Plotly chart. Return ONLY JSON:
{{"chart_type": "bar|line|scatter|histogram|pie|box", "x": "<col>", "y": "<col or null>", "title": "<short title>"}}"""
    try:
        cfg = json.loads(_groq(groq_client, prompt, json_mode=True))
        return cfg
    except:
        return None


def _nl_to_sql(question: str, df: pd.DataFrame, groq_client):
    """Feature 2: Convert question to SQL then run on df via pandasql."""
    cols = list(df.columns)
    prompt = f"""Table name is 'df'. Columns: {cols}.
User question: "{question}"
Write a single valid SQL SELECT query to answer it. Return ONLY JSON:
{{"sql": "<sql query>", "explanation": "<1 sentence what it does>"}}"""
    try:
        result = json.loads(_groq(groq_client, prompt, json_mode=True))
        return result
    except:
        return None


def _explain_dataset(df: pd.DataFrame, groq_client, lang: str = "English") -> str:
    """Feature 3: Full dataset explanation."""
    prompt = f"""Analyze this dataset and explain it in {lang}.
Columns: {list(df.columns)}
Sample (3 rows): {df.head(3).to_string()}
Dtypes: {df.dtypes.to_string()}

Generate a clear explanation covering:
1. What this dataset is about
2. The most important columns
3. Key patterns or observations
Keep it under 200 words. Plain text, no markdown headers."""
    return _groq(groq_client, prompt)


def _smart_insights(df: pd.DataFrame, groq_client, lang: str = "English") -> str:
    """Feature 4: Smart insight generator from df.describe()."""
    desc = df.describe(include='all').to_string()
    prompt = f"""You are a senior data analyst. Analyze this statistical summary in {lang}:
{desc}
Generate exactly 5 actionable insights (not just max/min). Look for trends, correlations, anomalies, and business implications.
Format as a numbered list."""
    return _groq(groq_client, prompt)


def _ai_chart_selection(df: pd.DataFrame, groq_client):
    """Feature 5: AI decides the best chart type."""
    num = df.select_dtypes('number').columns.tolist()
    cat = df.select_dtypes('object').columns.tolist()
    prompt = f"""Dataset has numeric columns: {num}, categorical columns: {cat}.
Which Plotly chart type is most insightful? Return ONLY JSON:
{{"chart_type":"bar|line|scatter|histogram|pie|box","x":"<col>","y":"<col or null>","reason":"<1 sentence>"}}"""
    try:
        return json.loads(_groq(groq_client, prompt, json_mode=True))
    except:
        return None


def _data_story(df: pd.DataFrame, groq_client, lang: str = "English") -> str:
    """Feature 6: Data story generator in narrative form."""
    desc = df.describe(include='all').to_string()
    cols = list(df.columns)
    prompt = f"""You are a data journalist. Write a 3-paragraph narrative story in {lang} about this dataset.
Columns: {cols}
Stats: {desc}
The story should read like an analyst report — mention trends, peaks, drops, and business context. No bullet points."""
    return _groq(groq_client, prompt)


def _business_recommendations(df: pd.DataFrame, groq_client) -> str:
    """Feature 7: Business recommendations."""
    num = df.select_dtypes('number').columns.tolist()
    cat = df.select_dtypes('object').columns.tolist()
    top_str = df.sort_values(by=num[0], ascending=False).head(3).to_string() if num else ""
    bot_str = df.sort_values(by=num[0], ascending=True).head(3).to_string() if num else ""
    prompt = f"""Based on this business data analysis:
Top performers: {top_str}
Bottom performers: {bot_str}
Categorical context: {cat}
Generate 5 specific, actionable business recommendations. Format as numbered list with 🎯 emoji."""
    return _groq(groq_client, prompt)


def _auto_dashboard_sections(df: pd.DataFrame, groq_client) -> list:
    """Feature 8: Groq decides dashboard section structure."""
    prompt = f"""Dataset columns: {list(df.columns)} | Dtypes: {df.dtypes.to_string()}
Suggest 3-5 dashboard section names (e.g. Overview, Trends, Comparisons, Forecast).
Return ONLY JSON: {{"sections": ["Section 1", "Section 2", ...]}}"""
    try:
        result = json.loads(_groq(groq_client, prompt, json_mode=True))
        return result.get("sections", ["Overview", "Trends", "Comparisons"])
    except:
        return ["Overview", "Trends", "Comparisons"]


def _fix_chart_error(error: str, df_info: str, groq_client) -> str:
    """Feature 9: Groq error fixer for chart generation."""
    prompt = f"""A Plotly chart generation failed with error: {error}
Dataframe info: {df_info}
Suggest a corrected Python Plotly express call (single line) that will work. Return ONLY the code."""
    return _groq(groq_client, prompt)


def _dataset_tag(df: pd.DataFrame, groq_client) -> str:
    """Feature 10: Dataset auto-labeling."""
    prompt = f"""Column names: {list(df.columns)}
Classify this dataset with a short 2-4 word label (e.g. 'Sales Dataset', 'HR Dataset', 'Finance Dataset').
Return ONLY JSON: {{"tag": "..."}}"""
    try:
        return json.loads(_groq(groq_client, prompt, json_mode=True)).get("tag", "General Dataset")
    except:
        return "General Dataset"


def _rename_columns(df: pd.DataFrame, groq_client) -> dict:
    """Feature 11: AI suggests user-friendly column names."""
    prompt = f"""These are raw column names: {list(df.columns)}
Suggest cleaner, user-friendly names for each (e.g. cust_id → Customer ID).
Return ONLY JSON: {{"renames": {{"original_name": "Friendly Name", ...}}}}"""
    try:
        return json.loads(_groq(groq_client, prompt, json_mode=True)).get("renames", {})
    except:
        return {}


def _multilang_insights(df: pd.DataFrame, groq_client, lang: str) -> str:
    """Feature 12: Insights in selected language."""
    return _smart_insights(df, groq_client, lang=lang)


def _explain_column(col: str, df: pd.DataFrame, groq_client) -> str:
    """Feature 13: Explain any single column."""
    stats = df[col].describe().to_string() if col in df.select_dtypes('number').columns else df[col].value_counts().head(5).to_string()
    prompt = f"""Column name: '{col}'
Statistics: {stats}
Explain what this column likely represents, its business importance, and any notable patterns. 2-3 sentences."""
    return _groq(groq_client, prompt)


def _predict_trend(df: pd.DataFrame, date_col: str, num_col: str, groq_client) -> str:
    """Feature 14: AI-based simple trend prediction text."""
    tail = df.sort_values(date_col).tail(10)[[date_col, num_col]].to_string() if date_col and num_col else ""
    prompt = f"""Recent time-series data (last 10 rows): {tail}
Column being tracked: {num_col}
Based on this trend, predict what might happen next (1 month or next period).
Be specific and concise. 2-3 sentences."""
    return _groq(groq_client, prompt)


def _dashboard_name(df: pd.DataFrame, groq_client) -> str:
    """Feature 15: Auto generate a great dashboard name."""
    prompt = f"""Column names: {list(df.columns)}
Generate a professional, specific dashboard name (4-6 words). Examples: 'Sales Performance Intelligence Dashboard', 'Customer Behavior Analytics Report'.
Return ONLY JSON: {{"name": "..."}}"""
    try:
        return json.loads(_groq(groq_client, prompt, json_mode=True)).get("name", "Data Intelligence Dashboard")
    except:
        return "Data Intelligence Dashboard"


# ── Main Render ──────────────────────────────────────────────────────────────

def render_groq_brain(df: pd.DataFrame, groq_client):
    """Render the 15 Groq-powered features in a tabbed panel."""
    st.markdown("---")
    st.markdown("## 🧠 Groq Brain")
    st.markdown("15 AI-powered analytical features, all driven by Groq LLM.")

    if groq_client is None:
        st.error("❌ Groq client not initialized. Set your API key in Settings.")
        return

    num_cols = df.select_dtypes('number').columns.tolist()
    cat_cols = df.select_dtypes('object').columns.tolist()
    date_cols = [c for c in df.columns if 'date' in c.lower() or 'time' in c.lower()]

    tabs = st.tabs([
        "💬 NL→Chart", "🗄️ SQL", "📖 Explain", "🔬 Insights",
        "📖 Story", "🤖 Recommend", "⚙️ AI Chart", "🔤 Labels & UX",
        "🌍 Language", "📈 Predict", "🏷️ Dashboard Name",
        "🏛️ Decision Engine", "🔮 What-If", "🚨 Problem Finder", "🧠 Genius Mode"
    ])

    # ── Tab 1: Natural Language → Chart ──────────────────────────────────────
    with tabs[0]:
        st.markdown("### 💬 Natural Language → Chart (Feature 1)")
        query = st.text_input("Ask a visualization question:", placeholder="Show sales by category", key="gb_nl")
        if query and st.button("🚀 Generate Chart", key="gb_nl_btn"):
            with st.spinner("Groq is analyzing your request..."):
                cfg = _nl_to_chart(query, df, groq_client)
            if cfg:
                try:
                    ct = cfg.get("chart_type", "bar")
                    x, y = cfg.get("x"), cfg.get("y")
                    title = cfg.get("title", query)
                    if ct == "bar":   fig = px.bar(df, x=x, y=y, title=title)
                    elif ct == "line": fig = px.line(df, x=x, y=y, title=title)
                    elif ct == "scatter": fig = px.scatter(df, x=x, y=y, title=title)
                    elif ct == "histogram": fig = px.histogram(df, x=x, title=title)
                    elif ct == "pie": fig = px.pie(df, names=x, values=y, title=title)
                    elif ct == "box": fig = px.box(df, x=x, y=y, title=title)
                    else: fig = px.bar(df, x=x, y=y, title=title)
                    fig.update_layout(**_dark_layout())
                    st.plotly_chart(fig, use_container_width=True)
                    st.success(f"📊 Groq chose: **{ct.title()}** chart → X: `{x}`, Y: `{y}`")
                except Exception as e:
                    st.error(f"Chart error: {e}")
                    fix = _fix_chart_error(str(e), df.dtypes.to_string(), groq_client)
                    st.info(f"💡 Groq suggestion: `{fix}`")
            else:
                st.error("Could not parse chart config from Groq.")

    # ── Tab 2: Auto SQL Generator ─────────────────────────────────────────────
    with tabs[1]:
        st.markdown("### 🗄️ Auto SQL Generator (Feature 2)")
        sql_q = st.text_input("Ask in plain English:", placeholder="Which category has the highest average sales?", key="gb_sql")
        if sql_q and st.button("🔍 Generate SQL & Run", key="gb_sql_btn"):
            with st.spinner("Converting to SQL..."):
                res = _nl_to_sql(sql_q, df, groq_client)
            if res and res.get("sql"):
                st.code(res["sql"], language="sql")
                st.caption(res.get("explanation", ""))
                try:
                    import pandasql as ps
                    result_df = ps.sqldf(res["sql"], {"df": df})
                    st.dataframe(result_df, use_container_width=True, hide_index=True)
                    # Auto-plot if result has 2 columns
                    r_num = result_df.select_dtypes('number').columns.tolist()
                    r_cat = result_df.select_dtypes('object').columns.tolist()
                    if r_cat and r_num:
                        fig = px.bar(result_df, x=r_cat[0], y=r_num[0])
                        fig.update_layout(**_dark_layout())
                        st.plotly_chart(fig, use_container_width=True)
                except ImportError:
                    st.warning("Install `pandasql` to run SQL: `pip install pandasql`")
                except Exception as e:
                    st.error(f"SQL execution error: {e}")

    # ── Tab 3: Full Dataset Explanation ──────────────────────────────────────
    with tabs[2]:
        st.markdown("### 📖 Full Dataset Explanation (Feature 3)")
        if st.button("🔍 Explain This Dataset", key="gb_explain"):
            with st.spinner("Groq is reading your dataset..."):
                explanation = _explain_dataset(df, groq_client)
            st.info(explanation)
        st.markdown("#### 🔎 Explain Any Column (Feature 13)")
        col_pick = st.selectbox("Select column to explain:", df.columns.tolist(), key="gb_col_exp")
        if st.button("Explain Column", key="gb_col_exp_btn"):
            with st.spinner(f"Explaining `{col_pick}`..."):
                col_exp = _explain_column(col_pick, df, groq_client)
            st.info(col_exp)

    # ── Tab 4: Smart Insights ─────────────────────────────────────────────────
    with tabs[3]:
        st.markdown("### 🔬 Smart Insight Generator (Feature 4)")
        if st.button("⚡ Generate 5 Smart Insights", key="gb_insights"):
            with st.spinner("Analyzing dataset statistics..."):
                insights = _smart_insights(df, groq_client)
            st.markdown(insights)

    # ── Tab 5: Data Story ─────────────────────────────────────────────────────
    with tabs[4]:
        st.markdown("### 📖 Data Story Generator (Feature 6)")
        if st.button("✍️ Write Data Story", key="gb_story"):
            with st.spinner("Writing your data story..."):
                story = _data_story(df, groq_client)
            st.markdown(f"> {story}")

    # ── Tab 6: Business Recommendations ──────────────────────────────────────
    with tabs[5]:
        st.markdown("### 🤖 Business Recommendations Engine (Feature 7)")
        if st.button("🎯 Get Strategic Recommendations", key="gb_reco"):
            with st.spinner("Groq is analyzing performance gaps..."):
                reco = _business_recommendations(df, groq_client)
            st.markdown(reco)

    # ── Tab 7: AI Chart Selection ─────────────────────────────────────────────
    with tabs[6]:
        st.markdown("### ⚙️ AI Chart Selection (Feature 5) + Dashboard Sections (Feature 8)")
        if st.button("🤖 Ask Groq: Best Chart?", key="gb_aichart"):
            with st.spinner("Groq picking the optimal chart..."):
                cfg = _ai_chart_selection(df, groq_client)
            if cfg:
                st.success(f"Groq recommends: **{cfg['chart_type'].title()} Chart** | X: `{cfg['x']}` | Y: `{cfg.get('y','N/A')}`")
                st.info(f"💡 Reason: {cfg.get('reason','')}")
                try:
                    ct, x, y = cfg['chart_type'], cfg['x'], cfg.get('y')
                    if ct == "bar":   fig = px.bar(df, x=x, y=y)
                    elif ct == "line": fig = px.line(df, x=x, y=y)
                    elif ct == "scatter": fig = px.scatter(df, x=x, y=y)
                    elif ct == "histogram": fig = px.histogram(df, x=x)
                    elif ct == "pie":  fig = px.pie(df, names=x, values=y)
                    elif ct == "box":  fig = px.box(df, x=x, y=y)
                    else: fig = px.bar(df, x=x, y=y)
                    fig.update_layout(title="AI-Selected Chart", **_dark_layout())
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as e:
                    st.error(f"Chart error: {e}")
        st.markdown("---")
        if st.button("🗂️ Ask Groq: Suggest Dashboard Sections", key="gb_sections"):
            with st.spinner("Groq is structuring your dashboard..."):
                sections = _auto_dashboard_sections(df, groq_client)
            st.success("Suggested Dashboard Structure:")
            for i, s in enumerate(sections, 1):
                st.markdown(f"**{i}. {s}**")

    # ── Tab 8: Labels & UX ────────────────────────────────────────────────────
    with tabs[7]:
        st.markdown("### 🔤 Dataset Tagging (Feature 10) + Column Renaming (Feature 11)")
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🏷️ Auto-Tag Dataset", key="gb_tag"):
                with st.spinner("Classifying dataset..."):
                    tag = _dataset_tag(df, groq_client)
                st.success(f"Dataset classified as: **{tag}**")
        with c2:
            if st.button("✏️ Suggest Friendly Column Names", key="gb_rename"):
                with st.spinner("Generating user-friendly names..."):
                    renames = _rename_columns(df, groq_client)
                if renames:
                    rename_df = pd.DataFrame([
                        {"Original": k, "Suggested": v} for k, v in renames.items()
                    ])
                    st.dataframe(rename_df, use_container_width=True, hide_index=True)
                    if st.button("✅ Apply Renames to Session", key="gb_apply_renames"):
                        st.session_state["_col_renames"] = renames
                        st.success("Renames stored! Reload dashboard to apply.")

    # ── Tab 9: Multi-Language ─────────────────────────────────────────────────
    with tabs[8]:
        st.markdown("### 🌍 Multi-Language Insights (Feature 12)")
        lang = st.selectbox("Select Language", ["English", "Hindi", "Spanish", "French", "German", "Arabic"], key="gb_lang")
        if st.button(f"Generate Insights in {lang}", key="gb_lang_btn"):
            with st.spinner(f"Generating insights in {lang}..."):
                result = _multilang_insights(df, groq_client, lang)
            st.markdown(result)

    # ── Tab 10: Trend Prediction ──────────────────────────────────────────────
    with tabs[9]:
        st.markdown("### 📈 Predict Future Trend (Feature 14)")
        d_col = st.selectbox("Date/Time Column", ["None"] + date_cols + cat_cols, key="gb_dcol")
        n_col = st.selectbox("Numeric Column to Forecast", num_cols if num_cols else ["None"], key="gb_ncol")
        if st.button("🔮 Predict Next Trend", key="gb_predict"):
            with st.spinner("Groq forecasting..."):
                pred = _predict_trend(df, d_col if d_col != "None" else None, n_col, groq_client)
            st.info(pred)

    # ── Tab 11: Dashboard Name ────────────────────────────────────────────────
    with tabs[10]:
        st.markdown("### 🏷️ AI Dashboard Name Generator (Feature 15)")
        if st.button("✨ Generate Dashboard Name", key="gb_dname"):
            with st.spinner("Generating premium dashboard name..."):
                name = _dashboard_name(df, groq_client)
            st.success(f"🎯 **{name}**")
            st.session_state["_ai_dashboard_name"] = name

    # ── Tab 12: Data → Decision Engine ───────────────────────────────────────
    with tabs[11]:
        st.markdown("### 🏛️ Decision Engine")
        st.caption("Not insights. Not analysis. Clear, direct business decisions.")
        if st.button("⚡ Make Decisions From Data", key="gb_decide", type="primary", use_container_width=True):
            with st.spinner("Groq is thinking like a CEO..."):
                num = df.select_dtypes('number').columns.tolist()
                cat = df.select_dtypes('object').columns.tolist()
                top = df.sort_values(by=num[0], ascending=False).head(3).to_string() if num else ""
                bot = df.sort_values(by=num[0], ascending=True).head(3).to_string() if num else ""
                prompt = f"""You are a CEO making data-driven decisions. Analyze this business data:
Top performers: {top}
Underperformers: {bot}
Columns: {list(df.columns)}
Stats: {df.describe().to_string()}

Generate 5 CLEAR, DIRECT business decisions — not insights, not analysis.
Each decision must be an action statement like:
"Increase budget for [X] by 30%"
"Discontinue [Y] immediately"
"Double inventory for [Z] in Q3"

Format as numbered list with 🔴🟡🟢 priority emojis. Be bold and specific."""
                decisions = _groq(groq_client, prompt)
            st.markdown(decisions)

    # ── Tab 13: What-If Simulator ─────────────────────────────────────────────
    with tabs[12]:
        st.markdown("### 🔮 What-If Simulator")
        st.caption("Simulate the impact of changes on your data before making them.")
        num_cols_sim = df.select_dtypes('number').columns.tolist()
        if not num_cols_sim:
            st.warning("No numeric columns for simulation.")
        else:
            sim_col = st.selectbox("Column to change:", num_cols_sim, key="gb_sim_col")
            sim_pct = st.slider("Change by (%):", -50, 100, 10, key="gb_sim_pct")
            cat_sim = df.select_dtypes('object').columns.tolist()
            if st.button("🔮 Simulate & Show Impact", key="gb_sim_btn", use_container_width=True):
                df_sim = df.copy()
                df_sim[sim_col] = df_sim[sim_col] * (1 + sim_pct / 100)
                # Show before vs after chart
                col_a, col_b = st.columns(2)
                chart_x = cat_sim[0] if cat_sim else df.index.astype(str)
                with col_a:
                    st.markdown("**Before**")
                    fig_b = px.bar(df.head(10), x=cat_sim[0] if cat_sim else df.index, y=sim_col)
                    fig_b.update_layout(**_dark_layout(), title="Original")
                    st.plotly_chart(fig_b, use_container_width=True)
                with col_b:
                    st.markdown("**After Simulation**")
                    fig_a = px.bar(df_sim.head(10), x=cat_sim[0] if cat_sim else df_sim.index, y=sim_col)
                    fig_a.update_layout(**_dark_layout(), title=f"After {sim_pct:+}%")
                    st.plotly_chart(fig_a, use_container_width=True)
                # AI interpretation
                orig_total = df[sim_col].sum()
                new_total = df_sim[sim_col].sum()
                diff = new_total - orig_total
                with st.spinner("Groq interpreting the simulation..."):
                    interp_prompt = f"""A business simulation shows:
Column '{sim_col}' changed by {sim_pct}%.
Original total: {orig_total:,.2f} → New total: {new_total:,.2f} (change: {diff:+,.2f})
Explain what this means for the business in 2-3 clear sentences. Be direct about the impact."""
                    interp = _groq(groq_client, interp_prompt)
                st.info(f"💡 **AI Impact Analysis:** {interp}")

    # ── Tab 14: Auto Problem Finder ───────────────────────────────────────────
    with tabs[13]:
        st.markdown("### 🚨 Auto Problem Finder")
        st.caption("Automatically detects problems, drops, and underperformers in your data.")
        if st.button("🔍 Scan for Problems", key="gb_problems", type="primary", use_container_width=True):
            problems_found = []
            num_cols_pf = df.select_dtypes('number').columns.tolist()
            cat_cols_pf = df.select_dtypes('object').columns.tolist()
            # Detect anomalies (IQR)
            for col in num_cols_pf[:3]:
                Q1, Q3 = df[col].quantile(0.25), df[col].quantile(0.75)
                IQR = Q3 - Q1
                outliers = df[(df[col] < (Q1 - 1.5*IQR)) | (df[col] > (Q3 + 1.5*IQR))]
                if len(outliers) > 0:
                    problems_found.append(f"🚨 **{len(outliers)} outliers** found in `{col}`")
            # Detect low-performers in categories
            if cat_cols_pf and num_cols_pf:
                grp = df.groupby(cat_cols_pf[0])[num_cols_pf[0]].mean()
                low_thresh = grp.quantile(0.25)
                low_cats = grp[grp < low_thresh].index.tolist()
                if low_cats:
                    problems_found.append(f"📉 **Underperforming categories** in `{cat_cols_pf[0]}`: {', '.join(str(c) for c in low_cats[:5])}")
            # High null density
            null_cols = df.columns[df.isnull().mean() > 0.1].tolist()
            if null_cols:
                problems_found.append(f"⚠️ **High null density** (>10%) in columns: {', '.join(null_cols)}")

            if problems_found:
                st.error("**Problems detected in your dataset:**")
                for p in problems_found:
                    st.markdown(p)
            else:
                st.success("✅ No critical problems detected in this dataset!")

            # AI Problem Summary
            with st.spinner("Groq generating full diagnostic report..."):
                diag_prompt = f"""You are a data forensics expert. Analyze this dataset for problems:
Columns: {list(df.columns)}
Stats: {df.describe().to_string()}
Null counts: {df.isnull().sum().to_string()}

Identify and report:
1. Negative trends or drops
2. Underperforming categories or segments
3. Data quality issues
4. Business risks hidden in the numbers

Format as a numbered diagnostic report. Be specific and direct."""
                diag = _groq(groq_client, diag_prompt)
            st.markdown("---")
            st.markdown("#### 📋 Full Diagnostic Report")
            st.markdown(diag)

    # ── Tab 15: One-Click Genius Mode ─────────────────────────────────────────
    with tabs[14]:
        st.markdown("### 🧠 One-Click Analysis")
        st.caption("Press one button. Get everything: Summary, Charts, Insights, and Decisions.")
        if st.button("🧠 MAKE ME UNDERSTAND EVERYTHING", key="gb_genius",
                     type="primary", use_container_width=True):
            num_g = df.select_dtypes('number').columns.tolist()
            cat_g = df.select_dtypes('object').columns.tolist()

            # 1. Summary
            with st.spinner("Step 1/4 — Generating Summary..."):
                summary = _explain_dataset(df, groq_client)
            st.markdown("#### 📖 What is this dataset?")
            st.info(summary)

            # 2. Auto Charts
            st.markdown("#### 📊 Key Visualizations")
            c1, c2 = st.columns(2)
            if cat_g and num_g:
                fig1 = px.bar(df.sort_values(by=num_g[0], ascending=False).head(10),
                              x=cat_g[0], y=num_g[0], title=f"Top 10 by {num_g[0]}")
                fig1.update_layout(**_dark_layout())
                c1.plotly_chart(fig1, use_container_width=True)
            if len(num_g) >= 2:
                fig2 = px.scatter(df, x=num_g[0], y=num_g[1],
                                  title=f"{num_g[0]} vs {num_g[1]}")
                fig2.update_layout(**_dark_layout())
                c2.plotly_chart(fig2, use_container_width=True)

            # 3. Smart Insights
            with st.spinner("Step 3/4 — Generating Insights..."):
                insights_g = _smart_insights(df, groq_client)
            st.markdown("#### 🔬 Top Insights")
            st.markdown(insights_g)

            # 4. Decisions
            with st.spinner("Step 4/4 — Making Decisions..."):
                top = df.sort_values(by=num_g[0], ascending=False).head(3).to_string() if num_g else ""
                bot = df.sort_values(by=num_g[0], ascending=True).head(3).to_string() if num_g else ""
                dec_prompt = f"""You are a CEO. Based on this data:
Top: {top}
Bottom: {bot}
Generate 5 direct business decisions. Format as numbered list with priority emojis. Be bold."""
                decisions_g = _groq(groq_client, dec_prompt)
            st.markdown("#### 🏛️ Business Decisions")
            st.markdown(decisions_g)
            st.balloons()

