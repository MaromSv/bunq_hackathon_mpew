import sounddevice as sd
import scipy.io.wavfile as wavfile
import tempfile
import openai
from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.prebuilt import ToolNode
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage, SystemMessage
from langgraph.checkpoint.memory import MemorySaver
import sys
import io
import os
import requests
import pandas as pd
import os
from langchain_core.tools import Tool
import asyncio
import uuid
from dotenv import load_dotenv
from agent import FinancialAdviceAIAgent
from langchain.chat_models import init_chat_model
from gtts import gTTS
from playsound import playsound
from openai import OpenAI
import os
load_dotenv()
import pyttsx3



llm = ChatOpenAI(model='gpt-4o')


ai_agent = FinancialAdviceAIAgent(llm)
thread_id = str(uuid.uuid4())


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def speak_text(text):
    engine = pyttsx3.init()
    engine.setProperty('rate', 150)  # Adjust speed if needed
    engine.setProperty('volume', 1.0)
    engine.say(text)
    engine.runAndWait()

def transcribe_audio_with_whisper(filename):
    with open(filename, "rb") as audio_file:
        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )
        return transcript.text


import tempfile

# Your main demo loop
def run_demo():
    while True:
        mode = input("Type 'v' for voice input, 't' for text input, or 'exit' to quit: ").strip().lower()
        use_voice_output = (mode == "v")

        if mode == "exit":
            print("Exiting demo.")
            break

        elif mode == "v":
            # Create a temp .wav file path
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
                temp_path = tmpfile.name

            # Record and transcribe
            user_input = transcribe_audio_with_whisper(temp_path)

            # Clean up the temp file
            try:
                os.remove(temp_path)
            except Exception as e:
                print(f"Warning: Could not delete temp file: {e}")

        elif mode == "t":
            user_input = input("User: ")
        else:
            print("Invalid option. Use 'v', 't', or 'exit'.")
            continue

        if user_input.lower() in ["exit", "quit"]:
            print("Exiting demo.")
            break

        print(f"\nYou said: {user_input}")
        print("\n--- Chat Interface ---\n")

        # Get AI response
        ai_response = ai_agent.process_message(user_input, thread_id=thread_id)

        # Speak only if in voice mode
        if use_voice_output:
            speak_text(ai_response)



if __name__ == "__main__":
    run_demo()
