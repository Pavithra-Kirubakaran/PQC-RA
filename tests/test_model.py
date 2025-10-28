from __future__ import annotations
import pytest
from qars.model import QARS, QARSConfig

def test_timeline_r_and_ftime():
    model = QARS(QARSConfig(alpha=10.0))
    r = model.timeline_raw(15, 2, 12)  # (17/12)=1.4167
    assert pytest.approx(r, rel=1e-3) == 17 / 12
    t = model.ftime(r)
    assert 0.5 < t <= 1.0

def test_sensitivity_mapping():
    model = QARS()
    assert model.fsens("Low") == 0.25
    assert model.fsens("Critical") == 1.0

def test_exposure_zero_for_pqc():
    model = QARS()
    assert model.fexpos(0, 1.0) == 0.0

def test_score_bounds():
    model = QARS()
    res = model.score(15,2,12,"High",1,0.3)
    assert 0.0 <= res.score <= 1.0
    assert res.band in {"Low","Medium","High","Critical"}