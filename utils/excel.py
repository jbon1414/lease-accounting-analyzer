import xlsxwriter
import io

def create_lease_amortization_schedule_excel(payment_df, df3):
    # Create a BytesIO buffer to write the Excel file in memory
    output = io.BytesIO()
    
    # Create workbook with the buffer instead of a filename
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    worksheet = workbook.add_worksheet("Lease Amortization Schedule Ex.")
    print(df3.columns)

    # Your existing cell definitions and formulas
    for cell, desc in [
        ["B2:C2", 'Primary Inputs'],
        ["B3", 'Measurement Date'],
        ["C3", df3['Values'].iloc[0]],
        ["B4", 'Lease Expiration Date'],
        ["B5", "Lease term (in months)"],
        ["C5", len(payment_df)],
        ["B6", "Annual Discount Rate"],
        ["C6", df3['Values'].iloc[3]],
        ["B7", 'Monthly Discount Rate'],
        ["C7", df3['Values'].iloc[4]],
        ["B8", "Initial Direct Costs"],
        ["B9", "Incentives"],
        ["B10", "Prepaid Rent"],
        ["B11", 'Periodic Payments Made At Beginning or Ending of Period'],
        ["C11", df3['Values'].iloc[8]],
        ["B12", "Lease Classification"],
        ["C12", df3['Values'].iloc[9]],

        ["B13:C13", "Beginning Balances"],
        ["D13", "Current"],
        ["E13", "Non-Current"],
        ["B14", "Initial Lease Liability"],
        ["C14", "=SUM(G20:G963)"],
        ["B15", "Initial ROU Asset"],
        ["C15", "=C14+C8-C9+C10"],
        ["B16", "Total Remaining Lease Costs"],
        ["C17", "=SUM(F20:F963)+C15-C14"],

        ["E4", "Lease Commencement Date Journal Entries"],
        ["E5", "ROU Asset"],
        ["E6", "Cash-Lease Incentives"],
        ["E7", "Lease Liability"],
        ["E8", "Cash- Initial Direct Costs"],
        ["E9", "Total"],

        ["B18:C18", "Date/Time"],
        ["D18:H18", "Lease Liability"],
        ["I18:L18", "Right of Use Asset"],
        ["M18:N18", "Current/ Non-Current Liabilities"],
        ["P18:U18", "Journal Entries"],
        ["B19", "Period"],
        ["C19", "Date"],
        ["D19", "Beginning Balance"],
        ["E19", "Liability Acretion"],
        ["F19", "Lease Payment"],
        ["G19", "PV Lease Payment"],
        ["H19", "End Balance"],
        ["I19", "Beginning Balance"],
        ["J19", "ROU Amortization- Finance Lease Cost- Operating"],
        ["K19", "Asset Reduction- Operating"],
        ["L19", "End Balance"],
        ["M19", "Current"],
        ["N19", "Non-Current"],
        ["P19", "Cash"],
        ["Q19", "Lease Expense"],
        ["R19", "Lease Liability - Current"],
        ["S19", "Lease Liability - Non-Current"],
        ["T19", "ROU Asset"],
        ["U19", "Check"],
        ["C7", "=C8/12"]
    ]:
        worksheet.write(cell, desc)

    # Your existing data population logic
    cell_start = 20
    for i, row in payment_df.iterrows():
        worksheet.write(f"F{cell_start+i}", row['Lease Payment'])
        worksheet.write(f"C{cell_start+i}", row['Date'])
        worksheet.write(f"B{cell_start+i}", i)
        worksheet.write(f"D{cell_start+i}", "=$C$17")
        worksheet.write(f"E{cell_start+i}", f"=IF($C$11='Beginning',(D{cell_start+i}-F{cell_start+i})*$C$7,D{cell_start+i}*$C$7)")
        worksheet.write(f"G{cell_start+i}", f"=F{cell_start+i}/(1+$C$7)^B{cell_start+i}")
        worksheet.write(f"H{cell_start+i}", f"=D{cell_start+i}+E{cell_start+i}-F{cell_start+i}")
        if i == 0:
            worksheet.write(f"I{cell_start+i}", f"=$C$15")
        else:
            worksheet.write(f"I{cell_start+i}", f"=L{cell_start+i-1}")

        worksheet.write(f"J{cell_start+i}", f"=IF($C$12='Finance',$I${cell_start+i}/$C$5,$C$17/$C$5)")
        worksheet.write(f"K{cell_start+i}", f"=IF($C$12='Operating',J{cell_start+i}-E{cell_start+i},0)")
        worksheet.write(f"L{cell_start+i}", f"=IF($C$12='Operating',I{cell_start+i}-K{cell_start+i},I{cell_start+i}-J{cell_start+i})")
        worksheet.write(f"M{cell_start+i}", f"=SUM(F{cell_start+i+1}:F{cell_start+i+12})-SUM(E{cell_start+i+1}:E{cell_start+i+12})")
        worksheet.write(f"N{cell_start+i}", f"=H{cell_start+i}-M{cell_start+i}")

    # Close the workbook to finalize the Excel file in memory
    workbook.close()
    
    # Get the Excel file data from the buffer
    excel_data = output.getvalue()
    output.close()
    
    return excel_data