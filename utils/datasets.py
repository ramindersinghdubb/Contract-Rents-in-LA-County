import os
import pandas as pd
from util_func import (
    masterfiles_folder,
    masterfile_creation,
    mastergeometry_creation,
    lat_lon_center_points
)

# Masterfile creation
masterfile_creation(['B25057', 'B25058', 'B25059'], API_key = os.environ['SECRET_KEY'], batch_size = 400)

# Formatting
ABBREV_NAMES = [file.split('_')[0] for file in os.listdir(masterfiles_folder) if 'masterfile.csv' in file]

for ABBREV_NAME in ABBREV_NAMES:
    CSV_file_path = f'{masterfiles_folder}{ABBREV_NAME}_masterfile.csv'
    df = pd.read_csv(CSV_file_path)

    df['Median'] = df['B25058_001E']
    df['75th'] = df['B25059_001E']
    df['25th'] = df['B25057_001E']
    for col in ['Median', '75th', '25th']:
        df[col] = '$' + df[col].astype(str)
        df[col] = df[col].str.replace('.0', '')
        df.loc[df[col] == '$nan', col] = 'Not Available!'
        df.loc[(df[col] == '$2001') & (df['YEAR'] <= 2014), col] = 'Not available. Exceeds $2000!'
        df.loc[(df[col] == '$3501') & (df['YEAR'] > 2014), col] = 'Not available. Exceeds $3500!'

    df = df.sort_values(by = ['YEAR', 'GEO_ID'], ignore_index = True)

    df.to_csv(CSV_file_path, index = False)

    JSON_file_path = f'{masterfiles_folder}{ABBREV_NAME}_masterfile.json'
    df.to_json(JSON_file_path, orient='records')

# Mastergeometry creation
mastergeometry_creation()

# Accompanying latitudinal and longitudinal center points
lat_lon_center_points()