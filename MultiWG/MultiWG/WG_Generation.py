# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 19:16:30 2019

@author: Philip
"""
from copy import deepcopy
import pandas as pd
import numpy as np
from time import gmtime, strftime
from scipy.stats import expon, gamma, weibull_min, norm
from joblib import Parallel, delayed    # For parallelization
from MultiWG.WG_General import Counter, ToPickle, ToCSV
from MultiWG.WG_ClimateScenario import UpdatePdist_MLE, TCliScenFactor_M2D


def GenRN(Setting, Stat):
    GenYear = Setting["GenYear"]
    LeapYear = Setting["LeapYear"]
    Var = Setting["Var"].copy(); Var.remove('PP01') 
    Stns = Setting["StnID"]
    n = GenYear*365
    if LeapYear: 
        if GenYear%4 != 0:
            print("GenYear has to be the multiple of 4 to generate leap year." )
            input()
            quit()
        n = n + int(GenYear/4)
    for Stn in Stns:
        RnNum = pd.DataFrame()
        RnNum["P_Occurrence"] = np.random.uniform(low=0.0, high=1.0, size = n)
        RnNum["PP01"] = np.random.uniform(low=0.0, high=1.0, size = n)
        for v in Var:
            RnNum[v] = np.random.normal(0, 1, size = n)
        Stat[Stn]["RnNum"] = RnNum
    # Save Stat
    ToPickle(Setting, "Stat.pickle", Stat)
    return Stat

def GenP(Wth_gen, Setting, Stat, Stn):
    GenYear = Setting["GenYear"]
    LeapYear = Setting["LeapYear"]
    Smooth = Setting["Smooth"]
    DayInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    DayInMonthLeap = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    # 先不管smoothing
    
    #  Calculate future parameters
    if Setting["ClimScenCsvFile"] is not None:
        UpdatePdist_MLE(Setting, Stat)  
        DailyStat = Stat[Stn]["MonthlyStatCC"]#.copy()
    else:
        DailyStat = Stat[Stn]["MonthlyStat"]#.copy()
        
    # Expand monthly statistics to daily. Users are able to decide wheather apply smoothing.    
    if Smooth:
        print("The smoothing schema is not fully supported yet! Please change the \"smooth\" setting to false.")
        input()
        quit()
    else:
        DailyStat_nonleap = pd.DataFrame(np.repeat(DailyStat.values, DayInMonth, axis=0), columns = list(DailyStat))
        if LeapYear:
            DailyStat_leap = pd.DataFrame(np.repeat(DailyStat.values, DayInMonthLeap, axis=0), columns = list(DailyStat))
            
    # Gen P Occurance        
    def Occurance(Rn, Pwd, Pww, pre_state):
        Occ = 0
        if pre_state == 1:
            if Rn <= Pww: Occ = 1
        elif pre_state == 0:
            if Rn <= Pwd: Occ = 1
        return Occ    
    Rn_P_Occ = Stat[Stn]["RnNum"]["P_Occurrence"]       
    P_Occurrence = [] 
    AccDay = 0
    # Initialize for index 0 
    if Rn_P_Occ[AccDay] <= DailyStat_nonleap["Pw"][0]:
        P_Occurrence.append(1)
    else:
        P_Occurrence.append(0)
    # MC1 simulation
    for y in range(GenYear):
        if LeapYear:
            for m in range(12):
                # Day in the month
                if (y+1)%4 == 0:Days = DayInMonthLeap[m]        # Set the leap year is at the end of every four year
                else:           Days = DayInMonth[m]
                # Generate Occurance
                for d in range(Days):
                    if AccDay == 0: 
                        AccDay += 1
                        continue
                    if (y+1)%4 == 0:
                        n = AccDay+1 - ( y*365 + int((y+1)/4) )    
                        P_Occurrence.append(Occurance(Rn_P_Occ[AccDay], DailyStat_leap["Pwd"][n], DailyStat_leap["Pww"][n], P_Occurrence[-1]))
                    else:           
                        n = AccDay - ( y*365 + int((y+1)/4) ) 
                        P_Occurrence.append(Occurance(Rn_P_Occ[AccDay], DailyStat_nonleap["Pwd"][n], DailyStat_nonleap["Pww"][n], P_Occurrence[-1]))           
                    AccDay += 1   
        else: # leapYear = False
            for m in range(12):
                # Day in the month
                Days = DayInMonth[m]
                # Generate Occurance
                for d in range(Days):
                    if AccDay == 0: 
                        AccDay += 1
                        continue
                    n = AccDay%365
                    P_Occurrence.append(Occurance(Rn_P_Occ[AccDay], DailyStat_nonleap["Pwd"][n], DailyStat_nonleap["Pww"][n], P_Occurrence[-1]))
                    AccDay += 1
    # Gen P Amount  
    def Amount(Rn, Dist, Coef):
        if Dist == "exp":
            GenP = expon.ppf(Rn,Coef[0],Coef[1])
        elif Dist == "gamma":
            GenP = gamma.ppf(Rn,Coef[0],Coef[1],Coef[2])
        elif Dist == "weibull":
            GenP = weibull_min.ppf(Rn,Coef[0],Coef[1],Coef[2])
        elif Dist == "lognorm":
            GenP = np.exp(norm.ppf(Rn,Coef[0],Coef[1])) # use norm generate lognorm
        #elif Dist == "pearson3":
        #    GenP = pearson3.ppf(Rn,coef[0],coef[1],coef[2])
        return GenP
    Rn_P_Amo = Stat[Stn]["RnNum"]["PP01"]
    P_Amount = [0]*len(Rn_P_Amo)
    AccDay = 0
    for y in range(GenYear):
        if LeapYear:
            for m in range(12):
                # Day in the month
                if (y+1)%4 == 0:Days = DayInMonthLeap[m]        # Set the leap year is at the end of every four year
                else:           Days = DayInMonth[m]
                # Generate Occurance
                for d in range(Days):
                    if P_Occurrence[AccDay] == 0: AccDay += 1; continue
                    if (y+1)%4 == 0:
                        n = AccDay+1 - ( y*365 + int((y+1)/4) )      
                        Pdist = DailyStat_leap["SelectedDist"][n]
                        P_Amount[AccDay] = Amount(Rn_P_Amo[AccDay], Pdist, DailyStat_leap.loc[n, Pdist])
                    else:           
                        n = AccDay - ( y*365 + int((y+1)/4) ) 
                        Pdist = DailyStat_nonleap["SelectedDist"][n]
                        P_Amount[AccDay] = Amount(Rn_P_Amo[AccDay], Pdist, DailyStat_nonleap.loc[n, Pdist])        
                    AccDay += 1   
        else: # leapYear = False
            for m in range(12):
                # Day in the month
                Days = DayInMonth[m]
                # Generate Occurance
                for d in range(Days):
                    if P_Occurrence[AccDay] == 0: AccDay += 1; continue
                    if AccDay == 0: 
                        AccDay += 1
                        continue
                    n = AccDay%365
                    Pdist = DailyStat_nonleap["SelectedDist"][n]
                    P_Amount[AccDay] = Amount(Rn_P_Amo[AccDay], Pdist, DailyStat_nonleap.loc[n, Pdist]) 
                    AccDay += 1
    Wth_gen[Stn] = {} # 要改掉 放到 setting 設定完之後馬上創建 (保留，多測站時會需要)
    Data = {"PP01": P_Amount,
            "P_Occurrence": P_Occurrence}
    Wth_gen[Stn] = pd.DataFrame(Data, columns = Data.keys())
    return Wth_gen
#==============================================================================
def GenT(Wth_gen, Setting, Stat, Stn):
    GenYear = Setting["GenYear"]
    LeapYear = Setting["LeapYear"]
    FourierOrder = Setting["FourierOrder"]
    Var = Setting["Var"].copy(); Var.remove('PP01') 
    # Calculate CC TFactor Timeseries
    if Setting["ClimScenCsvFile"] is not None:
        Stat = TCliScenFactor_M2D(Setting, Stat)
        
    if LeapYear: 
        if GenYear%4 != 0:
            print("GenYear has to be the multiple of 4 to generate leap year." )
            input()
            quit()
    Rn_T = Stat[Stn]["RnNum"][Var]  
    CoefAB = Stat[Stn]["CoefAB"]
    TFourierCoef = Stat[Stn]["TFourierCoef"]
    def AR1(CoefAB, Rn_T, Var):
        print("\tStart to Generate Residual...")
        res = np.zeros((Rn_T.shape[0]+1, Rn_T.shape[1]))
        for i in range(Rn_T.shape[0]):
            Rn = Rn_T.loc[i,:]
            res[i+1] = np.dot(CoefAB["A"],res[i]) + np.dot(CoefAB["B"],Rn)
        res = pd.DataFrame(res, columns = Var)
        print("\tResiduals generated!")
        return res.loc[1:,:].reset_index(drop=True)
    def FormFourYearFourierTimeseriesDf(TFourierCoef, LeapYear):
        Timeseries = pd.DataFrame()
        def FourierFunc(C, LeapYear):
            order = FourierOrder
            x = np.arange(1,365+1);T = 365/(2*np.pi)
            if LeapYear:
                x = np.insert(x,60,x[59])   # Replicate 2/28 as for 2/29
            if order == 2:
                Y = C[0]+C[3]*np.sin(x/T+C[1])+C[4]*np.sin(2*x/T+C[2])
            elif order == 3:
                Y = C[0]+C[4]*np.sin(x/T+C[1])+C[5]*np.sin(2*x/T+C[2])+C[6]*np.sin(3*x/T+C[3])
            elif order == 4:
                Y = C[0]+C[5]*np.sin(x/T+C[1])+C[6]*np.sin(2*x/T+C[2])+C[7]*np.sin(3*x/T+C[3])+C[8]*np.sin(4*x/T+C[4])
            return Y

        for item in TFourierCoef.keys():
            if LeapYear:
                Data_nonleap = FourierFunc(TFourierCoef[item], False)
                Data_leap = FourierFunc(TFourierCoef[item], True)
                if Setting["ClimScenCsvFile"] is not None:
                    if "avg" in item:
                        Data_leap = Data_leap+Stat[Stn]["FourYearFourierTimeseriesFactor"]["Leap"]["T_avg_delta"]
                        Data_nonleap = Data_nonleap+Stat[Stn]["FourYearFourierTimeseriesFactor"]["Nonleap"]["T_avg_delta"]
                    if "std" in item:
                        Data_leap = Data_leap*Stat[Stn]["FourYearFourierTimeseriesFactor"]["Leap"]["T_std_ratio"]
                        Data_nonleap = Data_nonleap*Stat[Stn]["FourYearFourierTimeseriesFactor"]["Nonleap"]["T_std_ratio"]
                    print("Update T-related parameters for CC.")
                FourYear = np.concatenate((Data_nonleap, Data_nonleap, Data_nonleap, Data_leap))
            else:
                Data_nonleap = FourierFunc(TFourierCoef[item], False)
                if Setting["ClimScenCsvFile"] is not None:
                    if "avg" in item:
                        Data_nonleap = Data_nonleap+Stat[Stn]["FourYearFourierTimeseriesFactor"]["Nonleap"]["T_avg_delta"]
                    if "std" in item:
                        Data_nonleap = Data_nonleap*Stat[Stn]["FourYearFourierTimeseriesFactor"]["Nonleap"]["T_std_ratio"]
                    print("Update T-related parameters for CC.")
                FourYear = np.concatenate((Data_nonleap, Data_nonleap, Data_nonleap, Data_nonleap))
            Timeseries[item] = FourYear
        return Timeseries
    # Caluculate AR1 residuals
    Residuals = AR1(CoefAB, Rn_T, Var)
    # Form the fourier time series
    Timeseries = FormFourYearFourierTimeseriesDf(TFourierCoef, LeapYear)
    Stat[Stn]["FourYearFourierTimeseries"] = Timeseries
    Timeseries = pd.concat([Timeseries]*int(GenYear/4), ignore_index=True) # Ignores the index
    # Put back the trend
    P_Occurrence = Wth_gen[Stn]["P_Occurrence"]
      
    # Apply condition method to generate TX04(Tmin), TX02(Tmax)    
    if "TX04" in Var and "TX02" in Var and Setting["Condition"]:
        print("\t Generate T with condition method.")
        Ti = Timeseries
        for t in ["w", "d"]:
            Ti["Cond_"+t] = Ti["TX02_"+t+"_std"] >= Ti["TX04_"+t+"_std"] 
            cond = Ti["Cond_"+t]; Ti["TX02_"+t] = np.nan; Ti["TX04_"+t] = np.nan
            # TX02 >= TX04
            Ti.loc[cond, "TX04_"+t] = Ti.loc[cond, "TX04_"+t+"_avg"] + Ti.loc[cond, "TX04_"+t+"_std"]*Residuals.loc[cond, "TX04"]  
            Ti.loc[cond, "TX02_"+t] = Ti.loc[cond, "TX04_"+t] + (Ti.loc[cond, "TX02_"+t+"_avg"] - Ti.loc[cond, "TX04_"+t+"_avg"]) + (Ti.loc[cond, "TX02_"+t+"_std"]**2 - Ti.loc[cond, "TX04_"+t+"_std"]**2)**0.5*Residuals.loc[cond, "TX02"] 
            # TX02 < TX04
            cond = cond==False
            Ti.loc[cond, "TX02_"+t] = Ti.loc[cond, "TX02_"+t+"_avg"] + Ti.loc[cond, "TX02_"+t+"_std"]*Residuals.loc[cond, "TX02"]  
            Ti.loc[cond, "TX04_"+t] = Ti.loc[cond, "TX02_"+t] - (Ti.loc[cond, "TX02_"+t+"_avg"] - Ti.loc[cond, "TX04_"+t+"_avg"]) - (Ti.loc[cond, "TX04_"+t+"_std"]**2 - Ti.loc[cond, "TX02_"+t+"_std"]**2)**0.5*Residuals.loc[cond, "TX04"] 
        Wth_gen[Stn]["TX02"] = Ti["TX02_w"]*P_Occurrence + Ti["TX02_d"]*(P_Occurrence-1)*(-1)
        Wth_gen[Stn]["TX04"] = Ti["TX04_w"]*P_Occurrence + Ti["TX04_d"]*(P_Occurrence-1)*(-1)
        # Recheack TX02 > TX04 (modified) ref: WeaGETs
        cond = Wth_gen[Stn]["TX04"] >= Wth_gen[Stn]["TX02"]
        Wth_gen[Stn].loc[cond,"TX04"] = Wth_gen[Stn].loc[cond,"TX02"] - np.abs(Wth_gen[Stn].loc[cond,"TX02"])*0.2
        # Gen other
        Var_other = [v for v in Var if v not in ['TX02', 'TX04']]
        for v in Var_other:
            Wth_gen[Stn][v] = (Timeseries[v+"_w_avg"]+Timeseries[v+"_w_std"]*Residuals[v])*P_Occurrence + (Timeseries[v+"_d_avg"]+Timeseries[v+"_d_std"]*Residuals[v])*(P_Occurrence-1)*(-1)
        # Check TX01 fall between TX02 & TX04
        if "TX01" in Var:
            cond1 = Wth_gen[Stn]["TX01"] >= Wth_gen[Stn]["TX02"]
            cond2 = Wth_gen[Stn]["TX01"] <= Wth_gen[Stn]["TX04"]
            Wth_gen[Stn].loc[cond1,"TX01"] = (Wth_gen[Stn].loc[cond1,"TX02"] + Wth_gen[Stn].loc[cond1,"TX04"])/2
            Wth_gen[Stn].loc[cond2,"TX01"] = (Wth_gen[Stn].loc[cond2,"TX02"] + Wth_gen[Stn].loc[cond2,"TX04"])/2
    else:
        print("\tGenerate T independently. The condition of the generated data needs to be checked.")
        # Generate T seperately X = mu + sig*e
        for v in Var:
            Wth_gen[Stn][v] = (Timeseries[v+"_w_avg"]+Timeseries[v+"_w_std"]*Residuals[v])*P_Occurrence + (Timeseries[v+"_d_avg"]+Timeseries[v+"_d_std"]*Residuals[v])*(P_Occurrence-1)*(-1)
        
    return Wth_gen

def DumpCheck(Wth_gen, Setting, Stat, s):
    Var = Setting["Var"].copy(); Var.remove('PP01') 
    def Interpolation(orgdata,nalist):
        if len(nalist)>0:   # If any nan exist
            nData = np.array(list(orgdata)[362:364]+list(orgdata)+list(orgdata)[0:2])
            for i in nalist:
                i = int(i)
                # Average over 21 days (2 before & 2 after)
                orgdata[i] = np.nanmean(nData[i:i+5+1]) 
        return orgdata
    
    Var_TX = [i for i in Var if "TX" in i]
    Var_other = [i for i in Var if "TX" not in i]
    
    # Correction for TX
    if Setting["Condition"] is False and len(Var_TX)>=2 and len(Var_TX)<=3:
        if "TX02" in Var_TX and "TX04" in Var_TX and len(Var_TX)==2:
            loc = Wth_gen[s]["TX02"] <= Wth_gen[s]["TX04"]
            Wth_gen[s].loc[loc,"TX02"] = Wth_gen[s].loc[loc,"TX04"]+1
        if "TX02" in Var_TX and "TX04" in Var_TX and "TX01" in Var_TX and len(Var_TX)==3:
            loc = Wth_gen[s]["TX02"] <= Wth_gen[s]["TX01"]
            Wth_gen[s].loc[loc,"TX02"] = Wth_gen[s].loc[loc,"TX01"]+1
            loc = Wth_gen[s]["TX04"] >= Wth_gen[s]["TX01"]
            Wth_gen[s].loc[loc,"TX04"] = Wth_gen[s].loc[loc,"TX01"]-1
            
    for v in Var_other:
        Data = Wth_gen[s][v].copy()
        Data[Data<=0] = np.nan
        nalist = np.argwhere(np.isnan(Data))  # list out nan loc
        Data = Interpolation(Data, nalist)
        Wth_gen[s][v] = Data
    return Wth_gen

def Generate(Wth_gen, Setting, Stat, Export = True, ParalCores = -1):
    Stns = Setting["StnID"]
    dumpcheck = Setting["DumpCheck"]
    Counter_All = Counter(); Counter_All.Start()
    
    # DatetimeIndex
    GenYear = Setting["GenYear"]
    LeapYear = Setting["LeapYear"]     
    if LeapYear:
        rng = list(pd.date_range( pd.datetime(2001,1,1), pd.datetime(2004,12,31)))*int(GenYear/4)
    else:
        rng = list(pd.date_range( pd.datetime(2001,1,1), pd.datetime(2001,12,31)))*int(GenYear)
        
    def GenForAStn(Wth_gen, Setting, Stat, s):
        # Note that the RnNum has to be generated in advanced and stored in Stat
        Wth_gen = GenP(Wth_gen, Setting, Stat, s)
        Wth_gen = GenT(Wth_gen, Setting, Stat, s)
        if dumpcheck:
            Wth_gen = DumpCheck(Wth_gen, Setting, Stat, s)
        # Add false date index (Only the for the program to use datetimeIndex).
        
        Wth_gen[s].index = pd.DatetimeIndex(rng)
        return Wth_gen[s]
    
    Stat2 = deepcopy(Stat)
    if Stat2.get("MultiSiteDict") is not None:
        if Stat2["MultiSiteDict"].get("V2UCurve") is not None:
            #Stat2["MultiSiteDict"]["V2UCurve"] = "Need to be re-generated when loaded from outside."
            ParalCores = 1
        else:
            print("Start weather generation in parallel.")
                
    WthParel = Parallel(n_jobs = ParalCores) \
                        ( delayed(GenForAStn)\
                          (Wth_gen, Setting, Stat2, s) \
                          for s in Stns \
                        ) 
    # Collect WthParel results
    for i, s in enumerate(Stns):
        Wth_gen[s] = WthParel[i]

    # for s in Stns:
    #     Counter_Stn = Counter(); Counter_Stn.Start()
    #     print("Start to generate ",s,"......")
    #     # Note that the RnNum has to be generated in advanced and stored in Stat
    #     Wth_gen = GenP(Wth_gen, Setting, Stat, s)
    #     Wth_gen = GenT(Wth_gen, Setting, Stat, s)
    #     if dumpcheck:
    #         Wth_gen = DumpCheck(Wth_gen, Setting, Stat, s)
    #     Counter_Stn.End()
    #     print("Finish ",s,". [",Counter_Stn.strftime,"]")
    #     # Add false date index
    #     GenYear = Setting["GenYear"]
    #     LeapYear = Setting["LeapYear"]     
    #     if LeapYear:
    #         rng = list(pd.date_range( pd.datetime(2001,1,1), pd.datetime(2004,12,31)))*int(GenYear/4)
    #     else:
    #         rng = list(pd.date_range( pd.datetime(2001,1,1), pd.datetime(2001,12,31)))*int(GenYear)
    #     Wth_gen[s].index = pd.DatetimeIndex(rng)
        
        
    Counter_All.End()
    # Save
    if Export:
        ToPickle(Setting, "OUT/Wth_gen_"+strftime("%Y%m%d_%H%M%S", gmtime())+".pickle", Wth_gen)
        ToCSV(Setting, Wth_gen)
    ToPickle(Setting, "Stat.pickle", Stat)
    print("Generation done! [",Counter_All.strftime,"]")
    return [Wth_gen, Stat]