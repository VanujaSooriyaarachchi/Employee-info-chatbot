import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import socketio
import openai
import requests
import uvicorn

load_dotenv()

openai.api_key = os.getenv("OPENAI_API_KEY")

app = FastAPI()
sio = socketio.AsyncServer(async_mode='asgi', cors_allowed_origins="*")
socket_app = socketio.ASGIApp(sio, other_asgi_app=app)

# CORS Middleware configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust this to allow specific origins if needed
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Function to get response from OpenAI GPT-3
async def get_response_from_gpt(query):
    try:
        response = openai.Completion.create(
            engine="davinci",
            prompt=query,
            max_tokens=300
        )
        return response.choices[0].text.strip()
    except Exception as e:
        print(f"Error getting response from GPT-3: {e}")
        return "An error occurred while processing your request."

# Function to fetch training data from the API
async def fetch_trainings(status, employee_id):
    try:
        url = f"http://testapi.romeohr.com/app/v1/{employee_id}/training"
        headers = {
            "Authorization": f"Bearer {os.getenv('ACCESS_TOKEN')}"
        }
        response = requests.get(url, headers=headers, params={"status": status})
        data = response.json()
        print(f"Fetched training data for status '{status}': {data}")  # Debugging
        return data
    except Exception as e:
        print(f"Error fetching training data: {e}")
        return []

@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")
    await sio.save_session(sid, {"state": "initial"})

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

@sio.event
async def message(sid, data):
    print(f"Message from {sid}: {data}")
    try:
        session = await sio.get_session(sid)

        if session["state"] == "initial":
            if "pending" in data["query"] or "completed" in data["query"]:
                session["state"] = "awaiting_employee_id"
                await sio.save_session(sid, session)
                response_text = "Enter your Employee ID"
            else:
                response_text = await get_response_from_gpt(data["query"])
        elif session["state"] == "awaiting_employee_id":
            employee_id = data["query"].strip()
            print(f"Fetching trainings for employee ID: {employee_id}")

            pending_trainings = await fetch_trainings("pending", employee_id)
            completed_trainings = await fetch_trainings("completed", employee_id)

            # Check the type and structure of the response
            if isinstance(pending_trainings, dict) and isinstance(completed_trainings, dict):
                pending_count = pending_trainings.get('pending_trainings', 0)
                completed_count = completed_trainings.get('completed_trainings', 0)
            else:
                pending_count = 0
                completed_count = 0

            response_text = f"You have {pending_count} pending trainings and {completed_count} completed trainings."
            print(f"Response: {response_text}")

            session["state"] = "initial"
            await sio.save_session(sid, session)

        await sio.emit('chat_response', {'response': response_text}, room=sid)
    except Exception as e:
        print(f"Error handling message: {e}")
        await sio.emit('chat_response', {'response': "An error occurred while processing your request."}, room=sid)

if __name__ == "__main__":
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)
