import numpy as np
from market_analyzer.models.stress import TimeGANStressTester

def test_timegan_sequence_builder():
    x=np.random.default_rng(3).normal(0,.01,(30,2))
    s=TimeGANStressTester.make_sequences(x,10)
    assert s.shape==(21,10,2)

def test_timegan_stress_evaluates_portfolio():
    tester=TimeGANStressTester(feature_dim=2,hidden_dim=4,sequence_length=5,seed=3)
    tester.fitted=True
    tester.sample=lambda paths: np.full((paths,5,2),.01,dtype=np.float32)
    report=tester.evaluate(paths=20,weights=np.array([.75,.25]))
    assert report.synthetic_paths==20
    assert report.horizon==5
    assert report.mean_return>0
    assert report.p05_return>0
    assert report.p01_return>0
    assert report.worst_mean_drawdown<=0
    assert report.collapsed is True
    assert report.return_std==0.0

def test_timegan_stress_detects_dispersion():
    tester=TimeGANStressTester(feature_dim=2,hidden_dim=4,sequence_length=5,seed=3)
    tester.fitted=True
    rng=np.random.default_rng(8)
    tester.sample=lambda paths: rng.normal(0,.01,(paths,5,2)).astype(np.float32)
    report=tester.evaluate(paths=100,weights=np.array([.75,.25]))
    assert report.return_std>0
    assert report.path_dispersion>0
