from bunq.sdk.context.api_context import ApiContext
from bunq.sdk.context.bunq_context import BunqContext
from bunq import ApiEnvironmentType
from bunq.sdk.model.generated.endpoint import MonetaryAccountBankApiObject, PaymentApiObject,BunqMeTabResultResponseApiObject,BunqMeTabApiObject, BunqMeTabEntryApiObject, BunqMeTabEntryApiObject
from bunq.sdk.model.generated.object_ import AmountObject, PointerObject, NotificationFilterObject
from bunq import Pagination
from typing import List, Dict, Optional, Union
import time
import json

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
    "gender": user_context.user_person.gender,
    "user_legal_name": user_context.user_person.legal_name
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