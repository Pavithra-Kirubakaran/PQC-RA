from __future__ import annotations
import argparse
import json
from qars.model import QARS, QARSConfig

def parse_args():
    p = argparse.ArgumentParser(description="Compute QARS for an asset")
    p.add_argument("--X", type=float, required=True, help="Confidentiality duration (years)")
    p.add_argument("--Y", type=float, required=True, help="Time to migrate (years)")
    p.add_argument("--Z", type=float, required=True, help="Projected CRQC horizon (years)")
    p.add_argument("--sensitivity", choices=["Low","Moderate","High","Critical"], default="Moderate")
    p.add_argument("--v", type=int, choices=[0,1], default=1, help="Uses breakable PK (1) or PQC (0)")
    p.add_argument("--q", type=float, default=0.5, help="Harvestability [0..1]")
    p.add_argument("--preset", choices=["default","finance","iot","cloud"], default="default")
    return p.parse_args()

def main():
    args = parse_args()
    if args.preset == "finance":
        model = QARS.preset_finance()
    elif args.preset == "iot":
        model = QARS.preset_iot()
    elif args.preset == "cloud":
        model = QARS.preset_cloud()
    else:
        model = QARS()
    res = model.score(args.X, args.Y, args.Z, args.sensitivity, args.v, args.q)
    out = {
        "input": {"X": args.X, "Y": args.Y, "Z": args.Z, "sensitivity": args.sensitivity, "v": args.v, "q": args.q, "preset": args.preset},
        "result": {"score": res.score, "band": res.band, "T": res.T, "S": res.S, "E": res.E, "breakdown": res.breakdown},
    }
    print(json.dumps(out, indent=2))

if __name__ == "__main__":
    main()