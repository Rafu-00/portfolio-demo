import streamlit as st
import requests

# This will be your deployed Render URL later
BACKEND_URL = "http://localhost:8000" 

st.set_page_config(page_title="Chat with My Portfolio")
st.title("👨‍💻 Portfolio Q&A Assistant")

st.sidebar.header("Admin Panel")
uploaded_file = st.sidebar.file_uploader("Upload Resume/Thesis (PDF)", type="pdf")

if uploaded_file and st.sidebar.button("Update Knowledge Base"):
    files = {"file": (uploaded_file.name, uploaded_file.getvalue())}
    with st.spinner('Indexing documents...'):
        res = requests.post(f"{BACKEND_URL}/index-portfolio", files=files)
        st.sidebar.success(res.json().get("message", "Success!"))

st.write("Ask anything about my experience, tech stack, or past projects.")
query = st.text_input("Example: What libraries does he prefer for data engineering?")

if query:
    with st.spinner('Thinking...'):
        response = requests.get(f"{BACKEND_URL}/ask", params={"query": query})
        if response.status_code == 200:
            st.write("**AI:**", response.json().get("answer"))
        else:
            st.error("Error connecting to backend.")