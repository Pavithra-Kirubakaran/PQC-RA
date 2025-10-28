from __future__ import annotations
# ...existing code...
from dataclasses import dataclass, asdict
from typing import Dict, Tuple, Literal
import math

SensitivityLabel = Literal["Low", "Moderate", "High", "Critical"]

DEFAULT_SENSITIVITY_MAP: Dict[SensitivityLabel, float] = {
    "Low": 0.25,
    "Moderate": 0.5,
    "High": 0.75,
    "Critical": 1.0,
}


@dataclass
class QARSConfig:
    wT: float = 1 / 3
    wS: float = 1 / 3
    wE: float = 1 / 3
    alpha: float = 8.0  # steepness for logistic timeline scaling
    timeline_linear: bool = False  # use linear ftime if True
    sens_map: Dict[SensitivityLabel, float] = None

    def __post_init__(self):
        if self.sens_map is None:
            self.sens_map = DEFAULT_SENSITIVITY_MAP
        # normalize weights
        s = self.wT + self.wS + self.wE
        if s <= 0:
            raise ValueError("Sum of weights must be positive")
        self.wT /= s
        self.wS /= s
        self.wE /= s


@dataclass
class QARSResult:
    T: float
    S: float
    E: float
    score: float
    band: str
    breakdown: Dict[str, float]


def _logistic(x: float, alpha: float = 8.0, x0: float = 1.0) -> float:
    # logistic map to [0,1], center at x0
    return 1.0 / (1.0 + math.exp(-alpha * (x - x0)))


def _linear_clip(x: float, maxv: float = 1.0) -> float:
    return min(max(x, 0.0), maxv)


class QARS:
    def __init__(self, config: QARSConfig = None):
        self.config = config or QARSConfig()

    def timeline_raw(self, X: float, Y: float, Z: float) -> float:
        """r = (X + Y) / Z, safe when Z==0 handled"""
        if Z <= 0:
            return float("inf") if (X + Y) > 0 else 0.0
        return (X + Y) / Z

    def ftime(self, r: float) -> float:
        if self.config.timeline_linear:
            return _linear_clip(r)
        return _logistic(r, alpha=self.config.alpha, x0=1.0)

    def fsens(self, label: SensitivityLabel) -> float:
        return float(self.config.sens_map.get(label, 0.0))

    def fexpos(self, v: int, q: float) -> float:
        # v in {0,1} (0 => PQC or non-public-key), q in [0,1]
        if v <= 0:
            return 0.0
        return _linear_clip(q)

    def score(
        self,
        X: float,
        Y: float,
        Z: float,
        sensitivity: SensitivityLabel,
        v: int,
        q: float,
    ) -> QARSResult:
        if any(val < 0 for val in (X, Y, Z, q)):
            raise ValueError("X,Y,Z,q must be non-negative")
        r = self.timeline_raw(X, Y, Z)
        T = self.ftime(r)
        S = self.fsens(sensitivity)
        E = self.fexpos(int(bool(v)), float(q))
        cfg = self.config
        score = cfg.wT * T + cfg.wS * S + cfg.wE * E
        band = self._band(score)
        breakdown = {"T": T, "S": S, "E": E, "wT": cfg.wT, "wS": cfg.wS, "wE": cfg.wE}
        return QARSResult(T=T, S=S, E=E, score=score, band=band, breakdown=breakdown)

    @staticmethod
    def _band(score: float) -> str:
        # default mapping: low < 0.30, medium 0.30–0.60, high >0.60, critical >0.85
        if score > 0.85:
            return "Critical"
        if score > 0.60:
            return "High"
        if score >= 0.30:
            return "Medium"
        return "Low"

    # convenience presets
    @classmethod
    def preset_finance(cls) -> "QARS":
        return cls(QARSConfig(wT=0.4, wS=0.4, wE=0.2, alpha=10.0))

    @classmethod
    def preset_iot(cls) -> "QARS":
        return cls(QARSConfig(wT=0.5, wS=0.2, wE=0.3, alpha=6.0))

    @classmethod
    def preset_cloud(cls) -> "QARS":
        return cls(QARSConfig(wT=0.3, wS=0.2, wE=0.5, alpha=8.0))