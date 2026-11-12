from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = MongoClient("mongodb://localhost:27017/")
db = client["tasks_db"]
collection = db["tasks"]


class Task(BaseModel):
    title: str
    status: str = "todo"


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "task_service"}


@app.post("/tasks/")
def create_task(task: Task):
    result = collection.insert_one(task.model_dump())
    return {"id": str(result.inserted_id), "title": task.title}


@app.get("/tasks/")
def get_tasks():
    tasks = list(collection.find({}, {"_id": 0}))
    return tasks