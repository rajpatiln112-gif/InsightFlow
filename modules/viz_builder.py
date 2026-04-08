"""
Visualization Builder Module
Interactive chart builder using Plotly.
"""
import streamlit as st
import plotly.express as px
import pandas as pd
from chart_service import log_chart_creation, get_chart_history


CHART_TYPES = {
    "📊 Bar Chart": "bar",
    "📈 Line Chart": "line",
    "🔵 Scatter Plot": "scatter",
    "📉 Histogram": "histogram",
    "📦 Box Plot": "box",
    "🥧 Pie Chart": "pie",
    "🫧 Bubble Chart": "bubble",
    "🔥 Heatmap": "heatmap",
    "🎻 Violin Plot": "violin",
}

COLOR_SCALES = [
    "Viridis", "Plasma", "Inferno", "Magma", "Cividis",
    "Blues", "Reds", "Greens", "Purples", "Turbo",
    "Sunset", "Teal", "Peach",
]


def render_viz_builder(df):
    """Render the structured 3-step visualization workflow."""

    st.markdown("## 📊 Visualization")
    st.markdown("Precision visualization architecture. Flow-based chart construction.")
    st.markdown("---")

    # Initialize sub-step in session state
    if "viz_step" not in st.session_state:
        st.session_state.viz_step = "Step 1: Select Best Chart"
    if "dashboard_charts" not in st.session_state:
        st.session_state.dashboard_charts = []

    # Navigation Buttons (Progress Bar)
    cols = st.columns(3)
    steps = ["Step 1: Select Best Chart", "Step 2: Create Clean Chart", "Step 3: Show Dashboard"]
    for i, step in enumerate(steps):
        is_active = st.session_state.viz_step == step
        if cols[i].button(step, use_container_width=True, type="primary" if is_active else "secondary"):
            st.session_state.viz_step = step
            st.rerun()

    st.markdown("")

    # ── STEP 1: SELECT BEST CHART ──────────────────────────────────────
    if st.session_state.viz_step == steps[0]:
        st.markdown('<div class="premium-card">', unsafe_allow_html=True)
        st.markdown("### 🎯 Step 1: Intelligent Chart Suggestion")
        st.write("Our system analyzes your data context to suggest the most impactful visualization.")
        
        numeric_cols = list(df.select_dtypes(include=["number"]).columns)
        categorical_cols = list(df.select_dtypes(include=["object", "category"]).columns)
        all_cols = list(df.columns)

        col1, col2 = st.columns([1, 2])
        with col1:
            if st.button("✨ AUTO-DETECT TRENDS", use_container_width=True, type="primary"):
                # Heuristics for "Best Chart"
                suggestion = {"type": "Bar Chart", "x": all_cols[0], "y": None}
                
                if len(numeric_cols) >= 2:
                    suggestion = {"type": "Scatter Plot", "x": numeric_cols[0], "y": numeric_cols[1]}
                elif len(categorical_cols) > 0 and len(numeric_cols) > 0:
                    suggestion = {"type": "Bar Chart", "x": categorical_cols[0], "y": numeric_cols[0]}
                elif len(numeric_cols) == 1:
                    suggestion = {"type": "Histogram", "x": numeric_cols[0], "y": None}
                
                st.session_state["_smart_chart"] = suggestion
                st.success(f"Suggested: **{suggestion['type']}** using `{suggestion['x']}`")

        if "_smart_chart" in st.session_state:
            sc = st.session_state["_smart_chart"]
            st.info(f"Recommended Configuration: {sc['type']} | X: {sc['x']} | Y: {sc['y'] or 'Count'}")
            if st.button("Proceed to Customization ➔", use_container_width=True):
                st.session_state.viz_step = steps[1]
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── STEP 2: CREATE CLEAN CHART ─────────────────────────────────────
    elif st.session_state.viz_step == steps[1]:
        st.markdown('<div class="premium-card">', unsafe_allow_html=True)
        st.markdown("### 🎨 Step 2: Create Clean Chart (Plotly)")
        
        # Load suggested values if they exist
        sc = st.session_state.get("_smart_chart", {"type": "Bar Chart", "x": df.columns[0], "y": None})
        
        numeric_cols = list(df.select_dtypes(include=["number"]).columns)
        all_cols = list(df.columns)

        colA, colB = st.columns(2)
        with colA:
            chart_label = st.selectbox("🎨 Chart Type", list(CHART_TYPES.keys()), index=list(CHART_TYPES.keys()).index(next(k for k in CHART_TYPES if sc["type"] in k)))
            x_col = st.selectbox("X Axis", all_cols, index=all_cols.index(sc["x"]) if sc["x"] in all_cols else 0)
        with colB:
            color_scale = st.selectbox("🌈 Color Scale", COLOR_SCALES)
            y_col = st.selectbox("Y Axis (optional)", [None] + numeric_cols, index=([None] + numeric_cols).index(sc["y"]) if sc["y"] in [None] + numeric_cols else 0)

        title = st.text_input("📝 Chart Title", value=f"{chart_label}")
        
        if st.button("🚀 GENERATE & PREVIEW", type="primary", use_container_width=True):
            chart_type = CHART_TYPES[chart_label]
            fig = _create_chart(df, chart_type, x_col, y_col, None, title, 500, color_scale, None)
            if fig:
                st.session_state["_last_fig"] = fig
                st.plotly_chart(fig, use_container_width=True)
                # Log chart creation
                log_chart_creation(chart_label)

        if "_last_fig" in st.session_state:
            if st.button("📥 SAVE TO DASHBOARD", use_container_width=True):
                st.session_state.dashboard_charts.append(st.session_state["_last_fig"])
                st.success("Synchronized with Dashboard Core")
                # Clear preview and move to dashboard
                st.session_state.viz_step = steps[2]
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    # ── STEP 3: SHOW DASHBOARD ─────────────────────────────────────────
    elif st.session_state.viz_step == steps[2]:
        st.markdown('<div class="premium-card">', unsafe_allow_html=True)
        st.markdown("### 🏢 Step 3: Global Dashboard")
        
        if not st.session_state.dashboard_charts:
            st.info("The dashboard is currently empty. Initialize visualizations in Step 2 to populate the grid.")
        else:
            if st.button("🗑️ Reset Dashboard", use_container_width=True):
                st.session_state.dashboard_charts = []
                st.rerun()

            # Render charts in a grid
            for i, fig in enumerate(st.session_state.dashboard_charts):
                st.markdown(f"#### 📊 Perspective {i+1}")
                st.plotly_chart(fig, use_container_width=True)
                st.markdown("---")
        st.markdown('</div>', unsafe_allow_html=True)
        
    # Show Chart History in Sidebar
    with st.sidebar:
        st.markdown("---")
        st.markdown("### 📜 My Chart History")
        history = get_chart_history()
        if history:
            for item in history:
                st.markdown(f"- **{item['chart_type']}**: {item['count']}")
        else:
            st.info("No charts created yet.")


def _create_chart(df, chart_type, x_col, y_col, color_col, title, height, color_scale, anim_col):
    """Create a Plotly figure based on the selected options."""
    # Downsample for intensive Plotly charts to prevent browser lockup
    plot_df = df.sample(n=1000, random_state=42) if len(df) > 1000 else df

    common = dict(
        title=title,
        color_discrete_sequence=px.colors.qualitative.Set2,
    )
    layout = dict(
        template="plotly_dark",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        height=height,
        font=dict(color="#E0E0E0"),
    )

    fig = None
    color_arg = color_col if color_col else None
    anim_arg = anim_col if anim_col else None

    if chart_type == "bar":
        fig = px.bar(plot_df, x=x_col, y=y_col, color=color_arg, animation_frame=anim_arg, **common)
    elif chart_type == "line":
        fig = px.line(plot_df, x=x_col, y=y_col, color=color_arg, animation_frame=anim_arg, **common)
    elif chart_type == "scatter":
        fig = px.scatter(plot_df, x=x_col, y=y_col, color=color_arg, animation_frame=anim_arg, **common)
    elif chart_type == "histogram":
        fig = px.histogram(plot_df, x=x_col, y=y_col, color=color_arg, marginal="box", **common)
    elif chart_type == "box":
        fig = px.box(plot_df, x=x_col, y=y_col, color=color_arg, **common)
    elif chart_type == "pie":
        pie_common = common.copy()
        pie_common["color_discrete_sequence"] = getattr(px.colors.sequential, color_scale, px.colors.sequential.Viridis)
        fig = px.pie(plot_df, names=x_col, values=y_col, **pie_common)
    elif chart_type == "bubble":
        size_col = y_col if y_col else None
        fig = px.scatter(plot_df, x=x_col, y=y_col, size=size_col, color=color_arg, **common)
    elif chart_type == "heatmap":
        if y_col:
            pivot = plot_df.pivot_table(values=y_col, index=x_col, aggfunc="mean")
            fig = px.imshow(pivot, color_continuous_scale=color_scale, **common)
    elif chart_type == "violin":
        fig = px.violin(plot_df, x=x_col, y=y_col, color=color_arg, box=True, **common)

    if fig:
        fig.update_layout(**layout)

    return fig
