from typing import List, Dict, Any
from langchain_core.tools import tool
from logger import log_tool_execution
from duckduckgo_search import DDGS
import requests
import re
from urllib.parse import urlparse
import time

class WebSearchTool:
    """
    Performs web searches and analyzes the results.
    """
    def __init__(self, max_results: int = 5, max_retries: int = 3):
        """
        Initialize the WebSearchTool with a given maximum number of results and maximum number of retries.
        
        :param max_results: The maximum number of results to return.
        :param max_retries: The maximum number of retries for the search.
        """
        self.max_results = max_results
        self.max_retries = max_retries
        self.ddgs = DDGS()

    def search(self, query: str) -> List[Dict[str, str]]:
        """
        Perform a web search using DuckDuckGo.
        
        :param query: The search query.
        :return: A list of search results.
        """
        try:
            results = list(self.ddgs.text(query, max_results=self.max_results))
            return results
        except Exception as e:
            return [{"error": f"Search failed: {str(e)}"}]

    def is_relevant_content(self, text: str, query: str) -> bool:
        """
        Check if the content is relevant to the query.
        
        :param text: The content to check.
        :param query: The search query.
        :return: True if the content is relevant, False otherwise.
        """
        query_terms = set(re.findall(r'\w+', query.lower()))
        text_terms = set(re.findall(r'\w+', text.lower()))
        
        # Count matching terms
        matches = len(query_terms.intersection(text_terms))
        return matches >= len(query_terms) * 0.5  # At least 50% of query terms should match

@tool
@log_tool_execution
def financial_web_search(query: str, max_results: int = 5) -> str:
    """
    Perform a web search for financial information and analyze the results.
    
    Args:
        query: The search query
        max_results: Maximum number of results to process (default: 5)
        
    Returns:
        str: A summary of relevant financial information found
    """
    try:
        search_tool = WebSearchTool(max_results=max_results)
        
        # Perform the search
        search_results = search_tool.search(query)
        
        if "error" in search_results[0]:
            return search_results[0]["error"]
        
        # Process and analyze results
        relevant_content = []
        for result in search_results:
            # Check if content is relevant using title and snippet
            content = f"{result.get('title', '')} {result.get('body', '')}"
            if search_tool.is_relevant_content(content, query):
                relevant_content.append({
                    "title": result.get("title", ""),
                    "snippet": result.get("body", ""),
                    "url": result.get("link", "")
                })
        
        if not relevant_content:
            return "No relevant financial information found for your query."
        
        # Format the results
        formatted_results = []
        for item in relevant_content:
            formatted_results.append(
                f"Title: {item['title']}\n"
                f"Snippet: {item['snippet']}\n"
                f"URL: {item['url']}\n"
                "---\n"
            )
        
        return "\n".join(formatted_results)
        
    except Exception as e:
        return f"Error performing financial web search: {str(e)}"

# List of available tools
tools = [financial_web_search] 