from openai import OpenAI
import json
import pandas as pd
from typing import Dict, Any, Tuple

def classify_lease(extracted_text: str, openai_api_key: str) -> Dict[str, Any]:
    """
    Classifies a lease as Operating, Finance, or requests help deciding based on the lease text.

    Args:
        extracted_text (str): The full text extracted from the lease document
        openai_api_key (str): OpenAI API key for GPT analysis

    Returns:
        Dict containing classification, reasoning, and supporting evidence
    """

    # Set up OpenAI client
    client = OpenAI(api_key=openai_api_key)

    # Create the analysis prompt
    analysis_prompt = f"""
        You are a lease accounting expert analyzing a lease document to determine its classification under ASC 842.

        LEASE CLASSIFICATION CRITERIA:
        A lease should be classified as a FINANCE LEASE if it meets ANY of the following criteria:

        a) The lease transfers ownership of the underlying asset to the lessee by the end of the lease term.
        b) The lease grants the lessee an option to purchase the underlying asset that the lessee is reasonably certain to exercise.
        c) The lease term is for the major part of the remaining economic life of the underlying asset. (Note: Don't use this criterion if the commencement date falls at or near the end of the economic life)
        d) The present value of lease payments and any guaranteed residual value equals or exceeds substantially all of the fair value of the underlying asset.
        e) The underlying asset is of such a specialized nature that it is expected to have no alternative use to the lessor at the end of the lease term.

        If NONE of these criteria are met, classify as OPERATING LEASE.

        If you cannot definitively determine the classification due to missing information, respond with "HELP_DECIDING" and explain what additional information is needed.

        LEASE DOCUMENT TEXT:
        {extracted_text}

        Please analyze this lease document and provide your response in the following JSON format and include section references from the lease document to support your analysis if possible:

        {{
            "classification": "OPERATING" | "FINANCE" | "HELP_DECIDING",
            "confidence": "HIGH" | "MEDIUM" | "LOW",
            "reasoning": "Detailed explanation of your analysis and decision",
            "key_lease_terms": {{
                "address: "Location of leased asset",
                "lessor": "Lessor or landloard name",
                "lessee": "Lessee or Tenant name",
                "description_of_premises": "description of the premises or description of rentable space",
                "lease_term": "lease term description or period of the lease in years and including start and end dates and any renewal options",
                "execution_date": "lease execution or signing date",
                "commencement_date": "   lease commencement date meaning the date of access per the lease, if none is explicitly stated then pose this as a question. Also check to see If the lease notes that access is granted upon execution then utilize the signing date",
                "purchase_options": "whether there is a purchase option (yes/no)",
                "renewal_options": "Description of renewal options if any (yes/no)",
                "break_options": "whether there is a break option or termination clause or opt-out clause (yes/no)",
                "end_date": "Lease End Date",
                "security_deposit": "Security Deposit Amount if specified, if not specified then 'HELP_DECIDING'",
                "payment_due_date": "Payment due date if specified, if not specified then 'HELP_DECIDING'",
                "prepaid_rent": "Prepaid Rent Amount if specified, if not specified then 'HELP_DECIDING'",
                "monthly_payment": "Amount to be paid monthly along with any increases",
                "rent_deescalation": "Rent De-escalation Clause if specified, if not specified then 'HELP_DECIDING'",
                "monthly_payment_list": "python dictionary of monthly payments with any increases calculated for each month rent will be paid. aka payments per each date in the lease term (ie monthly payment amount by month). All dates should be in the format YYYY-MM-DD.",
                "percentage_rent": "whether there is percentage rent where part of rent owed is based on the sales or other determinable factors outlined in the lease (yes/no)",
                "maintenance": "description of maintenance terms and who is responsible for maintenance",
                "utilities": "description of utilities terms and who is responsible for utilities",
                insurance": "description of insurance terms and who is responsible for insurance",
                "taxes": "description of taxes",
                "tenant_improvements": "Tenant Improvements if specified, if not specified then pose this as a question",
                "brokerage_commissions": "brokerage commissions amount and who is responsible for the brokerage commissions. and whether there are brokerage commissions or not (yes/no)",
                "lease_incentives": "whether there are lease incentives including rent abatement (free rent), tenant improvement allowance, relocation cost coverage, signing bonus, cash payments, furnished space, or free equipment (yes/no)",
                "lease_incentives_description": "Description of lease incentives if any, if not specified then 'HELP_DECIDING'",
                "lease_incentives_amount": "Total amount of lease incentives if specified, if not ask the question/tell the user to look at a certain section of the lease",
            }}
        }}

        Focus on extracting exact quotes from the lease document to support your analysis. Be thorough but precise.
        """

    try:
        # Make API call to OpenAI using the new client structure
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an expert lease accounting analyst specializing in ASC 842 lease classification. Provide thorough, accurate analysis with supporting evidence from the lease document."},
                {"role": "user", "content": analysis_prompt}
            ],
            temperature=0,
            max_tokens=4000
        )

        # Extract the response content
        response_content = response.choices[0].message.content

        # Clean the response content to handle markdown code blocks
        cleaned_content = response_content.strip()
        
        # Remove markdown code block formatting if present
        if cleaned_content.startswith("```json"):
            cleaned_content = cleaned_content[7:]  # Remove ```json
        elif cleaned_content.startswith("```"):
            cleaned_content = cleaned_content[3:]   # Remove ```
            
        if cleaned_content.endswith("```"):
            cleaned_content = cleaned_content[:-3]  # Remove closing ```
            
        cleaned_content = cleaned_content.strip()

        # Try to parse as JSON
        try:
            result = json.loads(cleaned_content)
        except json.JSONDecodeError as e:
            # If JSON parsing still fails, try to extract JSON from the response
            try:
                # Look for JSON-like content between curly braces
                import re
                json_match = re.search(r'\{.*\}', cleaned_content, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    raise json.JSONDecodeError("No JSON found", cleaned_content, 0)
            except json.JSONDecodeError:
                # If all JSON parsing fails, create a structured response
                result = {
                    "classification": "HELP_DECIDING",
                    "confidence": "LOW",
                    "reasoning": "Analysis completed but response format issue occurred. The AI provided analysis but in an unparseable format.",
                    "raw_response": response_content,
                    "cleaned_response": cleaned_content,
                    "error": f"JSON parsing failed: {str(e)}"
                }

        return result

    except Exception as e:
        return {
            "classification": "ERROR",
            "confidence": "LOW",
            "reasoning": f"Error occurred during analysis: {str(e)}",
            "error": str(e)
        }

def extract_primary_inputs(results: Dict[str, Any], measurement_date: str = "4/1/2025", annual_discount_rate: float = 9.08) -> pd.DataFrame:
    """
    Extracts primary inputs needed for lease accounting calculations from the classification results.

    Args:
        results (Dict): Results from classify_lease function
        measurement_date (str): The measurement date for the lease (default: "4/1/2025")
        annual_discount_rate (float): Annual discount rate as percentage (default: 9.08)

    Returns:
        pd.DataFrame: DataFrame with primary inputs for lease accounting
    """
    from datetime import datetime
    import calendar
    
    # Initialize primary inputs with defaults
    primary_inputs = {
        "Primary Inputs": [
            "Measurement Date:",
            "Lease Expiration Date:",
            "Lease Term (in months):",
            "Annual Discount Rate:",
            "Monthly Discount Rate:",
            "Initial Direct Costs:",
            "Incentives:",
            "Prepaid Rent:",
            "Periodic Payments Made At Beginning or Ending of Period:",
            "Lease Classification:"
        ],
        "Values": [
            measurement_date,
            "Not specified",
            "Not specified",
            f"{annual_discount_rate}%",
            f"{(annual_discount_rate/12):.2f}%",
            "-",
            "-",
            "-",
            "Beginning",
            "Not specified"
        ]
    }
    
    if "key_lease_terms" in results:
        terms = results["key_lease_terms"]
        
        # Extract lease expiration date
        end_date = terms.get("end_date", "Not specified")
        if end_date and end_date != "Not specified":
            primary_inputs["Values"][1] = end_date
        
        # Calculate lease term in months if we have start and end dates
        commencement_date = terms.get("commencement_date", "")
        if commencement_date and end_date and commencement_date != "Not specified" and end_date != "Not specified":
            try:
                # Parse dates - handle various formats
                start_formats = ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y/%m/%d"]
                end_formats = ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y/%m/%d"]
                
                start_parsed = None
                end_parsed = None
                
                for fmt in start_formats:
                    try:
                        start_parsed = datetime.strptime(commencement_date, fmt)
                        break
                    except ValueError:
                        continue
                
                for fmt in end_formats:
                    try:
                        end_parsed = datetime.strptime(end_date, fmt)
                        break
                    except ValueError:
                        continue
                
                if start_parsed and end_parsed:
                    # Calculate months between dates
                    months_diff = (end_parsed.year - start_parsed.year) * 12 + (end_parsed.month - start_parsed.month)
                    primary_inputs["Values"][2] = str(months_diff)
            except:
                pass  # Keep "Not specified" if calculation fails
        
        # Extract incentives
        incentives_amount = terms.get("lease_incentives_amount", "")
        if incentives_amount and incentives_amount not in ["Not specified", "HELP_DECIDING", "", "None"]:
            # Clean up the incentives amount
            clean_incentives = str(incentives_amount).replace("$", "").replace(",", "").strip()
            try:
                incentive_value = float(clean_incentives)
                if incentive_value > 0:
                    primary_inputs["Values"][6] = f"${incentive_value:,.2f}"
            except (ValueError, TypeError):
                if incentives_amount != "Not specified":
                    primary_inputs["Values"][6] = str(incentives_amount)
        
        # Extract prepaid rent
        prepaid_rent = terms.get("prepaid_rent", "")
        if prepaid_rent and prepaid_rent not in ["Not specified", "HELP_DECIDING", "", "None"]:
            # Clean up the prepaid rent amount
            clean_prepaid = str(prepaid_rent).replace("$", "").replace(",", "").strip()
            try:
                prepaid_value = float(clean_prepaid)
                if prepaid_value > 0:
                    primary_inputs["Values"][7] = f"${prepaid_value:,.2f}"
            except (ValueError, TypeError):
                if prepaid_rent != "Not specified":
                    primary_inputs["Values"][7] = str(prepaid_rent)
    
    # Extract lease classification
    classification = results.get("classification", "Not specified")
    if classification == "OPERATING":
        primary_inputs["Values"][9] = "Operating"
    elif classification == "FINANCE":
        primary_inputs["Values"][9] = "Finance"
    elif classification == "HELP_DECIDING":
        primary_inputs["Values"][9] = "Needs Review"
    else:
        primary_inputs["Values"][9] = classification
    
    return pd.DataFrame(primary_inputs)

def format_classification_results(results: Dict[str, Any]) -> Tuple[str, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Formats the classification results into a readable string for display and creates DataFrames.

    Args:
        results (Dict): Results from classify_lease function

    Returns:
        Tuple[str, pd.DataFrame, pd.DataFrame, pd.DataFrame]: Formatted results for display, main terms DataFrame, payment schedule DataFrame, and primary inputs DataFrame
    """
    
    # Initialize empty DataFrames
    df = pd.DataFrame(columns=["Terms and Conditions", "Information"])
    payment_df = pd.DataFrame(columns=["Date", "Lease Payment"])
    payment_df.index.name = "Period"
    
    # Create primary inputs DataFrame
    primary_inputs_df = extract_primary_inputs(results)

    if "error" in results:
        error_msg = f"❌ Error in Analysis\n\n{results.get('reasoning', 'Unknown error occurred')}"
        # Create a single row DataFrame for error case
        error_df = pd.DataFrame({
            "Terms and Conditions": ["Error"],
            "Information": [results.get('reasoning', 'Unknown error occurred')]
        })
        return error_msg, error_df, payment_df, primary_inputs_df

    classification = results.get('classification', 'Unknown')
    confidence = results.get('confidence', 'Unknown')
    reasoning = results.get('reasoning', 'No reasoning provided')

    # Determine emoji and color based on classification
    if classification == "OPERATING":
        emoji = "📋"
        class_text = "OPERATING LEASE"
    elif classification == "FINANCE":
        emoji = "💰"
        class_text = "FINANCE LEASE"
    elif classification == "HELP_DECIDING":
        emoji = "❓"
        class_text = "ADDITIONAL INFORMATION NEEDED"
    else:
        emoji = "⚠️"
        class_text = "CLASSIFICATION UNCERTAIN"

    formatted_result = f"""
{emoji} LEASE CLASSIFICATION: {class_text}

Confidence Level: {confidence}

Analysis Summary:
{reasoning}

"""

    # Create DataFrame rows list
    df_rows = []
    
    # Add classification information to DataFrame
    df_rows.append({
        "Terms and Conditions": "Lease Classification",
        "Information": class_text
    })
    
    df_rows.append({
        "Terms and Conditions": "Confidence Level", 
        "Information": str(confidence)
    })
    
    df_rows.append({
        "Terms and Conditions": "Analysis Summary",
        "Information": reasoning
    })

    # Add key lease terms if available
    if "key_lease_terms" in results:
        terms = results["key_lease_terms"]
        formatted_result += "Key Lease Terms:\n\n"
        
        # Updated field mapping to match your JSON structure
        field_mapping = {
            "address": "Address",
            "lessee": "Lessee", 
            "lessor": "Lessor",
            "description_of_premises": "Description of Premises",
            "lease_term": "Lease Term",
            "execution_date": "Execution Date",
            "commencement_date": "Commencement Date (Accounting Purposes)",
            "purchase_options": "Purchase Option",
            "renewal_options": "Renewal Option", 
            "break_options": "Break Option",
            "end_date": "Lease End Date",
            "security_deposit": "Security Deposit",
            "payment_due_date": "Payment Due Date",
            "prepaid_rent": "Prepaid Rent",
            "monthly_payment": "Monthly Rent Payments",
            "rent_deescalation": "Rent De-escalation Clause",
            "percentage_rent": "Percentage Rent",
            "maintenance": "Maintenance Terms",
            "utilities": "Utilities Terms",
            "insurance": "Insurance Terms",
            "taxes": "Tax Terms",
            "tenant_improvements": "Tenant Improvements", 
            "brokerage_commissions": "Brokerage Commissions",
            "lease_incentives": "Lease Incentives (Yes/No)",
            "lease_incentives_description": "Lease Incentives Description",
            "lease_incentives_amount": "Lease Incentives Amount"
        }
        
        # Handle monthly_payment_list separately for the payment schedule DataFrame
        monthly_payments = terms.get("monthly_payment_list", {})
        if monthly_payments and isinstance(monthly_payments, dict):
            payment_rows = []
            for date, amount in monthly_payments.items():
                payment_rows.append({
                    "Date": date,
                    "Lease Payment": f"${float(amount):,.2f}" if isinstance(amount, (int, float)) else str(amount)
                })
            
            if payment_rows:
                payment_df = pd.DataFrame(payment_rows)
                payment_df.index.name = "Period"
                # Reset index to create Period numbers starting from 1
                payment_df.reset_index(drop=True, inplace=True)
                payment_df.index = payment_df.index + 1
                payment_df.index.name = "Period"
        
        for key, display_name in field_mapping.items():
            # Skip monthly_payment_list as it's handled separately
            if key == "monthly_payment_list":
                continue
                
            value = terms.get(key, "Not specified")
            
            # Clean and format the value - show all values regardless of content
            clean_value = str(value).strip() if value else "Not specified"
            
            # Format monetary values
            if key in ["security_deposit", "monthly_payment", "prepaid_rent", "lease_incentives_amount"]:
                if clean_value not in ["Not specified", "N/A", "", "None", "HELP_DECIDING"]:
                    # Remove any extra formatting and ensure proper currency display
                    temp_value = clean_value.replace(',', '').replace('$', '')
                    try:
                        # Try to convert to float and format as currency
                        amount = float(temp_value)
                        clean_value = f"${amount:,.2f}"
                    except (ValueError, TypeError):
                        # If conversion fails, just add $ prefix if not already there
                        if not clean_value.startswith('$') and clean_value not in ["Not specified", "N/A", "", "None", "HELP_DECIDING"]:
                            clean_value = f"${clean_value}"
            
            # Add to formatted result
            formatted_result += f"    • {display_name}: {clean_value}\n"
            
            # Add to DataFrame
            df_rows.append({
                "Terms and Conditions": display_name,
                "Information": clean_value
            })
        
        # Add summary of payment schedule to main DataFrame
        if not payment_df.empty:
            df_rows.append({
                "Terms and Conditions": "Payment Schedule",
                "Information": f"{len(payment_df)} payments (see separate payment schedule table)"
            })
        
        formatted_result += "\n"

    # Handle raw response if JSON parsing failed
    if "raw_response" in results:
        formatted_result += "\nRaw AI Response (for debugging):\n\n"
        formatted_result += f"```\n{results['raw_response']}\n```\n"
        
        # Add raw response to DataFrame
        df_rows.append({
            "Terms and Conditions": "Raw AI Response (Debug)",
            "Information": results['raw_response']
        })

    # Create DataFrame from rows
    df = pd.DataFrame(df_rows)

    return formatted_result, df, payment_df, primary_inputs_df