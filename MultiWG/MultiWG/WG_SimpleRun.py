# -*- coding: utf-8 -*-
"""
Created on Wed Aug 14 00:35:01 2019

@author: Philip Lin
@email: philip928lin@gmail.com
"""

from MultiWG.WG_General import CreateTask, ReadFiles, ToCSV
from MultiWG.WG_HisAnalysis import HisAnalysis, MCplot
from MultiWG.WG_Generation import Generate, GenRN
from MultiWG.WG_Multi_RNGen import MultiGenRn
from MultiWG.WG_StatTest import MonthlyStatPlot, Kruskal_Wallis_Test, SpatialAutoCorrelationComparison 
from MultiWG.WG_Multi_HisAnalysis import MultiHisAnalysis
import os

# Show no warnings
import warnings
warnings.filterwarnings("ignore")

def WG(WorkingDir, SpatialCorr = False):
    # Step1: Create Task and prepare Setting file
    Wth_obv, Wth_gen, Setting, Stat = CreateTask(wd = WorkingDir)
    
    
    # Step2: Read in Weather data
    ## Read in files (WthObvCsvFile and ClimScenCsvFile)
    Wth_obv, Setting, Stat = ReadFiles(Wth_obv, Setting, Stat)
    
    
    # Step3: Run statistic analysis
    ## HisAnalysis
    Stat = HisAnalysis(Wth_obv, Setting, Stat)
    if SpatialCorr:
        Stat = MultiHisAnalysis(Stat, Setting, Wth_obv, Wth_gen)
    
    # Step4: Generate Weather data
    ## Generate RN set 
    if SpatialCorr:
        Stat = MultiGenRn(Setting, Stat)
    else:
        Stat = GenRN(Setting, Stat)
    
    ## Generate weather
    Wth_gen, Stat = Generate(Wth_gen, Setting, Stat)
    return [Wth_obv, Wth_gen, Setting, Stat]

def main(argv):
    # Introduction
    print("Welcome to MultiWG!\n")
    
    # Setting WD
    CurrentDir = os.getcwd()
    # print("Is \"",CurrentDir,"\" your working directory? [y/n]")
    # ans1 = input()
    # if ans1 == "y":
    #     WorkingDir = CurrentDir
    # else:
    #     print("\nPlease enter your working directory.")
    #     WorkingDir = input()
    WorkingDir = argv[0]

    # Checking folder setting
    Wth_obv, Wth_gen, Setting, Stat = CreateTask(wd = WorkingDir)
    if Setting["WDPath"] != WorkingDir:
        print("\nThe WDPath in existed Setting.json is not corresponding to the working directory that you entered.")
        # input()
        quit()
    
    # Checking weather to apply multisite generation
    print("\nDo you want to generate multi-site weather data with consideration of spatial auto correlation? [y/n]\n")
    # Multi = input()
    Multi = argv[1]
    # Start simulation
    try:
        print("\n################################################################")
        print("Start to generate........")
        if Multi == "y":
            Wth_obv, Wth_gen, Setting, Stat = WG(WorkingDir, SpatialCorr = True)
        else:
            Wth_obv, Wth_gen, Setting, Stat = WG(WorkingDir)
        print("\nPlease find your results under OUT folder.")
        if Setting["ClimScenCsvFile"] is None: 
            print("Do you want to output the validation result? [y/n]")
            # ans3 = input()
            ans3 = argv[2]
            if ans3 == "y":
                ## Checking first and second moments among weather variables 
                CompareResult = MonthlyStatPlot(Wth_gen, Wth_obv, Setting)
                ## Checking precipitation distribution
                KruskalDict = Kruskal_Wallis_Test(Wth_gen, Wth_obv, Setting)
                ToCSV(Setting, KruskalDict, commonfilename = "KruskalPrepDistTest")
                ## Checking Markov parameters for generating pricipitation events
                MCplot(Wth_gen, Stat, Setting)
                ## Checking daily and monthly spatial auto correlation
                if Multi == "y":
                    SpatialAutoCorrelationComparison(Setting, Stat, Wth_gen)
                print("Done! Check outputs at OUT folder: \"KruskalPrepDistTest.csv\", MonthlyStatPlot.png ,and MCplot.png")
    except:
        print("Please check your data csv files are in DATA folder and your Setting.json file is modified under your working directory.\n")
    # input()
    # quit()

if __name__ == "__main__":
    import sys
    main(sys.argv)
