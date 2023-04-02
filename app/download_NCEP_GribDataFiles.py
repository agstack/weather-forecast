import os
import warnings
import requests
import pandas as pd
import datetime as datetime
import urllib.request

from netCDF4 import Dataset
from bs4 import BeautifulSoup
from dotenv import load_dotenv

# from sqlalchemy import *

warnings.filterwarnings("ignore")
load_dotenv()

### GLOBALS
# get the latest date
rootUrl = os.getenv("rootUrl")
outDir = os.getenv("outDir")
updated_data_available_file = os.getenv("updated_data_available_file")


###############################################
# Make a list of variables we want (ref: https://www.nco.ncep.noaa.gov/pmb/products/gfs/gfs.t00z.pgrb2.0p25.f003.shtml)

# Relative Humidity [%]
var1 = ":RH:2 m above ground:"

# Temperature [K]
var2 = ":TMP:2 m above ground:"

# Soil Temperature [K]
var3 = ":TSOIL:0-0.1 m below ground:"
var4 = ":TSOIL:0.1-0.4 m below ground:"
var5 = ":TSOIL:0.4-1 m below ground:"
var6 = ":TSOIL:1-2 m below ground:"

# Volumetric Soil Moisture Content [Fraction]
var7 = ":SOILW:0-0.1 m below ground:"
var8 = ":SOILW:0.1-0.4 m below ground:"
var9 = ":SOILW:0.4-1 m below ground:"
var10 = ":SOILW:1-2 m below ground:"

# Specific Humidity [kg/kg]
var11 = ":SPFH:2 m above ground:"

# Dew Point Temperature [K]
var12 = ":DPT:2 m above ground:"

# Pressure Reduced to MSL [Pa]
var13 = ":PRMSL:mean sea level:"

# Pressure [Pa]
var14 = ":PRES:max wind:"

# Wind Speed (Gust) [m/s]
var15 = ":GUST:surface:"

# Total Cloud Cover [%]
var16 = ":TCDC:entire atmosphere"

# Downward Short-Wave Radiation Flux [W/m^2]
var17 = ":DSWRF:surface:"

# Downward Long-Wave Radiation Flux [W/m^2]
var18 = ":DLWRF:surface:"

# Upward Short-Wave Radiation Flux [W/m^2]
var19 = ":USWRF:surface:"

# Upward Long-Wave Radiation Flux [W/m^2]
var20 = ":ULWRF:surface:"

# Upward Long-Wave Radiation Flux [W/m^2]
var20 = ":ULWRF:surface:"

# Soil Type [-]
var21 = ":SOTYP:surface:"

# Categorical Rain [-] (3 hr forecast)
var22 = ":CRAIN:surface:"

# Precipitation Rate [kg/m^2/s]
var23 = ":PRATE:surface:"

varStr = (
    var1
    + "|"
    + var2
    + "|"
    + var3
    + "|"
    + var4
    + "|"
    + var5
    + "|"
    + var6
    + "|"
    + var7
    + "|"
    + var8
    + "|"
    + var9
    + "|"
    + var10
    + "|"
    + var11
    + "|"
    + var12
    + "|"
    + var13
    + "|"
    + var14
    + "|"
    + var15
    + "|"
    + var16
    + "|"
    + var17
    + "|"
    + var18
    + "|"
    + var19
    + "|"
    + var20
    + "|"
    + var21
    + "|"
    + var22
    + "|"
    + var23
)

###############################################
varDict = {
    var2: "Air Temp [C] (2 m above surface)",
    var4: "Soil Temperature [C] - 0.1-0.4 m below ground",
    var8: "Volumetric Soil Moisture Content [Fraction] - 0.1-0.4 m below ground",
    var22: "Rainfall Probability",
    var23: "Precipitation Rate [kg/m^2/s]",
    var1: "Relative Humidity [%]",
    var12: "Dew Point Temperature [C]",
    var13: "Pressure Reduced to MSL [Pa]",
    var14: "Pressure [Pa]",
    var15: "Wind Speed (Gust) [m/s]",
    var16: "Total Cloud Cover [%]",
}


def getGribFileName():
    utcDt = datetime.datetime.utcnow()
    utcDtOffset = pd.Timestamp.now().round("360min").tz_localize(
        "UTC"
    ).to_pydatetime() - datetime.timedelta(hours=6)

    CC = str(utcDtOffset.hour).zfill(2)
    dtStr = datetime.datetime.strftime(utcDtOffset, "%Y%m%d")

    return dtStr, [CC]


def getAPIVals(varDict, list_of_ncfiles, lon, lat):

    varList = list(varDict.keys())
    df = pd.DataFrame()
    idx = 0
    updated_dtStr = list_of_ncfiles[0].split("__")[0]
    updated_dt = datetime.datetime.strptime(updated_dtStr, "%Y%m%d_%H%M%S")
    for f in list_of_ncfiles:
        dtStr = f.split("__")[1]
        forecast_dt = datetime.datetime.strptime(dtStr, "%Y%m%d_%H%M%S")
        print(f)
        try:

            ncin = Dataset(outDir + f, "r")
            # valList = list(ncin.variables.keys())

            # extract the variable of interest from the list
            for varName in varList:
                titleStr = varDict[varName]
                var_mat = ncin.variables[varName][:]

                if "Temp" in titleStr:
                    var_val = var_mat.squeeze() - 273.15  # convert to DegC
                else:
                    var_val = var_mat.squeeze()
                lons = ncin.variables["longitude"][:]
                lats = ncin.variables["latitude"][:]

                lon_ind = [i for i, v in enumerate(lons.data) if v >= lon][0]
                lat_ind = [i for i, v in enumerate(lats.data) if v >= lat][0]

                vv = var_val[lat_ind, lon_ind]

                df.loc[idx, "UPDATED_DATE_UTC"] = updated_dt
                df.loc[idx, "FORECAST_DATE_UTC"] = forecast_dt
                df.loc[idx, "MEASURE"] = titleStr
                df.loc[idx, "lon"] = lon
                df.loc[idx, "lat"] = lat
                df.loc[idx, "VALUE"] = vv
                idx = idx + 1
            ncin.close()
        except Exception as e:
            print(e)

    df.FORECAST_DATE_UTC = df.FORECAST_DATE_UTC.astype(str)
    df.UPDATED_DATE_UTC = df.UPDATED_DATE_UTC.astype(str)

    return df


################ main script to download files.
# >python3 download_NCEP_GribDataFiles.py

response = requests.get(rootUrl)
soup = BeautifulSoup(response.text, "html.parser")
links = soup.find_all("a")
ll = [str(x) for x in links if str(x).startswith('<a href="gfs.')]
lastDtStr = ll[-1].split("gfs.")[1][0:8]


# dtStr = lastDtStr
# CC_list = ['00'] #For now, just do once a day
# ,'06','12','18']
FFF_list = [str(i).zfill(3) for i in range(0, 151)]
start_time = datetime.datetime.now()
dtStr, CC_list = getGribFileName()

# remove all the files from the directory
if any(fname.endswith(".nc") for fname in os.listdir(outDir)):
    print("\n###########################\nDeleting Old Files ... ")
    cmd = "rm " + outDir + "*"
    ret = os.system(cmd)
    print("Done!")

# Create new files
for CC in ["00"]:
    for FFF in FFF_list:
        try:
            # CC='00'
            # FFF='006'
            dtStr = datetime.datetime.strftime(
                datetime.datetime.strptime(dtStr, "%Y%m%d"), "%Y%m%d"
            )
            frct_dtStr = datetime.datetime.strftime(
                datetime.datetime.strptime(dtStr, "%Y%m%d")
                + datetime.timedelta(hours=int(CC)),
                "%Y%m%d_%H%M%S",
            )
            dest_dtStr = datetime.datetime.strftime(
                datetime.datetime.strptime(dtStr, "%Y%m%d")
                + datetime.timedelta(hours=int(FFF)),
                "%Y%m%d_%H%M%S",
            )
            res = "0p25"
            gribFile = "gfs.t" + CC + "z.pgrb2." + res + ".f" + FFF
            ncepDir = (
                "https://nomads.ncep.noaa.gov/pub/data/nccf/com/gfs/prod/gfs."
                + dtStr
                + "/"
                + CC
                + "/atmos/"
            )
            urlStr = ncepDir + gribFile

            outFile = (
                outDir + frct_dtStr + "__" + dest_dtStr + "__" + FFF + "___" + gribFile
            )
            print("\n\n\tDownloading GRIB File " + gribFile + " --> " + outFile)
            resp = urllib.request.urlretrieve(urlStr, outFile)
            print("\tDone!")

            # fix the coordinates to go from -180 and -
            outFile2 = outFile + ".grb2"
            print("\n\tConverting GRIB Coordinates")
            cmd1 = (
                "wgrib2 "
                + outFile
                + " -new_grid latlon -179.75:1440:0.25  -89.75:720:0.25 "
                + outFile2
            )
            ret = os.system(cmd1)
            print("\tDone!")

            # convert to netCDF file
            ncfile = outFile2 + ".nc"
            print(
                "\n\tConvertting GRIB files into NetCDF: "
                + outFile2
                + ", --> "
                + ncfile
            )
            cmd2 = (
                "wgrib2 "
                + outFile2
                + " -s | egrep '("
                + varStr
                + ")' | wgrib2 -i "
                + outFile2
                + " -netcdf "
                + ncfile
            )
            ret = os.system(cmd2)
            print("\tDone!")

            # Delete the grib files
            print("\n\tDeleting GRIB files: " + outFile + ", and " + outFile2)
            cmd3 = "rm " + outFile
            ret = os.system(cmd3)
            cmd3 = "rm " + outFile2
            ret = os.system(cmd3)
            print("\tDone!")
            end_time = datetime.datetime.now()
            print("\t********** Elapsed: " + str(end_time - start_time))
        except:
            print("Error in CC=" + CC + ", FFF=" + FFF)
            continue


# touch file
print("\nWriting updated_data_available.txt file")
cmd_complete = "touch " + updated_data_available_file
os.system(cmd_complete)
print("Done!")

end_time = datetime.datetime.now()
print("\n********** Total Elapsed: " + str(end_time - start_time))
print("###########################")

"""
print('Entering info into DB')
frct_dt = datetime.datetime.strptime(frct_dtStr, '%Y%m%d_%H%M%S')
#list of ncfiles
list_of_ncfiles = [x for x in os.listdir(outDir) if x.endswith('.nc')]
list_of_ncfiles.sort()
time_dim = len(list_of_ncfiles)
ncfiles_df = pd.DataFrame(columns=['UPDATE_DATE','FILES'])
ncfiles_df['FILES']=list_of_ncfiles
ncfiles_df['UPDATE_DATE']=frct_dt
"""
