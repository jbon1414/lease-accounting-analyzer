import openpyxl


def create_workbook(measurement_date, end_date, lease_length, discount_rate, classification, period_list, date_list, payment_list):
    wb = openpyxl.load_workbook(r"utils\Lease Template 2.0.xlsx")
    ws = wb.active 

    # Example: update row 2 and 5 (columns B and C)
    data_updates = {
        5: {'C': measurement_date},  
        6: {'C': end_date},
        7: {'C': lease_length},
        8: {'C': discount_rate/100},
        9: {'C': discount_rate/12},
        10: {'C': 0},
        11: {'C': 0},
        12: {'C': 0},
        13: {'C': 'Beginning'},
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
