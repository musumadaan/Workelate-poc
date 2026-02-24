# app.py
import streamlit as st
import re
from datetime import datetime
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_pinecone import PineconeVectorStore
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document

load_dotenv()

st.set_page_config(page_title="Living Inbox • One-brain", page_icon="⚡", layout="wide")
st.title("⚡ Living Inbox – One-brain Workspace")
st.caption("Context appears when you need it. Status lives with the project.")


@st.cache_resource
def get_vs():
    emb = OpenAIEmbeddings(model="text-embedding-3-small")
    return PineconeVectorStore(index_name="workelate-v1-index", embedding=emb)

@st.cache_resource
def get_llm():
    return ChatOpenAI(model="gpt-4o-mini", temperature=0.3)

vectorstore = get_vs()
llm = get_llm()


with st.sidebar:
    st.header("Workspace")
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_resource.clear()
        st.rerun()

    st.subheader("Recent Activity")
    try:
        recent = vectorstore.similarity_search("last_updated", k=5)
        for d in sorted(recent, key=lambda x: x.metadata.get("last_updated", ""), reverse=True)[:3]:
            name = d.metadata.get("project_name", "—")
            upd = d.metadata.get("last_updated", "—")[:10]
            st.caption(f"{name} • {upd}")
    except:
        st.caption("No recent data available")


def normalize_pid(pid: str) -> list:
    pid = pid.strip().upper()
    variations = [pid]
    if '-' in pid:
        variations.append(pid.replace("-", ""))
    if pid.startswith("PRJ"):
        variations.append(pid.replace("PRJ", "PRJ-"))
        variations.append(pid.replace("PRJ-", "PRJ"))
    return list(set(variations))


tab1, tab2, tab3, tab4 = st.tabs(["🔍 Query", "📥 Inbox", "🎯 Intent", "🌐 Explore"])


def extract_from_content(text, pattern, group=1, default="—"):
    match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
    return match.group(group).strip() if match else default


with tab1:
    st.subheader("Find Project / Customer / Developer")
    q = st.text_input("ID or keyword", placeholder="PRJ-001 | CI001 | DEV-003 | Vortex | blocked", key="query_input")

    if q:
        with st.spinner("Searching..."):
            # Show known IDs for debugging
            try:
                all_docs = vectorstore.similarity_search("", k=30)
                known_ids = sorted(set(doc.metadata.get("project_id", "—") for doc in all_docs))
                st.caption(f"Known project IDs in store: {', '.join(known_ids)}")
            except:
                pass

            q_norm_vars = normalize_pid(q)
            results = []

            # Try exact project_id match first
            for candidate in q_norm_vars:
                if candidate.startswith("PRJ"):
                    exact = vectorstore.similarity_search("", k=1, filter={"project_id": candidate})
                    if exact:
                        results = exact
                        break

            # Fallback to semantic + filter
            if not results:
                filter_ = None
                if any(v.startswith("PRJ") for v in q_norm_vars):
                    filter_ = {"project_id": {"$in": q_norm_vars}}
                elif any(v.startswith("CI") for v in q_norm_vars):
                    filter_ = {"customer_id": {"$in": q_norm_vars}}
                elif any(v.startswith("DEV") for v in q_norm_vars):
                    filter_ = {"developer_id": {"$in": q_norm_vars}}

                results = vectorstore.similarity_search(q, k=5, filter=filter_)

            if not results:
                st.warning(f"No matches for '{q}' (tried: {', '.join(q_norm_vars)})")
            else:
                seen_ids = set()
                for doc in results:
                    m = doc.metadata
                    text = doc.page_content

                    pid = m.get("project_id") or extract_from_content(text, r"Project ID:\s*(\S+)")
                    if pid in seen_ids:
                        continue
                    seen_ids.add(pid)

                    name     = m.get("project_name") or extract_from_content(text, r"Project Name:\s*(.+?)(?:\n|$)")
                    client   = m.get("client_name")  or extract_from_content(text, r"Client:\s*(.+?)(?:\n|$)")
                    dev_name = m.get("developer_name") or extract_from_content(text, r"Developer:\s*(.+?)\s*\(", default="Unassigned")
                    dev_id   = m.get("developer_id") or extract_from_content(text, r"\((DEV-\d+)\)", default="—")
                    cust_id  = m.get("customer_id") or extract_from_content(text, r"Customer ID:\s*(\S+)")

                    health_raw = m.get("health") or extract_from_content(text, r"Health:\s*(.+?)(?:\n|$)", default="Unknown")
                    priority   = m.get("priority") or extract_from_content(text, r"Priority:\s*(\w+)", default="—")
                    due        = m.get("due_date") or extract_from_content(text, r"Due Date:\s*([\d-]+)", default="Not set")

                    health_emoji = health_raw.split()[0] if " " in health_raw else health_raw

                    with st.container(border=True):
                        st.markdown(f"**{name}**  ({pid})")
                        st.caption(f"{client} • {cust_id} • {dev_name} ({dev_id})")

                        col1, col2, col3 = st.columns([4, 1.5, 1.5])
                        with col1:
                            with st.expander("Project Details"):
                                details_match = re.search(r"Details:\s*(.+?)(?=\n[A-Z]|$)", text, re.DOTALL | re.I)
                                st.write(details_match.group(1).strip() if details_match else "No details available")
                        with col2:
                            color_map = {"🟢": "#4CAF50", "🟡": "#FF9800", "🔴": "#F44336", "Unknown": "#9E9E9E"}
                            color = color_map.get(health_emoji, "#9E9E9E")
                            st.markdown(
                                f"<div style='background:{color};color:white;padding:8px;border-radius:6px;text-align:center;font-weight:bold;'>{health_raw}</div>",
                                unsafe_allow_html=True
                            )
                        with col3:
                            st.metric("Priority", priority)
                            st.caption(f"Due: **{due}**")

                        st.divider()

                        with st.expander("Activity History / Inbox Entries", expanded=True):
                            activities = re.findall(
                                r"───── Activity ([\d\- :]+) ─────\n(.*?)(?=───── Activity|$)",
                                text,
                                re.DOTALL | re.IGNORECASE
                            )
                            if activities:
                                for ts, content in activities:
                                    st.markdown(f"**{ts.strip()}**")
                                    st.markdown(content.strip())
                                    st.divider()
                            else:
                                st.info("No inbox activities added yet.")

                        with st.expander("Full Raw Document Content (debug)", expanded=False):
                            st.text_area("Complete stored text", text, height=350, disabled=True, key=f"raw_{pid}")

                    st.divider()


with tab2:
    st.subheader("Add Activity / Note / Email / Chat")
    c1, c2 = st.columns([1.2, 4])
    with c1:
        pid = st.text_input("Project ID", placeholder="PRJ-003", key="inbox_pid")
    with c2:
        note = st.text_area("Paste content here", height=140,
                            placeholder="Client: Please add dark mode toggle...")

    if st.button("Append to Context", type="primary", use_container_width=True):
        if not pid or not note.strip():
            st.error("Project ID and content are required.")
        else:
            pid_vars = normalize_pid(pid)
            with st.spinner("Updating..."):
                found = False
                current = None
                for candidate in pid_vars:
                    hits = vectorstore.similarity_search("", k=1, filter={"project_id": candidate})
                    if hits:
                        current = hits[0]
                        found = True
                        break

                if found:
                    ts = datetime.now().strftime("%Y-%m-%d %H:%M")
                    new_content = current.page_content + f"\n\n───── Activity {ts} ─────\n{note.strip()}"
                    new_doc = Document(page_content=new_content, metadata=current.metadata)
                    vectorstore.add_documents([new_doc], ids=[current.metadata["project_id"]])
                    st.success(f"Added to **{current.metadata.get('project_id')}**")
                    st.info(f"Just added:\n{note.strip()}")
                    st.caption(f"New length: {len(new_content)} chars")
                else:
                    st.error("Project not found")
                    st.warning(f"Tried IDs: {', '.join(pid_vars)}")
                    st.info("Copy the exact 'Project ID:' value from Query → Full Raw Document Content")
with tab3:
    st.subheader("Describe your goal / outcome")
    intent = st.text_input("What do you want to achieve?",
                           placeholder="Reschedule PeakPulse demo and add export button",
                           key="intent_input")

    if intent and st.button("Generate Plan", type="primary"):
        with st.spinner("Creating plan..."):
            prompt = PromptTemplate.from_template(
                """Available projects:
                - PRJ-001: Quantum Supply Chain – Phase 2 (Elena Vasquez / DEV-001)
                - PRJ-002: Carbon Ledger (Jamal Khalid / DEV-002)
                - PRJ-003: Dynamic Routing (Liam Chen / DEV-003)
                - PRJ-004: Supplier Risk (Elena Vasquez / DEV-001)

                Goal: {goal}

                Generate markdown:
                - Likely project
                - 4–6 numbered tasks
                - Suggested owner (use real names)
                - Deadline/urgency
                - Blockers"""
            )
            chain = prompt | llm | StrOutputParser()
            plan = chain.invoke({"goal": intent})

            st.markdown("### Generated Plan")
            st.markdown(plan)
with tab4:
    st.subheader("Projects by Customer or Developer")
    mode = st.radio("Group by", ["Customer ID", "Developer ID"], horizontal=True)

    term = st.text_input("Enter ID or name fragment", key="explore_search")

    if term:
        term_norm = term.strip().upper()
        fkey = "customer_id" if mode == "Customer ID" else "developer_id"

        # Try exact filter first
        results = vectorstore.similarity_search("", k=10, filter={fkey: term_norm})

        # Fallback to semantic search
        if not results:
            results = vectorstore.similarity_search(term, k=10)

        if results:
            seen = set()
            for d in results:
                m = d.metadata
                text = d.page_content

                pid = m.get("project_id") or extract_from_content(text, r"Project ID:\s*(\S+)", default="—")
                if pid in seen:
                    continue
                seen.add(pid)

                name = m.get("project_name") or extract_from_content(text, r"Project Name:\s*(.+?)(?:\n|$)", default="Unnamed Project")
                health = m.get("health") or extract_from_content(text, r"Health:\s*(.+?)(?:\n|$)", default="—")
                prio = m.get("priority") or extract_from_content(text, r"Priority:\s*(\w+)", default="—")
                due = m.get("due_date") or extract_from_content(text, r"Due Date:\s*([\d-]+)", default="—")
                dev_name = m.get("developer_name") or extract_from_content(text, r"Developer:\s*(.+?)\s*\(", default=m.get("developer_id", "—"))

                with st.container(border=True):
                    st.markdown(f"**{name}** ({pid})")
                    st.caption(f"Health: {health} • Priority: {prio} • Due: {due}")
                    st.caption(f"Developer: {dev_name}")
                st.divider()
        else:
            st.info(f"No projects found for '{term}' in {mode}")

st.divider()
st.caption("One-brain POC • 2026")