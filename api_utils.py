from bunq.sdk.context.api_context import ApiContext
from bunq.sdk.context.bunq_context import BunqContext
from bunq import ApiEnvironmentType
from bunq.sdk.model.generated.endpoint import MonetaryAccountBankApiObject, PaymentApiObject,BunqMeTabResultResponseApiObject,BunqMeTabApiObject, BunqMeTabEntryApiObject, BunqMeTabEntryApiObject
from bunq.sdk.model.generated.object_ import AmountObject, PointerObject, NotificationFilterObject
from bunq import Pagination
from typing import List, Dict, Optional, Union
import time
import json
from agno.agent import Agent
from agno.models.openai import OpenAIChat
from agno.tools.reasoning import ReasoningTools
from agno.team import Team

def extractUserInformation(api_key: str) -> List[str]:
    """
    Extracts user information from the given API key.
    
    Args:
        str (str): The string containing the API key of a user.
    
    Returns:
        List[str]: A list of json formatted strings containing user information.
    """

    api_context = ApiContext.create(
    ApiEnvironmentType.SANDBOX, # SANDBOX for testing
    api_key,
    "My Device Description"
    )

    api_context.save("bunq_api_context.conf")
    BunqContext.load_api_context(api_context)
    user_context = BunqContext.user_context()

    user_details = {
    "city": user_context.user_person.address_main.city,
    "country": user_context.user_person.address_main.country,
    "date_of_birth": user_context.user_person.date_of_birth,
    "gender": user_context.user_person.gender
    }

    return json.dumps(user_details, indent=4)
    


def extractTransaction(api_key: str) -> List[str]:
    """
    Extracts transactions from the primary account of the given user.
    
    Args:
        str (str): The string containing the API key of a user
        
    Returns:
        List[str]: A list of json formatted strings containing transaction details.
    """
    
    api_context = ApiContext.create(
    ApiEnvironmentType.SANDBOX, # SANDBOX for testing
    api_key,
    "My Device Description"
    )

    api_context.save("bunq_api_context.conf")
    BunqContext.load_api_context(api_context)

    transactionList = []

    for i in range(len(PaymentApiObject.list().value)):
        transactionList.append(PaymentApiObject.list().value[i].to_json())

    print(f"Total transactions: {len(transactionList)}")
    return transactionList

# Define specialized agents
class FinancialAgents:
    def __init__(self, llm):
        # Analysis Agent - Handles financial analysis
        self.analysis_agent = Agent(
            name="analysis_agent",
            role="financial_analyst",
            model=llm,
            tools=[ReasoningTools()],
            instructions=[
                "Analyze spending patterns and financial data",
                "Compare with demographic averages",
                "Identify trends and anomalies",
                "Provide clear, data-driven insights"
            ],
            show_tool_calls=True,
            markdown=True
        )

        # Transaction Agent - Processes transactions
        self.transaction_agent = Agent(
            name="transaction_agent",
            role="transaction_processor",
            model=llm,
            tools=[ReasoningTools()],
            instructions=[
                "Process and categorize transactions",
                "Detect spending patterns",
                "Identify unusual transactions",
                "Calculate key metrics"
            ],
            show_tool_calls=True,
            markdown=True
        )

        # Advice Agent - Provides recommendations
        self.advice_agent = Agent(
            name="advice_agent",
            role="financial_advisor",
            model=llm,
            tools=[ReasoningTools()],
            instructions=[
                "Generate personalized financial advice",
                "Suggest improvements based on analysis",
                "Provide actionable recommendations",
                "Consider user's financial goals"
            ],
            show_tool_calls=True,
            markdown=True
        )

        # Create the team
        self.team = Team(
            mode="coordinate",
            members=[
                self.analysis_agent,
                self.transaction_agent,
                self.advice_agent
            ],
            model=llm,
            success_criteria="A comprehensive financial analysis with clear insights and actionable recommendations.",
            instructions=[
                "Coordinate between agents to provide complete financial advice",
                "Ensure all aspects of the analysis are covered",
                "Present findings in a clear, structured manner"
            ],
            show_tool_calls=True,
            markdown=True
        )

    async def process_message(self, message: str) -> str:
        """Process a user message through the agent team"""
        try:
            # Process through the team
            response = await self.team.process(
                message,
                stream=True,
                show_full_reasoning=True
            )
            
            return response

        except Exception as e:
            return f"Error processing message: {str(e)}"