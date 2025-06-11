from typing import TypedDict
import datetime as dt
import streamlit as st

from langgraph.graph import StateGraph, END #StateGraph manages info flow between components 
from langchain.prompts import PromptTemplate #this created consistent instructions
from langchain.schema import HumanMessage
from langchain_openai import ChatOpenAI # connected to OpenAI

from utils.dict import *

llm = ChatOpenAI(model="gpt-4o", temperature=0.0, max_tokens=4000, openai_api_key=st.secrets["OPENAI_API_KEY"])

# Memory for the agent
class State2(TypedDict):

    text: str #stores the original input text
    terms_conditions_details: dict 
    terms_conditions_options: dict
    terms_conditions_financials: dict
    terms_conditions_additional: dict

def lease_details_node(state: State2) -> State2:
    """Extract the lease terms and conditions details."""
    prompt = PromptTemplate(
        input_variables=["text"],
        template="""
        You are a lease accounting expert analyzing a lease document to determine details of the lease for the terms and conditions section under ASC 842.

        Provide the result as a JSON dictionary with the following keys:
        {{
        "Address": {{"value": "property address", "proof": "description extracted from the text", "section": "Lease section or page number"}},
        "Lessee": {{"value": "lessee or tenant name", "proof": "description extracted from the text", "section": "Lease section or page number"}},
        "Lessor": {{"value": "lessor or landlord name", "proof": "description extracted from the text", "section": "Lease section or page number"}},
        "Premise Description": {{"value": "description of the premises or description of rentable space", "proof": "description  extracted from the text", "section": "Lease section or page number"}}
        }}

        Return only valid JSON without any additional text or formatting.

        Text to analyze: {text}
        """
    )

    message = HumanMessage(content=prompt.format(text=state["text"]))
    raw_response = llm.invoke([message]).content.strip()
    
    # Extract and validate lease details
    lease_details = extract_lease_details_dict(raw_response)

    return {'terms_conditions_details': lease_details}

def lease_options_node(state: State2) -> State2:
    prompt = PromptTemplate(
        input_variables=["text"],
        template="""
        You are a lease accounting expert analyzing a lease document to determine its classification under ASC 842.

        Provide the result as a JSON dictionary with the following keys:
        {{
            "Purchase Option": {{"value": "whether there is a purchase option (yes/no)", "proof": "description extracted from the text", "section": "Lease section or page number"}},
            "Renewal Option": {{"value": "whether there is a renewal option (yes/no)", "proof": "description extracted from the text", "section": "Lease section or page number"}},
            "Break Option": {{"value": "whether there is a break option or termination clause or opt-out clause, this includes any default by the tenant (yes/no)", "proof": "description of any break option or termination clause or opt-out clause, including any description for tenant defaults", "section": "Lease section or page number"}},
            "Security Deposit": {{"value": "whether there is a security deposit (yes/no)", "proof": "description extracted from the text and include information on what the security deposit represents such as going towards rent or other expenses or if the lessee will have the deposit returned", "section": "Lease section or page number", "amount": "amount of security deposit if applicable", "returned": "whether the security deposit is returned to the lessee at the end of the lease (yes/no)", "applied": "whether the security deposit is applied to the last month of rent (yes/no)"}},
            "Prepaid Rent": {{"value": "whether there is prepaid rent (yes/no)", "proof": "description extracted from the text includes any payment owed by the lessee upon execution of the lease if the lease execution is before the start of the lease term", "section": "Lease section or page number", "amount": "amount of prepaid rent if applicable"}}
        }}
        Return only valid JSON without any additional text or formatting.

        Text to analyze: {text}
        """
    )

    message = HumanMessage(content=prompt.format(text=state["text"]))
    raw_response = llm.invoke([message]).content.strip()

    # Extract and validate lease options
    options_dict = extract_lease_options_dict(raw_response)
    
    return {'terms_conditions_options': options_dict}

def lease_financials_node(state: State2) -> State2:
    prompt = PromptTemplate(
        input_variables=["text"],
        template="""
        You are a lease accounting expert analyzing a lease document to determine its classification under ASC 842.

        Provide the result as a JSON dictionary with the following keys:
        {{
            "Payment Due Date": {{"value": "rent payment due date description or period", "proof": "description extracted from the text", "section": "Lease section or page number"}},
            "Rent Payments": {{"value": "description of rent payments or payments per each date in the lease term (ie monthly payment amount by month) noting the amount of any increases in rent over the lease term", "proof": "description extracted from the text", "section": "Lease section or page number"}},
            "Rent Escalations": {{"value": "description of any rent escalations or deecalations, meaning an increase or decrease in rent during the lease term, including the amount and the period(s) in which they cover", "proof": "lease section reference for rent escalations", "section": "Lease section or page number"}},
            "Percentage Rent": {{"value": "whether there is percentage rent where part of rent owed is based on the sales or other determinable factors outlined in the lease (yes/no)", "proof": "description extracted from the text", "section": "Lease section or page number", "amount": "percentage of rent if applicable"}}
        }}
        Return only valid JSON without any additional text or formatting.

        Text to analyze: {text}
        """
    )

    message = HumanMessage(content=prompt.format(text=state["text"]))
    raw_response = llm.invoke([message]).content.strip()

    # Extract and validate lease financials
    financials_dict = extract_lease_financials_dict(raw_response)
    
    return {'terms_conditions_financials': financials_dict}

def lease_additional_terms_node(state: State2) -> State2:
    prompt = PromptTemplate(
        input_variables=["text"],
        template="""
        You are a lease accounting expert analyzing a lease document to determine its classification under ASC 842.

        Provide the result as a JSON dictionary with the following keys:
        {{
            "Taxes and Insurance": {{"value": "description of taxes and insurance terms, including the tenants proportionate share, if noted for taxes and the amount of insurance coverage required by the lessee", "proof": "description extracted from the text", "section": "Lease section or page number"}},
            "Brokerage Commissions": {{"value": "whether there are brokerage commissions (yes/no)", "proof": "description extracted from the text", "section": "Lease section or page number", "amount": "amount of brokerage commissions as a float if applicable", "responsible party": "who is responsible for the brokerage commissions, if commissions are strictly between landlord and broker note that they have no impact on the lease schedule for the lessor"}},
            "Lease Incentives": {{"value": "whether there are lease incentives , tenant improvement allowance, relocation cost coverage, signing bonus, cash payments, furnished space, cash returns of any kind,  or free equipment (yes/no)", "proof": "lease section reference for rent escalations", "section": "Lease section or page number", "amount": "lease incentives amount, if not provided calculate based on the allowance per square foot and the total square footage of the rentable space", "description": "description of any lease incentives such as free rent, tenant improvement allowances, or other concessions provided by the lessor to the lessee"}},
            "Rent Concessions": {{"value": "whether there are rent concessions including rent abatement (free rent), capped common area maintenance charges, or reduced rental periods (yes/no)", "proof": "description extracted from the text", "section": "Lease section or page number", "amount": "rent concession amount if applicable", "description": "description of any rent concessions including rent abatement (free rent), capped common area maintenance charges, or reduced rental periods"}}
        }}
        Return only valid JSON without any additional text or formatting.

        Text to analyze: {text}
        """
    )

    message = HumanMessage(content=prompt.format(text=state["text"]))
    raw_response = llm.invoke([message]).content.strip()

    # Extract and validate lease additional terms
    additional_terms_dict = extract_lease_additional_terms_dict(raw_response)
    
    return {'terms_conditions_additional': additional_terms_dict}

def app_2(State2):
    workflow = StateGraph(State2)

    # Add nodes to the graph
    workflow.add_node("lease_details_node", lease_details_node)
    workflow.add_node("lease_options_node", lease_options_node)
    workflow.add_node("lease_financials_node", lease_financials_node)
    workflow.add_node("lease_additional_terms_node", lease_additional_terms_node)

    workflow.set_entry_point('lease_details_node')
    workflow.add_edge('lease_details_node', 'lease_options_node')
    workflow.add_edge('lease_options_node', 'lease_financials_node')
    workflow.add_edge('lease_financials_node', 'lease_additional_terms_node')   
    workflow.add_edge('lease_additional_terms_node', END)

    app = workflow.compile()
    return app
