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

from tools import tools_past_advice, tools_future_advice

from api_utils import extractUserInformation




class FinancialAdviceAIAgent:
    """Financial advice autonomous AI Agent"""

    def __init__(self, llm):
        """
        Initialize the FinancialAdviceAIAgent with a given LLM.

        :param llm: The LLM to use for the agent.
        """
        self.llm = llm
        self.agents = {}
        self.memory = MemorySaver()
        self.user_info = extractUserInformation(os.getenv("BUNQ_API_KEY"))
        self._setup_graph()

    def _extract_routing_decision(self, state):
        """
        Extract routing decision from the agent's output
        
        :param state: The state of the agent.
        :return: The routing decision.
        """
            
        # Get the last AI message
        ai_messages = [m for m in state["messages"] if isinstance(m, AIMessage)]
        if not ai_messages:
            return "general"
            
        # Try to parse JSON from the last AI message
        try:
            last_message = ai_messages[-1].content
            # Check if this is a string containing JSON
            if isinstance(last_message, str):
                decision_data = json.loads(last_message)
                if "routing_decision" in decision_data:
                    # Store the routing decision in the state
                    routing_decision = decision_data["routing_decision"].lower()
                    if routing_decision in ["past", "future", "general"]:
                        print(f"Routing decision: {routing_decision}")
                        state["routing_decision"] = routing_decision
                        return routing_decision
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

        
        # Default to general if no clear decision
        return "general"

    def _setup_graph(self):
        """Setup a multi-agent LangGraph workflow and builds the graph"""
        
        # Define prompts
        orchestrator_prompt = (
            f"This is the person that owns the account: {self.user_info}, take this into account\n"
            "You are the orchestrator agent. Your task is to route financial questions to the appropriate specialist agent.\n"
            "1. For questions about past spending, expenses, or transaction history, route to 'past'.\n"
            "2. For questions about future planning, saving, investing, or goals, route to 'future'.\n"
            "3. For general questions or greetings, route to 'general'.\n\n"
            "Return a JSON with two keys:\n"
            "  - 'routing_decision': either 'past', 'future', or 'general'\n"
            "  - 'messages': a brief explanation of your decision\n\n"
            "Example outputs:\n"
            "For spending analysis: {\"routing_decision\": \"past\", \"messages\": [\"This is about past spending habits.\"]}\n"
            "For investment advice: {\"routing_decision\": \"future\", \"messages\": [\"This is about future financial planning.\"]}\n"
            "For general questions: {\"routing_decision\": \"general\", \"messages\": [\"This is a general inquiry.\"]}"
        )


        past_advice_prompt = (
            f"This is the person that owns the account: {self.user_info}, take this into account when giving advice.\n\n"
            "You are the Past Spending Advisor. Your job is to analyze the user's historical financial behavior and compare it in depth with others in similar financial situations (same income bracket, age group, location, etc.).\n\n"
            "You must:\n primarily use the tools available to you to do so."
            "1. Use the tools available to explore and break down the user's past spending into categories (e.g., groceries, transportation, subscriptions, entertainment, housing).\n"
            "2. For each category, compare the user's spending patterns against peer benchmarks.\n"
            "3. Highlight categories where the user is overspending or significantly underspending relative to similar users.\n"
            "4. For each such category, suggest specific and actionable recommendations (e.g., alternative providers, cheaper services, local discounts).\n\n"
            "If the user requests a breakdown, respond step-by-step by walking through each relevant category, beginning with the largest or most abnormal.\n"
            "Always check available values first using get_valid_filter_values(), and use all available tools before concluding.\n"
            "You are expected to reason like an analyst, not just summarize.\n\n"
            "Structure your responses clearly. You may use bullet points or headings per category. Only include categories relevant to the user’s transactions."
            "YOU MUST INCLUDE SNIPPETS OF THE DATA RETURNED USING THE TOOLS IN YOUR RESPONSE.\n\n"
        )


        future_advice_prompt = (
            f"This is the person that owns the account: {self.user_info}, take this into account.\n"
            "You are the Future Planning Advisor. The user is asking for financial guidance about a future action or goal.\n\n"
            "You must provide thorough, data-backed financial advice. Always consider the user's current situation and provide detailed, realistic recommendations Primarily by using the research tool\n\n"
            "When applicable (e.g., buying a car, house, moving, changing careers), do the following:\n"
            "1. Use location-specific data (e.g., local car insurance costs, housing prices, taxes) to guide your advice.\n"
            "2. Research the total cost of ownership, including recurring costs (e.g., maintenance, utilities, fuel, insurance).\n"
            "3. Suggest budgeting strategies, financing options (e.g., leasing vs. loans), and comparison benchmarks from users in similar financial situations.\n"
            "4. Use tools such as get_valid_filter_values() and relevant APIs when available. You are expected to research, not guess.\n\n"
            "Be structured in your response. Prioritize depth and actionability over brevity. You may use bullet points if helpful."
            "YOU MUST INCLUDE SNIPPETS OF THE DATA RETURNED USING THE TOOLS IN YOUR RESPONSE.\n\n"
        )


        general_prompt = (
            f"This is the person that owns the account: {self.user_info}, take this into account"
            "You are the General Advisor. The user is asking a general question or greeting. "
            "Your task is to provide a friendly and informative response. "
        )

        builder = StateGraph(AgentState)

        # Create all specialized agents
        orchestrator = create_react_agent(self.llm, tools=[], prompt=orchestrator_prompt, checkpointer=self.memory)
        past_advice_agent = create_react_agent(self.llm, tools=tools_past_advice, prompt=past_advice_prompt, checkpointer=self.memory)
        future_advice_agent = create_react_agent(self.llm, tools=tools_future_advice, prompt=future_advice_prompt, checkpointer=self.memory)
        general_agent = create_react_agent(self.llm, tools=[], prompt=general_prompt, checkpointer=self.memory)

        builder.add_node("orchestrator", orchestrator)
        builder.add_node("past_advice", past_advice_agent)
        builder.add_node("future_advice", future_advice_agent)
        builder.add_node("general_advice", general_agent)

        builder.set_entry_point("orchestrator")

        # Use our custom extraction function for routing with all three options
        builder.add_conditional_edges(
            "orchestrator", 
            self._extract_routing_decision,
            {
                "past": "past_advice",
                "future": "future_advice",
                "general": "general_advice",  
            }
        )

        # All specialized agents go to END
        builder.add_edge("past_advice", END)
        builder.add_edge("future_advice", END)
        
        # Build the graph
        self.graph = builder.compile()

        # Save graph visualization
        with open("graph.png", "wb") as f:
            f.write(self.graph.get_graph().draw_mermaid_png())


    def process_message(self, message, thread_id=None):
        """
        Processes a user message
        
        :param message: The user message to process.
        :param thread_id: The thread ID to use for the message.
        :return: The response from the agent.
        """
        try:
            # Create a human message
            human_msg = HumanMessage(content=message)

            # Run the graph with the correct config for checkpointer
            events = self.graph.stream(
                {"messages": [human_msg]},
                config={
                    "thread_id": thread_id,
                    "configurable": {"checkpointer": self.memory},
                    "recursion_limit": 10  
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
                        if len(content.split()) > 200:  # Roughly 2-3 sentences
                            content = " ".join(content.split()[:200]) + "..."
                        logger.log_agent_response(
                            "Bunq AI", content
                        )
                        return content
            return "I apologize, but I couldn't generate a proper response. Could you please rephrase your question?"
            
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            logger.log_agent_response("Bunq AI", error_msg)
            return error_msg
