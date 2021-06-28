# -*- coding: utf-8 -*-
"""
Created on Tue Aug 13 16:26:25 2019

@author: Philip
"""

Setting_template = {"WDPath": "Working directory",    
           "StnID": ["467080", "467440", "467480"],
           #(list of Weather station ID)
           "WthObvCsvFile": None,  
           #(Default None, which filename = StnID.csv / {"StnID": "filename.csv"})
           "ClimScenCsvFile":None, 
           #(Default None, which no parameters will be updated / {"StnID":"filename.csv"})
           "Var": ["PP01", "TX01", "TX02", "TX04"],
           #(Weather variables: Using Taiwan's Central Weather Bureau standard code.)
           "P_Threshold": 0.01,                     
           #(Seperate dry day and wet day [mm].)
           "P_Distribution": "Auto",                
           #(Default Auto: Select dist base on BIC and consistency. /
           # Assign distribution manually => Options: "exp", "gamma", "weibull", "lognorm".)
           "GenYear": 200,                          
           #(Total generation years. If leapYear = True, it has to be a multiple of 4.)
           "Condition": True,                       
           #(Default True for ensuring the order of Tmin & Tmax and Tavg are correct. 
           # If False, the order of generated data (Tmin & Tmax and Tavg) needs to be
           # checked afterward.)
           "LeapYear": True,                        
           #(Default True. Options for the generated weather data.)
           "Smooth": False,                         
           #(Default False (not open yet!). 
           # Smooth precipitation occurance and amount coefficients
           # If P_Distribution = Auto, it will be forced to be False.)
           "FourierOrder": 2,
           #(Defualt 2. The order of the fourier fitting lines for non-precipitation
           # variables. Value can be 2 or 3 or 4.)
           "DumpCheck": True,
           #(Default True. Check the order of min max mean tempertature are right if
           # Condition is set False. Check other non T or P variable. If it < 0 then
           # we interpolate it with values of index -2~+2.)
           "Plot": {"FourierDailyTFit": False,
                    "KSTestCDFPlot": False,
                    "Multi_ECDFFittingPlot": False,
                    "Multi_IrCurveFittingPlot": False},     
           #(Defualt False. Plot control.)
           "StatTestAlpha": {"PDistTest": 0.05,  
                             #"FTest": 0.05,
                             #"TTest": 0.05,
                             "Kruskal_Wallis_Test": 0.05},
           "MultiSite":{"WeightMethod": "Corr", # or SID
                        "WeightPOrder": [3, 2], # [P, P_Ocurrance]
                        "SpatialAutoCorrIndex": "SDI", # or MoranI or Provide the variable-specified list 
                        "rSimDataPoint": 10, # Default 10. Data points between rmax and rmin for forming the I-r curve. 
                        "rSimYear": 40 # Default 40. Simulation years per data point and it has to be a multiple of 4
                        }}   
           #(Default 0.05. The alpha values for statistic test.)