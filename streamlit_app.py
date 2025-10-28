from __future__ import annotations
# ...existing code...
import streamlit as st
import csv
import io
from typing import Dict
from qars.model import QARS, QARSConfig

st.set_page_config(page_title="QARS Prototype", layout="wide")

# Top header with a right-aligned toggle button to show/hide single-asset test
left, right = st.columns([9, 1])
with left:
    st.title("Quantum-Adjusted Risk Score (QARS) — Prototype with CSV import")
with right:
    if "show_single" not in st.session_state:
        st.session_state.show_single = False
    if st.button("Single asset test"):
        st.session_state.show_single = not st.session_state.show_single

# Default batch model (used for CSV scoring). Single-asset uses its own config when visible.
batch_model = QARS()

st.markdown("")  # separator

# If the toggle was clicked, show single-asset inputs and results
if st.session_state.show_single:
    st.markdown("## Single asset test")
    col1, col2 = st.columns(2)
    with col1:
        X = st.number_input("Confidentiality (X, years)", min_value=0.0, value=15.0, step=1.0, key="X")
        Y = st.number_input("Migration time (Y, years)", min_value=0.0, value=2.0, step=0.5, key="Y")
        Z = st.number_input("CRQC horizon (Z, years)", min_value=0.0, value=12.0, step=1.0, key="Z")
        sensitivity = st.selectbox("Sensitivity", ["Low", "Moderate", "High", "Critical"], index=2, key="sensitivity")
        v = st.selectbox("Cryptographic visibility v", [1, 0], index=0, format_func=lambda x: "Classical RSA/ECC/DH (1)" if x==1 else "PQC/non-PK (0)", key="v")
        q = st.slider("Harvestability q", min_value=0.0, max_value=1.0, value=0.3, step=0.01, key="q")
    with col2:
        preset = st.selectbox("Sector preset", ["default", "finance", "iot", "cloud"], key="preset")
        alpha = st.slider("Timeline steepness (alpha)", 1.0, 20.0, 8.0, key="alpha")
        wT = st.slider("Weight T", 0.0, 1.0, 1/3, key="wT")
        wS = st.slider("Weight S", 0.0, 1.0, 1/3, key="wS")
        wE = st.slider("Weight E", 0.0, 1.0, 1/3, key="wE")
        linear = st.checkbox("Use linear timeline scaling (ftime=min(1,r))", False, key="linear")

    # Build model for single-asset using chosen presets/weights
    if preset != "default":
        if preset == "finance":
            single_model = QARS.preset_finance()
        elif preset == "iot":
            single_model = QARS.preset_iot()
        else:
            single_model = QARS.preset_cloud()
        single_model.config.alpha = alpha
        single_model.config.timeline_linear = linear
    else:
        cfg = QARSConfig(wT=wT, wS=wS, wE=wE, alpha=alpha, timeline_linear=linear)
        single_model = QARS(cfg)

    # Compute and display single-asset score
    res = single_model.score(X, Y, Z, sensitivity, v, q)
    st.metric("QARS score", f"{res.score:.3f}")
    st.write(f"Band: **{res.band}**")
    st.write("Breakdown:", res.breakdown)
    st.markdown("---")

# Batch scoring via CSV upload (visible by default)
st.subheader("Batch scoring via CSV upload")
st.write("CSV must include these headers (case-insensitive):")
st.code("application,app type,algorithm,frequency,key size,data sensitivity,architecture flexibility,3rd party usage,is third party quantum safe,data transition algorithm,data shelf life,migration,vendor pkc complaint,vendor supply time")

uploaded = st.file_uploader("Upload CSV file", type=["csv"])
default_Z = st.number_input("Default CRQC horizon Z (years) for rows without Z", value=12.0, step=1.0)

# mapping helpers (adapt as needed)
def alg_to_v(alg: str) -> int:
    classical = {"rsa", "ecdsa", "dh", "dsa"}
    return 1 if (alg or "").strip().lower() in classical else 0

def freq_to_q(freq_val: str) -> float:
    import math
    if freq_val is None:
        return 0.5
    s = str(freq_val).strip().lower()
    try:
        val = float(s)
        return max(0.0, min(1.0, math.exp(-val / 2.0)))
    except Exception:
        if s in {"daily","day","1/day"}:
            return math.exp(-365/2)
        if s in {"weekly","week","1/week"}:
            return math.exp(-52/2)
        if s in {"monthly","month","1/month"}:
            return math.exp(-12/2)
        if s in {"annual","year","1/year"}:
            return math.exp(-1/2)
    return 0.5

def arch_to_y_adj(flex: str) -> float:
    if not flex:
        return 0.0
    s = str(flex).strip().lower()
    if s in {"high","flexible","modular","easy"}:
        return -0.5
    if s in {"low","rigid","hard"}:
        return 1.0
    return 0.0

def parse_bool_field(val: str) -> bool:
    if val is None:
        return False
    return str(val).strip().lower() in {"yes","true","1","y","t"}

def numeric_or_default(val, default=0.0):
    try:
        return float(val)
    except Exception:
        return default

def process_row_dict(row: Dict[str,str], qars_model: QARS, default_Z: float):
    get = lambda k: row.get(k) or row.get(k.lower()) or row.get(k.upper()) or ""
    X = numeric_or_default(get("data shelf life"), 0.0)
    Y_plan = numeric_or_default(get("migration"), 0.0)
    vendor_supply = numeric_or_default(get("vendor supply time"), 0.0)
    arch_f = get("architecture flexibility")
    Y = max(0.0, Y_plan + vendor_supply + arch_to_y_adj(arch_f))
    Z_val = get("Z") or get("crqc horizon") or ""
    Z = numeric_or_default(Z_val, default_Z)
    alg = get("algorithm")
    v_field = alg_to_v(alg)
    freq_field = get("frequency")
    q_score = freq_to_q(freq_field)
    third_usage = parse_bool_field(get("3rd party usage"))
    third_safe = parse_bool_field(get("is third party quantum safe"))
    if third_usage and not third_safe:
        q_score = max(q_score, 0.7)
        v_field = 1
    dta = get("data transition algorithm").strip().lower()
    if "pqc" in dta or "hybrid" in dta:
        v_field = 0
        q_score = min(q_score, 0.3)
    sensitivity = (get("data sensitivity") or "Moderate").title()
    res = qars_model.score(X, Y, Z, sensitivity, v_field, q_score)
    out = dict(row)
    out.update({
        "X_data_shelf_life": X,
        "Y_migration_years": Y,
        "Z_crqc_horizon": Z,
        "v_crypto_visible": v_field,
        "q_harvestability": f"{q_score:.3f}",
        "T": f"{res.T:.3f}",
        "S": f"{res.S:.3f}",
        "E": f"{res.E:.3f}",
        "QARS": f"{res.score:.3f}",
        "band": res.band
    })
    return out

if uploaded is not None:
    try:
        bytes_data = uploaded.getvalue()
        text = bytes_data.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        rows = list(reader)
        if not rows:
            st.warning("Uploaded CSV contains no rows.")
        else:
            scored = []
            for r in rows:
                scored.append(process_row_dict(r, batch_model, default_Z))
            st.success(f"Scored {len(scored)} assets")
            st.dataframe(scored)
            out_io = io.StringIO()
            writer = csv.DictWriter(out_io, fieldnames=list(scored[0].keys()))
            writer.writeheader()
            writer.writerows(scored)
            out_io.seek(0)
            st.download_button("Download scored CSV", data=out_io.getvalue(), file_name="scored_assets.csv", mime="text/csv")
    except Exception as e:
        st.error(f"Failed to process CSV: {e}")

st.caption("Model: QARS — Timeline (T), Sensitivity (S), Exposure (E). See qars/model.py for implementation.")