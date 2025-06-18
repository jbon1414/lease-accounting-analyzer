import openpyxl
import os


def create_workbook(measurement_date, end_date, lease_length, discount_rate, classification, period_list, date_list, payment_list, initial_direct_costs=0, incentives=0, prepaid_rent=0, payment_period='Beginning'):
    current_dir = os.path.dirname(__file__)
    excel_path = os.path.join(current_dir, 'Lease Template 2.0.xlsx')
    wb = openpyxl.load_workbook(excel_path)
    ws = wb.active 

    # Example: update row 2 and 5 (columns B and C)
    data_updates = {
        5: {'C': measurement_date},  
        6: {'C': end_date},
        7: {'C': lease_length},
        8: {'C': discount_rate/100},
        9: {'C': (discount_rate/100)/12},
        10: {'C': initial_direct_costs},
        11: {'C': incentives},
        12: {'C': prepaid_rent},
        13: {'C': payment_period},
        14: {'C': classification}

    }
    b_list=period_list
    for i, value in enumerate(b_list):
        row = i+24
        # Check if the row key exists in data_updates, if not, initialize an empty dictionary for it
        if row not in data_updates:
            data_updates[row] = {}
        data_updates[row]['B'] = value

    c_list = date_list
    for i, value in enumerate(c_list):
        row = i+24
        # Check if the row key exists in data_updates, if not, initialize an empty dictionary for it
        if row not in data_updates:
            data_updates[row] = {}
        data_updates[row]['C'] = value

    f_list = payment_list
    for i, value in enumerate(f_list):
        row = i+24
        # Check if the row key exists in data_updates, if not, initialize an empty dictionary for it
        if row not in data_updates:
            data_updates[row] = {}
        data_updates[row]['F'] = value


    for row_idx, updates in data_updates.items():
        for col_letter, value in updates.items():
            ws[f"{col_letter}{row_idx}"] = value

    return wb
