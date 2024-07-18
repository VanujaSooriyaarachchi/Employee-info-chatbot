import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import socketio
import openai
import requests

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dictionary to maintain the state of each user session
user_sessions = {}

async def get_response_from_gpt(query):
    response = openai.Completion.create(
        engine="davinci",
        prompt=query,
        max_tokens=50
    )
    return response.choices[0].text.strip()

async def fetch_trainings(status, employee_id):
    url = "http://testapi.romeohr.com/app/v1/82c3391d-2e65-43b9-a514-03b14ff3fcb1/training-category"
    headers = {
        "Authorization": f"Bearer {os.getenv('ACCESS_TOKEN')}"
    }
    response = requests.get(url, headers=headers, params={"status": status, "employee_id": employee_id})
    return response.json()

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")
    user_sessions[sid] = {"state": "initial"}

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
    if sid in user_sessions:
        del user_sessions[sid]

@sio.event
async def message(sid, data):
    if sid not in user_sessions:
        user_sessions[sid] = {"state": "initial"}

    session = user_sessions[sid]
    query = data.get("query", "")

    if session["state"] == "initial":
        if "pending" in query or "completed" in query:
            session["state"] = "awaiting_employee_id"
            session["query"] = query
            response_text = "Enter your Employee ID"
        else:
            response_text = await get_response_from_gpt(query)
    elif session["state"] == "awaiting_employee_id":
        employee_id = query.strip()
        session["employee_id"] = employee_id
        pending_trainings = await fetch_trainings("pending", employee_id)
        completed_trainings = await fetch_trainings("completed", employee_id)
        response_text = (
            f"You have {pending_trainings['pending_trainings']} pending trainings and "
            f"{completed_trainings['completed_trainings']} completed trainings."
        )
        session["state"] = "initial"  # Reset the state for the next interaction

    await sio.emit('chat_response', {'response': response_text}, room=sid)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)
