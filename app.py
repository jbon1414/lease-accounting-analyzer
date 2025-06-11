import streamlit as st
from datetime import date
import tempfile
import pandas as pd

from nodes import app, State
from nodes_2 import app_2, State2
from utils.pdf_reading import extract_text_from_pdf
from utils.ibr import build_ibr_df

st.set_page_config(
    page_title="ASC 842 Lease Classification",
    page_icon="📋",
    layout="wide"
)

st.title("ASC 842 Lease Classification Tool")

# PDF file uploader
uploaded_file = st.file_uploader(
    "Upload Lease Agreement (PDF)",
    type=['pdf'],
    help="Select the lease agreement PDF file for classification"
)

# Company holds debt checkbox
has_debt = st.checkbox("Company holds debt?")

# Conditional debt inputs - only show if checkbox is checked
if has_debt:
    st.subheader("Debt Information")
    
    debt_commencement = st.date_input(
        "Debt commencement date",
        value=date.today()
    )
    
    debt_end = st.date_input(
        "Debt end date", 
        value=date.today()
    )
    
    measurement_date = st.date_input(
        "Measurement date",
        value=date.today()
    )
    
    discount_rate = st.number_input(
        "Company discount rate/Borrowing Rate (%)",
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
        app_instance = app(State=State)
        app_2_instance = app_2(State2=State2)
        progress_bar = st.progress(0)
        status_text = st.empty()

        status_text.text("Processing PDF...")
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        
        method, extracted_text = extract_text_from_pdf(tmp_file_path, verbose=False)

        progress_bar.progress(10)
        status_text.text("Text from PDF extracted...")

        state_input = {"text": extracted_text}

        result = app_instance.invoke(state_input)

        st.write("Classification:", result["classification"])

        st.write("\nDiscount Rate:", result["discount_rate"])

        progress_bar.progress(90)
        status_text.text("Building Worksheets...")

        st.write("IBR Calculation:")
        st.data_editor(build_ibr_df((result["dates"]["commencement_date"]),
                                    result["dates"]["end_date"],
                                    result["discount_rate"]),
                       use_container_width=True,
                       hide_index=True)
        
        primary_inputs = pd.DataFrame([[
            result['dates']['start_date'],
            result['dates']['end_date'],
            len(result['dates']['payment_dates']),
            result["discount_rate"],
            result['classification']
        ]], columns=[
            'Measurement Date',
            'Lease Expiration Date',
            'Lease Term (Months)',
            'Discount Rate',
            'Classification'
        ])
        st.write("Primary Inputs:")
        st.dataframe(primary_inputs,)

        st.write("Risk-free Rates per the U.S. Treasury Department:")
        st.dataframe(result["treasury_df"], use_container_width=True, hide_index=True)

        st.write("Payment Dates:")
        print(result['dates'])
        payments_df = pd.DataFrame(list(result['dates']['payment_dates'].items()), columns=['Date','Lease Payment']).reset_index(names='Period')
        payments_df['PV Lease Payment'] = (payments_df['Lease Payment'] / ((1 + (result['discount_rate']/100)/12) ** (payments_df['Period']))).round(2)
        initial_lease_liability = payments_df['PV Lease Payment'].sum()

        st.dataframe(payments_df, use_container_width=True)

        status_text.text("Gathering Terms and Conditions...")
        progress_bar.progress(66)

        result_2 = app_2_instance.invoke(state_input)

        st.write("Terms and Conditions:")
        st.json(result_2['terms_conditions_details'], expanded=True)
        st.write("Terms and Conditions Options:")   
        st.json(result_2['terms_conditions_options'], expanded=True)
        st.write("terms and conditions financials:")
        st.json(result_2['terms_conditions_financials'], expanded=True)
        st.write("Terms and Conditions Additional Terms:")
        st.json(result_2['terms_conditions_additional'], expanded=True)

        progress_bar.progress(100)



