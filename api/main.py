import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routers import task
from shared import setup_logging


setup_logging()
logger = logging.getLogger(__name__)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(task.router, prefix="/tasks")
