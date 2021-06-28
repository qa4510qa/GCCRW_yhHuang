# -*- coding: utf-8 -*-
"""
Created on Sat Mar  9 21:59:06 2019
Using Taiwan CWB code
* PP01 降水量(mm)
* TX01 平均氣溫(℃)
* TX02 最高氣溫(℃)
* TX04 最低氣溫(℃)
* GR01 全天空日射量(MJ/m2)
@author: Philip Lin
@email: philip928lin@gmail.com
"""

from MultiWG.WG_General import CreateTask, ReadFiles
from MultiWG.WG_HisAnalysis import HisAnalysis, MCplot
from MultiWG.WG_Generation import Generate, GenRN
from MultiWG.WG_Multi_RNGen import MultiGenRn
from MultiWG.WG_StatTest import MonthlyStatPlot, Kruskal_Wallis_Test, SpatialAutoCorrelationComparison 
from MultiWG.WG_Multi_HisAnalysis import MultiHisAnalysis
#%%
'''
站號	站名	海拔高度(m)	經度	緯度	城市	地址	資料起始日期
467080	宜蘭	7.2	121.7565	24.764	宜蘭縣	宜蘭市力行路150號	1935/1/1
467440	高雄	2.3	120.3157	22.566	高雄市	前鎮區明孝里26鄰漁港南二路2號	1931/1/1
467480	嘉義	26.9	120.4329	23.4959	嘉義市	西區北新里海口寮路56號	1968/9/1
467490	臺中	84	120.6841	24.1457	臺中市	北區精武路295號	1896/01/01
467530	阿里山	2413.4	120.8132	23.5082	嘉義縣	阿里山鄉中正村4鄰東阿里山73-1號	1933/1/1
467590	恆春	22.1	120.7463	22.0039	屏東縣	恆春鎮天文路50號	1896/01/01
467660	臺東	9	121.1546	22.7522	臺東縣	臺東市大同路106號	1901/1/1
'''
# =============================================================================
# Step 1: Create Task and prepare Setting file
# =============================================================================
Wth_obv, Wth_gen, Setting, Stat = CreateTask(wd = r"C:\Users\Philip\Documents\GitHub\MultiWG\Test_CC")
# #Setting["WDPath"] = r"C:\Users\Philip\Documents\GitHub\MultiWG\TestWD"
# Setting["StnID"] = ["467490" "467080", "467440"]  #, "467480", "467490", "467530", "467590", "467660"]  # Wth Stn ID "C0C540", "C0C630"
# Setting["ClimScenCsvFile"] = None #{"C0A5370":"C0A570_Scen_test.csv"} #{"467571":"C0A570_Scen_test.csv"}
# Setting["Var"] = ['PP01', 'TX01', 'TX02', 'TX04'] # ['PP01', 'TX02', 'TX04', 'TX01', 'GR01']#

# =============================================================================
# Step2: Read-in Weather Data
# =============================================================================
## Read in files (WthObvCsvFile and ClimScenCsvFile)
Wth_obv, Setting, Stat = ReadFiles(Wth_obv, Setting, Stat) # Wth_obv has been preprocessed


# =============================================================================
# Step3: Run Statistical Analysis
# =============================================================================
# HisAnalysis
Stat = HisAnalysis(Wth_obv, Setting, Stat)
# (Optional) If you did't want to generate multiple sites with considering their spatial correlation, then you can skip this to save sometime. This step will take a bit of time to run.
Stat = MultiHisAnalysis(Stat, Setting, Wth_obv, Wth_gen)


# =============================================================================
# Step4: Generate RN Sets 
# =============================================================================
# For uni-site or multiple sites without considering spatial correlation
Stat = GenRN(Setting, Stat)
# For multiple sites. It will consider spatial correlation
Stat = MultiGenRn(Setting, Stat)


# =============================================================================
# Step5: Generate Weather Data
# =============================================================================
# Generate weather
Wth_gen, Stat = Generate(Wth_gen, Setting, Stat, ParalCores = 1)



#%% Validation Test
## Checking first and second moments among weather variables 
CompareResult = MonthlyStatPlot(Wth_gen, Wth_obv, Setting)

## Checking precipitation distribution
KruskalDict = Kruskal_Wallis_Test(Wth_gen, Wth_obv, Setting)

## Checking Markov parameters for generating pricipitation events
MCplot(Wth_gen, Stat, Setting)

## Spatial auticorrelation check
SpatialAutoCorrelationComparison(Setting, Stat, Wth_gen)


#Setting["StatTestAlpha"]["TTest"] = 0.05
#Setting["StatTestAlpha"]["FTest"] = 0.05
#TtestDict = WGTTest(Wth_gen, Wth_obv, Setting)
#FtestDict = WGFTest(Wth_gen, Wth_obv, Setting)



