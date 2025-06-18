import openpyxl
import os


def create_workbook(measurement_date, end_date, lease_length, discount_rate, classification, period_list, 
                    date_list, payment_list,t_c, initial_direct_costs=0, incentives=0, prepaid_rent=0, payment_period='Beginning',
                    ):
    current_dir = os.path.dirname(__file__)
    excel_path = os.path.join(current_dir, 'Lease Template 2.0.xlsx')
    wb = openpyxl.load_workbook(excel_path)
    ws = wb['Lease Amortization Schedule'] 

    # Example: update row 2 and 5 (columns B and C)
    data_updates = {
        5: {'C': measurement_date},  
        6: {'C': end_date},
        7: {'C': lease_length},
        8: {'C': discount_rate},
        9: {'C': (discount_rate)/12},
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
    
    ws_tc = wb['Lease T&C']


    t_c_updates = {
        5: {
            'C': t_c['terms_conditions_details']['Address']['section'],
            'D': t_c['terms_conditions_details']['Address']['value'],
            },  
        6: {
            'C': t_c['terms_conditions_details']['Lessee']['section'],
            'D': t_c['terms_conditions_details']['Lessee']['value'],
            },
        7: {
            'C': t_c['terms_conditions_details']['Lessor']['section'],
            'D': t_c['terms_conditions_details']['Lessor']['value'],
            },
        8: {
            'C': t_c['terms_conditions_details']['Premise Description']['section'],
            'D': t_c['terms_conditions_details']['Premise Description']['value'],
            },
        9: {
            'C': "",
            'D':classification, #TODO classification
            }, #TODO classfication 
        10: {
            'C': "",
            'D':lease_length
            }, #TODO lease term 
        11: {
            'C': "",
            'D': "", #TODO lease execution date
            }, #TODO lease execution date
        12: {
            'C': "",
            'D': "",
            }, #TODO commencement date
        13: {
            'C': t_c['terms_conditions_options']['Purchase Option']['section'],
            'D': t_c['terms_conditions_options']['Purchase Option']['value']+", "+t_c['terms_conditions_options']['Purchase Option']['proof'],
            },
        14: {
            'C': t_c['terms_conditions_options']['Renewal Option']['section'],
            'D': t_c['terms_conditions_options']['Renewal Option']['value']+", "+t_c['terms_conditions_options']['Renewal Option']['proof'],
            },
        15: {
            'C': t_c['terms_conditions_options']['Break Option']['section'],
            'D': t_c['terms_conditions_options']['Break Option']['value']+", "+t_c['terms_conditions_options']['Break Option']['proof'],
            },
        16: {
            'C': "",
            'D': end_date
            }, #TODO Lease end section
        17: {
            'C': "",
            'D': "", #TODO adoption date    
            }, #TODO adoption date
        18: {
            'C': "",
            'D': "", #TODO earlier of commencement or adoption date
            }, #TODO earlier of commencement or adoption date
        19: {
            'C': t_c['terms_conditions_options']['Security Deposit']['section'],
            'D': t_c['terms_conditions_options']['Security Deposit']['value']+", "+t_c['terms_conditions_options']['Security Deposit']['proof'],
            'E': t_c['terms_conditions_options']['Security Deposit']['amount'],
            },
        20: {
            'C': t_c['terms_conditions_options']['Prepaid Rent']['section'],
            'D': t_c['terms_conditions_options']['Prepaid Rent']['value']+", "+t_c['terms_conditions_options']['Prepaid Rent']['proof'],
            'E': t_c['terms_conditions_options']['Prepaid Rent']['amount'],
            },
        21: {
            'C': t_c['terms_conditions_financials']['Payment Due Date']['section'],
            'D': t_c['terms_conditions_financials']['Payment Due Date']['value'],},
        22: {
            'C': t_c['terms_conditions_financials']['Rent Payments']['section'],
            'D': t_c['terms_conditions_financials']['Rent Payments']['value'],
            },
        23: {
            'C': t_c['terms_conditions_financials']['Rent Escalations']['section'],
            'D': t_c['terms_conditions_financials']['Rent Escalations']['value'],
            },
        24: {
            'C': t_c['terms_conditions_financials']['Percentage Rent']['section'],
            'D': t_c['terms_conditions_financials']['Percentage Rent']['value'],
            },
        25: {
            'C': t_c['terms_conditions_additional']['Taxes and Insurance']['section'],
            'D': t_c['terms_conditions_additional']['Taxes and Insurance']['value'],
            },
        26: {
            'C': "",
            'D': ""
            }, #TODO Tenant Improvements
        27: {
            'C': t_c['terms_conditions_additional']['Brokerage Commissions']['section'],
            'D': t_c['terms_conditions_additional']['Brokerage Commissions']['value']+", "+t_c['terms_conditions_additional']['Brokerage Commissions']['proof'],
            'E': t_c['terms_conditions_additional']['Brokerage Commissions']['amount'],
            }, #TODO: responsible party
        28: {
            'C': t_c['terms_conditions_additional']['Lease Incentives']['section'],
            'D': t_c['terms_conditions_additional']['Lease Incentives']['value']+", "+t_c['terms_conditions_additional']['Lease Incentives']['proof'],
            'E': t_c['terms_conditions_additional']['Lease Incentives']['amount'],
            },
    }

    for row_idx, updates in t_c_updates.items():
        for col_letter, value in updates.items():
            ws_tc[f"{col_letter}{row_idx}"] = value


    return wb
