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
        self.llm = llm
        self.agents = {}
        self.memory = MemorySaver()
        self.user_info = extractUserInformation(os.getenv("BUNQ_API_KEY"))
        self._setup_graph()

    def _extract_routing_decision(self, state):
        """Extract routing decision from the agent's output"""
            
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
        """Setup a multi-agent LangGraph workflow"""
        
        # Define prompts
        orchestrator_prompt = (
            f"This is the person that owns the account: {self.user_information} "
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
            "You are the Past Spending Advisor. You analyze the user's past financial behaviors, "
            "including transactions, spending habits, and demographic comparisons. "
            "Use the tools available to you to identify where the user could optimize or reduce expenses. "
            "Make specific and practical suggestions based on their history, such as changing where they shop, "
            "adjusting subscriptions, or following trends from people in similar financial situations. "
            "When using expense analysis tools, always check available values first using get_valid_filter_values().\n\n"
            "For questions about affordability, first analyze the user's current spending patterns and then "
            "compare them with typical expenses in their demographic group. Provide specific recommendations "
            "based on the data and suggest ways to optimize their budget if needed.\n\n"
            "Keep your responses concise and focused. Limit responses to 2-3 sentences maximum."
        )

        future_advice_prompt = (
            "You are the Future Planning Advisor. The user is asking for financial guidance about a future action or goal. "
            "Use the tools available to you to help the user by providing them financial advice on future purchases. "
            "When using expense analysis tools, always check available values first using get_valid_filter_values().\n\n"
            "For questions about major purchases like cars or homes, first analyze the typical expenses in the user's "
            "demographic group, then provide specific advice about budgeting, saving strategies, and potential financing options. "
            "Always consider the user's current financial situation and provide realistic recommendations.\n\n"
            "Keep your responses concise and focused. Limit responses to 2-3 sentences maximum."
        )

        general_prompt = (
            "You are the General Advisor. The user is asking a general question or greeting. "
            "Your task is to provide a friendly and informative response. "
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
        """Process a user message"""
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
