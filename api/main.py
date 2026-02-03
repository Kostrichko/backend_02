from fastapi import FastAPI
from api.routers import task


app = FastAPI()
app.include_router(task.router, prefix="/tasks")
