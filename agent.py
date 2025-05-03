from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.graph.message import add_messages
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.types import Send
import os

from tools import tools_past_advice, tools_future_advice
from logger import logger
import datetime
import json



class FinancialAdviceAIAgent:
    """Financial advice autonomous AI Agent"""


    def __init__(self, llm):
        self.llm = llm
        self.agents = {}
        self.memory = MemorySaver()
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
                    # For backward compatibility
                    if routing_decision not in ["past", "future"]:
                        state["routing_decision"] = "general"
                        return "general"
                    state["routing_decision"] = routing_decision
                    return routing_decision
        except (json.JSONDecodeError, KeyError, TypeError):
            # If we can't parse JSON or find routing_decision, check for keywords
            pass            
            # If we can't clearly determine, route to general
            state["routing_decision"] = "general"
            return "general"
        
        # Default fallback
        state["routing_decision"] = "general"
        return "general"


    def _setup_graph(self):
        """Setup a multi-agent LangGraph workflow"""
        
        # Define prompts
        orchestrator_prompt = (
            "You are the orchestrator agent. A user provides a financial question or request. "
            "Your job is to: (1) understand the user's intent, (2) plan a strategy to answer it, and "
            "(3) decide whether the request is about *past behavior* (e.g., spending, expenses), *future planning* (e.g., saving, investing), "
            "or *general inquiry* (greetings, general questions not specific to finances). "
            "Return a JSON with two keys:\n"
            "  - 'routing_decision': either 'past', 'future', or 'general'\n"
            "  - 'messages': your internal reasoning or summary (a short message for the user)\n"
            "Example output:\n"
            "{\"routing_decision\": \"past\", \"messages\": [\"Your request seems focused on spending habits. I'll connect you with our past behavior advisor.\"]}"
        )

        past_advice_prompt = (
            "You are the Past Spending Advisor. You analyze the user's past financial behaviors, "
            "including transactions, spending habits, and demographic comparisons. "
            "Use the tools available to you to identify where the user could optimize or reduce expenses. "
            "Make specific and practical suggestions based on their history, such as changing where they shop, "
            "adjusting subscriptions, or following trends from people in similar financial situations."
        )

        future_advice_prompt = (
            "You are the Future Planning Advisor. The user is asking for financial guidance about a future action or goal. "
            "Use the tools available to you to help the user by providing them financial advice on future purchases "
        )
        


        builder = StateGraph(AgentState)

        # Create all specialized agents
        orchestrator = create_react_agent(self.llm, tools=[], prompt=orchestrator_prompt, checkpointer=self.memory)
        past_advice_agent = create_react_agent(self.llm, tools=tools_past_advice, prompt=past_advice_prompt, checkpointer=self.memory)
        future_advice_agent = create_react_agent(self.llm, tools=tools_future_advice, prompt=future_advice_prompt, checkpointer=self.memory)


        builder.add_node("orchestrator", orchestrator)
        builder.add_node("past_advice", past_advice_agent)
        builder.add_node("future_advice", future_advice_agent)


        builder.set_entry_point("orchestrator")

        # Use our custom extraction function for routing with all three options
        builder.add_conditional_edges(
            "orchestrator", 
            self._extract_routing_decision,
            {
                "past": "past_advice",
                "future": "future_advice",
                "general": "orchestrator",
            }
        )

        # All specialized agents go to END
        builder.add_edge("past_advice", END)
        builder.add_edge("future_advice", END)
     

        # Build the graph
        self.graph = builder.compile()

        with open("graph.png", "wb") as f:
            f.write(self.graph.get_graph().draw_mermaid_png())

        # Then open it manually or via code
        os.startfile("graph.png")  # Windows only

    # Update the process_message method as well
    def process_message(self, message, thread_id=None):
        """Process a user message"""
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
                
        #return messages

         # Return the last AI message content
        ai_messages = [m for m in messages if isinstance(m, AIMessage)]

        if ai_messages:
            logger.log_agent_response(
                "Bunq AI", ai_messages[-1].content
            )
            return ai_messages[-1].content
        return "No response from Bunq AI."
