import numpy as np
import pandas as pd
from market_analyzer.models.ensemble import IntelligenceEnsemble

def test_meta_training_precedes_calibration():
    dates=pd.date_range("2020-01-01",periods=300,freq="D")
    frame=pd.DataFrame({"date":dates,"tic":["AAA"]*300,"close":100*np.cumprod(1+np.random.default_rng(1).normal(.001,.01,300)),"expected_return_1d":.001,"expected_return_5d":.005,"expected_return_20d":.01})
    frame["ensemble_target"]=IntelligenceEnsemble.target(frame,5)
    frame=frame.dropna()
    assert frame["date"].iloc[int(len(frame)*.8)] > frame["date"].iloc[0]
