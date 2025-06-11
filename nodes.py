from typing import TypedDict
import datetime as dt
import streamlit as st
from pandas import DataFrame

from langgraph.graph import StateGraph, END #StateGraph manages info flow between components 
from langchain.prompts import PromptTemplate #this created consistent instructions
from langchain.schema import HumanMessage
from langchain_openai import ChatOpenAI # connected to OpenAI

from utils.dict import parse_llm_response_to_dict, extract_classification
from utils.ibr import calculate_dicount_rate

llm = ChatOpenAI(model="gpt-4o", temperature=0.0, max_tokens=4000, openai_api_key=st.secrets["OPENAI_API_KEY"])

# Memory for the agent
class State(TypedDict):

    text: str #stores the original input text
    classification: str #represents the lease classification result (e.g., "OPERATING", "FINANCE")
    dates: dict #stores a summarized version of the text
    discount_rate: float #stores the discount rate for present value calculations
    treasury_df: DataFrame #stores the treasury data used for discount rate calculations

def classification_node(state: State) -> State:
    """Classify the lease as OPERATING or FINANCE."""
    prompt = PromptTemplate(
        input_variables=["text"],
        template="""
        You are a lease accounting expert analyzing a lease document to determine its classification under ASC 842.

        LEASE CLASSIFICATION CRITERIA:
        A lease should be classified as a FINANCE LEASE if it meets ANY of the following criteria:

        a) The lease transfers ownership of the underlying asset to the lessee by the end of the lease term.
        b) The lease grants the lessee an option to purchase the underlying asset that the lessee is reasonably certain to exercise.
        c) The lease term is for the major part of the remaining economic life of the underlying asset. (Note: Don't use this criterion if the commencement date falls at or near the end of the economic life)
        d) The present value of lease payments and any guaranteed residual value equals or exceeds substantially all of the fair value of the underlying asset.
        e) The underlying asset is of such a specialized nature that it is expected to have no alternative use to the lessor at the end of the lease term.

        If NONE of these criteria are met, classify as OPERATING LEASE.
        
        IMPORTANT: Respond with ONLY one word - either "OPERATING" or "FINANCE". Do not include any explanation, reasoning, or additional text.
        
        Text to analyze: {text}"""
    )

    message = HumanMessage(content=prompt.format(text=state["text"]))
    raw_response = llm.invoke([message]).content.strip()
    
    # Extract and validate classification
    classification = extract_classification(raw_response)
    
    print(f"Raw response: {raw_response}")
    print(f"Extracted classification: {classification}")

    return {'classification': classification}

def dates_node(state: State) -> State:
    prompt = PromptTemplate(
        input_variables=["text"],
        template="""
        You are a lease accounting expert analyzing a lease document to determine its classification under ASC 842.

        Provide the result as a JSON dictionary with the following keys:
        - 'start_date': The start date of the lease as a string in the format 'YYYY-MM-DD'.
        - 'end_date': The end date of the lease as a string in the format 'YYYY-MM-DD'.
        - 'commencement_date': The commencement date of the lease as a string in the format 'YYYY-MM-DD'.
        - 'execution_date': lease execution or signing date as a string in the format 'YYYY-MM-DD'.
        - 'payment_dates': A python dictionary with keys as every payment date (PER MONTH UNLESS OTHERWISE STATED) as strings in the format 'YYYY-MM-DD' and values as the amount of the payment with ANY % INCREASE ALREADY CALCULATED as a float.
        
        Return only valid JSON without any additional text or formatting.

        Text to analyze: {text}
        """
    )

    message = HumanMessage(content=prompt.format(text=state["text"]))
    raw_response = llm.invoke([message]).content.strip()

    # Handle the dictionary response and ensure it is in the correct format
    dates_dict = parse_llm_response_to_dict(raw_response)
    print(dates_dict)
    
    return {'dates': dates_dict}


def discount_rate_node(state: State) -> State:
    """Determine the discount rate based on the classification."""
    if state["classification"] == "FINANCE":
        prompt = PromptTemplate(
            input_variables=["text"],
            template="""
            You are a lease accounting expert determining the discount rate for a finance lease.
            THE ONLY THING THAT SHOuLD BE RETURNED IS THE DISCOUNT RATE as a python float.
            A lessee should use the rate implicit in the lease whenever that rate is readily determinable.
            If that rate cannot be readily determined, the lessee should use its incremental borrowing rate, return a 0 if so.
            Please provide the discount rate as a python float representing a percentage (e.g., 5.0 for 5%):\n{text}"""
        ) #TODO: Check with anthony on differences
    else:
        prompt = PromptTemplate(
            input_variables=["text"],
            template="""
            You are a lease accounting expert determining the discount rate for an operating lease.
            THE ONLY THING THAT SHOuLD BE RETURNED IS THE DISCOUNT RATE as a python float with nothing else.
            A lessee should use the rate implicit in the lease whenever that rate is readily determinable.
            If that rate cannot be readily determined, the lessee should use its incremental borrowing rate, return a 0 if so.
            Please provide the discount rate as a python float representing a percentage (e.g., 5.0 for 5%):\n{text}"""
        )
    message = HumanMessage(content=prompt.format(text=state["text"]))
    discount_rate = float(llm.invoke([message]).content.strip())

    if discount_rate == 0:
        discount_rate, treasure_df = calculate_dicount_rate(
            state['dates']['commencement_date'], 
            len(state['dates']['payment_dates'])
        )

    return {'discount_rate': discount_rate, 'treasury_df': treasure_df} 

def app(State):
    workflow = StateGraph(State)

    # Add nodes to the graph
    workflow.add_node("classification_node", classification_node)
    workflow.add_node("dates_node", dates_node)
    workflow.add_node("discount_rate_node", discount_rate_node)

    workflow.set_entry_point('classification_node')
    workflow.add_edge('classification_node', 'dates_node')
    workflow.add_edge('dates_node', 'discount_rate_node')
    workflow.add_edge('discount_rate_node', END)

    app = workflow.compile()
    return app
