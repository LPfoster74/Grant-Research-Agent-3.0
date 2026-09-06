import os
import requests
import json

API_URL = 'https://api.bls.gov/publicAPI/v2/timeseries/data/'


def query_series(seriesids=None, startyear='2011', endyear='2014'):
    """Query the BLS JSON API for the given series IDs.

    Reads API key from the environment variable `BLS_API_KEY`.
    Returns the parsed JSON response.
    """
    key = os.environ.get('BLS_API_KEY')
    if not key:
        raise RuntimeError('BLS_API_KEY not set in environment')

    if not seriesids:
        seriesids = ['CUUR0000SA0', 'SUUR0000SA0']

    payload = {
        'seriesid': seriesids,
        'startyear': startyear,
        'endyear': endyear,
        'registrationKey': key,
    }
    headers = {'Content-type': 'application/json'}
    r = requests.post(API_URL, data=json.dumps(payload), headers=headers, timeout=15)
    r.raise_for_status()
    return r.json()
