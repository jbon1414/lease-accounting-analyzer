import pandas as pd
import datetime as dt


def calculate_discount_rate(date_string, lease_length):
    commencement_date = dt.datetime.strptime(date_string, '%Y-%m-%d')
    selected_year = commencement_date.year
    selected_year_2 = (commencement_date-dt.timedelta(days=365)).year
    commencement_date = dt.date(commencement_date.year, commencement_date.month, commencement_date.day)

    treasury_url = f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{selected_year}/all?type=daily_treasury_yield_curve&field_tdr_date_value={selected_year}&page&_format=csv"
    df = pd.read_csv(treasury_url)

    treasury_url_2 = f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{selected_year_2}/all?type=daily_treasury_yield_curve&field_tdr_date_value={selected_year_2}&page&_format=csv"
    df2 = pd.read_csv(treasury_url_2)

    df = pd.concat([df, df2])

    df['Date'] = pd.to_datetime(df['Date']).dt.date
    df = df.rename(columns={
        '1 Mo': 1,
        '1.5 Mo': 1.5,
        '2 Mo': 2,
        '3 Mo': 3,
        '4 Mo': 4,
        '6 Mo': 6,
        '1 Yr': 12,
        '2 Yr': 24,
        '3 Yr': 36,
        '5 Yr': 60,
        '7 Yr': 84,
        '10 Yr': 120,
        '20 Yr': 240,
        '30 Yr': 360
    })
    
    # Find the closest date with data
    final_df = df.loc[(df['Date'] == commencement_date)]
    while final_df.empty:
        commencement_date -= pd.Timedelta(days=1)
        final_df = df.loc[(df['Date'] == commencement_date)]
    
    print(f"commencement_date used:", commencement_date)
    print("original lease_length:", lease_length)
    
    # Available maturity periods (in months)
    available_periods = [1, 1.5, 2, 3, 4, 6, 12, 24, 36, 60, 84, 120, 240, 360]
    
    # Check if exact match exists
    if lease_length in available_periods:
        interpolated_rate = final_df[lease_length].values[0]
        print(f"Exact match found. Using rate: {interpolated_rate}")
    else:
        # Find the two closest periods for interpolation
        lower_period = None
        upper_period = None
        
        for period in available_periods:
            if period < lease_length:
                lower_period = period
            elif period > lease_length and upper_period is None:
                upper_period = period
                break
        
        # Handle edge cases
        if lower_period is None:
            # Lease length is shorter than shortest available period
            interpolated_rate = final_df[available_periods[0]].values[0]
            print(f"Lease length shorter than available data. Using {available_periods[0]} month rate: {interpolated_rate}")
        elif upper_period is None:
            # Lease length is longer than longest available period
            interpolated_rate = final_df[available_periods[-1]].values[0]
            print(f"Lease length longer than available data. Using {available_periods[-1]} month rate: {interpolated_rate}")
        else:
            # Perform linear interpolation
            lower_rate = final_df[lower_period].values[0]
            upper_rate = final_df[upper_period].values[0]
            
            # Linear interpolation formula: y = y1 + (x - x1) * (y2 - y1) / (x2 - x1)
            interpolated_rate = lower_rate + (lease_length - lower_period) * (upper_rate - lower_rate) / (upper_period - lower_period)
            
            print(f"Interpolating between {lower_period} months ({lower_rate}%) and {upper_period} months ({upper_rate}%)")
            print(f"Interpolated rate for {lease_length} months: {interpolated_rate}")
    
    # Return the interpolated rate and the dataframe with original column names
    return interpolated_rate, final_df.rename(columns={
        1: '1 Mo',
        1.5: '1.5 Mo',
        2: '2 Mo',
        3: '3 Mo',
        4: '4 Mo',
        6: '6 Mo',
        12: '1 Yr',
        24: '2 Yr',
        36: '3 Yr',
        60: '5 Yr',
        84: '7 Yr',
        120: '10 Yr',
        240: '20 Yr',
        360: '30 Yr'
    })

def build_ibr_df(commencement_date, end_date, discount_rate, has_debt=False, debt_data=None):
    """
    Build a DataFrame with the IBR data.
    """
    # Convert dates to datetime objects
    commencement_date = pd.to_datetime(commencement_date)
    end_date = pd.to_datetime(end_date)
    if has_debt and debt_data:
        debt_df = pd.DataFrame(debt_data)
        debt_df['Term (Years)'] = (pd.to_datetime(debt_df['end_date']) - pd.to_datetime(debt_df['measurement_date'])).dt.days / 365
        debt_df['Company Risk-Free Rate'] = pd.to_numeric('discount_rate', errors='coerce')
        debt_df['Company Risk Premium'] = debt_df['discount_rate']-debt_df['Company Risk-Free Rate']
    else:
        risk_premium = 0.0
        debt_df = None

    ibr_df = pd.DataFrame({
        'Lease Commencement Date': [commencement_date],
        'Lease End Date': [end_date],
        'Remaining Lease Term (Years)': [(end_date - commencement_date).days / 365],
        'Lease risk-free rate': [discount_rate],
        'Company risk premium': [risk_premium], 
        'Lease Incremental Borrowing Rate': [discount_rate + 0.0]
    })
    return ibr_df, debt_df
