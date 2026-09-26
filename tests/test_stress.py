import numpy as np
from market_analyzer.models.stress import TimeGANStressTester

def test_timegan_sequence_builder():
    x = np.random.default_rng(3).normal(0, .01, (30, 2))
    s = TimeGANStressTester.make_sequences(x, 10)
    assert s.shape == (21, 10, 2)
