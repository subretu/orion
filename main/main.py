from fastapi import FastAPI
from main.routers.controllers import router as controllers


app = FastAPI(
    version="0.9 beta",
)

app.include_router(controllers)
