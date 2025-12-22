import os
import pandas as pd
from util_func import masterfiles_folder, masterfile_creation, mastergeometry_creation, lat_lon_center_points

# Masterfile creation
masterfile_creation(['B25057', 'B25058', 'B25059'], API_key = os.environ['SECRET_KEY'])

# Formatting
years = [int(file.split('_')[0]) for file in os.listdir(masterfiles_folder) if 'masterfile.csv' in file]

df_list = []
for year in years:
    CSV_file_path = f'{masterfiles_folder}{year}_masterfile.csv'
    df = pd.read_csv(CSV_file_path)

    if not df.columns.isin(['Median', '75th', '25th', 'dummy']).any():

        df['Median'] = df['B25058_001E']
        df['75th'] = df['B25059_001E']
        df['25th'] = df['B25057_001E']
        columns = ['Median', '75th', '25th']
        for col in columns:
            df[col] = '$' + df[col].astype(str)
            df[col] = df[col].str.replace('.0', '')
            df.loc[df[col] == '$nan', col] = 'Not Available!'
            if year <= 2014:
                df.loc[df[col] == '$2001', col] = 'Not available. Exceeds $2000!'
            else:
                df.loc[df[col] == '$3501', col] = 'Not available. Exceeds $3500!'
        # For the trace
        df['dummy'] = 1

        df.to_csv(CSV_file_path, index = False)
        df_list.append(df)

        JSON_file_path = f'{masterfiles_folder}{year}_masterfile.json'
        df.to_json(JSON_file_path, orient='records')

masterfile = pd.concat(df_list, ignore_index = True)
masterfile.to_csv('data/masterfile.csv', index = False)
masterfile.to_json('data/masterfile.json', orient = 'records')

# Mastergeometry creation
mastergeometry_creation()

# Accompanying latitudinal and longitudinal center points
lat_lon_center_points()