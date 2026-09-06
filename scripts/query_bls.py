import os
import json
from prettytable import PrettyTable
from bls_api import query_series


def main():
    series_env = os.environ.get('BLS_SERIES')
    series = [s.strip() for s in series_env.split(',')] if series_env else ['CUUR0000SA0','SUUR0000SA0']
    startyear = os.environ.get('BLS_START', '2011')
    endyear = os.environ.get('BLS_END', '2014')

    try:
        j = query_series(seriesids=series, startyear=startyear, endyear=endyear)
    except Exception as e:
        print('BLS query failed:', e)
        return

    results = j.get('Results', {}).get('series', [])
    for series_obj in results:
        seriesId = series_obj.get('seriesID')
        table = PrettyTable(["series id","year","period","value","footnotes"])
        for item in series_obj.get('data', []):
            year = item.get('year')
            period = item.get('period')
            value = item.get('value')
            footnotes = ''
            for footnote in item.get('footnotes', []):
                if footnote:
                    footnotes += (footnote.get('text','') + ',')
            if 'M01' <= period <= 'M12':
                table.add_row([seriesId, year, period, value, footnotes[:-1]])
        print('\n--- Series', seriesId, '---')
        print(table.get_string())


if __name__ == '__main__':
    main()
