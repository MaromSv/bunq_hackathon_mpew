import io
import contextlib
import traceback
from langchain_core.tools import tool
from logger import log_tool_execution
import requests
from web_search_tools import tools as web_search_tools
from other_people_expenses_tools import tools as other_people_expenses_tools
from user_transactions_tools import tools as user_transactions_tools

from langchain_core.tools import tool

@tool
@log_tool_execution
def bunq_api_tool(input: str) -> str:
    """Access the Bunq API to retrieve relevant financial data of the user."""
    print("Accessing Bunq API...")
    return f"[Bunq API] Accessing Bunq for: {input}"


@tool
@log_tool_execution
def comparator_tool(input: str) -> str:
    """Compare previous purchases to identify patterns or savings."""
    print("Comparing previous purchases...")
    return f"[Comparator] Comparing previous purchases for: {input}"


@tool
@log_tool_execution
def research_tool(input: str) -> str:
    """Look up how much items cost on the internet."""
    print("Researching future purchases...")
    return f"[Research Tool] Looking up future purchases for: {input}"


# Tools for analyzing past spending and transactions
tools_past_advice = other_people_expenses_tools + user_transactions_tools
tools_future_advice = user_transactions_tools + web_search_tools