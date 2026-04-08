import streamlit as st
import pandas as pd
from chart_service import get_all_users_chart_history

def render_admin_dashboard():
    st.markdown("## 🛡️ Admin Dashboard")
    st.markdown("Monitor chart generation history across all users on the platform.")
    st.markdown("---")

    if st.session_state.username != "admin":
        st.error("Unauthorized access.")
        return

    with st.spinner("Fetching global chart history..."):
        history_data = get_all_users_chart_history()

    if not history_data:
        st.info("No chart history found across the system.")
        return

    st.markdown("### System-Wide Chart Analytics")

    df = pd.DataFrame(history_data)
    
    # We want to display username, chart_type, and count nicely.
    # We can pivot or just sort and display.
    # Grouping by username
    
    for user, group in df.groupby("username"):
        with st.expander(f"👤 User: {user}", expanded=True):
            col1, col2 = st.columns(2)
            with col1:
                # Format a small dataframe or table just for this user
                st.dataframe(group[["chart_type", "count"]].rename(columns={"chart_type": "Chart Type", "count": "Generated Count"}), hide_index=True)
            with col2:
                total_charts = int(group["count"].sum())
                st.metric(label="Total Charts Generated", value=total_charts)

