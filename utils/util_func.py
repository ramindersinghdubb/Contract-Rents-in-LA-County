import pandas as pd
import geopandas as gpd
import numpy as np
import requests as req
from datetime import datetime
from typing import List
from functools import reduce
from warnings import filterwarnings
import os, shutil, asyncio, unicodedata, json, aiohttp

filterwarnings('ignore')

# Folder paths
data_folder = f"{os.getcwd()}/data/"
masterfiles_folder = data_folder + "masterfiles/"
mastergeometries_folder = data_folder + "mastergeometries/"
for folder in [data_folder, masterfiles_folder, mastergeometries_folder]:
    if not os.path.exists(folder):
        os.makedirs(folder)

# Remove accent marks on strings
def remove_accents(input_str: str) -> str:
    """
    Return the non-accented ASCII string for the inputed string.
    
    :param input_str: Inputed string.
    :type input_str: str
    
    :return: Non-accented ASCII equivalent string.
    :rtype: str
    """
    nfkd_form = unicodedata.normalize('NFKD', input_str)
    only_ascii = nfkd_form.encode('ASCII', 'ignore')
    return only_ascii.decode('ASCII')

# Append county names for city names that show up more than once
def append_counties_to_cities(series, county_series):
    counts = series.value_counts()
    for item in counts.index:
        if counts[item] > 1:
            series[series == item] += ' (' + county_series[series == item] + ')'
    return series

# LA County Cities and their FIPS codes
txt_file_url = "https://www2.census.gov/geo/docs/reference/codes2020/place/st06_ca_place2020.txt"

ca2020 = pd.read_csv(txt_file_url, sep = '|', dtype = {'STATEFP': object, 'PLACEFP': object})
ca2020['FIPS'] = ca2020['STATEFP'] + ca2020['PLACEFP']
ca2020['NAME'] = ca2020['PLACENAME'].str.replace(' CDP', "").str.replace(' city', "").str.replace(' town', ' Town')
ca2020['NAME'] = append_counties_to_cities(ca2020['NAME'], ca2020['COUNTIES'])
ca2020['ABBREV_NAME'] = [ remove_accents(i).replace(" ", "") for i in ca2020['NAME'] ]

LA_cities_2020 = ca2020[ca2020.COUNTIES.str.contains('Los Angeles County')]

index_df = LA_cities_2020[['FIPS', 'NAME', 'ABBREV_NAME']]

# ---- Asynchronous Functions for ETL ---- #
async def _request(url: str):
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                return await resp.json()

async def url_extract(urls: list[str], batch_size: int):
    results = []
    for i in range(0, len(urls), batch_size):
        results.extend( await asyncio.gather(*[_request(u) for u in urls[i:i+batch_size]]) )
    return results


# ---- ETL Function ---- #
def ACS_data_extraction(ACS_code: str,
                        API_key: str,
                        initial_year: int = 2010,
                        final_year: int = datetime.now().year,
                        batch_size: int = 250) -> None:
    """
    ETL function that creates formatted .CSV files for all places in SoCal on the specified American Community Survey (ACS) code.
    
    Parameters
    -----------
    ACS_code (str) : ACS code for data of interest.

    API_key (str) : Census Bureau API key to allow for >50 url requests in a session.
    
    initial_year (int) : Starting year. Default '2010'.

    final_year (int) : Final year. Default current year.

    batch_size (int) : Batch size for rate-checking the asynchronous url extraction. Default '250'.
    
    """
    # Folder paths
    tmp_folder = data_folder + "tmp/"
    masterfiles_ACS_folder = masterfiles_folder + f'ACS_Codes/{ACS_code}/'

    for folder in [tmp_folder, masterfiles_ACS_folder]:
        if not os.path.exists(folder):
            os.makedirs(folder)

    if ACS_code.startswith('DP'):
        spec = '/profile'
    elif ACS_code.startswith('S'):
        spec = '/subject'
    else:
        spec = ''
    
    dummy_dict = {}

    for year in range(initial_year, final_year + 1):
        ACS_df_file_path = masterfiles_ACS_folder + f'{ACS_code}_{year}_masterfile.csv'
        if os.path.exists(ACS_df_file_path):
            continue
        
        for FIPS in index_df.FIPS:
            url = f'https://api.census.gov/data/{year}/acs/acs5{spec}?get=group({ACS_code})&ucgid=pseudo(1600000US{FIPS}$1400000)&key={API_key}'
            city_name = index_df.loc[index_df.FIPS == FIPS, 'NAME'].iloc[0]
            dummy_name = index_df.loc[index_df.FIPS == FIPS, 'ABBREV_NAME'].iloc[0]
            dummy_dict[url] = (FIPS, year, city_name, dummy_name)

    urls = list( dummy_dict.keys() )
    files = asyncio.run( url_extract(urls, batch_size) )
        
    df_list = []
    for file_info, file in zip(dummy_dict.values(), files):
        if file == None:
            continue

        FIPS, year, city_name, dummy_name = file_info
        df = pd.DataFrame(file[1:], columns = file[0], index = None)

        # Data cleaning
        try:
            if df.empty or df.shape[1] == 0:
                continue

            df = df.drop([col for col in df.columns if col.endswith('A')], axis = 1)
            
            df['GEO_ID'] = df['GEO_ID'].str.replace('1400000US', "").astype('object')
            df['YEAR'] = int(year)
            df['CITY'] = city_name
            df['NAME'] = df['NAME'].str.replace(';', ',')
            df[['TRACT', 'COUNTY', 'STATE']] = df['NAME'].str.split(', ', expand = True)
            df['ABBREV_NAME'] = dummy_name
            
            value_dict = {-222222222: np.nan, -333333333: np.nan, -555555555: np.nan, -666666666: np.nan, -888888888: np.nan, -999999999: np.nan,
                            '-222222222': np.nan, '-333333333': np.nan, '-555555555': np.nan, '-666666666': np.nan, '-888888888': np.nan, '-999999999': np.nan}
            df.replace(value_dict, inplace=True)
            ordered_columns = ['YEAR', 'GEO_ID', 'TRACT', 'CITY', 'COUNTY', 'STATE', 'ABBREV_NAME']
            df = df[ ordered_columns + [col for col in df.columns if ACS_code in col] ]

            df.sort_values(by = ['GEO_ID'], inplace = True)

            cleaned_file_path = f"{tmp_folder}{ACS_code}_{dummy_name}_{year}_cleaned.csv"
            df.to_csv(cleaned_file_path, index=False)
            df_list.extend(df.to_dict('records'))

        except pd.errors.EmptyDataError:
            continue
    
    if len(df_list) == 0:
        pass

    else:
        dummy_df = pd.DataFrame(df_list)
            
        for year in dummy_df.YEAR.unique():
            df = dummy_df[dummy_df.YEAR == year]
            ACS_df_file_path = masterfiles_ACS_folder + f'{ACS_code}_{year}_masterfile.csv'
            df.to_csv(ACS_df_file_path, index=False)
    
    shutil.rmtree(tmp_folder)


# ---- Masterfile Function ---- #
def masterfile_creation(ACS_codes: List[str], API_key: str):
    """
    Create year-segmented masterfiles on the specified ACS codes.
    
    :param ACS_code: Description
    :type ACS_code: List[str]

    :param API_key: Census Bureau API key to allow for >50 url requests in a session.
    :type API_key: str
    """
    df_list = []
    for ACS_code in ACS_codes:
        
        # Data extraction
        ACS_data_extraction(ACS_code, API_key)

        # Data concatenation
        dummy_list = []
        for root, dirs, files in os.walk(f'{masterfiles_folder}ACS_Codes/{ACS_code}'):
            for file in files:
                dummy_list.append( pd.read_csv( os.path.join(root, file) ) )
        dummy_df = pd.concat(dummy_list, ignore_index = True)
        df_list.append( dummy_df )

    # Segmentation
    df = reduce(lambda left, right: pd.merge(left, right, on = ['YEAR', 'GEO_ID', 'TRACT', 'CITY', 'COUNTY', 'STATE', 'ABBREV_NAME'], how = 'left'),
                df_list)
    for year in df.YEAR.unique():
        dummy_df = df[df.YEAR == year]

        CSV_file_path = f'{masterfiles_folder}{year}_masterfile.csv'
        dummy_df.to_csv(CSV_file_path, index = False)

        JSON_file_path = f'{masterfiles_folder}{year}_masterfile.json'
        dummy_df.to_json(JSON_file_path, orient='records')
    
    # Reference TXT file containing the earliest and most recent years of data for each city
    with open(f'{data_folder}reference.txt', 'w') as txtfile:
        txtfile.write("CITY|ABBREV_NAME|INITIAL_YEAR|RECENT_YEAR")
        txtfile.write("\n")
        for ABBREV_NAME in df['ABBREV_NAME'].unique():
            CITY = df.loc[df['ABBREV_NAME'] == ABBREV_NAME, 'CITY'].iloc[0]
            years = list(sorted(df['YEAR'][df['ABBREV_NAME'] == ABBREV_NAME].unique()))
            INT_YEAR = min(years)
            REC_YEAR = max(years)
            content = '|'.join([CITY, ABBREV_NAME, str(INT_YEAR), str(REC_YEAR)])
            txtfile.write(content)
            txtfile.write('\n')


# ---- Mastergeometry Function ---- #
def mastergeometry_creation():
    """
    Create year-segmented mastergeometries for the previously generated masterfiles.

    Note that `masterfile_creation()` must be called prior to this.
    """
    years = [int(file.split('_')[0]) for file in os.listdir(masterfiles_folder) if 'masterfile.csv' in file]
    
    for year in sorted(list(set(years))):
        file_path = mastergeometries_folder + f'{year}_mastergeometry.geojson'
        if os.path.exists(file_path):
            continue

        if year == 2010:
            zip_file_url = f'https://www2.census.gov/geo/tiger/TIGER2010/TRACT/2010/tl_2010_06_tract10.zip'
        else:
            zip_file_url = f'https://www2.census.gov/geo/tiger/TIGER{year}/TRACT/tl_{year}_06_tract.zip'
        
        r = req.get(zip_file_url)
        if r.status_code == 200:
            gdf = gpd.read_file(zip_file_url)

            if year == 2010:
                gdf = gdf[['STATEFP10', 'COUNTYFP10', 'TRACTCE10', 'GEOID10', 'NAMELSAD10', 'INTPTLAT10', 'INTPTLON10', 'geometry']]
                gdf.rename(
                    columns = {'STATEFP10': 'STATE',
                                'COUNTYFP10': 'COUNTY',
                                'TRACTCE10': 'TRACT',
                                'GEOID10': 'GEO_ID',
                                'NAMELSAD10': 'NAME',
                                'INTPTLAT10': 'INTPTLAT',
                                'INTPTLON10': 'INTPTLON'
                                },
                    inplace = True
                )
            else:
                gdf = gdf[['STATEFP', 'COUNTYFP', 'TRACTCE', 'GEOID', 'NAMELSAD', 'INTPTLAT', 'INTPTLON', 'geometry']]
                gdf.rename(
                    columns = {'STATEFP': 'STATE',
                                'COUNTYFP': 'COUNTY',
                                'TRACTCE': 'TRACT',
                                'GEOID': 'GEO_ID',
                                'NAMELSAD': 'NAME'
                                },
                    inplace = True
                )
            gdf['INTPTLAT'] = gdf['INTPTLAT'].str.replace('+', '').astype(float)
            gdf['INTPTLON'] = gdf['INTPTLON'].str.replace('+', '').astype(float)

            gdf['GEO_ID'] = gdf['GEO_ID'].astype('int64')

            masterfile_path = masterfiles_folder + f'{year}_masterfile.csv'
            dummy_df = pd.read_csv(masterfile_path)

            dummy_gdf = gdf[['GEO_ID', 'INTPTLAT', 'INTPTLON', 'geometry']].merge(dummy_df, on = 'GEO_ID')
            dummy_gdf = dummy_gdf[['YEAR', 'GEO_ID', 'TRACT', 'CITY', 'COUNTY', 'STATE', 'ABBREV_NAME', 'INTPTLAT', 'INTPTLON', 'geometry']]
            
            dummy_gdf.to_file(file_path, driver='GeoJSON')


# ---- Lat/Lon Center Points Function ---- #
def lat_lon_center_points():
    """
    Create year-segmented latitudinal/longitudinal center points for the previously generated mastergeometries.
    This helps center Dash-generated maps.

    Note that `mastergeometry_creation()` must be called prior to this.
    """
    mastergeometry_files = sorted([f'{mastergeometries_folder}{file}' for file in os.listdir(mastergeometries_folder)])

    lat_lon_center_points_folder = data_folder + 'lat_lon_center_points/'
    if not os.path.exists(lat_lon_center_points_folder):
        os.makedirs(lat_lon_center_points_folder)
    
    for mastergeometry_file in mastergeometry_files:
        gdf = gpd.read_file(mastergeometry_file)
        YEAR = gdf.loc[:, 'YEAR'][0]
        
        with open(f'{lat_lon_center_points_folder}{YEAR}_latlon_center_points.json', 'w') as jsonfile:
            json_list = []
            for ABBREV_NAME in sorted(gdf['ABBREV_NAME'].unique()):
                CITY = gdf.loc[gdf['ABBREV_NAME'] == ABBREV_NAME, 'CITY'].iloc[0]
                LAT_CENTER, LON_CENTER = map(lambda x: str(round(x, 10)), gdf[['INTPTLAT', 'INTPTLON']][gdf['ABBREV_NAME'] == ABBREV_NAME].mean(axis=0))
                content = {"CITY": CITY, "ABBREV_NAME": ABBREV_NAME, "LAT_CENTER": LAT_CENTER, "LON_CENTER": LON_CENTER}
                json_list.append(content)

            json.dump(json_list, jsonfile)