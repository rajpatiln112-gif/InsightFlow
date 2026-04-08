"""
Data Cleaning Module
Provides a UI for handling missing values, duplicates, and data type conversions.
"""
import streamlit as st
import pandas as pd
from modules.ai_chat import render_cleaning_chat

def render_data_cleaning(df):
    st.markdown("## 🧪 Data Cleaning")
    st.markdown("Structural optimization and fluid data refinement.")
    st.markdown("---")
    st.markdown('<div class="premium-card">', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Rows", df.shape[0])
    with col2:
        st.metric("Total Columns", df.shape[1])
    with col3:
        st.metric("Missing Values", df.isna().sum().sum())

    st.markdown("### 1. Handle Missing Values")
    missing_cols = df.columns[df.isna().any()].tolist()
    
    if missing_cols:
        st.info(f"Columns with missing values: {', '.join(missing_cols)}")
        
        with st.expander("🔍 Filter and Analyze Missing Values", expanded=False):
            filter_col = st.selectbox("Select column to filter nulls:", ["Any Column (All Missing)"] + missing_cols)
            if filter_col == "Any Column (All Missing)":
                null_df = df[df.isnull().any(axis=1)]
                st.caption(f"Showing **{len(null_df)}** rows containing at least one missing value across the entire matrix:")
            else:
                null_df = df[df[filter_col].isnull()]
                st.caption(f"Showing **{len(null_df)}** rows where `{filter_col}` specifically is missing:")
            st.dataframe(null_df, use_container_width=True)
        
        # ── Handle Missing Values ──
        null_count = df.isnull().sum().sum()
        
        if null_count >= 10:
            st.warning(f"⚠️ **HIGH VOLUME OF MISSING DATA**: {null_count} missing values detected.")
            with st.expander("👀 View Missing Value Previews & Locations", expanded=False):
                st.markdown("**Preview of Rows with Missing Values:**")
                st.dataframe(df[df.isnull().any(axis=1)].head(50), use_container_width=True)
                
                st.markdown("**Missing Locations by Column:**")
                loc_data = []
                for col in missing_cols:
                    n_idx = df[df[col].isnull()].index.tolist()
                    if n_idx:
                        sample_idx = str(n_idx[:20]) + ("..." if len(n_idx) > 20 else "")
                        loc_data.append({"Column": col, "Missing Count": len(n_idx), "Row Indices": sample_idx})
                st.dataframe(pd.DataFrame(loc_data), use_container_width=True)
        else:
            with st.expander("🛠️ Manual Data Repair (Row-by-Row)", expanded=True):
                st.caption(f"Carefully review and replace the {null_count} missing values manually.")
                new_df = df.copy()
                
                null_mask = df.isnull()
                null_indices = []
                for col in df.columns:
                    rows = df.index[null_mask[col]].tolist()
                    for r in rows:
                        null_indices.append((r, col))
                
                with st.form("manual_fixer_form"):
                    for r, col in null_indices:
                        val = st.text_input(f"Row {r + 1} | Column: {col} (Current: NULL)", key=f"manual_null_{r}_{col}")
                        if val:
                            orig_dtype = df[col].dtype
                            try:
                                if pd.api.types.is_numeric_dtype(orig_dtype):
                                    new_df.at[r, col] = float(val) if '.' in val else int(val)
                                else:
                                    new_df.at[r, col] = val
                            except:
                                new_df.at[r, col] = val
                    
                    if st.form_submit_button("🔨 Apply Manual Repairs"):
                        if new_df.isnull().sum().sum() >= null_count:
                            st.error("No values were filled.")
                        else:
                            st.session_state.df = new_df
                            st.success("Manual repairs applied successfully!")
                            st.rerun()
        # ──────────────────────────────
        
        st.markdown("**Or use Bulk Cleaning:**")
        col_to_clean = st.selectbox("Select column to clean:", missing_cols)
        clean_method = st.radio("Choose method:", 
                                ["Drop rows with missing values", 
                                 "Fill with Mean", 
                                 "Fill with Median", 
                                 "Fill with Mode",
                                 "Fill with Custom Value"])
        
        custom_val = ""
        if clean_method == "Fill with Custom Value":
            custom_val = st.text_input("Enter custom value:")
            
        if st.button("Apply Cleaning"):
            try:
                if clean_method == "Drop rows with missing values":
                    st.session_state.df = df.dropna(subset=[col_to_clean])
                elif clean_method == "Fill with Mean":
                    st.session_state.df[col_to_clean] = df[col_to_clean].fillna(df[col_to_clean].mean())
                elif clean_method == "Fill with Median":
                    st.session_state.df[col_to_clean] = df[col_to_clean].fillna(df[col_to_clean].median())
                elif clean_method == "Fill with Mode":
                    st.session_state.df[col_to_clean] = df[col_to_clean].fillna(df[col_to_clean].mode()[0])
                elif clean_method == "Fill with Custom Value":
                    st.session_state.df[col_to_clean] = df[col_to_clean].fillna(custom_val)
                st.success(f"Applied {clean_method} to {col_to_clean}!")
                st.rerun()
            except Exception as e:
                st.error(f"Error applying cleaning method: {e}. Note: Mean/Median only work on numeric columns.")
    else:
        st.success("No missing values found in the dataset!")

    st.markdown("### 2. Handle Duplicates")
    duplicate_count = df.duplicated().sum()
    st.write(f"Found **{duplicate_count}** duplicate rows.")
    
    if duplicate_count > 0:
        if st.button("Remove Duplicates"):
            st.session_state.df = df.drop_duplicates()
            st.success("Duplicate rows removed!")
            st.rerun()

    st.markdown("### 3. Data Type Conversion")
    col_to_convert = st.selectbox("Select column for type conversion:", df.columns)
    current_type = df[col_to_convert].dtype
    st.write(f"Current type: `{current_type}`")
    
    new_type = st.selectbox("Convert to:", ["string", "numeric", "date", "time", "currency", "character"])
    
    if st.button("Convert Type"):
        try:
            if new_type == "string":
                st.session_state.df[col_to_convert] = df[col_to_convert].astype(str)
            elif new_type == "character":
                # Convert to string and take the first character if exists
                st.session_state.df[col_to_convert] = df[col_to_convert].astype(str).str[0]
            elif new_type == "numeric":
                st.session_state.df[col_to_convert] = pd.to_numeric(df[col_to_convert], errors='coerce')
            elif new_type == "date":
                st.session_state.df[col_to_convert] = pd.to_datetime(df[col_to_convert], errors='coerce').dt.date
            elif new_type == "time":
                st.session_state.df[col_to_convert] = pd.to_datetime(df[col_to_convert], errors='coerce').dt.time
            elif new_type == "currency":
                # Strip currency symbols and commas, then convert to numeric
                clean_col = df[col_to_convert].astype(str).str.replace(r'[^\d.-]', '', regex=True)
                st.session_state.df[col_to_convert] = pd.to_numeric(clean_col, errors='coerce')
            st.success(f"Successfully converted {col_to_convert} to {new_type}!")
            st.rerun()
        except Exception as e:
            st.error(f"Conversion failed: {e}")

    st.markdown("### 5 Columns and Rows")
    st.dataframe(df.head(5))
    st.markdown('</div>', unsafe_allow_html=True)

    # Render AI Cleaning Chat
    render_cleaning_chat(df, st.session_state.groq_client)
