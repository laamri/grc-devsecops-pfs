from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from pymongo import MongoClient

app = FastAPI()

# Connexion MongoDB basique
client = MongoClient("mongodb://localhost:27017/")
db = client["tasks_db"]
collection = db["tasks"]

class Task(BaseModel):
    title: str
    status: str = "todo"

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/tasks/")
def create_task(task: Task):
    result = collection.insert_one(task.model_dump())
    return {"id": str(result.inserted_id), "title": task.title}

@app.get("/tasks/")
def get_tasks():
    tasks = list(collection.find({}, {"_id": 0}))
    return tasks