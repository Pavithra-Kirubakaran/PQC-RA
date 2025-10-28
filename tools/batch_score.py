import csv
from qars.model import QARS, QARSConfig

# simple mapping functions (adapt to your schema)
def alg_to_v(alg: str) -> int:
    classical = {"rsa","ecdsa","dh","dsa"}
    return 1 if (alg or "").strip().lower() in classical else 0

def freq_to_q(freq_per_year: float) -> float:
    # more frequent rotation -> lower q; example: q = exp(-freq/2)
    import math
    return max(0.0, min(1.0, math.exp(-freq_per_year / 2.0)))

def arch_to_y_adj(flex: str) -> float:
    if flex.lower() in {"high","flexible","modular"}:
        return -0.5
    if flex.lower() in {"low","rigid"}:
        return 1.0
    return 0.0

def process_row(row, qars: QARS, default_Z: float):
    X = float(row.get("data shelf life", 0.0))
    Y_plan = float(row.get("migration", 0.0))
    vendor_supply = float(row.get("vendor supply time", 0.0))
    Y = Y_plan + vendor_supply + arch_to_y_adj(row.get("architecture flexibility",""))
    Z = float(row.get("Z", default_Z))
    v = alg_to_v(row.get("algorithm",""))
    # combine frequency and 3rd-party quantum-safety
    freq = float(row.get("frequency", 0.0))
    q = freq_to_q(freq)
    if row.get("3rd party usage","").lower() in {"yes","true","1"} and row.get("is third party quantum safe","").lower() in {"no","false","0"}:
        q = max(q, 0.7)
        v = 1
    sensitivity = row.get("data sensitivity","Moderate").title()
    res = qars.score(X, Y, Z, sensitivity, v, q)
    out = dict(row)
    out.update({"T": f"{res.T:.3f}", "S": f"{res.S:.3f}", "E": f"{res.E:.3f}", "QARS": f"{res.score:.3f}", "band": res.band})
    return out

def batch_score(in_csv, out_csv, default_Z=12.0, preset="default"):
    cfg = QARSConfig()
    if preset=="finance":
        qars = QARS.preset_finance()
    elif preset=="iot":
        qars = QARS.preset_iot()
    elif preset=="cloud":
        qars = QARS.preset_cloud()
    else:
        qars = QARS(cfg)
    with open(in_csv, newline='') as inf, open(out_csv, "w", newline='') as outf:
        reader = csv.DictReader(inf)
        writer = None
        for row in reader:
            scored = process_row(row, qars, default_Z)
            if writer is None:
                writer = csv.DictWriter(outf, fieldnames=list(scored.keys()))
                writer.writeheader()
            writer.writerow(scored)

# example usage:
# python -m tools.batch_score input.csv output_scored.csv