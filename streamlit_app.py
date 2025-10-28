from __future__ import annotations
# ...existing code...
import streamlit as st
from qars.model import QARS, QARSConfig

st.set_page_config(page_title="QARS Prototype", layout="centered")

st.title("Quantum-Adjusted Risk Score (QARS) — Prototype")
col1, col2 = st.columns(2)

with col1:
    X = st.number_input("Confidentiality (X, years)", min_value=0.0, value=15.0, step=1.0)
    Y = st.number_input("Migration time (Y, years)", min_value=0.0, value=2.0, step=0.5)
    Z = st.number_input("CRQC horizon (Z, years)", min_value=0.0, value=12.0, step=1.0)
    sensitivity = st.selectbox("Sensitivity", ["Low", "Moderate", "High", "Critical"], index=2)
    v = st.selectbox("Cryptographic visibility v", [1, 0], index=0, format_func=lambda x: "Classical RSA/ECC/DH (1)" if x==1 else "PQC/non-PK (0)")
    q = st.slider("Harvestability q", min_value=0.0, max_value=1.0, value=0.3, step=0.01)

with col2:
    preset = st.selectbox("Sector preset", ["default", "finance", "iot", "cloud"])
    alpha = st.slider("Timeline steepness (alpha)", 1.0, 20.0, 8.0)
    wT = st.slider("Weight T", 0.0, 1.0, 1/3)
    wS = st.slider("Weight S", 0.0, 1.0, 1/3)
    wE = st.slider("Weight E", 0.0, 1.0, 1/3)
    linear = st.checkbox("Use linear timeline scaling (ftime=min(1,r))", False)

if preset != "default":
    if preset == "finance":
        model = QARS.preset_finance()
    elif preset == "iot":
        model = QARS.preset_iot()
    else:
        model = QARS.preset_cloud()
    # override alpha/weights UI to reflect preset but allow manual tweak
    cfg = model.config
    cfg.alpha = alpha
    cfg.timeline_linear = linear
else:
    cfg = QARSConfig(wT=wT, wS=wS, wE=wE, alpha=alpha, timeline_linear=linear)
    model = QARS(cfg)

res = model.score(X, Y, Z, sensitivity, v, q)

st.metric("QARS score", f"{res.score:.3f}", delta=None)
st.write(f"Band: **{res.band}**")
st.subheader("Component breakdown")
st.table({
    "component": ["Timeline T", "Sensitivity S", "Exposure E"],
    "value": [f"{res.T:.3f}", f"{res.S:.3f}", f"{res.E:.3f}"],
})
st.subheader("Weights")
st.write(res.breakdown)
st.subheader("Interpretation / recommended action")
if res.score > 0.85:
    st.error("Critical — Begin PQC migration immediately and/or apply compensating controls.")
elif res.score > 0.60:
    st.warning("High — Prioritise for early migration and implement mitigations.")
elif res.score >= 0.30:
    st.info("Medium — Schedule in roadmap; review during major upgrades.")
else:
    st.success("Low — Routine migration ok; monitor for changes.")
st.write("---")
st.caption("Model: QARS — Timeline (T), Sensitivity (S), Exposure (E). See qars/model.py for implementation.")