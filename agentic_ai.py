from langchain_core.messages import HumanMessage, AIMessage
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
# from langgraph.prebuilt.chat_agent_executor import AgentState
from langgraph.graph import StateGraph, START, END, MessagesState
from langgraph.graph.message import add_messages
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langgraph.types import Send
import os
import json
from logger import logger
import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from tools import tools

@dataclass
class AgentState:
    todo_list: List[str] = field(default_factory=list)
    completed_tasks: Dict[str, str] = field(default_factory=dict)
    current_task: Optional[str] = None
    user_data: Optional[dict] = field(default_factory=dict)  # Demographic, transaction info, etc.


class FinancialAdviceAIAgent:
    """Financial advice autonomous AI Agent"""

    def __init__(self, llm):
        self.llm = llm
        self.agents = {}
        self.memory = MemorySaver()
        self._setup_graph()

    # 2. Task completion checker
    def _check_if_all_tasks_done(self, state: AgentState) -> str:
        print("asdsadd...")
        if not state.todo_list:
            return "end"
        if len(state.completed_tasks) == len(state.todo_list):
            return "end"
        return "continue"
    
    def orchestrator_agent(self, state: AgentState) -> AgentState:
        wrote = False

        print("helo...")
        # 1. Generate todo list if needed
        if not state.todo_list:
            print("Generating todo list...")
            user_info = "\n".join([f"{k}: {v}" for k, v in state.user_data.items()])
            prompt = (
                "You are an orchestrator agent responsible for assigning financial advice tasks to a worker agent.\n"
                "Based on the following user data, list 3–5 specific financial analysis tasks that would help provide "
                "actionable advice. Respond with a Python list of short task strings only (no extra text).\n\n"
                f"User Data:\n{user_info}"
            )
            todo_list_response = self.llm.invoke(prompt)

            try:
                tasks = eval(todo_list_response)
                if isinstance(tasks, list) and all(isinstance(t, str) for t in tasks):
                    state.todo_list = tasks  # ✅ reassign tracked field
                else:
                    state.todo_list = []
                wrote = True
            except Exception:
                state.todo_list = []
                wrote = True

        # 2. Assign a new current task
        for task in state.todo_list:
            if task not in state.completed_tasks:
                state.current_task = task
                wrote = True
                break

        # 3. If nothing was updated, write dummy
        if not wrote:
            state.current_task = state.current_task  # force a write

        return state


            

    def worker_agent(self, state: AgentState) -> AgentState:
        print("heloadadasd...")
        task = state.current_task
        if not task:
            state.current_task = None  # write something to tracked state
            return state

        user_info = "\n".join([f"{k}: {v}" for k, v in state.user_data.items()])
        prompt = (
            f"You are a financial advisor. Based on the user data below, complete the task: {task}.\n\n"
            f"User Data:\n{user_info}"
        )

        result = self.llm.invoke(prompt)

        # ✅ Reassign the dict to trigger state write
        updated = dict(state.completed_tasks)
        updated[task] = result
        state.completed_tasks = updated

        state.current_task = None  # also tracked
        return state






    def _setup_graph(self):
        """Setup a multi-agent chaining LangGraph workflow"""

        # Create the graph
        builder = StateGraph(AgentState)

        # Register your custom Python functions as agent nodes
        builder.add_node("orchestrator", self.orchestrator_agent)
        builder.add_node("worker", self.worker_agent)

        builder.set_entry_point("orchestrator")

        # Loop between orchestrator and worker
        builder.add_edge("worker", "orchestrator")

        # Conditional: stop when done
        builder.add_conditional_edges(
            "orchestrator",
            self._check_if_all_tasks_done,
            {
                "continue": "worker",
                "end": END
            }
        )

        self.graph = builder.compile()  # Ensure the graph is compiled

        # Save graph visualization
        with open("graph.png", "wb") as f:
            f.write(self.graph.get_graph().draw_mermaid_png())

        # Ensure that the graph has a valid entry point and is compiled correctly
        assert self.graph is not None, "Graph compilation failed"
        print("Graph setup complete and compiled")



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
                    "recursion_limit": 3  # Further reduced to prevent loops
                },
            )

            # Collect all messages
            print("1...")
            messages = []
            for event in events:
                for _, node_output in event.items():
                    messages.extend(node_output.get("messages", []))

            # Return the last AI message content
            ai_messages = [m for m in messages if isinstance(m, AIMessage)]

            print("2...")
            if ai_messages:
                # Get the last non-empty message
                for msg in reversed(ai_messages):
                    if msg.content.strip():
                        # Limit response length
                        content = msg.content
                        if len(content.split()) > 50:  # Roughly 2-3 sentences
                            content = " ".join(content.split()[:50]) + "..."
                        logger.log_agent_response(
                            "Bunq AI", content
                        )
                        return content
            return "I apologize, but I couldn't generate a proper response. Could you please rephrase your question?"
            
        except Exception as e:
            error_msg = f"Error processing message: {str(e)}"
            logger.log_agent_response("Bunq AI", error_msg)
            return error_msg
