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
import uuid
from dotenv import load_dotenv
from agent import FinancialAdviceAIAgent
from langchain.chat_models import init_chat_model
from gtts import gTTS
from playsound import playsound
from openai import OpenAI
import os
load_dotenv()




llm = ChatOpenAI(model='gpt-4o')
ai_agent = FinancialAdviceAIAgent(llm)
thread_id = str(uuid.uuid4())

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


# Your main demo loop
def run_demo():
    """
    This is the main demo loop that allows the user to interact with the AI agent.
    It takes user input and passes it to the AI agent, which then returns a response.
    The response is then printed to the console.
    """

    while True:
        user_input = input("User (type 'exit' to quit): ").strip()

        if user_input.lower() in ["exit", "quit"]:
            print("Exiting demo.")
            break

        print(f"\nYou said: {user_input}")
        print("\n--- Chat Interface ---\n")

        # Get AI response
        ai_response = ai_agent.process_message(user_input, thread_id=thread_id)
        print(ai_response)



if __name__ == "__main__":
    run_demo()
