import streamlit as st
import requests
import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(
    page_title="Portfolio Q&A",
    page_icon="🎓",
    layout="centered",
)

st.title("🎓 Angelo's Portfolio Q&A Engine")
st.caption("Ask me anything about my research and professional experience.")

hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
st.markdown(hide_st_style, unsafe_allow_html=True)

with st.sidebar:
    st.header("About")
    st.write(
        "This assistant answers questions grounded in my resume and "
        "research paper. It uses Google Gemini under the hood."
    )
    if st.button("🔍 Check backend status"):
        try:
            r = requests.get(f"{BACKEND_URL}/health", timeout=10)
            data = r.json()
            if data.get("docs_loaded"):
                st.success(f"Backend online ✅  ({data['context_chars']:,} chars loaded)")
            else:
                st.warning("Backend reachable but no docs loaded.")
        except Exception as e:
            st.error(f"Backend unreachable: {e}")

if "messages" not in st.session_state:
    st.session_state.messages = []

# Replay previous messages so the conversation stays visible
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

if question := st.chat_input("Ask something about my work..."):

    # Show the user's question immediately
    st.session_state.messages.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.write(question)

    # Call the backend and display the answer
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                resp = requests.post(
                    f"{BACKEND_URL}/ask",
                    json={"question": question},
                    timeout=30,  # Render free-tier can cold-start; give it time
                )
                resp.raise_for_status()
                answer = resp.json()["answer"]
            except requests.exceptions.Timeout:
                answer = (
                    "⚠️ The backend took too long to respond. "
                    "It may be waking up from a cold start — try again in a moment."
                )
            except requests.exceptions.HTTPError as e:
                answer = f"⚠️ Backend returned an error: {e}"
            except Exception as e:
                answer = f"⚠️ Could not reach the backend: {e}"

        st.write(answer)
        st.session_state.messages.append({"role": "assistant", "content": answer})