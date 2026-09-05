from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.intelligence.resource_planner import ResourcePlanner

app = FastAPI(
    title="ZenUI Enterprise",
    version="0.1.0",
)


# -----------------------------------------
# CORS
# -----------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://frontend-three-self-67.vercel.app",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -----------------------------------------
# Routes
# -----------------------------------------

app.include_router(chat_router)


# -----------------------------------------
# Root
# -----------------------------------------

@app.get("/")
async def root():

    return {
        "name": "ZenUI Enterprise",
        "status": "running",
        "version": "0.1.0",
    }


# -----------------------------------------
# Health
# -----------------------------------------

@app.get("/health")
async def health():

    return {
        "status": "healthy",
        "service": "zenui-backend",
    }
@app.get("/test-resource")
async def test_resource():

    planner = ResourcePlanner()

    result = await planner.plan(
        user_prompt="What's the weather now in Trichy?"
    )

    return result