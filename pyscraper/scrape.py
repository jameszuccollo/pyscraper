# -*- coding: utf-8 -*-
# Scrapers returning pandas dataframes.

# ONS IMPORTER

import pandas as pd


def _retrieve_ONS_csv(dataset, series):
    """Return csv file url for required dataset and series"""
    # Clean input parameters
    dataset = dataset.lower().strip()
    series = [s.upper().replace(" ", "") for s in series]
    # Grab the raw csv
    target_url = 'http://www.ons.gov.uk/ons/datasets-and-tables/downloads/csv.csv?dataset=' + dataset \
        + '&cdid=' + ','.join(series)
    return target_url


def _create_quarterly_index(dfindex):
    """Takes a pandas dataframe index, '2002 Q2', and returns DatetimeIndex"""

    thedate = dfindex.values[0].split()
    starting_quarter = str(3 * int(thedate[1][-1]))
    starting_year = thedate[0]
    df2index = pd.date_range('1/' + starting_quarter + '/' + starting_year,
                             periods=len(dfindex), freq='Q-DEC')
    return df2index


def _timeseries_index(df, freq):
    """Takes dataframe and converts first column to DateTimeIndex"""
    df2 = df.set_index('Unnamed: 0')
    if freq == 'Q':
        df2.index = _create_quarterly_index(df2.index)
    elif freq == 'M':
        df2.index = pd.to_datetime(df2.index, format='%Y %b', errors='raise')
    elif freq == 'A':
        df2.index = pd.to_datetime(df2.index, format='%Y', errors='raise')
    return df2


def from_ONS(dataset, series, freq, print_url=False):
    """

    Function to download specific series from the ONS website and
    return a pandas dataframe. Downloads a csv from the ONS site and parses it.

    Takes:
        dataset: the abbreviated name of the ONS dataset (string). eg. 'qna', 'lms', 'mm23'
        series: ONS series codes to retrieve (list of strings). eg. ['YBHA', 'ABMI']
        freq: frequency of data required, {'A', 'Q', 'M'}

    Returns:
        A pandas dataframe.

    Example

    from_ONS('qna', ['YBHA', 'ABMI'], 'Q')
    """

    re_dict = {'Q': r'\d{4,4} Q\d$',
               'A': r'\d{4,4}$',
               'M': r'\d{4,4} [A-Z]{3,3}$'}

    freq = freq.upper()
    myfile = _retrieve_ONS_csv(dataset, series)
    if print_url:
        print(myfile)
    dfraw = pd.read_csv(myfile)
    criterion = dfraw['Unnamed: 0'].str.contains(re_dict[freq], na=False)
    if dfraw[criterion].empty:
        print("That frequency is unavailable for your series.")
        return
    else:
        df = _timeseries_index(dfraw[criterion], freq)
    df = df.astype(float)

    return df


# BoE IMPORTER

def _get_initial_date(yearsback):
    """
    Returns the date yearsback years before today.

    """

    from datetime import datetime

    initial_date = datetime.now()

    try:
        initial_date = initial_date.replace(year=initial_date.year - yearsback)
    except ValueError:
        initial_date = initial_date.replace(
            year=initial_date.year - yearsback, day=initial_date.day - 1)
    return initial_date


def from_BoE(series, datefrom=None, yearsback=5, vpd='y'):
    """

    Import latest data from the Bank of England website using csv interface.

    Takes:
        series: BoE series names (list of strings)
        datefrom: Initial date of series (pandas datetime)
        yearsback: If datefrom is not specified, how many years of
                   data would you like, counting backwards from today?

    Returns:
        df: Pandas dataframe of time series

    eg. df = from_BoE(['LPMAUZI', 'LPMAVAA'], datefrom=pd.datetime(2007, 8, 1))


    Optional arguments:

       vpd: Include provisional data? ('Y' or 'N')

    """
    import datetime

    Datefrom = datefrom if datefrom is not None else _get_initial_date(
        yearsback)
    Dateto = 'now'
    SeriesCodes = ','.join(series)
    UsingCodes = 'Y'
    CSVF = 'TN'
    VPD = vpd

    assert isinstance(series, list), "Input series must be a list."
    assert isinstance(
        Datefrom, datetime.datetime), "Date must be datetime.datetime."

    url = 'http://www.bankofengland.co.uk/boeapps/iadb/fromshowcolumns.asp?csv.x=yes&Datefrom=' + Datefrom.strftime("%d/%b/%Y") \
        + '&Dateto=' + Dateto \
        + '&SeriesCodes=' + SeriesCodes \
        + '&UsingCodes=' + UsingCodes \
        + '&CSVF=' + CSVF \
        + '&VPD=' + VPD
    print("CSV retrieved from", url)
    return pd.read_csv(url, index_col=0, parse_dates=True, header=0)

# IMF IMPORTER


def from_IMF(dataset, series=None, countries=None):
    """

    Import latest data from the IMF website.

    Takes:
        dataset: IMF dataset (string, currently accepts 'weo' or 'pubfin')
        series: Series codes to return (list of strings. Optional, default returns all).
        countries: Country names (not codes) to include (list of strings. Optional, default returns all).

    Returns:
        panel: Pandas panel of time series

    eg. df = from_IMF('weo', series=['GGSB_NPGDP', 'GGX_NGDP'], countries=['United Kingdom'])

        df = from_IMF('pubfin', series=['rev', 'prim_exp'], countries=['United Kingdom'])

    """
    # Grab the right dataset
    in_data = dataset.lower().strip()
    if in_data == 'weo':
        rawdata = _get_weo_data()
    elif in_data == 'pubfin':
        rawdata = _get_pubfin_data()
    else:
        raise ValueError("Unrecognised dataset.")

    if series is None and countries is None:
        return rawdata
    if series is None:
        return rawdata.loc[:, countries, :]
    if countries is None:
        return rawdata.loc[series, :, :]
    return rawdata.loc[series, countries, :]


def _get_pubfin_data():
    """
    Return the IMF Public Finances in Modern History dataset
    as a pandas panel object
    """

    import requests
    from zipfile import ZipFile
    from io import BytesIO

    zipFileURL = "http://www.imf.org/external/pubs/ft/wp/2013/data/wp1305.zip"
    xlsx_name = "Historical Public Finance Dataset_1.xlsx"

    IMFzip = requests.get(zipFileURL)
    IMFdata = ZipFile(BytesIO(IMFzip.content))
    IMFxlsx = IMFdata.open(xlsx_name)
    dfraw = pd.read_excel(IMFxlsx, sheetname="data")
    df = dfraw.set_index(['country', 'year'])

    #yr_one = int(df.index.levels[1][0])
    #yr_last = int(df.index.levels[1][-1])
    # yrindex = pd.date_range(start=pd.datetime(yr_one, 12, 31),
    #                        end=pd.datetime(yr_last, 12, 31), freq='A-DEC')

    #df.index.levels[1] = yrindex

    return df.to_panel()


def float_convert(s):
    """Convert data to floats"""
    if isinstance(s, str):
        return float(s.replace(',', ''))
    elif isinstance(s, float):
        return s
    else:
        print("Encountered type", type(s))


def _get_weo_data():
    """Return the IMF WEO dataset as a pandas panel object"""

    FileURL = "http://www.imf.org/external/pubs/ft/weo/2013/02/weodata/WEOOct2013all.xls"

    # Read in raw table
    dfraw = pd.read_table(FileURL,
                          na_values=['n/a', '--'])

    # Drop unneeded columns
    keep_cols = ['WEO Subject Code', 'Country']
    for i in dfraw.columns.values:
        if i.isdigit():
            keep_cols.append(i)
    dfdropped = dfraw[keep_cols]

    # Set multiindex
    dfdropped.set_index(['Country', 'WEO Subject Code'], inplace=True)

    # Reshape so variables are the columns
    dfdropped = dfdropped.stack().unstack(level=1)

    # Create timestamps for time index
    #yr_one = int(dfdropped.index.levels[1][0])
    #yr_last = int(dfdropped.index.levels[1][-1])
    # time_index = pd.date_range(
    #    start=pd.datetime(yr_one, 12, 31),
    #    end=pd.datetime(yr_last, 12, 31), freq='A-DEC')
    # dfdropped.index.levels[1] = time_index  #multi-index levels are now
    # immutable

    dftyped = dfdropped.applymap(float_convert)

    # Convert to panel
    return dftyped.to_panel()
