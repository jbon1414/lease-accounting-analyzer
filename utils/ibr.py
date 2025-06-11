import pandas as pd
import datetime as dt


def calculate_dicount_rate(date_string, lease_length):
    commencement_date = dt.datetime.strptime(date_string, '%Y-%m-%d')
    selected_year = commencement_date.year
    selected_year_2 = (commencement_date-dt.timedelta(days=365)).year
    commencement_date = dt.date(commencement_date.year, commencement_date.month, commencement_date.day)

    treasury_url = f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{selected_year}/all?type=daily_treasury_yield_curve&field_tdr_date_value={selected_year}&page&_format=csv"
    df = pd.read_csv(treasury_url)

    treasury_url_2 = f"https://home.treasury.gov/resource-center/data-chart-center/interest-rates/daily-treasury-rates.csv/{selected_year_2}/all?type=daily_treasury_yield_curve&field_tdr_date_value={selected_year_2}&page&_format=csv"
    df2 = pd.read_csv(treasury_url_2)

    df =  pd.concat([df, df2])

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
    lease_length = min([1,1.5, 2, 3, 4, 6, 12, 24, 36, 60, 84, 120, 240, 360], key=lambda x: abs(x - lease_length))
    final_df = df.loc[(df['Date'] == commencement_date)]
    while final_df.empty:
        commencement_date -= pd.Timedelta(days=1)
        lease_length = min([1,1.5, 2, 3, 4, 6, 12, 24, 36, 60, 84, 120, 240, 360], key=lambda x: abs(x - lease_length))
        final_df = df.loc[(df['Date'] == commencement_date)]
    print(f"commencent_date used:", commencement_date)
    print("lease_length used:", lease_length)
    return final_df[lease_length].values[0], final_df.rename(columns={
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
        360:'30 Yr'
            })

def build_ibr_df(commencement_date, end_date, discount_rate):
    """
    Build a DataFrame with the IBR data.
    """
    # Convert dates to datetime objects
    commencement_date = pd.to_datetime(commencement_date).dt.date
    end_date = pd.to_datetime(end_date).dt.date

    ibr_df = pd.DataFrame({
        'Lease Commencement Date': [commencement_date],
        'Lease End Date': [end_date],
        'Remainging Lease Term (Years)': [(end_date - commencement_date).days / 365],
        'Lease risk-free rate': [discount_rate],
        'Company risk premium': [0.0],  # Placeholder for risk premium
        'Lease Incremental Borrowing Rate': [discount_rate + 0.0]  # Placeholder for IBR calculation
    })
    return ibr_df
