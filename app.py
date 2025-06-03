import streamlit as st
import pandas as pd
import tempfile
import os
import json
from datetime import datetime
from utils.pdf_reading import extract_text_from_pdf
from utils.openai import classify_lease, format_classification_results, validate_with_quotes, format_validation_results
from utils.excel import create_lease_amortization_schedule_excel

st.set_page_config(
    page_title="PDFLease Accounting Classifier",
    page_icon="📄",
    layout="wide"
)

st.title("📄 PDF Lease Accounting Classifier")

# Initialize session state for storing results
if 'classification_results' not in st.session_state:
    st.session_state.classification_results = None
if 'extracted_text' not in st.session_state:
    st.session_state.extracted_text = None
if 'validation_results' not in st.session_state:
    st.session_state.validation_results = None

# Create tabs
tab1, tab2 = st.tabs(["PDF Lease Classifier", "Treasury Rates"])

with tab1:
    st.markdown("Upload a PDF file and extract text using multiple extraction methods, with optional AI-powered lease classification.")

    # Create columns for better layout
    col1, col2 = st.columns([1, 2])

    with col1:
        st.header("Upload PDF")
        uploaded_file = st.file_uploader("Choose a PDF file", type="pdf", help="Upload a PDF file to extract text from")
        st.subheader("Lease Classification")
        openai_key = st.text_input("OpenAI API Key", type="password", help="Enter your OpenAI API key to enable lease classification analysis")
        extract_button = st.button("Extract Info", type="primary", disabled=not openai_key)
    
    with col2:
        st.header("Results")
        if uploaded_file:
            st.info(f"**File:** {uploaded_file.name}")

        if extract_button and uploaded_file:
            progress_bar = st.progress(0)
            status_text = st.empty()

            try:
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                    tmp_file.write(uploaded_file.getvalue())
                    tmp_file_path = tmp_file.name

                progress_bar.progress(33)
                status_text.text("Processing PDF...")

                method, extracted_text = extract_text_from_pdf(tmp_file_path, verbose=False)
                
                # Store extracted text in session state
                st.session_state.extracted_text = extracted_text

                os.unlink(tmp_file_path)
                progress_bar.progress(50)
                status_text.text("Analyzing Lease...")
                if method and extracted_text:
                    with st.expander("Extracted Text"):
                        st.text_area("Extracted Text", value=extracted_text, height=400, help="You can select and copy this text")
                        st.download_button("📥 Download extracted text as .txt file", data=extracted_text, file_name=f"{uploaded_file.name}_extracted.txt", mime="text/plain")
                    st.markdown("---")
                    st.subheader("🔍 Lease Classification Analysis")
                    with st.spinner("Analyzing lease classification with AI..."):
                        classification_results = classify_lease(extracted_text, openai_key)
                        # Store classification results in session state
                        st.session_state.classification_results = classification_results
                    
                    progress_bar.progress(75)
                    status_text.text("Validating analysis with supporting quotes...")
                    
                    # Run validation automatically as part of the analysis
                    with st.spinner("Validating analysis and extracting supporting quotes..."):
                        validation_results = validate_with_quotes(
                            extracted_text, 
                            classification_results, 
                            openai_key
                        )
                        st.session_state.validation_results = validation_results
                    
                    progress_bar.progress(100)
                    status_text.text("Analysis complete!")
                    
                    # Format and display classification results
                    formatted_results, df, payment_df, df3 = format_classification_results(classification_results)
                    st.markdown(formatted_results)
                    
                    # Display validation results automatically
                    if validation_results and validation_results.get('validation_status') != 'ERROR':
                        st.markdown("---")
                        st.subheader("🔍 Validation with Supporting Quotes")
                        formatted_validation, quotes_df = format_validation_results(validation_results)
                        st.markdown(formatted_validation)
                        
                        if not quotes_df.empty:
                            st.markdown("### Supporting Evidence")
                            st.data_editor(quotes_df, use_container_width=True, hide_index=True)
                    
                    if classification_results.get('classification') != 'ERROR':
                        current_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Create comprehensive report including validation
                        report_data = (
                            f"LEASE CLASSIFICATION ANALYSIS REPORT\n"
                            f"Generated from: {uploaded_file.name}\n"
                            f"Date: {current_date}\n\n"
                            f"{formatted_results}\n\n"
                        )
                        
                        # Add validation results to report if available
                        if validation_results and validation_results.get('validation_status') != 'ERROR':
                            formatted_validation, quotes_df = format_validation_results(validation_results)
                            report_data += (
                                f"VALIDATION RESULTS:\n"
                                f"{formatted_validation}\n\n"
                                f"SUPPORTING EVIDENCE:\n"
                                f"{quotes_df.to_string(index=False) if not quotes_df.empty else 'No supporting quotes found'}\n\n"
                            )
                        
                        report_data += (
                            f"RAW ANALYSIS DATA:\n"
                            f"{json.dumps(classification_results, indent=2)}\n\n"
                        )
                        
                        # Add raw validation data if available
                        if validation_results and validation_results.get('validation_status') != 'ERROR':
                            report_data += (
                                f"RAW VALIDATION DATA:\n"
                                f"{json.dumps(validation_results, indent=2)}"
                            )
                        
                        st.download_button("📄 Download complete analysis report", data=report_data, file_name=f"{uploaded_file.name}_complete_analysis_report.txt", mime="text/plain")
                    
                    st.subheader("📊 Lease Terms and Conditions Summary")
                    st.data_editor(df, use_container_width=True, hide_index=True)
                    st.data_editor(df3, use_container_width=True, hide_index=True)
                    st.data_editor(payment_df, use_container_width=True)

                    excel_data = create_lease_amortization_schedule_excel(payment_df, df3)
                    
                    # Create download button
                    st.download_button(
                        label="📄 Download Lease Amortization Schedule",
                        data=excel_data,
                        file_name="Final_Lease_Amortization.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )

                else:
                    st.error("❌ Failed to extract text from the PDF. The file might be:")
                    st.markdown("- Scanned images without OCR-readable text\n- Password protected\n- Corrupted\n- In an unsupported format")
            except Exception as e:
                st.error(f"An error occurred during processing: {str(e)}")
                if 'tmp_file_path' in locals() and os.path.exists(tmp_file_path):
                    os.unlink(tmp_file_path)
                progress_bar.empty()
                status_text.empty()

with tab2:
    st.header("📈 Daily Treasury Rates")
    st.markdown("U.S. Treasury yield curve data from the Department of Treasury")
    
    # Year selector
    current_year = datetime.now().year
    selected_year = st.selectbox(
        "Select Year:",
        options=list(range(current_year, 1999, -1)),  # From current year down to 2000
        index=0  # Default to current year
    )
    
    # Load data button
    load_data = st.button("Load Treasury Data", type="primary")
    
    if load_data:
        try:
            # Construct URL with selected year
            treasury_url = f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{selected_year}/all?type=daily_treasury_yield_curve&field_tdr_date_value={selected_year}&page&_format=csv"
            
            with st.spinner(f"Loading Treasury rates data for {selected_year}..."):
                treasury_df = pd.read_csv(treasury_url)
            
            st.success(f"✅ Loaded {len(treasury_df)} records of Treasury rates data for {selected_year}")
            
            # Display the dataframe
            st.dataframe(treasury_df, use_container_width=True)
            
            # Add download button for the data
            csv_data = treasury_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Treasury Rates Data as CSV",
                data=csv_data,
                file_name=f"treasury_rates_{selected_year}.csv",
                mime="text/csv"
            )
        except Exception as e:
            st.error(f"❌ Error loading Treasury rates data for {selected_year}: {str(e)}")
            st.info("Please check your internet connection or try a different year.")
