# GCCRW Readme

GCCRW(Greenhouse Crop Climate Risk early Warning system) can be seperated into four time-scale sub models including "RealTime", "aWeek", "SeasonalLongTerm", and "ClimateChange". To run GCCRW, one should execute the main.py after complete all parameter settings. Required data are as followed:
1. Climate Data: to estimate realtime, seasonalLongTerm, and climateChange risk. aWeek future climate data will be extract from CWB database through API directly. 
2. Condition Data: to define hazard level.
3. OperationMethodData: to generate proper operational suggestions accroding to actual farm conditions.
4. SDmodel: to simulate the water resources supply situation using SDmodel of vensim.
5. Other parameters: parameters setting of other sub-model, should be setted up in the inputData.json.

Algorithm logic please refer to <<從台灣傳統溫室建構智慧溫室物聯網系統：以溫室番茄的氣候風險為例，黃宇弘，2021>>