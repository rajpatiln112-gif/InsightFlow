"""
AI Chat Module
Handles natural-language querying of data via Groq.
Now with Firestore chat persistence.
"""
import streamlit as st
import pandas as pd
import traceback
import re
import uuid
import speech_recognition as sr
from modules.data_handler import get_schema_string
from query_service import save_query, get_queries


def render_chat(df, groq_client, uid="guest", dataset_name="Unknown"):
    """Render the AI chat interface with optional Firestore persistence."""

    st.markdown('<div class="premium-card">', unsafe_allow_html=True)
    st.markdown("## 💬 AI Assistant")
    st.markdown("Engage with the fluid intelligence core to extract high-precision insights from your data stream.")
    st.markdown("---")

    # Initialize chat history & session
    if "chat_history" not in st.session_state:
        st.session_state.chat_history = []
    if "chat_session_id" not in st.session_state:
        st.session_state.chat_session_id = str(uuid.uuid4())[:8]

    # ── Sidebar: Saved Chat Sessions ─────────────────────────────────
    _render_chat_sidebar(uid)

    # Display chat history
    for msg in st.session_state.chat_history:
        avatar = "👤" if msg["role"] == "user" else "💧"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])
            # Auto-render charts from history if code exists
            if msg["role"] == "assistant":
                code_blocks = _extract_code_blocks(msg["content"])
                if code_blocks:
                    for i, code in enumerate(code_blocks):
                        with st.expander(f"🐍 View Generated Code", expanded=False):
                            st.code(code, language="python")
                        _safe_execute(code, df)





    # Sidebar quick actions
    with st.sidebar:
        st.markdown("### 💡 Example Questions")
        example_questions = [
            "Summarize this dataset in 3 sentences",
            "What are the top 5 trends in this data?",
            "Are there any anomalies or outliers?",
            "What columns are most correlated?",
            "Suggest a machine learning model for this data",
            "Write Python code to clean this dataset",
        ]
        for q in example_questions:
            if st.button(f"📌 {q}", key=f"example_{q[:20]}"):
                st.session_state["_prefill_question"] = q
                st.rerun()

    # Handle prefill
    if "_prefill_question" in st.session_state:
        prefill = st.session_state.pop("_prefill_question")
        st.session_state.chat_history.append({"role": "user", "content": prefill})
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(prefill)
        with st.chat_message("assistant", avatar="🤖"):
            with st.spinner("🧠 Thinking..."):
                response_text = _get_ai_response(df, groq_client, prefill)
                st.markdown(response_text)
                
                # Auto-execute any code blocks
                code_blocks = _extract_code_blocks(response_text)
                if code_blocks:
                    for i, code in enumerate(code_blocks):
                        with st.expander(f"🐍 View Generated Code", expanded=False):
                            st.code(code, language="python")
                        _safe_execute(code, df)
                        
        st.session_state.chat_history.append({"role": "assistant", "content": response_text})
        _auto_save_chat(uid, dataset_name)
        
    # Chat input & Voice Input (Rendered at the bottom)
    user_input = st.chat_input("Ask anything about your data... (e.g., 'What's the average salary by department?')")
    
    col_voice, _ = st.columns([1, 4])
    with col_voice:
        if st.button("🎤 Use Voice to Ask", help="Click and speak your question"):
            with st.spinner("Listening..."):
                r = sr.Recognizer()
                with sr.Microphone() as source:
                    try:
                        audio = r.listen(source, timeout=5, phrase_time_limit=10)
                        voice_text = r.recognize_google(audio)
                        st.session_state["_voice_query"] = voice_text
                        st.rerun()
                    except sr.WaitTimeoutError:
                        st.error("No speech detected. Try again.")
                    except sr.UnknownValueError:
                        st.error("Could not understand the audio.")
                    except Exception as e:
                        st.error(f"Speech recognition error: {e}")

    # Process voice query if captured
    if "_voice_query" in st.session_state:
        user_input = st.session_state.pop("_voice_query")
        
    if user_input:
        # Display user message
        st.session_state.chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(user_input)

        # Generate AI response
        with st.chat_message("assistant", avatar="💧"):
            with st.spinner("⏳ Filtering Data..."):
                response_text = _get_ai_response(df, groq_client, user_input)
                st.markdown(response_text)

                # Check if response contains executable Python code
                code_blocks = _extract_code_blocks(response_text)
                if code_blocks:
                    for i, code in enumerate(code_blocks):
                        with st.expander(f"🐍 View Generated Code", expanded=False):
                            st.code(code, language="python")
                        # Auto-execute immediately
                        _safe_execute(code, df)

        st.session_state.chat_history.append({"role": "assistant", "content": response_text})

        # Auto-save to Firestore
        _auto_save_chat(uid, dataset_name)
        st.rerun()

    # Clear chat / New session buttons
    if st.session_state.chat_history:
        st.markdown("---")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🗑️ Clear Chat", use_container_width=True):
                st.session_state.chat_history = []
                st.session_state.chat_session_id = str(uuid.uuid4())[:8]
                st.rerun()
        with col2:
            if st.button("➕ New Chat", use_container_width=True):
                _auto_save_chat(uid, dataset_name)
                st.session_state.chat_history = []
                st.session_state.chat_session_id = str(uuid.uuid4())[:8]
                st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)


def _render_chat_sidebar(uid):
    """Render saved chat sessions in the sidebar."""
    if uid == "guest":
        return

    try:
        from modules.firestore_ops import load_chats, load_chat_messages, delete_chat
    except ImportError:
        return

    with st.sidebar:
        st.markdown("### 📂 Saved Chats")
        saved_chats = load_chats(uid)
        if saved_chats:
            for chat in saved_chats[:10]:
                session_id = chat.get("session_id", "")
                dataset = chat.get("dataset_name", "Unknown")
                msg_count = chat.get("message_count", 0)
                label = f"📄 {dataset} ({msg_count} msgs)"

                col_btn, col_del = st.columns([4, 1])
                with col_btn:
                    if st.button(label, key=f"load_{session_id}", use_container_width=True):
                        messages = load_chat_messages(uid, session_id)
                        st.session_state.chat_history = messages
                        st.session_state.chat_session_id = session_id
                        st.rerun()
                with col_del:
                    if st.button("🗑️", key=f"del_{session_id}"):
                        delete_chat(uid, session_id)
                        st.rerun()
        else:
            st.caption("No saved chats yet.")
        st.markdown("---")


def _auto_save_chat(uid, dataset_name):
    """Auto-save current chat to SQLite if user is logged in."""
    if uid == "guest" or not st.session_state.chat_history:
        return
    
    # Save the last message pair if possible
    last_user_msg = ""
    last_assistant_msg = ""
    for msg in reversed(st.session_state.chat_history):
        if msg["role"] == "user" and not last_user_msg:
            last_user_msg = msg["content"]
        if msg["role"] == "assistant" and not last_assistant_msg:
            last_assistant_msg = msg["content"]
        if last_user_msg and last_assistant_msg:
            break
            
    if last_user_msg:
        save_query(last_user_msg, last_assistant_msg)


def _get_ai_response(df, groq_client, question):
    """Send question + data context to Groq and return the response."""
    try:
        schema = get_schema_string(df)
        prompt = (
            "You are an expert data analyst assistant. You have access to a dataset with the "
            "following schema and sample data. Answer the user's question thoroughly.\n\n"
            "If the question requires computation or charting, write Python/Pandas code that the user can run. "
            "Wrap code in ```python code blocks.\n\n"
            "**CRITICAL - DATAFRAME `df`:**\n"
            "The data is ALREADY LOADED for you in a pandas dataframe variable specifically named `df`.\n"
            "**DO NOT** write code to load data (e.g., NO `pd.read_csv()`). ALWAYS use the existing `df` variable.\n\n"
            "**CRITICAL - CHARTS AND PLOTS:**\n"
            "If building a chart/plot, ALWAYS use Plotly (`import plotly.express as px` or `import plotly.graph_objects as go`).\n"
            "**DO NOT** use Matplotlib or Seaborn. Strictly use Plotly.\n"
            "Assign the final Plotly figure to a variable named EXACTLY `fig` (e.g. `fig = px.bar(...)`).\n"
            "DO NOT call `fig.show()`, the UI will handle rendering the Plotly `fig` variable automatically.\n"
            "**If you generate a chart code block, you MUST also provide a brief 1-2 sentence explanation of what the chart shows and any key insights from it.**\n\n"
            "If the question is analytical, provide insights directly based on the data statistics.\n\n"
            "Always be specific — reference actual column names, values, and statistics.\n\n"
            f"=== DATASET INFO ===\n{schema}\n\n"
            f"=== USER QUESTION ===\n{question}\n"
        )

        # Include conversation context (last 4 exchanges)
        history_context = ""
        recent = st.session_state.get("chat_history", [])[-8:]
        if recent:
            history_context = "\n=== RECENT CONVERSATION ===\n"
            for msg in recent:
                role = "User" if msg["role"] == "user" else "Assistant"
                history_context += f"{role}: {msg['content'][:300]}\n"
            prompt = prompt + history_context

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Error generating response: {str(e)}"


def _extract_code_blocks(text):
    """Extract Python code blocks from markdown text."""
    pattern = r"```python\s*\n(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL)
    return matches


def _safe_execute(code, df):
    """Safely execute Python code with the DataFrame in scope and render charts if generated."""
    try:
        # Pre-import common viz libraries to make AI code more robust
        import plotly.express as px
        import plotly.graph_objects as go
        import numpy as np

        exec_globals = {
            "pd": pd,
            "np": np,
            "df": df.copy(),
            "st": st,
            "px": px,
            "go": go,
            "__builtins__": {
                "__import__": __import__,
                "print": print,
                "len": len,
                "range": range,
                "int": int,
                "float": float,
                "str": str,
                "list": list,
                "dict": dict,
                "tuple": tuple,
                "set": set,
                "sorted": sorted,
                "min": min,
                "max": max,
                "sum": sum,
                "abs": abs,
                "round": round,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "isinstance": isinstance,
                "type": type,
                "True": True,
                "False": False,
                "None": None,
            },
        }
        import io
        import sys
        old_stdout = sys.stdout
        sys.stdout = buffer = io.StringIO()
        exec(code, exec_globals)
        sys.stdout = old_stdout
        output = buffer.getvalue()
        
        # Display printed text
        if output:
            st.code(output)
            
        # Display result variable if present
        if "result" in exec_globals:
            res = exec_globals["result"]
            if isinstance(res, pd.DataFrame):
                st.dataframe(res, use_container_width=True)
            else:
                st.write(res)
                
        # Display charts if 'fig' variable is present
        if "fig" in exec_globals:
            raw_fig = exec_globals["fig"]
            
            # Helper to render a single Plotly chart
            def _render_single_fig(f):
                if hasattr(f, "to_dict") and "layout" in dir(f):
                    st.plotly_chart(f, use_container_width=True)
                else:
                    st.write("Generated Object (Plotly expected):", f)
            
            # Handle if the AI returns a list/tuple of figures
            if isinstance(raw_fig, (list, tuple)):
                for f in raw_fig:
                    _render_single_fig(f)
            else:
                _render_single_fig(raw_fig)
                
        st.success("✅ Code executed successfully!")
    except Exception as e:
        import sys
        if hasattr(sys, 'stdout') and isinstance(sys.stdout, io.StringIO):
             sys.stdout = sys.__stdout__
        st.error(f"❌ Execution error: {str(e)}")
        st.code(traceback.format_exc())

# ── Query History Component ───────────────────────────────────────────
def render_query_history():
    st.markdown("---")
    with st.expander("🕰️ View Query History"):
        history = get_queries()
        if history:
            for q in history:
                st.markdown(f"**Question:** {q['question']}")
                st.markdown(f"**Answer/Code Snippet:**")
                st.code(q['sql_query'][:500] + ("..." if len(q['sql_query']) > 500 else ""), language="python")
                st.caption(f"Created: {q['created_at']}")
                st.markdown("---")
        elif "chat_history" in st.session_state and len(st.session_state.chat_history) > 0:
            st.info("No persistent history yet. Saving session queries...")
            for idx, msg in enumerate(st.session_state.chat_history):
                if msg["role"] == "user":
                    st.markdown(f"**You:** {msg['content']}")
                else:
                    st.markdown(f"**AI:** {msg['content'][:200]}...")
        else:
            st.info("No queries found in history.")


# ══════════════════════════════════════════════════════════════════════
#   AI CLEANING CHAT  — embedded inside the Data Cleaning page
# ══════════════════════════════════════════════════════════════════════

def render_cleaning_chat(df, groq_client):
    """AI assistant embedded in the Data Cleaning page.
    The AI suggests cleaning operations and the executor applies them
    directly to st.session_state.df so the live DataFrame is updated.
    """

    st.markdown("---")
    st.markdown("### 🧬 Data Cleaning")
    st.markdown(
        "Describe your structural optimization naturally. The assistant will refine the data flow. "
        "*e.g. \"Filter out incomplete records from Column X\"*"
    )

    # Guard: need API key
    if not groq_client:
        st.info("🔑 Set your **Groq API key** in the sidebar settings to enable the AI assistant.")
        return

    # Session state for this chat's history (separate from main chat)
    if "cleaning_chat_history" not in st.session_state:
        st.session_state.cleaning_chat_history = []

    # ── Display history ───────────────────────────────────────────────
    for msg in st.session_state.cleaning_chat_history:
        avatar = "👤" if msg["role"] == "user" else "🌊"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

    # ── Chat input ────────────────────────────────────────────────────
    user_input = st.chat_input(
        "Describe a cleaning task…",
        key="cleaning_chat_input",
    )

    if user_input:
        st.session_state.cleaning_chat_history.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="🧑‍💻"):
            st.markdown(user_input)

        with st.chat_message("assistant", avatar="🌊"):
            with st.spinner("⚡ SMOOTHING DATA FLOW..."):
                response_text = _get_cleaning_ai_response(df, groq_client, user_input)
                st.markdown(response_text)

                # Extract and execute code — mutations go back to session state
                code_blocks = _extract_code_blocks(response_text)
                if code_blocks:
                    for code in code_blocks:
                        with st.expander("🐍 View Generated Code", expanded=False):
                            st.code(code, language="python")
                        _safe_execute_cleaning(code)

        st.session_state.cleaning_chat_history.append({"role": "assistant", "content": response_text})
        st.rerun()

    # ── Clear button ──────────────────────────────────────────────────
    if st.session_state.cleaning_chat_history:
        if st.button("🗑️ Clear Cleaning Chat", key="clear_cleaning_chat"):
            st.session_state.cleaning_chat_history = []
            st.rerun()


def _get_cleaning_ai_response(df, groq_client, question):
    """Send a cleaning-specific prompt to Groq and return the response."""
    try:
        schema = get_schema_string(df)
        null_summary = df.isna().sum()
        null_info = null_summary[null_summary > 0].to_string() if null_summary.any() else "No nulls!"

        prompt = (
            "You are an expert data-cleaning assistant. The user wants to clean their pandas DataFrame.\n\n"
            "Rules:\n"
            "1. ONLY help with data-cleaning tasks (handling nulls, duplicates, type conversion, renaming, etc.).\n"
            "2. If the user asks something unrelated, politely redirect them.\n"
            "3. When a cleaning operation is needed, write a Python code block.\n"
            "4. The DataFrame is already in memory as `df` — DO NOT load data from files.\n"
            "5. After any modification, assign the result back to `df` "
            "(e.g. `df = df.dropna(subset=['Age'])`). The system will persist it automatically.\n"
            "6. Wrap all code in ```python blocks.\n"
            "7. After the code, give a one-sentence summary of what was done.\n\n"
            f"=== DATASET SCHEMA ===\n{schema}\n\n"
            f"=== NULL VALUE SUMMARY ===\n{null_info}\n\n"
            f"=== USER REQUEST ===\n{question}\n"
        )

        # Include last few exchanges for context
        history_context = ""
        recent = st.session_state.get("cleaning_chat_history", [])[-6:]
        if recent:
            history_context = "\n=== RECENT CONVERSATION ===\n"
            for msg in recent:
                role = "User" if msg["role"] == "user" else "Assistant"
                history_context += f"{role}: {msg['content'][:300]}\n"
            prompt += history_context

        response = groq_client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Error generating response: {str(e)}"


def _safe_execute_cleaning(code):
    """Execute AI-generated cleaning code and write the mutated df back to session state."""
    import traceback as tb
    try:
        import numpy as np

        # Work on a copy of the current live DataFrame
        working_df = st.session_state.df.copy()

        exec_globals = {
            "pd": pd,
            "np": np,
            "df": working_df,
            "st": st,
            "__builtins__": {
                "__import__": __import__,
                "print": print,
                "len": len,
                "range": range,
                "int": int,
                "float": float,
                "str": str,
                "list": list,
                "dict": dict,
                "tuple": tuple,
                "set": set,
                "sorted": sorted,
                "min": min,
                "max": max,
                "sum": sum,
                "abs": abs,
                "round": round,
                "enumerate": enumerate,
                "zip": zip,
                "map": map,
                "filter": filter,
                "isinstance": isinstance,
                "type": type,
                "True": True,
                "False": False,
                "None": None,
            },
        }

        exec(code, exec_globals)

        # If the AI modified `df`, persist it
        new_df = exec_globals.get("df", working_df)
        rows_before = st.session_state.df.shape[0]
        rows_after = new_df.shape[0]
        st.session_state.df = new_df

        st.success(
            f"✅ Dataset updated! "
            f"Rows: {rows_before} → {rows_after} | "
            f"Columns: {new_df.shape[1]}"
        )
        st.markdown("**📋 Updated Data Preview (first 5 rows):**")
        st.dataframe(new_df.head(5), use_container_width=True)

    except Exception as e:
        st.error(f"❌ Execution error: {str(e)}")
        st.code(tb.format_exc())
