import json
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from langchain_core.documents import Document
from pinecone import Pinecone, ServerlessSpec

load_dotenv()

INDEX_NAME = "workelate-v1-index"
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")

if not PINECONE_API_KEY:
    raise ValueError("PINECONE_API_KEY not set.")

pc = Pinecone(api_key=PINECONE_API_KEY)

# Create index if it doesn't exist
existing_indexes = [idx.name for idx in pc.list_indexes()]
if INDEX_NAME not in existing_indexes:
    print(f"Creating serverless index: {INDEX_NAME}")
    pc.create_index(
        name=INDEX_NAME,
        dimension=1536,
        metric="cosine",
        spec=ServerlessSpec(cloud="aws", region="us-east-1")
    )

# Load data
with open("data.json", "r", encoding="utf-8") as f:
    data = json.load(f)

documents = []
ids = []

for item in data:
    proj_id = item.get("project_id")
    if not proj_id:
        print(f"Skipping entry without project_id: {item.get('project_name', 'unnamed')}")
        continue

    print(f"→ {proj_id} | {item.get('project_name')} | cust={item.get('customer_id')} | dev={item.get('developer_id')} | due={item.get('due_date')}")

    # Build rich content for embedding
    lines = [
        f"Project ID: {proj_id}",
        f"Customer ID: {item.get('customer_id', '—')}",
        f"Client: {item.get('client_name', 'Unknown')}",
        f"Project Name: {item.get('project_name', 'Unnamed')}",
        f"Details: {item.get('project_details', 'No details provided')}",
        f"Status & Health: {item.get('health', 'Unknown')}",
        f"Priority: {item.get('priority', 'Medium')}",
        f"Due Date: {item.get('due_date', 'Not set')}",
        f"Assigned Developer: {item.get('developer_name', 'Unassigned')} ({item.get('developer_id', '—')})",
        f"Last Interaction: {item.get('last_interaction', 'No recent activity')}",
        f"Last Updated: {item.get('last_updated', datetime.now(ZoneInfo('UTC')).isoformat())}",
    ]

    if tags := item.get("tags"):
        lines.append(f"Tags: {', '.join(tags)}")

    content = "\n".join(lines)

    # Rich metadata – this is the most important part for display
    metadata = {
        "project_id": proj_id,
        "customer_id": item.get("customer_id"),
        "project_name": item.get("project_name", "Unnamed"),
        "client_name": item.get("client_name", "Unknown"),
        "developer_id": item.get("developer_id"),
        "developer_name": item.get("developer_name", "Unassigned"),
        "health": item.get("health", "Unknown"),
        "priority": item.get("priority", "Medium"),
        "due_date": item.get("due_date"),
        "last_updated": item.get("last_updated", datetime.now(ZoneInfo("UTC")).isoformat()),
    }

    if tags:
        metadata["tags"] = tags

    doc = Document(page_content=content, metadata=metadata)
    documents.append(doc)
    ids.append(proj_id)

# Upsert
if documents:
    print(f"\nAdding/Upserting {len(documents)} project vectors...")
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
    vectorstore = PineconeVectorStore(index_name=INDEX_NAME, embedding=embeddings)
    vectorstore.add_documents(documents=documents, ids=ids)
    print(f" Successfully added/updated {len(documents)} projects.")
else:
    print("No valid projects to ingest.")

print("Ingestion complete.")