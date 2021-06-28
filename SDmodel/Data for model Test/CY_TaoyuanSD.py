# -*- coding: utf-8 -*-
"""
Created on Thu Sep 20 14:16:10 2018

@author: Philip
"""

'''
Note
vensim 只看index input 要同長度
vensim 輸出每日末的值，也就是如果設 initial = 0 輸出從1開始
level box variables:
    ShiMen Reservoir
    ZhongZhuang Adjustment Reservoir
    ShiMen WPP Storage Pool
Date input 是 1-365 (此為lookup table 所使用的值)
Lookup tables:
    水庫放水規則(103)
    V to H(103)
    V to surface area(103)
    蒸發散月份值(99)
'''
import os, errno
os.chdir(r"C:\Users\Philip\Documents\GitHub\TaoyuanSD\Data for model Test")
import pandas as pd
import numpy as np
import pysd
from tqdm import tqdm
#%%

def TendayToDay(df):
    df = df.iloc[:,0:(df.shape[1]-1)]
    df2 = []
    N = [10, 10, 11, 10, 10, 8, 10, 10, 11, 10, 10, 10, 10, 10, 11, 10, 10, 10, 10,
     10, 11, 10, 10, 11, 10, 10, 10, 10, 10, 11, 10, 10, 10, 10, 10, 11]
    for i in range(0,36):              ##i表"旬"
        n = N[df.loc[i,"Ten-days"]-1]  ##n為旬中的天數
        re = [df.loc[i,:]]*n
        df2 = df2 + re
    dfc = pd.DataFrame(df2)
    dfc = dfc.reset_index()
    J = []
    for i in range(1,366):
        J.append(i)
    dfc["Date"] = J
    dfc = dfc.iloc[:,3:]
    return dfc
# inport EXCEL function
def ExcelToInput(path):
    df = pd.read_excel(path)
    df = df.dropna(axis = 1)
    Input = TendayToDay(df)
    Input = Input.to_dict(orient='series')
    return Input

# Export to CSV function
def combine_and_update(df1,df2):
    output_path = os.getcwd()+"/Output/System Output/"
    try:
        os.makedirs(output_path)
    except OSError as e:
        if e.errno != errno.EEXIST:
            raise
    new_df = pd.concat([df1,df2])
    new_df.to_csv(output_path+"System_model_result.csv", sep=',', encoding='utf-8')
    return new_df

# Run other rounds function
def Run_round(model, Input_Data, start, end, Return_columns):    
    System_Go = model.run(initial_condition='current',return_timestamps=range(start,end),params = Input_Data,return_columns=Return_columns)
    return System_Go
#%%
# Convert Vensim to Python
#SDmodel = pysd.read_vensim("TaoYuanSystem_SDLab_no-loss-rate.mdl")    
SDmodel = pysd.load("TaoYuanSystem_SDLab_NoLossRate.py")
#%%
# Read in data
Vensim_path = r"C:\Users\Philip\Documents\GitHub\TaoyuanSD\Data for model Test"
os.chdir(Vensim_path)

Inflow_path = r"Data_inflow_2012.xlsx"
Inflow = ExcelToInput(Inflow_path)

Allocation_path = r"Data_allocation_2012_Test.xlsx"
Allocation = ExcelToInput(Allocation_path)
 
#%%
# Forming Input data
SDInput = {**Inflow,**Allocation}
SDInput["INITIAL TIME"] = 0
SDInput["FINAL TIME"] = 365
SDInput["Tap Water Loss Rate"] = 0
SDInitial = {'ShiMen Reservoir':205588000,
             'ZhongZhuang Adjustment Reservoir':5050000,
             'ShiMen WPP Storage Pool':500000}

#%%
# Run model
ActualOut = ['Date', 'ShiMen Reservoir',"ShiMen Reservoir Depth","Transfer From ShiMenAgriChannel To ShiMenAgriWaterDemand","Transfer From TaoYuanAgriChannel To TaoYuanAgriWaterDemand","Domestic Water Demand","Industry Water Demand","\"Domestic-Industry Proportion\""]
PlanOutAgri = ["Water Right ShiMen AgriChannel AgriWater","Water Right TaoYuan AgriChannel AgriWater"]
PlanOutPublic = ["Water Right ShiMenLongTan WPP","Water Right PingZhen WPP1","Water Right PingZhen WPP2","Water Right BanXin WPP","Water Right DaNan WPP1","Water Right DaNan WPP2"]
# 中油中科友專館外送
SDResult = SDmodel.run(params = SDInput,
                        initial_condition=(0, 
                            {'ShiMen Reservoir':205588000,
                             'ZhongZhuang Adjustment Reservoir':5050000,
                             'ShiMen WPP Storage Pool':500000})),
                            return_columns=ActualOut+PlanOutAgri+PlanOutPublic)  
SDResult.to_csv(r"C:\Users\Philip\Documents\GitHub\TaoyuanSD\Data for model Test/2012Output.csv")
    
#%% Really slow
# Daily Run  
SDResult_All = pd.DataFrame()
for i in tqdm(range(365)):
    SDInput["INITIAL TIME"] = 0 + i%365
    SDInput["FINAL TIME"] = 1 + i%365
    SDResult_D = SDmodel.run(params = SDInput,
                            initial_condition=(0, SDInitial),
                            return_columns=['Date', 'ShiMen Reservoir'])  
    # Update ShiMen Reservoir value
    if i == 0: 
        SDResult_All = SDResult_D
    else:
        SDResult_All = pd.concat([SDResult_All,SDResult_D.tail(1)],axis = 0)
    SDInitial["ShiMen Reservoir"] = float(SDResult_D.tail(1).loc[:,"ShiMen Reservoir"])
#%% Speed is OK
SDResult_All = pd.DataFrame()
# SD output structure info:
# The level item will output the begining value of the day while others will output the ending value of the day.
# Therefore, to sovle this, we need to simulate one more day to extract the initial value of the level item of next day.
for i in tqdm(range(365)):
    SDInput["INITIAL TIME"] = 0 + i%365
    SDInput["FINAL TIME"] = 2 + i%365
    if i == 0:
        SDResult_D = SDmodel.run(params = SDInput,
                                initial_condition = (0, SDInitial),
                                return_columns = ['Date', 'ShiMen Reservoir', 'ShiMen Reservoir Depth'],
                                return_timestamps = range(0,2))  
    else:
        SDResult_D = Run_round(SDmodel, SDInput, 0 + i%365, 1 + i%365,['Date', 'ShiMen Reservoir', 'ShiMen Reservoir Depth'])
    # Update ShiMen Reservoir value
    if i == 0: 
        SDResult_All = SDResult_D.iloc[0,:].to_frame().T
    else:
        SDResult_All = pd.concat([SDResult_All,SDResult_D.iloc[0,:].to_frame().T],axis = 0)
    SDInitial["ShiMen Reservoir"] = float(SDResult_D.tail(1).loc[:,"ShiMen Reservoir"])
#%%
def Performance(Sim,Obv):
    Obv = np.array(Obv)
    Sim = np.array(Sim)
    rms = (np.nanmean((Obv-Sim)**2))**0.5   #mean_squared_error(Obv, Sim)**0.5
    r = np.nansum((Obv-np.nanmean(Obv))*((Sim-np.nanmean(Sim)))) / ( ((np.nansum((Obv-np.nanmean(Obv))**2))**0.5)*((np.nansum((Sim-np.nanmean(Sim))**2))**0.5))
            #r2_score(Sim,Obv)
    CE = 1 - np.nansum((Obv-Sim)**2)/np.nansum((Obv-np.nanmean(Obv))**2) # Nash
    CP = 1 - np.nansum((Obv[1:]-Sim[1:])**2)/np.nansum((Obv[1:]-Obv[:-1])**2)
    data = {"RMSE": rms,
            "r": r,
            "CE": CE,
            "CP": CP}
    performance = pd.DataFrame(data,columns = data.keys(),index = [0])
    print(performance)
    return performance
df = pd.read_csv("CY_2012performance.csv",engine = "python", index_col = ["Date"],parse_dates = ["Date"])
#df["Sim"] = SDResult_All.loc[:,"ShiMen Reservoir Depth"]
Performance(np.array(df.loc[:,"Sim"]),np.array(df.loc[:,"Obv"]))
df.plot(encoding = )
