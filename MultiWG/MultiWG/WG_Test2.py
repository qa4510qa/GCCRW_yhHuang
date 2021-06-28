# -*- coding: utf-8 -*-
"""
Created on Sat Mar  9 21:59:06 2019
* PP01 降水量(mm)
* TX01 平均氣溫(℃)
* TX02 最高氣溫(℃)
* TX04 最低氣溫(℃)
* GR01 全天空日射量(MJ/m2)
@author: Philip
"""

from MultiWG.WG_General import CreateTask, ReadFiles, CheckSetting
from MultiWG.WG_HisAnalysis import HisAnalysis, MCplot
from MultiWG.WG_Generation import Generate, GenRN_Stn
from MultiWG.WG_StatTest import WGTTest, WGFTest, MonthlyStatPlot, Kruskal_Wallis_Test





# Setup variables 
Wth_obv, Wth_gen, Setting, Stat = CreateTask()
Setting = {"WDPath": r"C:\Users\Philip\Documents\GitHub\MultiWG\TestWD",    # Working dir
           "StnID": ["467571"],           # Wth Stn ID "C0C540", "C0C630"
           "WthObvCsvFile": None,                   # Default None: filename = StnID.csv or Manually set: {"StnID": filename}
           "ClimScenCsvFile":None,#{"467571":"467571_Scen_test.csv"},  # Default None: {"StnID": filename}
           "Var": ["PP01", "TX01", "TX02", "TX04"],# "TX02", "TX04", "GR01"], # Weather variables 
           "P_Threshold": 0.01,                     # If PP01 < P_threshold => 0 (mm)
           "P_Distribution": "Auto",                # Auto: Select dist base on BIC and consistency. Users are enable to assign one dist or modify it later on 
           "GenYear": 200,                          # Generating year number
           "Condition": True,                       # Corrected method for Tmin & Tmax and Tavg. If turned False, condition of generated data needs to be check afterward. 
           "LeapYear": True,                        # Option for generated wth data
           "Smooth": False,                         # Smooth Prep occurance and amount coef; If P_Distribution = Auto, it will be forced to False
           "FourierOrder": 2,
           "Scenario": {"GCM": None,                #
                        "RCP": None,                #
                        "Period": None},
           "Plot": {"FourierDailyTFit": False,
                    "KSTestCDFPlot": False},     # Plot control
           "StatTestAlpha": {"PDistTest": 0.05, # The alpha value for statistic test 
                             "FTest": 0.05,
                             "TTest": 0.05,
                             "Kruskal_Wallis_Test": 0.05}}     

CheckSetting(Setting)

# Read in files (WthObvCsvFile and ClimScenCsvFile)
Wth_obv, Setting, Stat = ReadFiles(Wth_obv, Setting, Stat)

# HisAnalysis
Stat = HisAnalysis(Wth_obv, Setting, Stat)

# Generate RN set 
for s in Setting["StnID"]:
    Stat = GenRN_Stn(Setting, Stat, s)

# Generate weather
Wth_gen, Stat = Generate(Wth_gen, Setting, Stat)

#%% Validation Test
#TtestDict = WGTTest(Wth_gen, Wth_obv, Setting)
#FtestDict = WGFTest(Wth_gen, Wth_obv, Setting)
a = MonthlyStatPlot(Wth_gen, Wth_obv, Setting)
KruskalDict = Kruskal_Wallis_Test(Wth_gen, Wth_obv, Setting)
MCplot(Wth_gen, Stat, Setting)


#%%
from numpy.linalg import inv, lstsq
import numpy as np
def Fourier(data, order = 2, Plot = False, name = None):
        # Fit 365 data points which are averaged across the provided period 
        #least-squares solution to a linear matrix equation
        length = len(data)
        x = np.arange(1,length+1); T = length/(2*np.pi)
        if order == 2:
            X = np.array([np.ones(x.shape[0]), np.sin(x/T), np.cos(x/T), np.sin(2*x/T), np.cos(2*x/T)]).T
            c = lstsq(X, data)[0]
            # C = [C0 D1 D2 C1 C2]  => Y=C0+C1*sin(t/T+D1)+C2*sin(2*t/T+D2)
            C = [c[0], np.arctan(c[2]/c[1]), np.arctan(c[4]/c[3])]
            C.append(c[1]/np.cos(C[1])); C.append(c[3]/np.cos(C[2]))
            
        elif order == 3:
            X = np.array([np.ones(x.shape[0]), np.sin(x/T), np.cos(x/T), np.sin(2*x/T), np.cos(2*x/T), np.sin(3*x/T), np.cos(3*x/T)]).T
            c = lstsq(X, data)[0]
            # C = [C0 D1 D2 D3 C1 C2 C3]  => Y=C0+C1*sin(t/T+D1)+C2*sin(2*t/T+D2)+C3*sin(3*t/T+D3)
            C = [c[0], np.arctan(c[2]/c[1]), np.arctan(c[4]/c[3]), np.arctan(c[6]/c[5])]
            C.append(c[1]/np.cos(C[1])); C.append(c[3]/np.cos(C[2])), C.append(c[5]/np.cos(C[3]))
            
        elif order == 4:
            X = np.array([np.ones(x.shape[0]), np.sin(x/T), np.cos(x/T), np.sin(2*x/T), np.cos(2*x/T), np.sin(3*x/T), np.cos(3*x/T), np.sin(4*x/T), np.cos(4*x/T)]).T
            c = lstsq(X, data)[0]
            # C = [C0 D1 D2 D3 D4 C1 C2 C3 C4]  => Y=C0+C1*sin(t/T+D1)+C2*sin(2*t/T+D2)+C3*sin(3*t/T+D3)+C4*sin(4*t/T+D4)
            C = [c[0], np.arctan(c[2]/c[1]), np.arctan(c[4]/c[3]), np.arctan(c[6]/c[5]), np.arctan(c[8]/c[7])]
            C.append(c[1]/np.cos(C[1])); C.append(c[3]/np.cos(C[2])), C.append(c[5]/np.cos(C[3])), C.append(c[7]/np.cos(C[4]))
        
        # Calculate fourier value
        if order == 2:
            Y = C[0]+C[3]*np.sin(x/T+C[1])+C[4]*np.sin(2*x/T+C[2])
        elif order == 3:
            Y = C[0]+C[4]*np.sin(x/T+C[1])+C[5]*np.sin(2*x/T+C[2])+C[6]*np.sin(3*x/T+C[3])
        elif order == 4:
            Y = C[0]+C[5]*np.sin(x/T+C[1])+C[6]*np.sin(2*x/T+C[2])+C[7]*np.sin(3*x/T+C[3])+C[8]*np.sin(4*x/T+C[4])  
        # Plot the result
        if Plot:
            plt.figure()
            plt.plot(x, data, 'o', label='Origin', markersize=3)
            plt.plot(x, Y, 'r', label='Fitted')
            plt.title('Fourier seasonal trend: '+name)
            plt.legend();
            plt.show()
            
        # New residue
        Residue_new = data - Y
        
        return C,Residue_new,Y
#%%
import matplotlib.pyplot as plt
import pandas as pd
Residue_new = pd.DataFrame()
Y = pd.DataFrame()
for v in ["TX01", "TX02", "TX04"]:
    plt.figure()
    ax = Stat["467571"]["Residual"][v].plot()
    ax = Wth_obv["467571"][v].plot()
    ax.set_title(v)
    C, Residue_new[v], Y[v] = Fourier(Stat["467571"]["Residual"][v], order = 4, Plot = True, name = v)
rng = Stat["467571"]["Residual"].index
Y.index = rng
Y.plot()
Stat["467571"]["Residual"].mean()
Residue_new.mean()
Residue_new.std()
Stat["467571"]["Residual"].std()
Residue_new.plot()

for v in ["TX01", "TX02", "TX04"]:
    Fourier(Residue_new[v], order = 4, Plot = True, name = v)
    
# 做個小實驗，找出低頻後先去除
for v in ["TX01", "TX02", "TX04"]:
    Wth_obv["467571"][v] = Wth_obv["467571"][v]-Y[v]
# 結論: 可以用
#%%
import numpy as np
from spectrum import aryule
import matplotlib.pyplot as plt
def Spectrum(Data):
    Data[Data<0] = 0
    ar, variance, coeff_reflection = aryule(Data, 5)
    plt.figure()
    plt.stem(range(len(ar)), ar)
    plt.show()
    plt.figure()
    Residual = Data - np.mean(Data)
    plt.hist(Residual)
    return ar
Wth_obv2 = Wth_obv["467571"].resample("M").mean()
Wth_obv21 = Wth_obv2[Wth_obv2.index.month == 1]
Wth_obv3 = Wth_obv["467571"].resample("Y").mean()

Wth_obv3["TX01"].hist()
data1 = Wth_obv3["TX01"]
data2 = Wth_obv3["TX02"]
Spectrum(Wth_obv3["TX02"])
data1 = Wth_obv["467571"]["TX01"]
data2 = Wth_obv["467571"]["TX02"]
data2 = Wth_gen["467571"]["GR01"][0:365]
Wth_gen
Spectrum(data1)
Spectrum(data2)
Spectrum(Wth_obv21["PP01"])
Spectrum(Wth_obv3["PP01"])
Spectrum(np.random.uniform(low=0.0, high=1.0, size = 1000))
from statsmodels.distributions.empirical_distribution import ECDF
ecdf = ECDF(data1[0:10])
plt.plot(ecdf.x,ecdf.y)
ecdf(4)
#%%
Wth_gen["467571"].iloc[0:365,:].plot()
Wth_obv["467571"].iloc[0:365,:].plot()
min(Wth_obv["467571"]["GR01"])
Wth_gen["C0C540"].loc[0:365,:].plot()
Stat["C0C540"]["PrepDF"]["P"].plot()
Stn = "C0C540"
Wth_obv["467571"].groupby(Wth_obv["467571"].index.month).mean()
a = Wth_obv["467571"][Wth_obv["467571"]["GR01"]<5]
Wth_obv["467571"]["GR01"].hist()
b = Wth_gen["467571"][Wth_gen["467571"]["GR01"]<5]
b["GR01"].hist()
Wth_gen["467571"]["GR01"].hist()
df = Stat["C0C540"]["FourYearFourierTimeseries"]
h = [i for i in list(df) if "std" in i]
h_w = [i for i in list(h) if "_w_" in i]
h_d = [i for i in list(h) if "_d_" in i]
df[h_w][0:365].plot()
df[h_d][0:365].plot()
# Low-Frequency.py

# residual 的問題要再確認

# WG Generation
    
#%%
import pandas as pd
# Test for monthly status
FourierData = Stat["467571"]["FourYearFourierTimeseries"]
rng = list(pd.date_range( pd.datetime(2001,1,1), pd.datetime(2004,12,31)))*int(4/4)
FourierData.index = rng
Fm = FourierData.groupby(FourierData.index.month).mean()
MonthlyStat = Stat["467571"]["MonthlyStat"] 
Fm["TX01"] = Fm["TX01_w_avg"]*MonthlyStat["Pw"] + Fm["TX01_d_avg"]*(1 - MonthlyStat["Pw"])
WthData = Wth_obv["467571"].groupby(Wth_obv["467571"].index.month).mean()
err3 = Fm["TX01"] - WthData["TX01"]
