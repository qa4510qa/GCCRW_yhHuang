import os
import pandas as pd
import numpy as np
import pysd
from tqdm import tqdm

#%%

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
# inport EXCEL function
def SD_ExcelToInput(path):
    df = pd.read_excel(path)
    Input = TendayToDay(df)
    Input = Input.to_dict(orient='series')
    return Input

# Run other rounds function
def SD_Run_round(model, Input_Data, start, end, Return_columns):    
    System_Go = model.run(initial_condition='current',return_timestamps=range(start,end),params = Input_Data,return_columns=Return_columns)
    return System_Go

def SD_ReadVensim(filename, AutoSelect = True):    
    if filename.split(".")[-1] == ".py":
        SDmodel = pysd.load(filename)
    elif AutoSelect:
        if os.path.isfile(filename[0:-3]+"py"):
            SDmodel = pysd.load(filename[0:-3]+"py")
            print("Auto load existed py file.")
        else:
            SDmodel = pysd.read_vensim(filename)    
    else:
        SDmodel = pysd.read_vensim(filename)   
    return SDmodel

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


#%% Speed is OK
# SD output structure info:
# The level item will output the begining value of the day while others will output the ending value of the day.
# Therefore, to sovle this, we need to simulate one more day to extract the initial value of the level item of next day.
def SD_Sim1yr(SDmodel, SDInitial, SDLevelComponents, SDOutputVar, ListofFile, Tenday2Day = True, FileDir = None, SDDecisionTimePoint = None):
    ReturnCol = list(set(SDLevelComponents+SDOutputVar))
    ActualOut = ['Date', 'ShiMen Reservoir',"ShiMen Reservoir Depth","Transfer From ShiMenAgriChannel To ShiMenAgriWaterDemand","Transfer From TaoYuanAgriChannel To TaoYuanAgriWaterDemand","Domestic Water Demand","Industry Water Demand"] #,"\"Domestic-Industry Proportion\""
    PlanOutAgri = ["Water Right ShiMen AgriChannel AgriWater","Water Right TaoYuan AgriChannel AgriWater"]
    PlanOutPublic = ["Water Right ShiMenLongTan WPP","Water Right PingZhen WPP1","Water Right PingZhen WPP2","Water Right BanXin WPP","Water Right DaNan WPP1","Water Right DaNan WPP2"]
    ReturnCol = list(set(ReturnCol+ActualOut+PlanOutAgri+PlanOutPublic))
    
    SDInput = SD_ReadInputData(ListofFile, Tenday2Day, FileDir)
    SDInput["Date"].at[365] = 1
    SDInput["INITIAL TIME"] = 0
    SDInput["FINAL TIME"] = 365
    SDInput["Tap Water Loss Rate"] = 0 # 才能算比例
    SDResult_All = pd.DataFrame()
    for i in tqdm(range(365)):
        if SDDecisionTimePoint is not None:
            if i in SDDecisionTimePoint:
                SDInput = SD_ReadInputData(ListofFile, Tenday2Day, FileDir)
                SDInput["Date"].at[365] = 1
                print("Update SDInput Data at day "+str(i+1))
        if i == 0:
            SDInput["Date"].at[365] = 1
            SDResult_D = SDmodel.run(params = SDInput,
                                    initial_condition = (0, SDInitial),
                                    return_columns = ReturnCol,
                                    return_timestamps = range(0,2))  
        else:
            SDResult_D = SD_Run_round(SDmodel, SDInput, start = 0+i%365, end = 2+i%365, Return_columns = ReturnCol)
        SDResult_All = pd.concat([SDResult_All,SDResult_D.iloc[0,:].to_frame().T],axis = 0)
        # Update ShiMen Reservoir value
        for LevelItem in SDLevelComponents:
            SDInitial[LevelItem] = float(SDResult_D.tail(1).loc[:,LevelItem])
    return SDResult_All

def SD_SIvalue(Actual, Demand, NYears = None):
    Deficit = Demand - Actual
    Deficit[Deficit<0] = 0
    if NYears is None: NYears = int(len(Actual)/365)
    SIindex = 0
    for i in range(NYears):
        deficit = np.sum(Deficit[0+365*i:365+365*i])
        demand = np.sum(Demand[0+365*i:365+365*i])
        SIindex = SIindex+(deficit/demand)**2
    SIindex = 100/NYears*SIindex
    return SIindex

def SD_DailyRatio(SDResult): #2012
    # Agri ratio should equal to one, Ind = Domes >=1 since there is other water source from Sansia river and other sluce.
    PlanOutPublic = ["Water Right ShiMenLongTan WPP","Water Right PingZhen WPP1","Water Right PingZhen WPP2","Water Right DaNan WPP1","Water Right DaNan WPP2"] # ,"Water Right BanXin WPP" 因北桃固定拿17萬噸的水，同時板新還供應其他地方，故暫時不考慮
    Public = SDResult["Domestic Water Demand"]+SDResult["Industry Water Demand"]-SDResult["Transfer From BanXinWPP To NorthTaoYuanWaterDemand"]
    OutData = {"TaoyuanIrrRatio":SDResult["Transfer From TaoYuanAgriChannel To TaoYuanAgriWaterDemand"]/SDResult["Water Right TaoYuan AgriChannel AgriWater"],
               "ShimenIrrRatio":SDResult["Transfer From ShiMenAgriChannel To ShiMenAgriWaterDemand"]/SDResult["Water Right ShiMen AgriChannel AgriWater"],
               "Domestic":Public/(SDResult[PlanOutPublic].sum(axis = 1)),  #*(SDResult["\"Domestic-Industry Proportion\""])
               "Industry":Public/(SDResult[PlanOutPublic].sum(axis = 1))}  #*(1-SDResult["\"Domestic-Industry Proportion\""]))
    OutData = pd.DataFrame(OutData,columns= OutData.keys())
    SI_Public = SD_SIvalue(SDResult["Domestic Water Demand"]+SDResult["Industry Water Demand"], SDResult[PlanOutPublic].sum(axis = 1), NYears = None)
    SI_AgriTao = SD_SIvalue(SDResult["Transfer From TaoYuanAgriChannel To TaoYuanAgriWaterDemand"], SDResult["Water Right TaoYuan AgriChannel AgriWater"])
    SI_AgriShi = SD_SIvalue(SDResult["Transfer From ShiMenAgriChannel To ShiMenAgriWaterDemand"], SDResult["Water Right ShiMen AgriChannel AgriWater"])
                
    return OutData, [SI_Public, SI_AgriTao, SI_AgriShi]

def main(argv):
    #%%
    #This is a simple example for a single year simulation.

    # Setting
    # os.chdir(r"C:\Users\Philip\Documents\GitHub\TaoyuanSD\Data for model Test")
    VensimPath = './SDmodel'
    # SDInputPath = './Data for model Test'

    # Level component has initial values.
    SDLevelComponents = ["ShiMen Reservoir","ShiMen WPP Storage Pool", "ZhongZhuang Adjustment Reservoir"]

    # Set the output variables.
    #SDOutputVar = ['Date', 'ShiMen Reservoir', 'ShiMen Reservoir Depth']
    SDOutputVar = ['Date', 'ShiMen Reservoir', 'ShiMen Reservoir Depth',"Transfer From BanXinWPP To NorthTaoYuanWaterDemand"]

    # Read in vensim file. If it is not working, delete the TaoYuanSystem_SDLab_NoLossRate.py at VensimPath first.
    SDmodel = SD_ReadVensim(VensimPath+"/"+"TaoYuanSystem_SDLab_NoLossRate.mdl", AutoSelect = True)

    # Forming Input data
    # Those files are in a tenday scale. Tenday2Day = True will convert them into dailty scale.
    # You can create you own SDInput. It is a dictionary with keys as the item name (have to be consist to mdl) and valus as series.
    SDInput = SD_ReadInputData(ListofFile = ["./SDmodel/SD_inputData/Data_inflow_2012.xlsx","./SDmodel/SD_inputData/Data_allocation_2012_Test.xlsx"], Tenday2Day = True, FileDir = None) # (立方公尺/日)

    # Set the initial value. 
    SDInitial = {'ShiMen Reservoir':205588000,
                'ZhongZhuang Adjustment Reservoir':5050000,
                'ShiMen WPP Storage Pool':500000}
    # If you would like to re load input files in the middle of the simulation, else set None
    SDDecisionTimePoint = None # If None => Year. or Assign the day list of making decision. EX: [ 30, 50]

    # Run the simulation for 1 year.
    SDResult = SD_Sim1yr(SDmodel, SDInitial, SDLevelComponents, SDOutputVar, ListofFile = ["./SDmodel/SD_inputData/Data_inflow_2012_full.xlsx","./SDmodel/SD_inputData/Data_allocation_2012_Test.xlsx"], Tenday2Day = True, FileDir = None, SDDecisionTimePoint = SDDecisionTimePoint)

    # Calculate the SI for this year.
    ActualRatio, SI = SD_DailyRatio(SDResult)

    # Note:
        # I think now you should be able to modify the code according to your numerical experiment design. This code is design for a single year simulation. If you want to run for multiple years, there are two ways to do it. 
        # (1) Write a for loop and run the SD_Sim1yr multiple times with updated initial values.
        # (2) Modify SD_Sim1yr function. Change 365 to your desire length. However, some other minor changes might be required.
        # Good luck!

    print(ActualRatio)
    print(SI)

if __name__ == '__main__':
    import sys
    main(sys.argv)