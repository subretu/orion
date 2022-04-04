from fastapi import FastAPI
from app.routers.controllers import router as controllers


app = FastAPI(
    version="0.9 beta",
)

app.include_router(controllers)
