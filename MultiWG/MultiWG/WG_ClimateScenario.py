# -*- coding: utf-8 -*-
"""
Created on Thu Jul 25 14:36:31 2019

@author: Philip
"""
from scipy.special import gamma 
import numpy as np
import pandas as pd
from scipy.optimize import fsolve
from scipy.interpolate import CubicSpline

def UpdatePdist_MLE(Setting, Stat):
    Stns = Setting["StnID"]
    for s in Stns:
        # Adjust rainfall amount
        MonthlyStat = Stat[s]["MonthlyStat"]
        MonthlyStatCC = MonthlyStat.copy()
        CliScenFactor = Stat[s]["CliScenFactor"]
    
        Dist = ["exp", "gamma", "lognorm", "weibull"]
        for dist in Dist:   
            List = []
            for m in range(12):
                tur = MonthlyStat.loc[m+1,dist]
                if dist == "exp":
                    avg = tur[1]*CliScenFactor.loc[m+1,"P_avg_ratio"]
                    var = (tur[1]**2)*CliScenFactor.loc[m+1,"P_std_ratio"]
                    #shape = avg**2/var
                    scale = avg
                    List.append((0,scale))
                elif dist == "gamma":
                    avg = tur[0]/tur[2]*CliScenFactor.loc[m+1,"P_avg_ratio"]
                    var = (tur[0]/tur[2]**2)*CliScenFactor.loc[m+1,"P_std_ratio"]
                    shape = avg**2/var
                    scale = avg/var
                    List.append((shape,0,scale)) # loc = 0
                elif dist == "lognorm":
                    avg = np.exp(tur[0]+(tur[1]**2)/2)*CliScenFactor.loc[m+1,"P_avg_ratio"]
                    var = (np.exp(2*(tur[0]+tur[1]**2)) - np.exp(2*tur[0]+tur[1]**2))*CliScenFactor.loc[m+1,"P_std_ratio"]
                    mu = np.log(avg)-np.log(var/avg**2+1)/2
                    sig = (np.log(var/avg**2+1))**0.5
                    List.append((mu, sig))
                elif dist == "weibull":  # have to solve it numerically
                    avg = tur[2]*gamma(1+1/tur[0])*CliScenFactor.loc[m+1,"P_avg_ratio"]
                    var = (tur[2]**2*gamma(1+2/tur[0])-avg**2)*CliScenFactor.loc[m+1,"P_std_ratio"]
                    func = lambda a : (gamma(1+1/a))**2/gamma(1+2/a) - avg**2/(var+avg**2)
                    
                    # plt.plot(np.arange(0.001,1,0.001), func(np.arange(0.001,1,0.001)))
                    # plt.plot(np.arange(0.00,500,0.1),weibull_min.pdf(np.arange(0.0,500,0.1),1,tur[1],tur[2]))
                    # 瑋柏參數校正有問題，需要再討論
                                        
                    
                    shape = fsolve(func,0.8)[0]
                    # 這裡先就急
                    if shape <= 0 and MonthlyStat.loc[m+1,"SelectedDist"] == dist:
                        print("Error in Weibull updating weibull parameter! Please assign different distribution untill revised version was released. \n Go to Settting.json => ex \"P_Distribution\": \"lognorm\" ")
                        input()
                        quit()
                    scale = avg/gamma(1+1/shape)
                    List.append((shape,0,scale)) # loc = 0
                elif dist in list(MonthlyStatCC):
                    MonthlyStatCC = MonthlyStatCC.drop(columns = dist)
            MonthlyStatCC[dist] = List
        Stat[s]["MonthlyStatCC"] = MonthlyStatCC
        print("Update parameters of rainfall distribution.")
        # Adjust rainfall event
        PEventFactor = ["Pw_ratio","Pwd_ratio","Pww_ratio"]
        PEvent = ["Pw","Pwd","Pww"]
        if PEventFactor in list(CliScenFactor):
            for e in PEvent:
                MonthlyStatCC[e] = MonthlyStat[e]*CliScenFactor[e+"_ratio"]
        Stat[s]["MonthlyStatCC"] = MonthlyStatCC    
        print("Update Markov chain parameters")
    return Stat
#Stat = UpdatePdist_MLE(Setting, Stat)
    
def TCliScenFactor_M2D(Setting, Stat):
    Stns = Setting["StnID"]
    
    for s in Stns:
        # Adjust rainfall amount
        TCliScenFactor = ["T_avg_delta","T_std_ratio"]
        df_TCliScenFactor = Stat[s]["CliScenFactor"][TCliScenFactor]
      
        # Smooth method: Spline fitting to interpolate the monthly value to daily
        Smooth = True # Deflaut = True
        if Smooth:
            StatDaily_ly = pd.DataFrame()
            StatDaily_nly = pd.DataFrame()
            # Assign the mid point of each month and repeat another two times (before and after)
        # LeapYear
            x_ly = np.array([15.5, 45.5, 75.5, 106, 136.5, 167, 197.5, 228.5, 259, 289.5, 320, 350.5])
            x_ly = np.array(list(x_ly-365) + list(x_ly) + list(x_ly+366))
            xgen_ly = np.arange(1,367)
        # NonLeapYear
            x_nly = np.array([15.5, 45, 74.5, 105, 135.5, 166, 196.5, 227.5, 258, 288.5, 319, 349.5])
            x_nly = np.array(list(x_nly-364) + list(x_nly) + list(x_nly+365))
            xgen_nly = np.arange(1,366)
            for var in list(TCliScenFactor):
                # Repeat 3 times for better fitting at two ends
                y = np.array(list(df_TCliScenFactor.loc[:,var])*3) 
                
                spline_ly = CubicSpline(x_ly, y)
                StatDaily_ly[var] = spline_ly(xgen_ly)
                
                spline_nly = CubicSpline(x_nly, y)
                StatDaily_nly[var] = spline_nly(xgen_nly)
        Stat[s]["FourYearFourierTimeseriesFactor"] = {"Leap":StatDaily_ly,
                                               "Nonleap":StatDaily_nly}
    return Stat

def UpdatePar(Avgdelta,Stdratio, StatAvgCC, StatStdCC, Var,wType = None):
    if wType=='temp' or wType is None:
        var1 = Var.copy(); var1.remove('PP01'); var2 = []
        for var in var1:
            if var[0:2] == "TX":
                var2.append(var); var2.append(var+"d"); var2.append(var+"w")
                
        for var in var2:
            for m in range(12):
                StatAvgCC.loc[m,var] = StatAvgCC.loc[m,var]+Avgdelta[m]
                StatStdCC.loc[m,var] = StatStdCC.loc[m,var]*Stdratio[m]
    if wType=='rain' or wType is None:
        for m in range(12):
            StatAvgCC.loc[m,"PP01"] = StatAvgCC.loc[m,"PP01"]*Avgdelta[m]
            StatStdCC.loc[m,"PP01"] = StatStdCC.loc[m,"PP01"]*Stdratio[m]
    return StatAvgCC,StatStdCC

