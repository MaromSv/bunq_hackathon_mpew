from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.graph.message import add_messages
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.types import Send
import os
import json
from logger import logger
import datetime

from transaction_analysis_tools import tools as transaction_tools

class TransactionAnalysisAgent:
    """Transaction Analysis AI Agent"""

    def __init__(self, llm):
        self.llm = llm
        self.memory = MemorySaver()
        self._setup_graph()

    def _setup_graph(self):
        """Setup the LangGraph workflow"""
        
        # Define prompt
        prompt = (
            "You are a Transaction Analysis Advisor. Your role is to analyze and summarize the user's spending patterns "
            "based on their transaction history.\n\n"
            "When analyzing transactions:\n"
            "1. Review the total spending amount\n"
            "2. Analyze the monthly spending patterns\n"
            "3. Look for trends in the recent transactions\n"
            "4. Identify any unusual spending patterns\n"
            "5. Provide specific insights about their spending habits\n\n"
            "For future purchase questions (like 'can I afford X?'):\n"
            "1. First analyze the user's current spending patterns\n"
            "2. Calculate their average monthly disposable income\n"
            "3. Consider their recent spending trends\n"
            "4. Provide a clear recommendation based on their actual spending data\n\n"
            "Keep your responses to 2-3 sentences maximum, focusing on the most important insights.\n"
            "Focus on providing clear, actionable insights about their spending patterns."
        )
        
        # Create the agent
        agent = create_react_agent(
            self.llm,
            tools=transaction_tools,
            prompt=prompt,
            checkpointer=self.memory
        )
        
        # Create the graph
        builder = StateGraph(AgentState)
        builder.add_node("agent", agent)
        builder.set_entry_point("agent")
        builder.add_edge("agent", END)
        
        self.graph = builder.compile()

    def process_message(self, message, thread_id=None):
        """Process a user message"""
        try:
            # Create a human message
            human_msg = HumanMessage(content=message)

            # Run the graph
            events = self.graph.stream(
                {"messages": [human_msg]},
                config={
                    "thread_id": thread_id,
                    "configurable": {"checkpointer": self.memory},
                    "recursion_limit": 3
                },
            )

            # Collect all messages
            messages = []
            for event in events:
                for _, node_output in event.items():
                    messages.extend(node_output.get("messages", []))

            # Return the last AI message content
            ai_messages = [m for m in messages if isinstance(m, AIMessage)]

            if ai_messages:
                # Get the last non-empty message
                for msg in reversed(ai_messages):
                    if msg.content.strip():
                        # Limit response length
                        content = msg.content
                        if len(content.split()) > 50:  # Roughly 2-3 sentences
                            content = " ".join(content.split()[:50]) + "..."
                        logger.log_agent_response(
                            "Transaction Analysis", content
                        )
                        return content
            return "I couldn't analyze your transactions. Please provide more details about your spending patterns."
            
        except Exception as e:
            error_msg = f"Error analyzing transactions: {str(e)}"
            logger.log_agent_response("Transaction Analysis", error_msg)
            return error_msg 