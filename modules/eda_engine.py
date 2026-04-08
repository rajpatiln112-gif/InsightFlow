"""
Autonomous EDA Engine
Generates comprehensive exploratory data analysis automatically.
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import plotly.figure_factory as ff
import streamlit as st
import numpy as np


def render_eda(df, groq_client=None):
    """Run full autonomous EDA on the DataFrame."""

    st.markdown("## 🔬 Exploratory Data Analysis")
    st.markdown("---")
    st.markdown('<div class="premium-card">', unsafe_allow_html=True)

    numeric_cols = list(df.select_dtypes(include=["number"]).columns)
    categorical_cols = list(df.select_dtypes(include=["object", "category"]).columns)

    # Downsample for intensive Plotly charts to prevent browser lockup
    # Further reduced to 1000 to completely avoid Streamlit browser crashes
    plot_df = df.sample(n=1000, random_state=42) if len(df) > 1000 else df

    # ── Section 1: AI-Generated Summary (Moved to Top) ───────────────────
    if groq_client:
        with st.expander("🤖 AI-Generated Data Insight & Report", expanded=True):
            with st.spinner("🧠 AI is analyzing your data to generate insights..."):
                try:
                    stats_text = _build_stats_prompt(df, numeric_cols, categorical_cols, df.isnull().sum()[df.isnull().sum() > 0])
                    response = groq_client.chat.completions.create(
                        model="llama-3.3-70b-versatile",
                        messages=[{"role": "user", "content": stats_text}],
                    )
                    st.markdown(response.choices[0].message.content)
                except Exception as e:
                    st.warning(f"⚠️ AI summary unavailable: {str(e)}")
    else:
        st.info("💡 Enter a Groq API key in the sidebar to get an AI-generated data insight report.")

    st.markdown("---")

    # ── Section 2: Dataset Overview ──────────────────────────────────────
    with st.container():
        st.markdown("### 📋 Dataset Overview")
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("🔢 Rows", f"{df.shape[0]:,}")
        col2.metric("📊 Columns", f"{df.shape[1]:,}")
        col3.metric("🔄 Duplicates", f"{df.duplicated().sum():,}")
        mem_mb = df.memory_usage(deep=True).sum() / 1024 / 1024
        col4.metric("💾 Memory", f"{mem_mb:.2f} MB")

    st.markdown("")

    # ── Section 2: Column Types ──────────────────────────────────────────
    with st.expander("📐 Column Types & Data Quality", expanded=True):
        quality_data = []
        for col in df.columns:
            missing = df[col].isnull().sum()
            unique = df[col].nunique()
            quality_data.append({
                "Column": col,
                "Type": str(df[col].dtype),
                "Non-Null": f"{df[col].notna().sum():,}",
                "Missing": f"{missing:,} ({missing / len(df) * 100:.1f}%)",
                "Unique": f"{unique:,}",
            })
        st.dataframe(
            pd.DataFrame(quality_data),
            use_container_width=True,
            hide_index=True,
        )

    # ── Section 3: Missing Values ────────────────────────────────────────
    missing_total = df.isnull().sum()
    cols_with_missing = missing_total[missing_total > 0]
    if len(cols_with_missing) > 0:
        with st.expander("🕳️ Missing Value Analysis", expanded=True):
            fig = px.bar(
                x=cols_with_missing.index,
                y=cols_with_missing.values,
                labels={"x": "Column", "y": "Missing Count"},
                title="Missing Values by Column",
                color=cols_with_missing.index,
                color_discrete_sequence=px.colors.qualitative.Set3,
            )
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#E0E0E0"),
            )
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.success("✅ No missing values detected!")

    # ── Section 4: Descriptive Statistics ────────────────────────────────
    if numeric_cols:
        with st.expander("📈 Descriptive Statistics (Numeric)", expanded=True):
            st.dataframe(
                df[numeric_cols].describe().round(2).T,
                use_container_width=True,
            )

    # ── Section 5: Distribution Analysis ─────────────────────────────────
    if numeric_cols:
        with st.expander("📊 Distribution Analysis", expanded=True):
            selected_dist_cols = numeric_cols[:3]  # Limit to 3 columns
            n_cols_per_row = min(len(selected_dist_cols), 3)
            rows = (len(selected_dist_cols) + n_cols_per_row - 1) // n_cols_per_row
            for row_idx in range(rows):
                cols = st.columns(n_cols_per_row)
                for col_idx in range(n_cols_per_row):
                    i = row_idx * n_cols_per_row + col_idx
                    if i < len(selected_dist_cols):
                        col_name = selected_dist_cols[i]
                        with cols[col_idx]:
                            fig = px.histogram(
                                plot_df, x=col_name,
                                title=f"{col_name}",
                                color=categorical_cols[0] if len(categorical_cols) > 0 and len(df[categorical_cols[0]].unique()) < 10 else None,
                                color_discrete_sequence=px.colors.qualitative.Set2,
                                marginal="box",
                            )
                            fig.update_layout(
                                template="plotly_dark",
                                paper_bgcolor="rgba(0,0,0,0)",
                                plot_bgcolor="rgba(0,0,0,0)",
                                showlegend=False,
                                height=350,
                                font=dict(size=10, color="#E0E0E0"),
                            )
                            st.plotly_chart(fig, use_container_width=True)

    # ── Section 6: Correlation Heatmap ───────────────────────────────────
    if len(numeric_cols) >= 2:
        with st.expander("🔥 Correlation Heatmap", expanded=True):
            corr_cols = numeric_cols[:15] # Limit to 15 columns to avoid massive computation and render
            corr = df[corr_cols].corr().round(2)
            fig = px.imshow(
                corr,
                text_auto=True,
                color_continuous_scale="RdBu_r",
                zmin=-1, zmax=1,
                title="Pearson Correlation Matrix",
            )
            fig.update_layout(
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                height=500,
                font=dict(color="#E0E0E0"),
            )
            st.plotly_chart(fig, use_container_width=True)

            # Highlight strong correlations
            strong = []
            for i in range(len(corr.columns)):
                for j in range(i + 1, len(corr.columns)):
                    val = corr.iloc[i, j]
                    if abs(val) > 0.7:
                        strong.append({
                            "Column 1": corr.columns[i],
                            "Column 2": corr.columns[j],
                            "Correlation": val,
                            "Strength": "🟢 Strong +" if val > 0 else "🔴 Strong −",
                        })
            if strong:
                st.markdown("**🔗 Strong Correlations (|r| > 0.7):**")
                st.dataframe(pd.DataFrame(strong), use_container_width=True, hide_index=True)

    # ── Section 7: Categorical Analysis (Bar & Pie Charts) ─────────────────────
    if categorical_cols:
        with st.expander("🏷️ Categorical Column Analysis", expanded=True):
            # Generate one Pie Chart if there is a categorical column with < 10 unique values
            pie_col = next((c for c in categorical_cols if df[c].nunique() < 10), None)
            if pie_col:
                pie_counts = df[pie_col].value_counts().reset_index()
                pie_counts.columns = [pie_col, 'Count']
                fig_pie = px.pie(
                    pie_counts, names=pie_col, values='Count',
                    title=f"Distribution of {pie_col}",
                    color_discrete_sequence=px.colors.qualitative.Set3,
                    hole=0.4
                )
                fig_pie.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#E0E0E0"),
                    height=350,
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            # Limit bar charts to 2
            selected_cat_cols = [c for c in categorical_cols if c != pie_col][:2]
            for col_name in selected_cat_cols:
                top_n = min(df[col_name].nunique(), 15)
                value_counts = df[col_name].value_counts().head(top_n)
                fig = px.bar(
                    x=value_counts.index.astype(str),
                    y=value_counts.values,
                    labels={"x": col_name, "y": "Count"},
                    title=f"Top {top_n} values in '{col_name}'",
                    color=value_counts.index.astype(str),
                    color_discrete_sequence=px.colors.qualitative.Set2,
                )
                fig.update_layout(
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#E0E0E0"),
                    height=350,
                )
                st.plotly_chart(fig, use_container_width=True)

    # ── Section 8: Trend Analysis (Line Chart) ───────────────────────────
    # Identify potential date/time columns
    date_cols = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c]) or 'date' in c.lower() or 'year' in c.lower() or 'month' in c.lower()]
    if numeric_cols:
        with st.expander("📈 Trend Analysis (Line Charts)", expanded=True):
            time_col = date_cols[0] if date_cols else (df.index.name or 'Index')
            val_cols = [c for c in numeric_cols if c != time_col][:3] # Plot up to 3 numeric series
            if val_cols:
                if date_cols:
                    df_sorted = plot_df.sort_values(by=time_col)
                    x_data = df_sorted[time_col]
                else:
                    df_sorted = plot_df
                    x_data = plot_df.index

                fig = go.Figure()
                line_colors = px.colors.qualitative.Set2
                for idx, v in enumerate(val_cols):
                    fig.add_trace(go.Scatter(x=x_data, y=df_sorted[v], mode='lines', name=v, line=dict(color=line_colors[idx % len(line_colors)])))
                fig.update_layout(
                    title=f"Trends over {time_col}",
                    xaxis_title=str(time_col),
                    template="plotly_dark",
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#E0E0E0")
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                 st.info("No numeric columns found to plot.")

    # ── Section 9: Variable Relationships (Scatter Plot) ─────────────────
    if len(numeric_cols) >= 2:
        with st.expander("🔍 Variable Relationships (Scatter Plots)", expanded=True):
            # Try to plot interesting pairs (e.g., highly correlated ones, or just the first few)
            pairs_to_plot = []
            if len(numeric_cols) >= 4:
                pairs_to_plot = [(numeric_cols[0], numeric_cols[1]), (numeric_cols[2], numeric_cols[3])]
            elif len(numeric_cols) >= 2:
                 pairs_to_plot = [(numeric_cols[0], numeric_cols[1])]
            
            n_cols = min(len(pairs_to_plot), 2)
            cols = st.columns(n_cols)
            
            for i, (col_x, col_y) in enumerate(pairs_to_plot):
                 with cols[i]:
                     fig = px.scatter(
                         plot_df, x=col_x, y=col_y,
                         title=f"{col_y} vs {col_x}",
                         opacity=0.8,
                         color=categorical_cols[0] if len(categorical_cols) > 0 and len(df[categorical_cols[0]].unique()) < 10 else None,
                         color_discrete_sequence=px.colors.qualitative.Set1
                     )
                     fig.update_layout(
                         template="plotly_dark",
                         paper_bgcolor="rgba(0,0,0,0)",
                         plot_bgcolor="rgba(0,0,0,0)",
                         font=dict(color="#E0E0E0"),
                         height=400
                     )
                     st.plotly_chart(fig, use_container_width=True)

    # ── Section 10: Outlier Detection ─────────────────────────────────────
    if numeric_cols:
        with st.expander("🚨 Outlier Detection (IQR Method)", expanded=False):
            outlier_summary = []
            for col_name in numeric_cols:
                q1 = df[col_name].quantile(0.25)
                q3 = df[col_name].quantile(0.75)
                iqr = q3 - q1
                lower = q1 - 1.5 * iqr
                upper = q3 + 1.5 * iqr
                n_outliers = int(((df[col_name] < lower) | (df[col_name] > upper)).sum())
                if n_outliers > 0:
                    outlier_summary.append({
                        "Column": col_name,
                        "Outliers": n_outliers,
                        "% of Data": f"{n_outliers / len(df) * 100:.1f}%",
                        "Lower Bound": round(lower, 2),
                        "Upper Bound": round(upper, 2),
                    })
            if outlier_summary:
                st.dataframe(pd.DataFrame(outlier_summary), use_container_width=True, hide_index=True)
                # Box plots for columns with outliers
                outlier_cols = [o["Column"] for o in outlier_summary[:6]]
                if outlier_cols:
                    fig = px.box(
                        plot_df[outlier_cols].melt(),
                        x="variable", y="value",
                        color="variable",
                        title="Box Plots — Columns with Outliers",
                        color_discrete_sequence=px.colors.qualitative.Set2,
                    )
                    fig.update_layout(
                        template="plotly_dark",
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)",
                        showlegend=False,
                        font=dict(color="#E0E0E0"),
                    )
                    st.plotly_chart(fig, use_container_width=True)
            else:
                st.success("✅ No significant outliers detected!")
    st.markdown('</div>', unsafe_allow_html=True)


def _build_stats_prompt(df, numeric_cols, categorical_cols, cols_with_missing):
    """Build a concise prompt for the AI to summarise the dataset."""
    prompt = (
        "You are a senior data analyst. Provide a clear, insightful, and actionable summary "
        "of the following dataset in **markdown** format. Include:\n"
        "1. A brief overview of what the dataset appears to contain\n"
        "2. Key statistical findings and patterns\n"
        "3. Data quality observations\n"
        "4. Potential next steps for analysis\n\n"
        f"**Dataset shape:** {df.shape[0]} rows × {df.shape[1]} columns\n\n"
    )

    if numeric_cols:
        prompt += f"**Numeric columns:** {', '.join(numeric_cols)}\n"
        prompt += f"**Numeric stats:**\n{df[numeric_cols].describe().round(2).to_string()}\n\n"

    if categorical_cols:
        prompt += f"**Categorical columns:** {', '.join(categorical_cols)}\n"
        for col in categorical_cols[:5]:
            top = df[col].value_counts().head(5)
            prompt += f"  - {col}: {dict(top)}\n"
        prompt += "\n"

    if len(cols_with_missing) > 0:
        prompt += f"**Missing values:** {dict(cols_with_missing)}\n\n"
    else:
        prompt += "**Missing values:** None\n\n"

    if len(numeric_cols) >= 2:
        corr = df[numeric_cols].corr()
        strong_pairs = []
        for i in range(len(corr.columns)):
            for j in range(i + 1, len(corr.columns)):
                val = corr.iloc[i, j]
                if abs(val) > 0.5:
                    strong_pairs.append(f"{corr.columns[i]} ↔ {corr.columns[j]}: {val:.2f}")
        if strong_pairs:
            prompt += f"**Notable correlations:**\n" + "\n".join(f"  - {p}" for p in strong_pairs) + "\n"

    return prompt
