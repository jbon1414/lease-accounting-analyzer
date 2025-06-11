import json
import re
from typing import Dict, Any, Union

def extract_classification(response: str) -> str:
    """
    Extract classification from LLM response and ensure it's either OPERATING or FINANCE.
    """
    # Clean the response
    cleaned_response = response.strip().upper()
    
    # Look for OPERATING or FINANCE in the response
    if "FINANCE" in cleaned_response:
        return "FINANCE"
    elif "OPERATING" in cleaned_response:
        return "OPERATING"
    
    # Try to find the words using regex (case insensitive)
    finance_match = re.search(r'\bFINANCE\b', cleaned_response, re.IGNORECASE)
    operating_match = re.search(r'\bOPERATING\b', cleaned_response, re.IGNORECASE)
    
    if finance_match:
        return "FINANCE"
    elif operating_match:
        return "OPERATING"
    
    # If we can't find either, try to parse first word
    first_word = cleaned_response.split()[0] if cleaned_response.split() else ""
    
    if first_word in ["FINANCE", "OPERATING"]:
        return first_word
    
    # Default fallback - you might want to handle this differently
    print(f"Warning: Could not extract valid classification from: '{response}'")
    return "OPERATING" 

def parse_llm_response_to_dict(response: str) -> Dict[str, Any]:
    """
    Parse LLM response and convert to dictionary with error handling.
    Updated to handle payment_dates as a dictionary.
    """
    # Try to parse as JSON first
    try:
        # Clean up common JSON formatting issues
        cleaned_response = response.strip()
        
        # Remove markdown code blocks if present
        if cleaned_response.startswith('```'):
            # Extract content between code blocks
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', cleaned_response, re.DOTALL)
            if match:
                cleaned_response = match.group(1).strip()
        
        # Parse JSON
        parsed_dict = json.loads(cleaned_response)
        
        # Validate and process expected keys
        expected_keys = ['start_date', 'end_date', 'commencement_date', 'execution_date', 'payment_dates']
        validated_dict = {}
        
        for key in expected_keys:
            if key in parsed_dict:
                if key == 'payment_dates':
                    # Ensure payment_dates is a dictionary
                    payment_data = parsed_dict[key]
                    if isinstance(payment_data, dict):
                        # Validate that keys are date strings and values are numbers
                        validated_payments = {}
                        for date_key, amount in payment_data.items():
                            try:
                                # Validate date format (basic check)
                                if re.match(r'\d{4}-\d{2}-\d{2}', str(date_key)):
                                    validated_payments[str(date_key)] = float(amount)
                                else:
                                    print(f"Warning: Invalid date format in payment_dates: {date_key}")
                            except (ValueError, TypeError):
                                print(f"Warning: Invalid amount in payment_dates: {amount}")
                        validated_dict[key] = validated_payments
                    elif isinstance(payment_data, list):
                        # Handle case where it's still returned as a list (backward compatibility)
                        print("Warning: payment_dates returned as list instead of dictionary")
                        validated_dict[key] = {str(date): 0.0 for date in payment_data if isinstance(date, str)}
                    else:
                        validated_dict[key] = {}
                else:
                    validated_dict[key] = parsed_dict[key]
            else:
                if key == 'payment_dates':
                    validated_dict[key] = {}
                else:
                    validated_dict[key] = None
        
        return validated_dict
        
    except json.JSONDecodeError:
        # If JSON parsing fails, try to extract key-value pairs manually
        return extract_dict_from_text(response)

def extract_dict_from_text(text: str) -> Dict[str, Any]:
    """
    Fallback method to extract dictionary-like information from text.
    Updated to handle payment_dates as a dictionary.
    """
    result = {
        'start_date': None,
        'end_date': None,
        'commencement_date': None,
        'execution_date': None,
        'payment_dates': {}
    }
    
    # Regular expressions to find date patterns
    date_pattern = r'\d{4}-\d{2}-\d{2}'
    
    # Look for simple date field patterns
    patterns = {
        'start_date': r'start_date[\'\":\s]*([\'\"]*\d{4}-\d{2}-\d{2}[\'\"]*)',
        'end_date': r'end_date[\'\":\s]*([\'\"]*\d{4}-\d{2}-\d{2}[\'\"]*)',
        'commencement_date': r'commencement_date[\'\":\s]*([\'\"]*\d{4}-\d{2}-\d{2}[\'\"]*)',
        'execution_date': r'execution_date[\'\":\s]*([\'\"]*\d{4}-\d{2}-\d{2}[\'\"]*)',
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            date_str = match.group(1).strip('\'"')
            result[key] = date_str
    
    # Extract payment_dates dictionary - look for dictionary/object patterns
    payment_dates_dict = {}
    
    # Try to find payment_dates as a dictionary/object
    payment_dict_match = re.search(r'payment_dates[\'\":\s]*\{(.*?)\}', text, re.DOTALL | re.IGNORECASE)
    if payment_dict_match:
        dict_content = payment_dict_match.group(1)
        # Look for key-value pairs in the dictionary content
        # Pattern to match "date": amount or 'date': amount
        pair_pattern = r'[\'\"]*(\d{4}-\d{2}-\d{2})[\'\"]*\s*:\s*([0-9]+\.?[0-9]*)'
        pairs = re.findall(pair_pattern, dict_content)
        
        for date_str, amount_str in pairs:
            try:
                payment_dates_dict[date_str] = float(amount_str)
            except ValueError:
                print(f"Warning: Could not convert amount to float: {amount_str}")
    
    # Fallback: look for payment_dates as a list (backward compatibility)
    if not payment_dates_dict:
        payment_dates_match = re.search(r'payment_dates[\'\":\s]*\[(.*?)\]', text, re.DOTALL | re.IGNORECASE)
        if payment_dates_match:
            dates_str = payment_dates_match.group(1)
            dates = re.findall(date_pattern, dates_str)
            # Convert to dictionary with 0.0 amounts
            payment_dates_dict = {date: 0.0 for date in dates}
    
    result['payment_dates'] = payment_dates_dict
    
    return result

def get_payment_dates_list(dates_dict: Dict[str, Any]) -> list:
    """
    Helper function to extract just the payment dates as a list from the dates dictionary.
    Useful for backward compatibility with existing code that expects a list.
    """
    payment_dates_dict = dates_dict.get('payment_dates', {})
    if isinstance(payment_dates_dict, dict):
        return list(payment_dates_dict.keys())
    elif isinstance(payment_dates_dict, list):
        return payment_dates_dict
    else:
        return []

def get_payment_amounts_list(dates_dict: Dict[str, Any]) -> list:
    """
    Helper function to extract just the payment amounts as a list from the dates dictionary.
    """
    payment_dates_dict = dates_dict.get('payment_dates', {})
    if isinstance(payment_dates_dict, dict):
        return list(payment_dates_dict.values())
    else:
        return []

def get_total_payments(dates_dict: Dict[str, Any]) -> float:
    """
    Helper function to calculate the total of all payments.
    """
    payment_dates_dict = dates_dict.get('payment_dates', {})
    if isinstance(payment_dates_dict, dict):
        return sum(payment_dates_dict.values())
    else:
        return 0.0
    

def extract_lease_details_dict(response: str) -> Dict[str, Any]:
   """
   Extract lease details dictionary from LLM response with error handling.
   """
   # Try to parse as JSON first
   try:
       # Clean up common JSON formatting issues
       cleaned_response = response.strip()
       
       # Remove markdown code blocks if present
       if cleaned_response.startswith('```'):
           # Extract content between code blocks
           match = re.search(r'```(?:json)?\s*(.*?)\s*```', cleaned_response, re.DOTALL)
           if match:
               cleaned_response = match.group(1).strip()
       
       # Parse JSON
       parsed_dict = json.loads(cleaned_response)
       
       # Validate expected keys and structure
       expected_keys = ['Address', 'Lessee', 'Lessor', 'Premise Description']
       validated_dict = {}
       
       for key in expected_keys:
           if key in parsed_dict and isinstance(parsed_dict[key], dict):
               # Validate that each entry has the expected sub-keys
               entry = parsed_dict[key]
               validated_entry = {
                   'value': entry.get('value', None),
                   'proof': entry.get('proof', None),
                   'section': entry.get('section', None)
               }
               validated_dict[key] = validated_entry
           else:
               # Create empty structure if key is missing
               validated_dict[key] = {
                   'value': None,
                   'proof': None,
                   'section': None
               }
       
       return validated_dict
       
   except json.JSONDecodeError:
       print(f"Warning: Could not parse JSON from response: {response[:100]}...")
       # Return empty structure if parsing fails
       return {
           'Address': {'value': None, 'proof': None, 'section': None},
           'Lessee': {'value': None, 'proof': None, 'section': None},
           'Lessor': {'value': None, 'proof': None, 'section': None},
           'Premise Description': {'value': None, 'proof': None, 'section': None}
       }
   
def extract_lease_options_dict(response: str) -> Dict[str, Any]:
    """
    Extract lease options dictionary from LLM response with error handling.
    """
    # Try to parse as JSON first
    try:
        # Clean up common JSON formatting issues
        cleaned_response = response.strip()
        
        # Remove markdown code blocks if present
        if cleaned_response.startswith('```'):
            # Extract content between code blocks
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', cleaned_response, re.DOTALL)
            if match:
                cleaned_response = match.group(1).strip()
        
        # Parse JSON
        parsed_dict = json.loads(cleaned_response)
        
        # Validate expected keys and structure
        expected_keys = ['Purchase Option', 'Renewal Option', 'Break Option', 'Security Deposit', 'Prepaid Rent']
        validated_dict = {}
        
        for key in expected_keys:
            if key in parsed_dict and isinstance(parsed_dict[key], dict):
                entry = parsed_dict[key]
                
                # Base structure for all options
                validated_entry = {
                    'value': entry.get('value', None),
                    'proof': entry.get('proof', None),
                    'section': entry.get('section', None)
                }
                
                # Additional fields for Security Deposit
                if key == 'Security Deposit':
                    validated_entry.update({
                        'amount': entry.get('amount', None),
                        'returned': entry.get('returned', None),
                        'applied': entry.get('applied', None)
                    })
                
                # Additional fields for Prepaid Rent
                elif key == 'Prepaid Rent':
                    validated_entry['amount'] = entry.get('amount', None)
                
                validated_dict[key] = validated_entry
            else:
                # Create empty structure if key is missing
                base_structure = {
                    'value': None,
                    'proof': None,
                    'section': None
                }
                
                # Add additional fields for specific keys
                if key == 'Security Deposit':
                    base_structure.update({
                        'amount': None,
                        'returned': None,
                        'applied': None
                    })
                elif key == 'Prepaid Rent':
                    base_structure['amount'] = None
                
                validated_dict[key] = base_structure
        
        return validated_dict
        
    except json.JSONDecodeError:
        print(f"Warning: Could not parse JSON from response: {response[:100]}...")
        # Return empty structure if parsing fails
        return {
            'Purchase Option': {'value': None, 'proof': None, 'section': None},
            'Renewal Option': {'value': None, 'proof': None, 'section': None},
            'Break Option': {'value': None, 'proof': None, 'section': None},
            'Security Deposit': {
                'value': None, 'proof': None, 'section': None,
                'amount': None, 'returned': None, 'applied': None
            },
            'Prepaid Rent': {'value': None, 'proof': None, 'section': None, 'amount': None}
        }

def extract_lease_financials_dict(response: str) -> Dict[str, Any]:
    """
    Extract lease financials dictionary from LLM response with error handling.
    """
    # Try to parse as JSON first
    try:
        # Clean up common JSON formatting issues
        cleaned_response = response.strip()
        
        # Remove markdown code blocks if present
        if cleaned_response.startswith('```'):
            # Extract content between code blocks
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', cleaned_response, re.DOTALL)
            if match:
                cleaned_response = match.group(1).strip()
        
        # Parse JSON
        parsed_dict = json.loads(cleaned_response)
        
        # Validate expected keys and structure
        expected_keys = ['Payment Due Date', 'Rent Payments', 'Rent Escalations', 'Percentage Rent']
        validated_dict = {}
        
        for key in expected_keys:
            if key in parsed_dict and isinstance(parsed_dict[key], dict):
                entry = parsed_dict[key]
                
                # Base structure for all financials
                validated_entry = {
                    'value': entry.get('value', None),
                    'proof': entry.get('proof', None),
                    'section': entry.get('section', None)
                }
                
                # Additional fields for Percentage Rent
                if key == 'Percentage Rent':
                    validated_entry['amount'] = entry.get('amount', None)
                
                validated_dict[key] = validated_entry
            else:
                # Create empty structure if key is missing
                base_structure = {
                    'value': None,
                    'proof': None,
                    'section': None
                }
                
                # Add additional fields for specific keys
                if key == 'Percentage Rent':
                    base_structure['amount'] = None
                
                validated_dict[key] = base_structure
        
        return validated_dict
        
    except json.JSONDecodeError:
        print(f"Warning: Could not parse JSON from response: {response[:100]}...")
        # Return empty structure if parsing fails
        return {
            'Payment Due Date': {'value': None, 'proof': None, 'section': None},
            'Rent Payments': {'value': None, 'proof': None, 'section': None},
            'Rent Escalations': {'value': None, 'proof': None, 'section': None},
            'Percentage Rent': {'value': None, 'proof': None, 'section': None, 'amount': None}
        }


def extract_lease_additional_terms_dict(response: str) -> Dict[str, Any]:
    """
    Extract lease additional terms dictionary from LLM response with error handling.
    """
    # Try to parse as JSON first
    try:
        # Clean up common JSON formatting issues
        cleaned_response = response.strip()
        
        # Remove markdown code blocks if present
        if cleaned_response.startswith('```'):
            # Extract content between code blocks
            match = re.search(r'```(?:json)?\s*(.*?)\s*```', cleaned_response, re.DOTALL)
            if match:
                cleaned_response = match.group(1).strip()
        
        # Parse JSON
        parsed_dict = json.loads(cleaned_response)
        
        # Validate expected keys and structure
        expected_keys = ['Taxes and Insurance', 'Brokerage Commissions', 'Lease Incentives', 'Rent Concessions']
        validated_dict = {}
        
        for key in expected_keys:
            if key in parsed_dict and isinstance(parsed_dict[key], dict):
                entry = parsed_dict[key]
                
                # Base structure for all additional terms
                validated_entry = {
                    'value': entry.get('value', None),
                    'proof': entry.get('proof', None),
                    'section': entry.get('section', None)
                }
                
                # Additional fields for Brokerage Commissions
                if key == 'Brokerage Commissions':
                    validated_entry.update({
                        'amount': entry.get('amount', None),
                        'responsible party': entry.get('responsible party', None)
                    })
                
                # Additional fields for Lease Incentives
                elif key == 'Lease Incentives':
                    validated_entry.update({
                        'amount': entry.get('amount', None),
                        'description': entry.get('description', None)
                    })
                
                # Additional fields for Rent Concessions
                elif key == 'Rent Concessions':
                    validated_entry.update({
                        'amount': entry.get('amount', None),
                        'description': entry.get('description', None)
                    })
                
                validated_dict[key] = validated_entry
            else:
                # Create empty structure if key is missing
                base_structure = {
                    'value': None,
                    'proof': None,
                    'section': None
                }
                
                # Add additional fields for specific keys
                if key == 'Brokerage Commissions':
                    base_structure.update({
                        'amount': None,
                        'responsible party': None
                    })
                elif key == 'Lease Incentives':
                    base_structure.update({
                        'amount': None,
                        'description': None
                    })
                elif key == 'Rent Concessions':
                    base_structure.update({
                        'amount': None,
                        'description': None
                    })
                
                validated_dict[key] = base_structure
        
        return validated_dict
        
    except json.JSONDecodeError:
        print(f"Warning: Could not parse JSON from response: {response[:100]}...")
        # Return empty structure if parsing fails
        return {
            'Taxes and Insurance': {'value': None, 'proof': None, 'section': None},
            'Brokerage Commissions': {
                'value': None, 'proof': None, 'section': None,
                'amount': None, 'responsible party': None
            },
            'Lease Incentives': {
                'value': None, 'proof': None, 'section': None,
                'amount': None, 'description': None
            },
            'Rent Concessions': {
                'value': None, 'proof': None, 'section': None,
                'amount': None, 'description': None
            }
        }