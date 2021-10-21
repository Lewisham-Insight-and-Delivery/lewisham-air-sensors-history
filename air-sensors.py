import requests
from datetime import date, datetime, timedelta
import sqlite_utils

# SETUP DATABASE, TABLE AND SCHEMA
db = sqlite_utils.Database("air-sensors.db")
# WE ARE ONLY COLLECTING NO2 AS THIS IS THE ONLY PARTICLE THAT IS MEASURED AT ALL SITES
tablename = 'NO2'
table = db.table(
    tablename,
    pk=('@MeasurementDateGMT', '@Site'),
    not_null={"@MeasurementDateGMT", "@Value", "@Site"},
    column_order=("@MeasurementDateGMT", "@Value", "@Site")
)

# EXTRACT THE SITES IN LEWISHAM
req = requests.get("https://api.erg.ic.ac.uk/AirQuality/Information/MonitoringSiteSpecies/GroupName=lewisham/Json")
js = req.json()
sites = js['Sites']['Site']

# PREPARE TO SCAN DATA FOR THE LAST 1 WEEK
EndDate = date.today() + timedelta(days = 1)
EndWeekDate = EndDate
StartWeekDate = EndDate - timedelta(weeks = 1)
StartDate = StartWeekDate - timedelta(days = 1)

# GET THE JSON DATA, UPSERT INTO THE FULL HISTORY DATABASE
while StartWeekDate > StartDate :
    for el in sites:
        def convert(l):
            l['@Value'] = float(l['@Value'])
            l['@Site'] = el['@SiteName']
            return l
        url = f'https://api.erg.ic.ac.uk/AirQuality/Data/SiteSpecies/SiteCode={el["@SiteCode"]}/SpeciesCode=NO2/StartDate={StartWeekDate.strftime("%d %b %Y")}/EndDate={EndWeekDate.strftime("%d %b %Y")}/Json'
        print(url)
        req = requests.get(url, headers={'Connection':'close'})
        j = req.json()
        # CLEAN SITES WITH NO DATA OR ZERO VALUE OR NOT NO2 (ONLY MEASURE AVAILABLE AT ALL SITES)
        filtered = [a for a in j['RawAQData']['Data'] if a['@Value'] != '' and a['@Value'] != '0' ]
        if len(filtered) != 0:
            filtered = map(convert, filtered)
            filteredList = list(filtered)
            db[tablename].upsert_all(filteredList,pk=('@MeasurementDateGMT', '@Site'))
    EndWeekDate = StartWeekDate
    StartWeekDate = EndWeekDate - timedelta(weeks = 1)
