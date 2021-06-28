# -*- coding: utf-8 -*-
"""
Created on Wed Sep 12 18:12:00 2018

@author: Zunnex
"""

import os, errno
import pandas as pd
import pysd
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
def Run_round(model, Input_Data, start, end):    
    System_Go = model.run(initial_condition='current',return_timestamps=range(start,end),params = Input_Data)
    return System_Go
#%%############################################################################
########################### Simulation Section ################################
###############################################################################   
    
# Set path and input data
Vensim_path = r"C:\Users\Philip\Documents\GitHub\TaoyuanSD\Data for model Test"
os.chdir(Vensim_path)

inflow_path = r"Data_inflow_2012.xlsx"
inflow = ExcelToInput(inflow_path)

allocation_path = r"Data_allocation_2012.xlsx"
allocation = ExcelToInput(allocation_path)
 

# combine data
Input_Data = {**inflow,**allocation}

# Vensim model
model = pysd.read_vensim("TaoYuanSystem_SDLab.mdl")

#%%

try:
    os.remove(r"C:\Users\Zunnex\Desktop\ZunLinGo\Output\System Output\System_model_result.csv")
except:
    file = os.open(r"C:\Users\Zunnex\Desktop\ZunLinGo\Output\System Output\System_model_result.csv",os.O_CREAT)
    os.close(file)
    
test_result = model.run(params = Input_Data)  
round_result = pd.DataFrame()
round_result = combine_and_update(round_result,test_result)   
 

