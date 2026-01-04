from fastapi import APIRouter
from pydantic import BaseModel
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()

# OpenAI client (chỉ dùng để trả lời, không embed)
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

router = APIRouter(prefix="/api/chatbot", tags=["Chatbot"])

# ----- ChromaDB local -----
chroma_client = chromadb.PersistentClient(path="app/AI/vector_db")
collection = chroma_client.get_collection("medical_rag")

# ----- Load local BGE model để embed câu hỏi -----
print("Loading BGE-small for query embedding...")
embed_model = SentenceTransformer("BAAI/bge-small-en")

SYSTEM_PROMPT = """
Bạn là trợ lý y tế an toàn, chỉ hỗ trợ các vấn đề liên quan đến sức khỏe và y tế.

QUY TẮC:
- Chỉ trả lời các câu hỏi thuộc lĩnh vực y tế, triệu chứng, bệnh, chăm sóc sức khỏe, sơ cứu, hướng dẫn an toàn.
- Nếu câu hỏi KHÔNG liên quan đến y tế -> phải trả lời: 
  "Tôi chỉ hỗ trợ các câu hỏi liên quan đến sức khỏe và y tế."
- Ưu tiên dùng dữ liệu từ RAG.
- Nếu RAG không đủ, có thể đưa ra lời khuyên chung chung nhưng phải liên quan đến sức khỏe.
- KHÔNG chẩn đoán bệnh chính xác.
- KHÔNG kê thuốc.
- KHÔNG tự kết luận bệnh.
- Có thể đưa ra hướng dẫn chăm sóc cơ bản (uống nước, nghỉ ngơi, theo dõi triệu chứng).
- Nếu triệu chứng nguy hiểm (khó thở, đau ngực, lơ mơ, sốt cao kéo dài...) -> yêu cầu người dùng đến bệnh viện ngay.
- Luôn đưa ra 1–3 gợi ý hành động an toàn.

YÊU CẦU TRẢ LỜI:
- Ngắn gọn, dễ hiểu, tiếng Việt.
- Không nói về các chủ đề ngoài y tế.
"""

class UserMessage(BaseModel):
    message: str

# ----- RAG Retrieval -----
def retrieve_context(query: str):
    # Tạo embedding câu hỏi bằng BGE-small
    query_vec = embed_model.encode([query]).tolist()

    # Query bằng vector, KHÔNG dùng query_texts
    result = collection.query(
        query_embeddings=query_vec,
        n_results=3
    )
    
    docs = result["documents"][0]
    return "\n\n".join(docs)

@router.post("")
async def chatbot(msg: UserMessage):
    user_input = msg.message
    context = retrieve_context(user_input)

    # 🔒 BLOCK: Nếu không có dữ liệu y tế trong RAG → chặn câu hỏi không liên quan
    if context.strip() == "":
        return {
            "reply": "Tôi chỉ hỗ trợ các câu hỏi liên quan đến sức khỏe và y tế."
        }

    prompt = f"""
{SYSTEM_PROMPT}

Dữ liệu RAG thu được:
{context}

Câu hỏi của người dùng:
{user_input}
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2
    )

    return {"reply": response.choices[0].message.content}

