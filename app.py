import streamlit as st
from datetime import date
import tempfile
import pandas as pd
from io import BytesIO

from nodes import app, State
from nodes_2 import app_2, State2
from utils.pdf_reading import extract_text_from_pdf
from utils.ibr import *
from utils.excel import *


if 'result' not in st.session_state:
    st.session_state['result'] = None

if 'result_2' not in st.session_state:
    st.session_state['result_2'] = None

if 'wb' not in st.session_state:
    st.session_state['wb'] = None


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
# else:
    # st.info("ℹ️ Will use the start date per the lease agreement as commencement date")

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
        "Debt Maturity date", 
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

        status_text = st.empty()
        progress_bar = st.progress(0)

        status_text.text("Processing PDF...")

        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_file_path = tmp_file.name
        
        method, extracted_text = extract_text_from_pdf(tmp_file_path, verbose=False)

        status_text.text("Text from PDF extracted...")
        progress_bar.progress(10)

        # NEW: Run app_2_instance first to gather terms and conditions
        status_text.text("Gathering Terms and Conditions...")
        progress_bar.progress(20)

        state_input = {"text": extracted_text}
        result_2 = app_2_instance.invoke(state_input)
        st.session_state['result_2'] = result_2

        st.write("Terms and Conditions:")
        st.json(result_2['terms_conditions_details'], expanded=True)
        st.write("Terms and Conditions Options:")   
        st.json(result_2['terms_conditions_options'], expanded=True)
        st.write("Terms and Conditions Financials:")
        st.json(result_2['terms_conditions_financials'], expanded=True)
        st.write("Terms and Conditions Additional Terms:")
        st.json(result_2['terms_conditions_additional'], expanded=True)

        # Now run the main classification process
        status_text.text("Running lease classification...")
        progress_bar.progress(40)

        state_input = {"text": extracted_text, "rent_abatement":result_2['terms_conditions_additional']["Rent Concessions"]}

        result = app_instance.invoke(state_input)

        # Save data to session_state
        st.session_state['result'] = result

        if early_possession and actual_commencement_date:
            effective_commencement_date = actual_commencement_date
            st.info(f"Using actual possession date as commencement: {actual_commencement_date}")
        else:
            effective_commencement_date = result["dates"]["commencement_date"]
            st.info(f"Using lease agreement start date as commencement: {result['dates']['commencement_date']}")

        st.write("Classification:", result["classification"])
        st.write("\nDiscount Rate:", result["discount_rate"])

        status_text.text("Building Worksheets...")
        progress_bar.progress(60)
        if has_debt:
            debt_data = {
                'commencement_date': [debt_commencement],
                'end_date': [debt_end],
                'measurement_date': [measurement_date],
                'discount_rate': [discount_rate]
            }
        else:
            debt_data = None

        st.write("IBR Calculation:")
        ibr_df, debt_df = build_ibr_df(effective_commencement_date,
                                    result["dates"]["end_date"],
                                    result["discount_rate"], has_debt=has_debt, debt_data=debt_data)
        if debt_df is not None:
            st.write("Debt Information:")
            st.dataframe(debt_df, use_container_width=True, hide_index=True)
        st.data_editor(ibr_df, use_container_width=True, hide_index=True)
        
        primary_inputs = pd.DataFrame([[
            result['dates']['start_date'],
            result['dates']['end_date'],
            len(result['dates']['payment_dates']),
            result["discount_rate"],
            ((float(result['discount_rate'])/100)/12),
            0,
            -float(result_2['terms_conditions_additional']["Lease Incentives"]['amount']),
            float(result_2['terms_conditions_options']["Prepaid Rent"]['amount']),
            'Beginning',
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
        print(result['dates'])
        payments_df = pd.DataFrame(list(result['dates']['payment_dates'].items()), columns=['Date','Lease Payment']).reset_index(names='Period')
        payments_df['PV Lease Payment'] = (payments_df['Lease Payment'] / ((1 + (result['discount_rate']/100)/12) ** (payments_df['Period']))).round(2)
        initial_lease_liability = payments_df['PV Lease Payment'].sum()

        st.dataframe(payments_df, use_container_width=True)

        status_text.text("Building Excel Workbook...")
        progress_bar.progress(80)

        wb = create_workbook(
            result['dates']['start_date'], 
            result['dates']['end_date'], 
            len(result['dates']['payment_dates']), 
            result["discount_rate"]/100,
            result['classification'],
            [x for x in range(len(result['dates']['payment_dates']))], 
            list(result['dates']['payment_dates'].keys()), 
            list(result['dates']['payment_dates'].values()),
            0,
            -float(result_2['terms_conditions_additional']["Lease Incentives"]['amount']),
            float(result_2['terms_conditions_options']["Prepaid Rent"]['amount']),
            'Beginning'
            )
        st.session_state['wb'] = wb

        if 'wb' in st.session_state:
            output = BytesIO()
            st.session_state['wb'].save(output)
            output.seek(0)

            st.download_button(
                label="📥 Download Excel Workbook",
                data=output,
                file_name="lease_classification.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

        progress_bar.progress(100)
        status_text.text("Done!")
