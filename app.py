import streamlit as st
from datetime import date
import tempfile
import pandas as pd
from io import BytesIO
import os

from nodes import app, State
from nodes_2 import app_2, State2
from utils.pdf_reading import extract_text_from_pdf
from utils.ibr import *
from utils.excel import *

# Initialize session state variables
if 'result' not in st.session_state:
    st.session_state['result'] = None

if 'result_2' not in st.session_state:
    st.session_state['result_2'] = None

if 'wb' not in st.session_state:
    st.session_state['wb'] = None

if 'processing_complete' not in st.session_state:
    st.session_state['processing_complete'] = False

if 'effective_commencement_date' not in st.session_state:
    st.session_state['effective_commencement_date'] = None

if 'has_debt_processed' not in st.session_state:
    st.session_state['has_debt_processed'] = False

if 'debt_data_processed' not in st.session_state:
    st.session_state['debt_data_processed'] = None

st.set_page_config(
    page_title="ASC 842 Lease Classification",
    page_icon="📋",
    layout="wide"
)

current_dir = os.path.dirname(__file__)
image_path = os.path.join(current_dir, r'The Glenwood Group-02.png')
st.image(image_path, width=400)
st.title("ASC 842 Lease Classification Tool")

# PDF file uploader
uploaded_file = st.file_uploader(
    "Upload Lease Agreement (PDF)",
    type=['pdf'],
    help="Select the lease agreement PDF file for classification"
)

# Lease Commencement section
st.subheader("Lease Commencement")

early_possession = st.checkbox(
    "Did you gain access and possession of the leased asset prior to the start date per the lease agreement?",
    help="Access and possession should be defined as the lessee has control over the leased space and it is ready for use, meaning that landlord directed improvements are complete and the space is at the direction of the lessee under the lease terms."
)

# Conditional lease commencement date input
actual_commencement_date = None
if early_possession:
    actual_commencement_date = st.date_input(
        "Enter the date that possession was taken:",
        value=date.today(),
        help="This date will be used as the commencement date for lease terms and calculations"
    )
    st.info("✓ Using actual possession date as lease commencement date")

# Company holds debt checkbox
has_debt = st.checkbox("Company holds debt?")

# Conditional debt inputs - only show if checkbox is checked
debt_commencement = None
debt_end = None
measurement_date = None
discount_rate = None

if has_debt:
    st.subheader("Debt Information")
    
    debt_commencement = st.date_input(
        "Debt commencement date",
        value=date.today()
    )
    
    debt_end = st.date_input(
        "Debt Maturity date", 
        value=date.today()
    )
    
    measurement_date = debt_commencement
    
    discount_rate = st.number_input(
        "Debt Interest Rate (%)",
        min_value=0.0,
        max_value=100.0,
        value=5.0,
        step=0.1,
        format="%.2f"
    )

# Start Classification Process button
if st.button("Start Classification Process", type="primary"):
    if uploaded_file is None:
        st.error("Please upload a PDF file")
    else:
        # Reset processing state
        st.session_state['processing_complete'] = False
        
        app_instance = app(State=State)
        app_2_instance = app_2(State2=State2)

        status_text = st.empty()
        progress_bar = st.progress(0)

        status_text.text("Processing PDF...")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        
        method, extracted_text = extract_text_from_pdf(tmp_file_path, verbose=False)

        status_text.text("Text from PDF extracted...")
        progress_bar.progress(10)

        # Run app_2_instance first to gather terms and conditions
        status_text.text("Gathering Terms and Conditions...")
        progress_bar.progress(20)

        state_input = {"text": extracted_text}
        result_2 = app_2_instance.invoke(state_input)
        st.session_state['result_2'] = result_2

        # Now run the main classification process
        status_text.text("Running lease classification...")
        progress_bar.progress(40)

        state_input = {"text": extracted_text, "rent_abatement":result_2['terms_conditions_additional']["Rent Concessions"]}

        result = app_instance.invoke(state_input)
        st.session_state['result'] = result

        # Store effective commencement date
        if early_possession and actual_commencement_date:
            st.session_state['effective_commencement_date'] = actual_commencement_date
        else:
            st.session_state['effective_commencement_date'] = result["dates"]["commencement_date"]

        status_text.text("Building Worksheets...")
        progress_bar.progress(60)
        
        # Store debt information
        st.session_state['has_debt_processed'] = has_debt
        if has_debt:
            st.session_state['debt_data_processed'] = {
                'commencement_date': [debt_commencement],
                'end_date': [debt_end],
                'measurement_date': [measurement_date],
                'discount_rate': [discount_rate]
            }
        else:
            st.session_state['debt_data_processed'] = None

        status_text.text("Building Excel Workbook...")
        progress_bar.progress(80)

        # Build IBR dataframe
        ibr_df, debt_df = build_ibr_df(st.session_state['effective_commencement_date'],
                                    result["dates"]["end_date"],
                                    result["discount_rate"], 
                                    has_debt=st.session_state['has_debt_processed'], 
                                    debt_data=st.session_state['debt_data_processed'])

        start_date_str = result['dates']['start_date']
        start_date = pd.to_datetime(start_date_str)

        if start_date.day <= 15:
            p_p = "Beginning"
        else:
            p_p = "Ending"

        wb = create_workbook(
            result['dates']['start_date'], 
            result['dates']['end_date'], 
            len(result['dates']['payment_dates']), 
            result["discount_rate"]/100,
            result['classification'],
            [x for x in range(len(result['dates']['payment_dates']))], 
            list(result['dates']['payment_dates'].keys()), 
            list(result['dates']['payment_dates'].values()),
            result_2,
            ibr_df, debt_df,
            float(result_2['terms_conditions_additional']["Initial Direct Costs"]['amount']),
            -float(result_2['terms_conditions_additional']["Lease Incentives"]['amount']),
            float(result_2['terms_conditions_options']["Prepaid Rent"]['amount']),
            'Beginning',
            lease_name=uploaded_file.name.split(".")[0]
        )
        st.session_state['wb'] = wb
        st.session_state['processing_complete'] = True

        progress_bar.progress(100)
        status_text.text("Complete, just Building Workbook!")

# Display results if processing is complete
if st.session_state['processing_complete'] and st.session_state['result'] is not None:
    result = st.session_state['result']
    result_2 = st.session_state['result_2']
    
    # Display commencement date info
    if st.session_state['effective_commencement_date']:
        if early_possession and actual_commencement_date:
            st.info(f"Using actual possession date as commencement: {actual_commencement_date}")
        else:
            st.info(f"Using lease agreement start date as commencement: {result['dates']['commencement_date']}")

    st.write("Terms and Conditions:")
    st.json(result_2['terms_conditions_details'], expanded=True)
    st.write("Terms and Conditions Options:")   
    st.json(result_2['terms_conditions_options'], expanded=True)
    st.write("Terms and Conditions Financials:")
    st.json(result_2['terms_conditions_financials'], expanded=True)
    st.write("Terms and Conditions Additional Terms:")
    st.json(result_2['terms_conditions_additional'], expanded=True)

    st.write("Classification:", result["classification"])
    st.write("Discount Rate:", result["discount_rate"])

    # Rebuild IBR dataframe for display
    ibr_df, debt_df = build_ibr_df(st.session_state['effective_commencement_date'],
                                result["dates"]["end_date"],
                                result["discount_rate"], 
                                has_debt=st.session_state['has_debt_processed'], 
                                debt_data=st.session_state['debt_data_processed'])
    
    st.write("IBR Calculation:")
    if debt_df is not None:
        st.write("Debt Information:")
        st.dataframe(debt_df, use_container_width=True, hide_index=True)
    st.data_editor(ibr_df, use_container_width=True, hide_index=True)

    # Primary inputs
    start_date_str = result['dates']['start_date']
    start_date = pd.to_datetime(start_date_str)

    if start_date.day <= 15:
        p_p = "Beginning"
    else:
        p_p = "Ending"
    
    primary_inputs = pd.DataFrame([[
        result['dates']['start_date'],
        result['dates']['end_date'],
        len(result['dates']['payment_dates']),
        result["discount_rate"],
        ((float(result['discount_rate'])/100)/12),
        float(result_2['terms_conditions_additional']["Initial Direct Costs"]['amount']),
        -float(result_2['terms_conditions_additional']["Lease Incentives"]['amount']),
        float(result_2['terms_conditions_options']["Prepaid Rent"]['amount']),
        p_p,
        result['classification']
    ]], columns=[
        'Measurement Date',
        'Lease Expiration Date',
        'Lease Term (Months)',
        'Discount Rate',
        'Monthly Discount Rate',
        'Initial Direct Costs',
        'Incentives',
        'Prepaid Rent',
        'Periodic Payments Made at Beginning or Ending of Period', 
        'Classification'
    ])
    st.write("Primary Inputs:")
    st.dataframe(primary_inputs)

    st.write("Risk-free Rates per the U.S. Treasury Department:")
    st.dataframe(result["treasury_df"], use_container_width=True, hide_index=True)

    st.write("Payment Dates:")
    payments_df = pd.DataFrame(list(result['dates']['payment_dates'].items()), columns=['Date','Lease Payment']).reset_index(names='Period')
    payments_df['PV Lease Payment'] = (payments_df['Lease Payment'] / ((1 + (result['discount_rate']/100)/12) ** (payments_df['Period']))).round(2)
    initial_lease_liability = payments_df['PV Lease Payment'].sum()

    st.dataframe(payments_df, use_container_width=True)

    # Download button - this should now preserve the displayed content
    if st.session_state['wb'] is not None:
        try:
            # Create a fresh BytesIO object each time
            output = BytesIO()
            
            # Save the workbook to the BytesIO object
            st.session_state['wb'].save(output)
            
            # Get the data before seeking
            excel_data = output.getvalue()
            output.close()  # Close the BytesIO object
            
            st.download_button(
                label="📥 Download Excel Workbook",
                data=excel_data,
                file_name=f"{uploaded_file.name.split('.')[0]}_lease_classification.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                key="download_excel"
            )
        except Exception as e:
            print(e)
