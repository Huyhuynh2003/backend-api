from fastapi import APIRouter
from pydantic import BaseModel
import chromadb
from sentence_transformers import SentenceTransformer
from openai import OpenAI
import os

# ----------------------------
# OpenAI client
# ----------------------------
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
if not OPENAI_API_KEY:
    raise RuntimeError("Missing OPENAI_API_KEY environment variable!")

client = OpenAI(api_key=OPENAI_API_KEY)

# ----------------------------
router = APIRouter(prefix="/api/chatbot", tags=["Chatbot"])

# ----------------------------
# Lazy globals
# ----------------------------
chroma_client = None
collection = None
embed_model = None

# ----------------------------
# Init RAG
# ----------------------------
def init_rag():
    global chroma_client, collection, embed_model
    if chroma_client is None:
        chroma_client = chromadb.PersistentClient(path="app/AI/vector_db")
    if collection is None:
        collection = chroma_client.get_collection("medical_rag")
    if embed_model is None:
        embed_model = SentenceTransformer("BAAI/bge-small-en")

# ----------------------------
# System prompt
# ----------------------------
SYSTEM_PROMPT = """
Bạn là trợ lý y tế an toàn, chỉ hỗ trợ các vấn đề liên quan đến sức khỏe và y tế.

QUY TẮC:
- Chỉ trả lời các câu hỏi thuộc lĩnh vực y tế, triệu chứng, bệnh, chăm sóc sức khỏe, sơ cứu, hướng dẫn an toàn.
- Nếu câu hỏi KHÔNG liên quan đến y tế -> phải trả lời:
  "Tôi chỉ hỗ trợ các câu hỏi liên quan đến sức khỏe và y tế."
- Ưu tiên dùng dữ liệu từ RAG.
- KHÔNG chẩn đoán bệnh.
- KHÔNG kê thuốc.
- Nếu triệu chứng nguy hiểm -> yêu cầu đến bệnh viện.
"""

class UserMessage(BaseModel):
    message: str

# ----------------------------
# RAG retrieval
# ----------------------------
def retrieve_context(query: str):
    init_rag()
    query_vec = embed_model.encode([query]).tolist()
    result = collection.query(query_embeddings=query_vec, n_results=3)
    docs = result.get("documents", [[]])[0]
    return "\n\n".join(docs)

# ----------------------------
# Chatbot API
# ----------------------------
@router.post("")
async def chatbot(msg: UserMessage):
    user_input = msg.message
    context = retrieve_context(user_input)

    if context.strip() == "":
        return {"reply": "Tôi chỉ hỗ trợ các câu hỏi liên quan đến sức khỏe và y tế."}

    prompt = f"""
{SYSTEM_PROMPT}

Dữ liệu RAG:
{context}

Câu hỏi:
{user_input}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return {"reply": response.choices[0].message.content}
