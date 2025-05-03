from langchain_openai import ChatOpenAI
import os
import uuid
from dotenv import load_dotenv
from agent import FinancialAdviceAIAgent
from openai import OpenAI
from flask import Flask, request, jsonify
from flask_cors import CORS
load_dotenv()

app = Flask(__name__)
CORS(app)

llm = ChatOpenAI(model='gpt-4o')
ai_agent = FinancialAdviceAIAgent(llm)
thread_id = str(uuid.uuid4())

@app.route("/chat", methods=["POST"])
def chat():
    data = request.json
    user_input = data.get("message")

    if not user_input:
        return jsonify({"error": "Missing 'message'"}), 400
    
    ai_response = ai_agent.process_message(user_input, thread_id=thread_id)
    return jsonify({"response": ai_response})

@app.route("/insight", methods=["POST"])
def insight():
    try:
        prompt = "You are an expert financial analyst. Your task is to give me a detailed summary of my current financial situation based on recent data. Highlight specific patterns, strengths, weaknesses. Offer tips on how to improve and change certain spending habits. "
        response = ai_agent.process_message(prompt, thread_id=thread_id)
        return jsonify({"insight": response})
    except Exception as e:
        print(f"Error generating insight: {e}")
        return jsonify({"error": "Failed to generate insight"}), 500

if __name__ == "__main__":
    app.run(port=8000, debug=True)


