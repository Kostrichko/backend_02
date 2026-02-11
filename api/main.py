import logging
from fastapi import FastAPI
from api.routers import task
from shared import setup_logging


setup_logging()
logger = logging.getLogger(__name__)


app = FastAPI()
app.include_router(task.router, prefix="/tasks")
