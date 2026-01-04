import pandas as pd
import chromadb
from sentence_transformers import SentenceTransformer
import os

# ----- 1. LOAD DATA CSV -----
df_sym = pd.read_csv("app/AI/disease_dataAI2.csv")
df_desc = pd.read_csv("app/AI/disease_descriptionsAI.csv")
df_doc = pd.read_csv(
    "app/AI/Doctor_Versus_Disease.csv",
    encoding='latin1',
    names=['Disease', 'Specialist']
)

# ----- 2. LOAD LOCAL EMBEDDING MODEL (FREE) -----
print("⏳ Loading embedding model BGE-small...")
model = SentenceTransformer("BAAI/bge-small-en")

# ----- 3. INIT CHROMA -----
chroma_client = chromadb.PersistentClient(path="app/AI/vector_db")

collection = chroma_client.get_or_create_collection(
    name="medical_rag",
    metadata={"hnsw:space": "cosine"}
)

# Nếu DB đã có dữ liệu → skip
if collection.count() > 0:
    print(f"⚠️ Vector DB đã tồn tại ({collection.count()} docs). Bỏ qua việc tạo lại.")
    exit()

documents = []
metas = []
ids = []

# ----- 4. BUILD DOCUMENTS -----
print("⏳ Building documents...")

for idx, row in df_desc.iterrows():
    disease = row["Disease"].strip()
    desc = str(row["Description"]).replace("\n", " ").strip()

    # Triệu chứng
    sym_row = df_sym[df_sym["Disease"] == disease]
    symptoms = sym_row.iloc[0].tolist()[1:] if not sym_row.empty else []

    # Chuyên khoa
    doc_row = df_doc[df_doc["Disease"] == disease]
    specialist = (
        str(doc_row.iloc[0]["Specialist"]).strip()
        if not doc_row.empty
        else "Chưa xác định"
    )

    # Text tối ưu cho local RAG
    full_text = f"""
Bệnh: {disease}
Triệu chứng: {', '.join([str(s) for s in symptoms if pd.notna(s)])}
Mô tả: {desc}
Khoa điều trị: {specialist}
""".strip()

    documents.append(full_text)
    metas.append({"disease": disease})
    ids.append(str(idx))

# ----- 5. GENERATE LOCAL EMBEDDINGS -----
print("⏳ Generating embeddings (local BGE-small)...")

vectors = model.encode(documents, convert_to_numpy=True)

# ----- 6. SAVE TO CHROMA -----
collection.add(
    embeddings=vectors,
    documents=documents,
    metadatas=metas,
    ids=ids
)

print("🎉 Vector DB đã được tạo thành công — sử dụng LOCAL embeddings (BGE-small)!")
