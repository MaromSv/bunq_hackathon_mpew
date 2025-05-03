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
load_dotenv()


llm = init_chat_model("meta/llama-3.1-70b-instruct", model_provider="nvidia")

ai_agent = FinancialAdviceAIAgent(llm)
thread_id = str(uuid.uuid4())

def run_demo():
    while True:
        user_input = input("User: ")
        if user_input.lower() in ["exit", "quit"]:
            print("Exiting demo.")
            break

        print("\n--- Chat Interface ---\n")
        ai_agent.process_message(user_input, thread_id=thread_id)

if __name__ == "__main__":
    run_demo()
