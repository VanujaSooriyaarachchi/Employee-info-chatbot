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
async def fetch_trainings(status, employee_id, company_id):
    try:
        url = f"http://testapi.romeohr.com/app/v1/{company_id}/training/employee/{employee_id}"
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
            session["employee_id"] = data["query"].strip()
            session["state"] = "awaiting_company_id"
            await sio.save_session(sid, session)
            response_text = "Enter your Company ID"
        elif session["state"] == "awaiting_company_id":
            session["company_id"] = data["query"].strip()
            employee_id = session["employee_id"]
            company_id = session["company_id"]

            print(f"Fetching trainings for employee ID: {employee_id} and company ID: {company_id}")

            pending_trainings = await fetch_trainings("pending", employee_id, company_id)
            completed_trainings = await fetch_trainings("completed", employee_id, company_id)

            # Extract training names from the response
            pending_training_names = [training['name'] for training in pending_trainings]
            completed_training_names = [training['name'] for training in completed_trainings]

            response_text = (f"You have {len(pending_training_names)} pending trainings: {', '.join(pending_training_names)}. "
                             f"You have completed {len(completed_training_names)} trainings: {', '.join(completed_training_names)}.")

            print(f"Response: {response_text}")

            session["state"] = "initial"
            await sio.save_session(sid, session)

        await sio.emit('chat_response', {'response': response_text}, room=sid)
    except Exception as e:
        print(f"Error handling message: {e}")
        await sio.emit('chat_response', {'response': "An error occurred while processing your request."}, room=sid)

if __name__ == "__main__":
    uvicorn.run(socket_app, host="0.0.0.0", port=8000)
