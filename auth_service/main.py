from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Auth Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class UserLogin(BaseModel):
    username: str


@app.get("/health")
def health_check():
    return {"status": "ok", "service": "auth_service"}


@app.post("/login")
def login(user: UserLogin):
    return {"message": f"Utilisateur {user.username} connecté", "token": "fake-jwt-token-us05"}