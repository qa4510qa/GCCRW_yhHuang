# -*- coding: utf-8 -*-
"""
Created on Thu Dec 19 14:26:41 2019

@author: Philip
"""
from copy import deepcopy
from time import gmtime, strftime
from tqdm import tqdm
import numpy as np
import pandas as pd
from numpy.linalg import eig
import matplotlib.pyplot as plt
from statsmodels.distributions.empirical_distribution import ECDF
from scipy.optimize import curve_fit
from joblib import Parallel, delayed    # For parallelization
from MultiWG.WG_General import ToPickle, Counter
from MultiWG.WG_Generation import Generate

# Calculate W for each var
def CalWeight(MultiSiteDict, Setting, Wth_obv):
    Var = Setting["Var"] + ["P_Occurrence"] # Add prep event variable
    Stns = Setting["StnID"] 
    
    WeightPOrder = Setting["MultiSite"]["WeightPOrder"]
    # Extract the event info from Stat
    HisWthData = Wth_obv.copy()
    for s in Stns:
         HisWthData[s]["P_Occurrence"] = HisWthData[s]["PP01"]
         HisWthData[s]["P_Occurrence"][HisWthData[s]["P_Occurrence"]>0] = 1
    #MultiSiteDict = MultiSiteDict.copy() # To prevent when error happens everything collapse
    MultiSiteDict["Weight"] = {}    
    
    def Weight(MultiSiteDict, var):
        #MultiSiteDict = MultiSiteDict.copy() # To prevent when error happens everything collapse
        WeightMethod = Setting["MultiSite"]["WeightMethod"]
        if type(WeightMethod) == dict:  # If they specify the method for each variables 
            WeightMethod = WeightMethod[var]
        Order = 1 # For other var we use order = 1 (power of the weight matrix)
        if var == "PP01":
            Order = WeightPOrder[0]
        elif var == "P_Occurrence":
            Order = WeightPOrder[1]
            
        DayInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
        def Row_standardize(matrix):
            matrix = (matrix.T/np.sum(matrix,axis = 1)).T 
            return matrix
        # calculate for each month
    #    if WeightMethod == "SID": # Square Inversed Distance
    #        Location = MultiSiteDict.get("Location")
    #        Location = list(Location.values())
    #        Dist = scipy.spatial.distance.cdist(Location, Location, 'euclidean')
    #        Dist = 1/Dist**2
    #        np.fill_diagonal(Dist, 0)
    #        MultiSiteDict["Weight"][var] = {}
    #        for m in range(12):
    #            MultiSiteDict["Weight"][var][m+1] = Row_standardize(Dist)
        if WeightMethod == "Corr":
            HisWthofAllStns = pd.DataFrame()
            # Collect wth data from all stations
            for s in Stns:  
                HisWthofAllStns[s] = HisWthData[s][var]
            HisWthofAllStns.index = list(np.arange(0,365))*int(HisWthofAllStns.shape[0]/365) 
            
            # For rainfall amount simulation, eliminate all dry days
            if var == "PP01":
                HisWthofAllStns = HisWthofAllStns.loc[(HisWthofAllStns!=0).any(axis=1)]
            MultiSiteDict["Weight"][var] = {}
            accday = 0
            for m in range(12):
                HisWthofAllStns_m = HisWthofAllStns[[i in range(accday,accday+DayInMonth[m]) for i in HisWthofAllStns.index.tolist()]] # Extract month data for every year
                accday = accday + DayInMonth[m]
                Corr = np.array(HisWthofAllStns_m.corr())
                np.fill_diagonal(Corr, 0) # We are counting the weight for other stns.
                Corr = Corr**Order
                MultiSiteDict["Weight"][var][m+1] = Row_standardize(Corr)
        return MultiSiteDict
           
    for i, v in tqdm(enumerate(Var), desc = "Calculate MultiSite Weight"):            
        MultiSiteDict = Weight(MultiSiteDict, v)
    return MultiSiteDict

# =============================================================================
# 
# =============================================================================
def MoransI(npArray,W):
    d = npArray # one column for one station
    if d.ndim == 1: # assure (x,) to be the right shape
        d = d.reshape((len(d),1))
    L = npArray.shape[0]
    d = (d - np.mean(d,axis=0)).T  #(xi - xavg)
    Iv = []
    for i in range(d.shape[0]):
        Iv.append(np.sum(W*np.dot(d[i].reshape((L,1)),d[i].reshape((1,L))))/np.sum(d[i]**2))    
    return Iv

def SDI(npArray,W):
    d = npArray # one column for one station
    if d.ndim == 1: # assure (x,) to be the right shape
        d = d.reshape((len(d),1))
    L = npArray.shape[0]
    d = d.T
    Iv = []
    for i in range(d.shape[0]):
        Iv.append(np.sum(W*np.dot(d[i].reshape((L,1)),d[i].reshape((1,L))))/np.sum(d[i]**2))    
    return Iv

def HisI(MultiSiteDict, Setting, Wth_obv, ForGenWth = False):
    #MultiSiteDict = MultiSiteDict.copy()
    Var = Setting["Var"] + ["P_Occurrence"] # Add prep event variable
    Stns = Setting["StnID"] 
    SpatialAutoCorrIndex = Setting["MultiSite"]["SpatialAutoCorrIndex"]
    HisWthData = Wth_obv.copy()
    for s in Stns:
         HisWthData[s]["P_Occurrence"] = HisWthData[s]["PP01"]
         HisWthData[s]["P_Occurrence"][HisWthData[s]["P_Occurrence"]>0] = 1
    DayInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]

    # =========================================================================
    #  For handling final generation wth data with leap year setting   ?????
#    LeapYear = Setting["LeapYear"]
#    if LeapYear and ForGenWth:
#        rng = list(pd.date_range( pd.datetime(2013,1,1), pd.datetime(2016,12,31)))*int(SimYear/4)+list(pd.date_range( pd.datetime(2013,1,1), pd.datetime(2013+SimYear%4-1,12,31)))
#        for s in Stns:
#            GenWth = MultiSiteDict.get("HisWthData").get(s) 
#            GenWth.index = pd.DatetimeIndex(rng)
#            GenWth = GenWth[~((GenWth.index.month == 2) & (GenWth.index.day == 29))]
#            MultiSiteDict.get("HisWthData")[s]=GenWth
    # =========================================================================
    I = []
    for v in tqdm(Var,desc = "Cal HisI"):   
        if type(SpatialAutoCorrIndex) == dict:  # If they specify the method for each variables 
            SpatialAutoCorrIndex = SpatialAutoCorrIndex[v]
        # Extract series
        d = np.array([list(HisWthData[s].loc[:,v]) for s in Stns])            
        # Calculate yearly mean for all 365 days by month
        accday = 0; accyear = 0; Year = int(d.shape[1]/365)
        Iv = []
        for y in range(Year):
            for m in range(12):
                day_in_month = DayInMonth[m]
                W = MultiSiteDict["Weight"][v][m+1]
                d1 = d[:,accday+365*y:accday+365*y+day_in_month]
                accday = accday + day_in_month
                if SpatialAutoCorrIndex == "Moran":
                    iv = MoransI(d1,W)
                elif SpatialAutoCorrIndex == "SDI":
                    iv = SDI(d1,W)
                else:
                    print("SpatialAutoCorrIndex is not defined correctly.")
                Iv = Iv + iv
            accyear += 1        
        #if v != "PP01":
        Iv = pd.Series(Iv).fillna(1) # if all stations are dry or wet or the amount are all 0 then we assign spatial autocorrelation to 1
        Iv = np.nanmean( np.reshape(np.array(Iv), (-1,365)) ,axis = 0) 
        I.append(Iv)
    I = pd.DataFrame(np.array(I).T,columns=Var) # Transform to df
    MultiSiteDict["HisI"] = I
    return MultiSiteDict

# =============================================================================
# 
# =============================================================================
# V = r*W*U+U
def GenMultiRN(r,W,Type,Size = 1,TransformFunc = None,Warn = True,HisGen = False):
    # transformFunc = None: def to convert V back to U again
    if HisGen:
        r = np.array(r)        
    else:
        r = np.array(r)   
        r = r.reshape(1,len(r))
    
    StnsNum = W.shape[0]
    if Type == "P":
        U = np.random.uniform(low=0.0, high=1.0, size = (StnsNum,Size))
        V = r*np.dot(W,U)+U  # W: row-standardized
#        df = pd.DataFrame(U.T)
#        df.hist(bins = 20)
#        df = pd.DataFrame(V.T)
#        df.hist(bins = 20)
    elif Type == "T":
        N = np.random.normal(loc=0.0, scale=1.0, size = (StnsNum,Size))
        V = r*np.dot(W,N)+N  # W: row-standardized
    if TransformFunc is not None:
        V = TransformFunc(np.array(V))
    elif Warn:
        print("V has not converted yet!")
    return V

# For Rainfall uniform transformation
# Transformation: To convert V(n) into U[0,1] again
def ECDFFitting(r,W,plot = False):
    Vlist = list(GenMultiRN(r,W,Type = "P", Size = 10000,Warn = False,HisGen = True).ravel())
    Vlist = sorted(Vlist)
    ecdf = ECDF(Vlist)
    Fx = ecdf(Vlist)
    x =np.arange(min(Vlist)-0.05,max(Vlist)+0.05,0.01)
    Fxx = ecdf(x)
    if plot:
        name = "ECDF"
        plt.figure()
        plt.plot(Vlist, Fx, 'o', label=name+': Origin', markersize=3)
        #plt.plot(Vlist, FittedFunc(Vlist), 'r', label=name+': Fitted')
        plt.plot(x, Fxx, 'r', label=name+': Fitted ecdf')
        plt.title('ECDF '+" fitting: r = "+str(r))
        plt.legend()
        plt.show()
    return ecdf
#ECDFFitting(0.5,W,plot = True)(1.3001)
    
# For other than Rainfall N(0,1) transformation
# Transformation:For T standardization
def Standardization(r,W):
    Vlist = list(GenMultiRN(r,W,Type = "T", Size = 10000,Warn = False,HisGen = True).ravel())
    Vlist = np.array(Vlist)
    Avg = np.mean(Vlist)
    Std = np.std(Vlist, ddof=1)
    def standize(x):
        return (x-Avg)/Std
    return standize
    
# Single simulation of r 
def CalSimI(r, MultiSiteDict, Setting, Stat, Wth_gen):
    # MultiSiteDict = MultiSiteDict.copy()
    Var = Setting["Var"] + ["P_Occurrence"] # Add prep event variable
    rSimYear = Setting["MultiSite"]["rSimYear"]
    Stns = Setting["StnID"] 
    plot = Setting["Plot"]["Multi_ECDFFittingPlot"]
    DayInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    SpatialRnNum = {}
    
    # Simulate spatial correlated RN
    for v in Var:        
        # Gen 40 years for the size is greater than 1000 for each month, which we consider as statistically robust
        Rn = 0
        for y in range(rSimYear):
            for m in range(12):
                day_in_month = DayInMonth[m]
                W = MultiSiteDict["Weight"][v][m+1]
                # Gen Rn
                if v == "PP01" or "P_Occurrence":
                    rn = GenMultiRN(r, W, Type = "P", Size = day_in_month, TransformFunc = ECDFFitting(r,W,plot),HisGen = True) 
                else:
                    rn = GenMultiRN(r, W, Type = "T", Size = day_in_month, TransformFunc = Standardization(r,W),HisGen = True)
                # Add up
                if type(Rn) is int: 
                    Rn = rn
                else:
                    Rn = np.concatenate((Rn,rn), axis = 1)
        SpatialRnNum[v] = Rn
    MultiSiteDict["SpatialRnNum"] = SpatialRnNum
    
    # Re-organize the Rn to each stn
    for i, s in enumerate(Stns):
        RnNum = pd.DataFrame()
        for v in Var:
            RnNum[v] = SpatialRnNum[v][i]         
        Stat[s]["RnNum"] = RnNum
    
    # Creat the "Setting" dictionary for I-r curve simulation. We need to turn off the leap year option to make sure the output are able to be iterate
    Setting_Multi = Setting.copy()
    Setting_Multi["GenYear"] = rSimYear
    Setting_Multi["LeapYear"] = False 
    Setting_Multi["Condition"] = True
    for k in list(Setting_Multi["Plot"].keys()): # Ture off all plotting options
        Setting_Multi["Plot"][k] = False
    
    # Generate weather data and re-calculate spetial autocorrelation index
    # Use single core here since we already distribute r into different cores/threads.
    Wth_gen, Stat = Generate(Wth_gen, Setting_Multi, Stat, Export = False, ParalCores = 1)
    SimI = HisI(MultiSiteDict, Setting, Wth_gen, ForGenWth = False)["HisI"]

    # Calculate monthly mean for establish I-r curve
    rng = pd.date_range( pd.datetime(2013,1,1), pd.datetime(2013,12,31))
    SimI.index = rng
    SimI = SimI.groupby(pd.Grouper(freq='M')).mean()
    SimI = SimI.reset_index().drop("index",axis=1)
    SimI.index = np.arange(1,13)
    return SimI


# Gen I for each r
def CalSimIDict(MultiSiteDict, Setting, Stat, Wth_gen):
    #MultiSiteDict = MultiSiteDict.copy()
    Var = Setting["Var"] + ["P_Occurrence"] # Add prep event variable
    rSimDataPoint = Setting["MultiSite"]["rSimDataPoint"]
    
    # Calculate the range for each var and each month
    Rmax = pd.DataFrame(); Rmin = pd.DataFrame()
    MultiSiteDict["rRange"] = {}
    for v in Var:
        rmax = []; rmin = []
        for m in range(12):
            W = MultiSiteDict["Weight"][v][m+1]
            EigValue = eig(W)[0]
            rmax.append(round(-1/np.min(EigValue),4))
            rmin.append(round(-1/np.max(EigValue),4)) 
        Rmax[v] = rmax
        Rmin[v] = rmin
    Rmax.index = np.arange(1,13); Rmin.index = np.arange(1,13)
    MultiSiteDict["rRange"]["Rmax"] = Rmax
    MultiSiteDict["rRange"]["Rmin"] = Rmin
    # Form the rlist to simulate and to form the IrCurve later on
    # Note that for TX01 TX02 TX04 (TX related var), we simply apply their rmax for the generation. No need to form the IrCurve due to their always high spatial correlation.
    Var_No_TX = [v for v in Var if "TX" not in v]
    rlist = []; RSimList = []; minRange = 1000 # just a initial value
    for v in Var_No_TX:
        for m in range(12):
            rmax = MultiSiteDict["rRange"]["Rmax"].loc[m+1, v]
            rmin = MultiSiteDict["rRange"]["Rmin"].loc[m+1, v]
            minRange = min(minRange,rmax-rmin)
            RSimList.append(rmax); RSimList.append(rmin)
            rlist = rlist + [round(rmin+i*(rmax-rmin)/(rSimDataPoint),4) for i in range(1,rSimDataPoint)]
    # Elminate closed r point in r list to alleviate the computational time. We will make sure the min range still obtain enough data points.
    interval = minRange/rSimDataPoint
    rlist.sort() # ascending
    rlist = np.array(rlist)
    new_rlist = [rlist[0]]; Acc = 0 # just an initial value
    while Acc < max(rlist):
        Acc = new_rlist[-1] + interval
        new_rlist.append(rlist[rlist <= Acc][-1])
    
    # Form the final r list which add the extreme points of each var in each month + interval points
    RSimList = list(set(RSimList))
    RSimList = RSimList + list(new_rlist)
    
    # Start the simulation for each r in RSimList
    print("Start to simulate I in parallel. (This will need some time.)")
    Counter_All = Counter(); Counter_All.Start()
    MultiSiteDict2 = deepcopy(MultiSiteDict) # To avoid original HisI been modified
    RParel = Parallel(n_jobs = -1) \
                        ( delayed(CalSimI)\
                          (r, MultiSiteDict2, Setting, Stat, Wth_gen) \
                          for r in RSimList \
                        ) 
    # Collect WthParel results
    SimIDict = {}
    for i, r in enumerate(RSimList):
        SimIDict[r] = RParel[i]
    Counter_All.End()
    print("SimIDict done! [",Counter_All.strftime,"]")
    
    # SimIDict = {}
    # for r in tqdm(RSimList, desc = "CalSimI"):
    #     MultiSiteDict2 = MultiSiteDict.copy() # To avoid original HisI been modified
    #     SimIDict[r] = CalSimI(r, MultiSiteDict2, Setting, Stat, Wth_gen)
    MultiSiteDict["SimIDict"] = SimIDict
    MultiSiteDict["RSimList"] = RSimList
    return MultiSiteDict

# =============================================================================
# 
# =============================================================================
def PolyFunc(x, a, b, c, d):
    x = np.array(x)
    return a*x**3 + b*x**2 + c*x + d
# PolyFit
def PolyFit(x,y,HisI_plot,plot = False,Title = "I vs r",xylabel = ["I","r"]):
    x, y = map(np.array,zip(*sorted(zip(x, y)))) # Sorted ref I
    popt, pcov = curve_fit(PolyFunc, x, y)
    if plot:
        plt.figure()
        x1 = np.arange(x[0],x[-1],0.01)
        plt.plot(x1, PolyFunc(x1, *popt), 'r-')
        plt.plot(x, y, 'o')
        plt.plot(HisI,PolyFunc(HisI, *popt),'go')
        plt.xlabel(xylabel[0]); plt.ylabel(xylabel[1])
        plt.title(Title)
        plt.legend(["PloyFitted","Original","HisI"])
        r_squared = np.corrcoef(x,y)[0,1]**2
        plt.text(x[-1]-0.2, y[0], 'R2 = %0.3f' % r_squared,fontsize=9)
        plt.show()
    return popt 

# Fitting I & r
def IrCurveFitting(MultiSiteDict, Setting):
    # only fit PP01 Pevent and others not T
    #MultiSiteDict = MultiSiteDict.copy()
    Var = Setting["Var"] + ["P_Occurrence"] # Add prep event variable
    Var = [v for v in Var if "TX" not in v] # No need to fit TX related var
    SimIDict = MultiSiteDict["SimIDict"]
    DayInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    
    IrCurvePar = pd.DataFrame()
    # Fitting I & r for each month and each variable
    for v in tqdm(Var,desc = "IrCurvePar"):
        mCurve = []       
        Accday = 0
        for m in range(12):  
            day_in_month = DayInMonth[m]
            HisI = MultiSiteDict["HisI"].loc[Accday:Accday+day_in_month,v]
            Accday = Accday + day_in_month
            # Select r points within its range
            rmax = MultiSiteDict["rRange"]["Rmax"].loc[m+1, v]
            rmin = MultiSiteDict["rRange"]["Rmin"].loc[m+1, v]
            RSimList = MultiSiteDict["RSimList"]
            rlist = [r for r in RSimList if r<=rmax and r>=rmin]
            # Extract I for month m variable v
            I = [SimIDict[r].loc[m+1,v] for r in rlist] 
            # Fitting using spline
            name = v+" I vs r " +"(Month "+str(m+1)+" )"
            plot = Setting["Plot"]["Multi_IrCurveFittingPlot"] 
            #plot = True
            PolyFuncPar = PolyFit(I, rlist, HisI, plot, Title = name, xylabel = ["I","r"])
            mCurve.append(PolyFuncPar)
        IrCurvePar[v] = mCurve
    IrCurvePar.index = np.arange(1,13)
    MultiSiteDict["IrCurvePar"] = IrCurvePar
    return MultiSiteDict

def GenSimrV2UCurve(MultiSiteDict, Setting):
    #MultiSiteDict = MultiSiteDict.copy()
    Var = Setting["Var"] + ["P_Occurrence"] # Add prep event variable
    HisI = MultiSiteDict["HisI"]
    IrCurvePar = MultiSiteDict["IrCurvePar"]
    DayInMonth = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
        
    Simr = pd.DataFrame(); 
    V2UCurve = pd.DataFrame();
    for v in tqdm(Var,desc = "GenSimrV2UCurve"):
        simr = []; v2UCurve = []; count = 0
        for m in range(12):
            W = MultiSiteDict["Weight"][v][m+1]
            day_in_month = DayInMonth[m]
            if "TX" in v:
                # Set TX's r = constant = rmax
                rmax = MultiSiteDict["rRange"]["Rmax"].loc[m+1, v]
                simr = simr + [rmax]*day_in_month
                v2UCurve = v2UCurve + [Standardization(rmax, W)]*day_in_month
            else:
                for d in range(day_in_month):
                    # Simr
                    PolyFuncPar = IrCurvePar.loc[m+1,v]
                    rmax = MultiSiteDict["rRange"]["Rmax"].loc[m+1, v]
                    simr.append( min(rmax, PolyFunc(HisI.loc[count,v],*PolyFuncPar) ) ) # Make sure that r is not exceed rmax
                    # V2Ucurve
                    if v == "PP01" or v == "P_Occurrence":
                        v2UCurve.append(ECDFFitting(simr[-1], W, plot = False)) 
                        count += 1
                    else:
                        v2UCurve.append(Standardization(simr[-1], W)) 
                        count += 1                
        Simr[v] = simr
        V2UCurve[v] = v2UCurve
    MultiSiteDict["Simr"] = Simr
    MultiSiteDict["V2UCurve"] = V2UCurve
    return MultiSiteDict

def MultiHisAnalysis(Stat, Setting, Wth_obv, Wth_gen):
    #Stat = Stat.copy()
    MultiSiteDict = {}
    # We nee to ensure the length of weather data in each station  is identical.
    Var = Setting["Var"]
    Stns = Setting["StnID"] 
    try:
        shape = [Wth_obv[s][Var].shape for s in Stns]
    except:
        print("Make sure all stations in Wth_obv obtain variables that you intend to generate.\n")
        input()
        quit()
    if len(set(shape)) != 1:
        print("The sizes of input weather data are not identical. Please make sure all stations obtain same length of weather data.\n")
        input()
        quit()
        
    # ["Weight"]
    try:
        MultiSiteDict = CalWeight(MultiSiteDict, Setting, Wth_obv)
    except:
        print("Error at Weight.")
        Stat["MultiSiteDict"] = MultiSiteDict
        return Stat
    
    # Calculate spatial correlation Moran's I for 365 days averaging through years
    # ["HisI"]
    try:
        MultiSiteDict = HisI(MultiSiteDict, Setting, Wth_obv, ForGenWth = False)
    except:
        print("Error at HisI.")
        Stat["MultiSiteDict"] = MultiSiteDict
        return Stat
    #MultiSiteDict = HisMoranI(MultiSiteDict)
    # Simulate weather data and calculate Moran' I across the range of r and calculate monthly mean and average through years
    # ["SimIDict"], ["SimRlists"]
    try:
        MultiSiteDict = CalSimIDict(MultiSiteDict, Setting, Stat, Wth_gen)
    except:
        print("Error at SimIDict & SimRlists.")
        Stat["MultiSiteDict"] = MultiSiteDict
        return Stat
    #MultiSiteDict = Stat["MultiSiteDict"]
    # Fitting Sim I with r using 3 order polynomial
    # ["IrCurvePar"]
    try:
        MultiSiteDict = IrCurveFitting(MultiSiteDict, Setting)
    except:
        print("Error at IrCurvePar.")
        Stat["MultiSiteDict"] = MultiSiteDict
        return Stat
    #MultiSiteDict = IrCurveFitting(MultiSiteDict,True)
    
    # Using His I and IrCurvePar to form r for 365 days and V2UCurve for each month and each var (P: to uniform, T: standardize)
    # ["Simr"], ["V2UCurve"]
    try:
        MultiSiteDict = GenSimrV2UCurve(MultiSiteDict, Setting)     
    except:
        print("Error at Simr & V2UCurve.")
        Stat["MultiSiteDict"] = MultiSiteDict
        return Stat
    
    Stat["MultiSiteDict"] = MultiSiteDict
    ToPickle(Setting, "Stat.pickle", Stat)
    print("Done!!!!")      
    return Stat