from typing import List, Dict, Any, Optional
from langchain_core.tools import tool
from logger import log_tool_execution
import pandas as pd
import json

class ExpenseAnalyzer:
    def __init__(self, csv_path: str = "monthly_spending_by_age_group.csv"):
        self.csv_path = csv_path
        self.df = self._load_data()
        self._initialize_valid_values()

    def _load_data(self) -> pd.DataFrame:
        """Load and preprocess the expense data."""
        try:
            df = pd.read_csv(self.csv_path)
            # Ensure Category column is present
            if 'Category' not in df.columns:
                raise ValueError("CSV file must contain 'Category' column")
            
            # Get all age group columns
            self.age_columns = [col for col in df.columns if col != 'Category']
            
            # Convert all age group columns to numeric
            for col in self.age_columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
                
            return df
        except Exception as e:
            raise ValueError(f"Error loading CSV file: {str(e)}")

    def _initialize_valid_values(self):
        """Initialize lists of valid values for each filter."""
        self.valid_categories = sorted(self.df['Category'].unique().tolist())
        self.valid_age_groups = sorted(self.age_columns)

    def get_valid_values(self) -> Dict[str, List[str]]:
        """Return all valid values for each filter."""
        return {
            "expense_categories": self.valid_categories,
            "age_groups": self.valid_age_groups
        }

    def filter_data(
        self,
        category: Optional[str] = None,
        age_group: Optional[str] = None
    ) -> pd.DataFrame:
        """Filter the data based on provided criteria."""
        df = self.df.copy()
        
        if category:
            df = df[df['Category'].str.lower() == category.lower()]
            
        if age_group:
            if age_group not in self.age_columns:
                return pd.DataFrame()  # Return empty DataFrame for invalid age group
            df = df[['Category', age_group]]
            df = df.rename(columns={age_group: 'amount'})
            
        return df

    def get_summary_statistics(self, df: pd.DataFrame, age_group: Optional[str] = None) -> Dict[str, Any]:
        """Calculate summary statistics for the filtered data."""
        if df.empty:
            return {"message": "No data matches the specified criteria"}
            
        if age_group:
            # For specific age group, return the amount directly
            return {
                "category": df['Category'].iloc[0],
                "age_group": age_group,
                "amount": df['amount'].iloc[0]
            }
        else:
            # For category across all age groups
            stats = {}
            for age_col in self.age_columns:
                stats[age_col] = df[age_col].iloc[0]
            return stats

@tool
@log_tool_execution
def get_valid_filter_values() -> str:
    """
    Get all valid values for expense categories and age groups.
    Use this tool to understand what values are available in the dataset.
    
    Returns:
        str: A formatted list of valid values for each filter
    """
    try:
        analyzer = ExpenseAnalyzer()
        valid_values = analyzer.get_valid_values()
        
        result = [
            "Available filter values in the dataset:",
            "\nExpense Categories:",
            *[f"- {category}" for category in valid_values["expense_categories"]],
            "\nAge Groups:",
            *[f"- {age_group}" for age_group in valid_values["age_groups"]]
        ]
        
        return "\n".join(result)
    except Exception as e:
        return f"Error getting valid values: {str(e)}"

@tool
@log_tool_execution
def analyze_expenses(
    query: str,
    category: Optional[str] = None,
    age_group: Optional[str] = None
) -> str:
    """
    Analyze expense data based on the provided criteria.
    
    Important: Before using this tool, first call get_valid_filter_values() to see what values are available.
    Only use values that are listed in the valid values to ensure accurate results.
    
    Args:
        query: The user's query for context
        category: Optional expense category filter (must be one of the categories listed in get_valid_filter_values())
        age_group: Optional age group filter (must be one of the age groups listed in get_valid_filter_values())
        
    Returns:
        str: A formatted analysis of the expense data
    """
    try:
        analyzer = ExpenseAnalyzer()
        print("I AM HERE")
        # Filter the data
        filtered_df = analyzer.filter_data(category, age_group)
        
        # Get summary statistics
        stats = analyzer.get_summary_statistics(filtered_df, age_group)
        
        if stats.get("message"):
            return stats["message"]
            
        # Format the results
        if age_group:
            # Single age group result
            result = [
                f"Analysis Results:",
                f"Category: {stats['category']}",
                f"Age Group: {stats['age_group']}",
                f"Monthly Amount: {stats['amount']:.2f}"
            ]
        else:
            # All age groups for a category
            result = [
                f"Analysis Results for {category}:",
                f"Monthly amounts by age group:"
            ]
            for age_group, amount in stats.items():
                result.append(f"- {age_group}: {amount:.2f}")
        
        return "\n".join(result)
        
    except Exception as e:
        return f"Error analyzing expenses: {str(e)}"

# List of available tools
tools = [analyze_expenses, get_valid_filter_values] 