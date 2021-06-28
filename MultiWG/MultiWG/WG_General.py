# -*- coding: utf-8 -*-
"""
Created on Sat Mar  9 22:27:31 2019

@author: Philip
"""
import os 
import pandas as pd
import numpy as np
import time
from time import gmtime, strftime
import json
import pickle
import copy
from MultiWG.WG_Dictionary import Setting_template
pd.options.mode.chained_assignment = None  # default='warn'

def CheckSetting(Setting):
    def check(Set):
        if len(list(Hcc)) > 0:
            print("Missing ",list(Hcc)," in Setting dictionary.\n")
            print("Please use the provided template by calling \"CreateTask()\".")
            return True
    # To assert the keys are given in the dict
    # Required keys in the dict
    H = ['WDPath', 'StnID', 'WthObvCsvFile', 'ClimScenCsvFile', 'Var', 'P_Threshold', 'P_Distribution', 'GenYear', 'Condition', 'LeapYear', 'Smooth', 'FourierOrder', 'Plot', 'StatTestAlpha', 'MultiSite']
    H_plot = ['FourierDailyTFit', 'KSTestCDFPlot', 'Multi_ECDFFittingPlot', 'Multi_IrCurveFittingPlot']
    H_stat = ['PDistTest', 'Kruskal_Wallis_Test']
    H_multisite = ['SpatialAutoCorrIndex', 'WeightMethod', 'WeightPOrder', 'rSimDataPoint', "rSimYear"]
    Hsub = ["Plot", "StatTestAlpha", 'MultiSite']
    Hc = set(H) - set(H).intersection(Setting.keys())
    Hcc = Hc.intersection(Hsub)
    
    # Checking keys
    if check(Hcc): return False
    Hc_plot = set(H_plot) - set(H_plot).intersection(Setting["Plot"].keys())
    Hc_stat = set(H_stat) - set(H_stat).intersection(Setting["StatTestAlpha"].keys())
    if Setting["MultiSite"] is None:
        print("This Setting is only eligible for weather generation without considering spatial correlation.")
        Hc_multi = []
    else:
        Hc_multi = set(H_multisite) - set(H_multisite).intersection(Setting["MultiSite"].keys())
    if check(Hc_plot) or check(Hc_stat) or check(Hc_multi):
        return False
    
    # Checking the generation year length
    if Setting["GenYear"] > 2261:
        print("The GenYear is bigger than the python datetime max 2261.")
        return False
    
    # Checking FourierOrder
    if Setting["FourierOrder"] is None or Setting["FourierOrder"] < 2:
        print("Please assign the \"FourierOrder\" with an integer equal or higher than 2.")
        return False
    
    # Checking MultiSite setting
    if Setting["MultiSite"] is not None:
        if Setting["MultiSite"]["rSimYear"]%4 != 0:
            print("Please set rSimYear in MultiSite Setting to the multiple of 4. We suggest to set 40.")
            return False
    
    return True

# Setting file
def ToJson(Setting, filename, Dict):
    WDPath = Setting["WDPath"]
    with open(os.path.join(WDPath,filename), 'w') as f:
        json.dump(Dict, f, indent=4)
    return None

# Stat file
    # 還是不行QQ
def ToPickle(Setting, filename, Dict):
    WDPath = Setting["WDPath"]
    Dict1 = copy.deepcopy(Dict)
    # Eliminate functions type variables since functions cannot be saved as pickle
    if "MultiSiteDict" in list(Dict1.keys()):
        if "V2UCurve" in list(Dict1["MultiSiteDict"].keys()):
            Dict1["MultiSiteDict"]["V2UCurve"] = "Need to be re-generated when loaded from outside."
    with open(os.path.join(WDPath,filename), 'wb') as handle:
        pickle.dump(Dict1, handle, protocol=pickle.HIGHEST_PROTOCOL)
    return None

# Wth_gen file
def ToCSV(Setting, Dict, commonfilename = ""):
    Stns = Setting["StnID"]
    WDPath = Setting["WDPath"]
    for s in Stns:
        Dict[s].to_csv(os.path.join(WDPath,"OUT",commonfilename+s+"_"+strftime("%Y%m%d_%H%M%S", gmtime())+".csv"))
    return None

# Create a set of empty storage variables
def CreateTask(wd = None):
    # Create WD folders if not exists
    def CreateFolders(working_dirctory):
        if not os.path.exists(os.path.join(working_dirctory,"DATA")):
            os.makedirs(os.path.join(working_dirctory,"DATA"))
            print("Folder DATA has been created.")
        if not os.path.exists(os.path.join(working_dirctory,"OUT")):
            os.makedirs(os.path.join(working_dirctory,"OUT"))
            print("Folder OUT has been created.")
    # Initialization
    Wth_obv = {}        # Observed weather data "StnID": df
    Wth_gen = {}        # Generated weather data "StnID": df
    if wd is None:
        # Create empty WD with folder at the program dir
        Setting = Setting_template
        print("\nSetting.json has been created using template.")
        CurrentPath = os.getcwd()
        if not os.path.exists(os.path.join(CurrentPath,"MultiWG_WD")):
            os.makedirs(os.path.join(CurrentPath,"MultiWG_WD"))
        Setting["WDPath"] = os.path.join(CurrentPath,"MultiWG_WD")
        print("The working directory is set to ",Setting["WDPath"])
        CreateFolders(Setting["WDPath"])
    else:
        # Load existed Setting.json at WD.
        if os.path.isfile(os.path.join(wd,"Setting.json")):
            print("\nThe existed Setting.json has been loaded.")
            with open(os.path.join(wd,"Setting.json"), 'r') as f:
                Setting = json.load(f)
            Setting["WDPath"] = wd
            CreateFolders(Setting["WDPath"])
            print("\nThe working directory is set to ",Setting["WDPath"])
        else:
            # Create empty WD with folder at the given wd
            Setting = Setting_template
            print("\nSetting.json has been created using template.")
            if not os.path.exists(wd):
                os.makedirs(wd)
            Setting["WDPath"] = wd
            CreateFolders(Setting["WDPath"])
            print("\nThe working directory is set to ",Setting["WDPath"])

    Stat = {}        # Stn-specified setting and calculated coef
    # Save
    ToJson(Setting, "Setting.Json", Setting)
    ToPickle(Setting, "Stat.pickle", Stat)
    if CheckSetting(Setting):
        print("Keys of the Setting.json file is ok!")
    else:
        print("Please correct your Setting.json and run again!")
    return [Wth_obv, Wth_gen, Setting, Stat]


#print("For monthly low frequency correction, the observed year have to be even. Please make sure the year number is correct or the program will automatically drop the last year for low frequency correction. BTW 產製資料是obv的倍數")

# Single version of ReadWthObv
def PreProcess(df_WthObv, Setting):
    Var = Setting["Var"].copy(); Var.remove('PP01')
    df_WthObv = df_WthObv[~((df_WthObv.index.month == 2) & (df_WthObv.index.day == 29))] # Eliminate leap year
    # Set all kind of error value to Nan
    df_WthObv['PP01'][df_WthObv['PP01']<0] = np.nan 
    for v in Var:
        if "TX" in v:
            df_WthObv.loc[df_WthObv[v]<-100,v] = np.nan 
        else:
            df_WthObv.loc[df_WthObv[v]<0,v] = np.nan 
        # For the convience of the calculation, we replace 0 to 1e-5 
        # (W and D usage) for all Var except PP01 
        df_WthObv[v][df_WthObv[v] == 0] = 0.00001 
    df_Err = df_WthObv.isnull().sum()
    print("Summery of error values in the observed weather data:\n",df_Err)
    return df_WthObv

# Read in observed weather data and process it into WG workable format
def ReadWthObv(Wth_obv, Setting, Stat):
    WDPath = Setting["WDPath"]
    Stns = Setting["StnID"]
    Var = Setting["Var"]
    # 可以改平行運算!!
    def readfile(WthObvPath):
        try:
            df = pd.read_csv(WthObvPath, usecols=["Date"]+Var, parse_dates = ["Date"], index_col = "Date")
            df = df.loc[df.index.dropna()]
            return df
        except IOError:
            #WarnSound()
            print("Cannot open the file at: ", WthObvPath)
    
    for s in Stns:
        if Setting["WthObvCsvFile"] is None:
            WthObvPath = os.path.join(WDPath, "DATA", s+".csv")
        else:
            WthObvPath = os.path.join(WDPath, "DATA", Setting["WthObvCsvFile"][s])
        df_WthObv = readfile(WthObvPath) # Read in CSV observed wth data
        print("\n", s)
        Wth_obv[s] = PreProcess(df_WthObv, Setting)
        
        # Create the storage space for each Stn in Stat
        Stat[s] = {}
        Stat[s]['Warning'] = []
    return [Wth_obv, Setting, Stat]

def ReadScen(Setting, Stat):
    WDPath = Setting["WDPath"]
    Stns = Setting["StnID"]
    def readfile(ScenPath):
        try:
            df = pd.read_csv(ScenPath)
            return df
        except IOError:
            #WarnSound()
            print("Cannot open the file at: ", ScenPath)
    
    for s in Stns:
        if Setting["ClimScenCsvFile"] is None:
            Stat[s]["CliScenFactor"] = None
        else:
            ScenPath = os.path.join(WDPath, "DATA", Setting["ClimScenCsvFile"][s])
            df_Scen = readfile(ScenPath) # Read in CSV observed wth data
            df_Scen.index = np.arange(1,13)
            Stat[s]["CliScenFactor"] = df_Scen
    
def ReadFiles(Wth_obv, Setting, Stat):
    ReadWthObv(Wth_obv, Setting, Stat)
    ReadScen(Setting, Stat)
    return [Wth_obv, Setting, Stat]

def SaveFig(fig, name, Setting, FigFormat = ".png"):
    WDPath = Setting["WDPath"]
    fig.savefig(os.path.join(WDPath, "OUT", name+"_"+strftime("%Y%m%d_%H%M%S", gmtime()) + FigFormat), dpi = 500)
    
class Counter:
    def __ini__(self):
        self.start = None
        self.end = None
        self.elapse = None
        self.strftime = None
    def Start(self):
        self.start = time.time()
    def End(self):
        self.end = time.time()
        self.elapse = self.end - self.start
        self.strftime = time.strftime("%H:%M:%S", time.gmtime(self.elapse))