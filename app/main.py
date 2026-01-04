from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from .database import engine, Base
from .routers import auth, doctors, hospitals
from pathlib import Path
import os
from app.routers import chatbot, users, appointments, profile
from app.AI import predict_disease


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Smart Healthcare API", version="1.0.0")


# ✅ 1️⃣ Bật CORS middleware trước khi mount static
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://127.0.0.1:5000"],  # frontend origin
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ 2️⃣ Include tất cả API routers trước khi mount static
app.include_router(auth.router)
app.include_router(doctors.router)
app.include_router(hospitals.router)
app.include_router(chatbot.router)
app.include_router(predict_disease.router)
app.include_router(users.router)
app.include_router(appointments.router, prefix="/api/appointments")
app.include_router(profile.router)

print("Routers included:", app.routes)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# ✅ 3️⃣ Mount frontend cuối cùng (để không chồng lên /api)
frontend_dist = Path(__file__).parent.parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

# ----------------------------
# Run uvicorn (Render)
# ----------------------------
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))  # Render sẽ set PORT
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
