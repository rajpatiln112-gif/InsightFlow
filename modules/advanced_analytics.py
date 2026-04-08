"""
Advanced Analytics Module
Contains Predictive Analysis and Business Recommendation Engine.
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error, r2_score

def render_advanced_analytics(df, groq_client):
    st.markdown("## 🔮 Advanced Analytics Studio")
    st.markdown("Leverage Machine Learning and AI to forecast trends and get actionable business recommendations.")
    st.markdown("---")
    st.markdown('<div class="premium-card">', unsafe_allow_html=True)
    
    tab1, tab2 = st.tabs(["📈 Predictive Analysis", "💼 Business Recommendations"])
    
    # ── TAB 1: Predictive Analysis ──────────────────────────────────────────
    with tab1:
        st.markdown("### Simple Linear Regression / Forecasting")
        st.write("Predict a target numerical value based on another numerical feature.")
        
        numeric_cols = list(df.select_dtypes(include=["number"]).columns)
        
        if len(numeric_cols) < 2:
            st.warning("⚠️ Predictive analysis requires at least two numeric columns in the dataset.")
        else:
            col_pred1, col_pred2 = st.columns(2)
            with col_pred1:
                target_col = st.selectbox("Select Target Variable (What to predict?)", numeric_cols, index=len(numeric_cols)-1)
            with col_pred2:
                feature_col = st.selectbox("Select Feature Variable (Based on what?)", [c for c in numeric_cols if c != target_col])
                
            if st.button("🚀 Run Prediction Model", type="primary"):
                try:
                    # Clean data for model
                    categorical_cols = list(df.select_dtypes(include=["object", "category"]).columns)
                    color_col = categorical_cols[0] if categorical_cols and len(df[categorical_cols[0]].unique()) < 10 else None
                    cols_to_keep = [feature_col, target_col]
                    if color_col: cols_to_keep.append(color_col)

                    clean_df = df[cols_to_keep].dropna(subset=[feature_col, target_col])
                    
                    if len(clean_df) < 10:
                        st.error("Not enough valid data points (need at least 10 non-null rows).")
                    else:
                        X = clean_df[[feature_col]]
                        y = clean_df[target_col]
                        
                        # Split and Train
                        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
                        model = LinearRegression()
                        model.fit(X_train, y_train)
                        
                        # Predict
                        y_pred = model.predict(X_test)
                        r2 = r2_score(y_test, y_pred)
                        rmse = np.sqrt(mean_squared_error(y_test, y_pred))
                        
                        # Display Metrics
                        m1, m2, m3 = st.columns(3)
                        m1.metric("Model Accuracy (R² Score)", f"{r2:.2f}")
                        m2.metric("Root Mean Squared Error", f"{rmse:.2f}")
                        m3.metric("Trend (Coefficient)", f"{model.coef_[0]:.4f}")
                        
                        # Plot
                        st.markdown("#### Actual vs Predicted")
                        fig = px.scatter(clean_df, x=feature_col, y=target_col, color=color_col, color_discrete_sequence=px.colors.qualitative.Set2, opacity=0.8, title=f"{target_col} vs {feature_col}")
                        
                        # Add regression line
                        line_x = np.linspace(X.min(), X.max(), 100).reshape(-1, 1)
                        line_y = model.predict(line_x)
                        fig.add_scatter(x=line_x.flatten(), y=line_y, mode='lines', name='Prediction Trend', line=dict(color='#F43F5E', width=3, dash='dash'))
                        
                        fig.update_layout(template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", font=dict(color="#E0E0E0"))
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Future Prediction Simulator
                        st.markdown("#### 🔮 Simulation Engine")
                        sim_val = st.number_input(f"If {feature_col} is:", value=float(X.mean().iloc[0]))
                        pred_val = model.predict([[sim_val]])[0]
                        st.success(f"**Predicted {target_col}:** {pred_val:.2f}")
                        
                except Exception as e:
                    st.error(f"Error running model: {e}")

    # ── TAB 2: Business Recommendations ─────────────────────────────────────
    with tab2:
        st.markdown("### AI Strategic Advisor")
        st.write("Get concrete business strategies based on your dataset's statistical profile.")
        
        if not groq_client:
            st.warning("⚠️ Please provide a Groq API Key in the sidebar to use the Recommendation Engine.")
        else:
            focus_area = st.selectbox(
                "Select area of focus:",
                ["Revenue Growth & Sales", "Cost Reduction & Efficiency", "Risk Management", "Customer Retention", "General Strategy"]
            )
            
            if st.button("💡 Generate Strategic Recommendations", type="primary"):
                with st.spinner(f"Analyzing data for {focus_area} strategies..."):
                    try:
                        # Quick data summary for prompt
                        num_stats = df.describe().round(2).to_string()
                        
                        prompt = (
                            f"You are a top-tier Management Consultant (like McKinsey/Bain). Act as an advisor focusing on '{focus_area}'.\n\n"
                            "Based strictly on the following statistical summary of the business's dataset, provide 3 highly concrete, actionable "
                            "business recommendations. For each recommendation, explain the data-driven rationale.\n\n"
                            f"**Data Profile:**\nRow count: {len(df)}\n"
                            f"**Numeric Statistics:**\n{num_stats}\n\n"
                            "Format your response in clean Markdown with headers and bullet points. Be specific, not generic."
                        )
                        
                        response = groq_client.chat.completions.create(
                            model="llama-3.3-70b-versatile",
                            messages=[{"role": "user", "content": prompt}],
                        )
                        st.markdown(response.choices[0].message.content)
                    except Exception as e:
                        st.error(f"Error generating recommendations: {e}")
    st.markdown('</div>', unsafe_allow_html=True)
