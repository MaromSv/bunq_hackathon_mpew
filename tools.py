import io
import contextlib
import traceback
from langchain_core.tools import tool
from logger import log_tool_execution
import requests
from web_search_tools import tools as web_search_tools
from expense_analysis_tools import tools as expense_analysis_tools
from transaction_analysis_tools import tools as transaction_analysis_tools

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
tools_past_advice = expense_analysis_tools + transaction_analysis_tools
tools_future_advice = transaction_analysis_tools + web_search_tools