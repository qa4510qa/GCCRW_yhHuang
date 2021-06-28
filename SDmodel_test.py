import os
import pandas as pd
import numpy as np
import pysd
from tqdm import tqdm

def TendayToDay(df, TendayColName = "Ten-days"):
  df = df.iloc[:,0:(df.shape[1])]
  df2 = []
  N = [10, 10, 11, 10, 10, 8, 10, 10, 11, 10, 10, 10, 10, 10, 11, 10, 10, 10, 10,
    10, 11, 10, 10, 11, 10, 10, 10, 10, 10, 11, 10, 10, 10, 10, 10, 11]
  for i in range(0,36):              ##i表"旬"
    n = N[df.loc[i,TendayColName]-1]  ##n為旬中的天數
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

def SD_ReadInputData(ListofFile,Tenday2Day = True, FileDir = None):
  def readfile(file):
    if file.split(".")[-1] == "csv":
      df = pd.read_csv(file,engine = "python")
      df.columns = [ item.strip() for item in list(df)]
    if file.split(".")[-1] == "xlsx":
      df = pd.read_excel(file)
    df = df.dropna(axis = 1)
    return df
  InputDate = pd.DataFrame()
  ListofFile = ListofFile.copy()
  if FileDir is not None:
    ListofFile = [ FileDir+"/"+item for item in ListofFile]
  for f in ListofFile:
    File = readfile(f)
    if Tenday2Day: File = TendayToDay(File)
    InputDate = pd.concat([InputDate,File],axis = 1)
    print("Read in "+f)
  InputDate = InputDate.to_dict(orient='series')
  return InputDate

VensimPath = "./AgriHydro-master/SD Model"
SDInputPath = "./AgriHydro-master/SD Model/SD_inputData"
SDmodel = pysd.read_vensim('./SD model/TaoYuanSystem_SDLab_NoLossRate.mdl')
SDLevelComponents = ["ShiMen Reservoir","ShiMen WPP Storage Pool", "ZhongZhuang Adjustment Reservoir"]
SDOutputVar = ['Date', 'ShiMen Reservoir', 'ShiMen Reservoir Depth']
SDInput = SD_ReadInputData(ListofFile = ["./SD Model/SD_inputData/Data_inflow_2012.xlsx","./SD Model/SD_inputData/Data_allocation_2012_Ind_Pub.xlsx"],Tenday2Day = True,FileDir = None) # (立方公尺/日)
SDInitial = {'ShiMen Reservoir':205588000,
            'ZhongZhuang Adjustment Reservoir':5050000,
           'ShiMen WPP Storage Pool':500000}
ReturnCol = list(set(SDLevelComponents+SDOutputVar))
ActualOut = ['Date', 'ShiMen Reservoir',"ShiMen Reservoir Depth","Transfer From ShiMenAgriChannel To ShiMenAgriWaterDemand","Transfer From TaoYuanAgriChannel To TaoYuanAgriWaterDemand","Domestic Water Demand","Industry Water Demand","\"Domestic-Industry Proportion\""]
PlanOutAgri = ["Water Right ShiMen AgriChannel AgriWater","Water Right TaoYuan AgriChannel AgriWater"]
PlanOutPublic = ["Water Right ShiMenLongTan WPP","Water Right PingZhen WPP1","Water Right PingZhen WPP2","Water Right BanXin WPP","Water Right DaNan WPP1","Water Right DaNan WPP2"]
ReturnCol = list(set(ReturnCol+ActualOut+PlanOutAgri+PlanOutPublic))
SDInput["Date"] = SDInput["Date"].at(365, 1)
print(SDInput)
SDResult = SDmodel.run(params = SDInput,
                        initial_condition = (0, SDInitial),
                        return_columns = ReturnCol,
                        return_timestamps = range(0,2))  

print(SDResult)