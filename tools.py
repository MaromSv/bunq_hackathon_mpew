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

# Tools for analyzing past spending and transactions
tools_past_advice = other_people_expenses_tools, user_transactions_tools
tools_future_advice = web_search_tools