from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from logger import log_tool_execution
import pandas as pd
import json
from datetime import datetime
from api_utils import extractTransaction

class TransactionAnalyzer:
    def __init__(self, transactions_path: str = None, bunq_api_key: str = None):
        self.transactions_path = transactions_path
        self.bunq_api_key = bunq_api_key
        self.transactions = self._load_transactions()

    def _load_transactions(self) -> List[Dict[str, Any]]:
        """Load and preprocess user transactions."""
        try:
            if self.transactions_path is None:
                transactions = extractTransaction(self.bunq_api_key)
            else:
                with open(self.transactions_path, 'r') as f:
                    transactions = json.load(f)
                return transactions
        except Exception as e:
            raise ValueError(f"Error loading transactions: {str(e)}")

    def get_transactions_summary(self) -> str:
        """Get a detailed summary of all transactions."""
        if not self.transactions:
            return "No transactions found."
            
        # Calculate total spending
        total_spent = sum(float(t.get('amount', 0)) for t in self.transactions)
        
        # Group transactions by month
        monthly_totals = {}
        for t in self.transactions:
            date_str = t.get('created_at', '')
            try:
                date = datetime.strptime(date_str, '%Y-%m-%dT%H:%M:%S.%fZ')
                month_key = date.strftime('%B %Y')
                amount = float(t.get('amount', 0))
                monthly_totals[month_key] = monthly_totals.get(month_key, 0) + amount
            except (ValueError, TypeError):
                continue
        
        # Format the summary
        summary = [
            f"Total Spending: {total_spent:.2f}",
            "\nMonthly Breakdown:"
        ]
        
        for month, total in sorted(monthly_totals.items()):
            summary.append(f"{month}: {total:.2f}")
            
        summary.append("\nRecent Transactions:")
        recent_transactions = sorted(
            self.transactions,
            key=lambda x: x.get('created_at', ''),
            reverse=True
        )[:5]  # Show last 5 transactions
        
        for t in recent_transactions:
            summary.append(
                f"Date: {t.get('created_at', 'N/A')}, "
                f"Amount: {t.get('amount', 'N/A')}, "
                f"Description: {t.get('description', 'N/A')}"
            )
            
        return "\n".join(summary)

@tool
@log_tool_execution
def analyze_user_spending(query: str) -> str:
    """
    Analyze user's spending patterns and provide a summary.
    
    Args:
        query: The user's query for context
        
    Returns:
        str: A formatted summary of the user's spending patterns
    """
    try:
        analyzer = TransactionAnalyzer()
        # return analyzer.get_transactions_summary()
        return analyzer._load_transactions()
            
    except Exception as e:
        return f"Error analyzing spending: {str(e)}"

# List of available tools
tools = [analyze_user_spending] 