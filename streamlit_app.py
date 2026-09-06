import streamlit as st
import requests

API_URL = "http://127.0.0.1:8000"

st.set_page_config(page_title="Knowledge Assistant", layout="wide")

st.title("Knowledge Assistant")
st.write("Upload one or more PDFs and ask questions grounded in their content.")

#---PDF Upload -----
st.header("Upload Doc")
uploaded_files = st.file_uploader("Upload PDFs", type=["pdf"], accept_multiple_files=True)

if uploaded_files and st.button("Process selected PDFs", type="primary"):
    files = [("files", (item.name, item.getvalue(), "application/pdf")) for item in uploaded_files]
    try:
        with st.spinner("Uploading and processing PDFs..."):
            res = requests.post(f"{API_URL}/upload", files=files, timeout=300)
        if res.ok:
            data = res.json()
            st.success(f"Indexed {len(data['files'])} PDF(s), with {data['total_chunks']} chunks.")
        else:
            st.error(res.json().get("detail", "Failed to upload PDFs"))
    except requests.RequestException as exc:
        st.error(f"Could not reach the backend: {exc}")

st.divider()


#---Query Section ---
st.header("Ask a Question")
question = st.text_area("Enter your question", height=100, placeholder="Ask for a detailed explanation if you need a long answer.")

if st.button("Ask") and question:
    payload = {"question": question}
    with st.spinner("Searching knowledge base..."):
        res = requests.post(f"{API_URL}/query", json=payload, timeout=300)

    if res.status_code != 200:
        st.error(res.json().get("detail", "Error querying backend"))
    else:
        data = res.json()

        st.subheader("Answer")
        st.markdown(data.get("answer", ""))

        sources = data.get("sources",[])
        if sources:
            st.subheader("Sources")
            for i,src in enumerate(sources, 1):  #expandable UI
                citation = src.get("filename", f"Source {i}")
                if src.get("page"):
                    citation += f" — page {src['page']}"
                if src.get("question"):
                    citation += f" | for: {src['question']}"
                with st.expander(f"{citation} (similarity={src.get('similarity', 1-src['distance']):.3f})"):
                    st.write(src["text"])
        else:
            st.info("No sources returned")

