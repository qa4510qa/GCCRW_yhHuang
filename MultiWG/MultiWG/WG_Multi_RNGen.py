# -*- coding: utf-8 -*-
"""
Created on Sat Dec 21 10:27:29 2019

@author: Philip
"""

from MultiWG.WG_Multi_HisAnalysis import GenMultiRN, GenSimrV2UCurve
from MultiWG.WG_General import ToPickle
from tqdm import tqdm
import numpy as np
import pandas as pd

# TX Rn 有問題
def MultiGenRn(Setting, Stat):
    MultiSiteDict = Stat["MultiSiteDict"]
    Var = Setting["Var"].copy() + ["P_Occurrence"] # Add prep event variable
    GenYear = Setting["GenYear"]
    LeapYear = Setting["LeapYear"]
    Stns = Setting["StnID"] 
    DayInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    DayInMonthLeap = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    Simr = MultiSiteDict["Simr"]
    V2UCurve = MultiSiteDict["V2UCurve"]
    if type(V2UCurve) == str:  # When MultiSiteDict (Stat) is loaded from out source since functions cannot be saved as pickle
        MultiSiteDict = GenSimrV2UCurve(MultiSiteDict, Setting)  
        Stat["MultiSiteDict"] = MultiSiteDict
        V2UCurve = MultiSiteDict["V2UCurve"]
    SpatialRnNum = {}
    
    if LeapYear: 
        if GenYear%4 != 0:
            print("GenYear has to be the multiple of 4 to generate leap year." )
            input()
            quit()
    
    # Simulate spatial correlated RN
    for v in tqdm(Var, desc = "Gen spatial correlated RN"):        
        # Gen 40 years for the size is greater than 1000 for each month, which we consider as statistically robust
        Rn = 0
        for y in range(GenYear):
            dcount = 0
            for m in range(12):
                day_in_month = DayInMonth[m]
                if LeapYear and (y+1)%4 == 0:
                    day_in_month = DayInMonthLeap[m]
                    
                W = MultiSiteDict["Weight"][v][m+1]
                r = Simr.loc[dcount:dcount+day_in_month-1,v] 
                if v == "PP01" or v == "P_Occurrence":
                    rn = GenMultiRN(r, W, Type = "P", Size = day_in_month, TransformFunc = None, Warn = False) 
                else:
                    rn = GenMultiRN(r, W, Type = "T", Size = day_in_month, TransformFunc = None, Warn = False)
                # Gen Rn
                for d in range(day_in_month):
                    CovertCurve = V2UCurve.loc[dcount,v]
                    rn[:,d] = CovertCurve(rn[:,d])

                    if day_in_month == 29 and (d+1) == 29: #2/29 = 2/28
                        dcount -= 1
                    dcount += 1
                # Add up
                if type(Rn) is int: 
                    Rn = rn
                else:
                    Rn = np.concatenate((Rn,rn), axis = 1)
        SpatialRnNum[v] = Rn
    Stat["MultiSiteDict"]["SpatialRnNum"] = SpatialRnNum
        
    # Re-organize the Rn to each stn
    for i, s in enumerate(Stns):
        RnNum = pd.DataFrame()
        for v in Var:
            RnNum[v] = SpatialRnNum[v][i]         
        Stat[s]["RnNum"] = RnNum
    ToPickle(Setting, "Stat.pickle", Stat)
    return Stat

#def MultiGenRn(Setting, Stat):
#    MultiSiteDict = Stat["MultiSiteDict"]
#    Var = Setting["Var"].copy() + ["P_Occurrence"] # Add prep event variable
#    GenYear = Setting["GenYear"]
#    LeapYear = Setting["LeapYear"]
#    Stns = Setting["StnID"] 
#    DayInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
#    DayInMonthLeap = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
#    Simr = MultiSiteDict["Simr"]
#    V2UCurve = MultiSiteDict["V2UCurve"]
#    if type(V2UCurve) == str:  # When MultiSiteDict (Stat) is loaded from out source since functions cannot be saved as pickle
#        MultiSiteDict = GenSimrV2UCurve(MultiSiteDict, Setting)  
#        Stat["MultiSiteDict"] = MultiSiteDict
#        V2UCurve = MultiSiteDict["V2UCurve"]
#    SpatialRnNum = {}
#    
#    if LeapYear: 
#        if GenYear%4 != 0:
#            print("GenYear has to be the multiple of 4 to generate leap year." )
#            quit()
#    
#    # Simulate spatial correlated RN
#    for v in tqdm(Var, desc = "Gen spatial correlated RN"):        
#        # Gen 40 years for the size is greater than 1000 for each month, which we consider as statistically robust
#        Rn = 0
#        for y in range(GenYear):
#            dcount = 0
#            for m in range(12):
#                day_in_month = DayInMonth[m]
#                if LeapYear and (y+1)%4 == 0:
#                    day_in_month = DayInMonthLeap[m]
#                    
#                W = MultiSiteDict["Weight"][v][m+1]
#                # Gen Rn
#                for d in range(day_in_month):
#                    r = Simr.loc[dcount,v] 
#                    CovertCurve = V2UCurve.loc[dcount,v]
#                    if v == "PP01" or "P_Occurrence":
#                        rn = GenMultiRN(r, W, Type = "P", Size = 1, TransformFunc = CovertCurve, HisGen = True) 
#                    else:
#                        rn = GenMultiRN(r, W, Type = "T", Size = 1, TransformFunc = CovertCurve, HisGen = True)
#                    # Add up
#                    if type(Rn) is int: 
#                        Rn = rn
#                    else:
#                        Rn = np.concatenate((Rn,rn), axis = 1)
#                    if day_in_month == 29 and (d+1) == 29: #2/29 = 2/28
#                        dcount -= 1
#                    dcount += 1
#        SpatialRnNum[v] = Rn
#    Stat["MultiSiteDict"]["SpatialRnNum"] = SpatialRnNum
#        
#    # Re-organize the Rn to each stn
#    for i, s in enumerate(Stns):
#        RnNum = pd.DataFrame()
#        for v in Var:
#            RnNum[v] = SpatialRnNum[v][i]         
#        Stat[s]["RnNum"] = RnNum
#    ToPickle(Setting, "Stat.pickle", Stat)
#    return Stat
    
    
