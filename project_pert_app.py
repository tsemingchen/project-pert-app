
import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from collections import defaultdict
from io import BytesIO
import xlsxwriter

st.set_page_config(page_title="ProjectPERT", page_icon="📊", layout="wide")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=DM+Sans:wght@300;400;500;600&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; font-size: 22px; }
.stApp { background-color: #f0f2f8; color: #1a1a2e; }
#MainMenu, footer, header { visibility: hidden; }
.hero { background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%); border-radius: 16px; padding: 2.5rem 3rem; margin-bottom: 2rem; }
.hero-title { font-family: 'Space Mono', monospace; font-size: 3.2rem; font-weight: 700; color: #ffffff; margin: 0 0 0.4rem 0; }
.hero-sub { color: rgba(255,255,255,0.75); font-size: 1.4rem; margin: 0; }
.card { background: #ffffff; border: 1px solid #dde1f0; border-radius: 12px; padding: 1.8rem; margin-bottom: 1.2rem; box-shadow: 0 2px 8px rgba(99,102,241,0.07); }
.section-label { font-family: 'Space Mono', monospace; font-size: 0.95rem; letter-spacing: 3px; text-transform: uppercase; color: #6366f1; margin-bottom: 1rem; }
.metric-row { display: flex; gap: 1rem; margin-bottom: 1.5rem; }
.metric-tile { flex: 1; background: #ffffff; border: 1px solid #dde1f0; border-radius: 10px; padding: 1.6rem; text-align: center; box-shadow: 0 2px 8px rgba(99,102,241,0.07); }
.metric-val { font-family: 'Space Mono', monospace; font-size: 2.8rem; font-weight: 700; color: #4f46e5; }
.metric-lbl { font-size: 1.1rem; color: #888; margin-top: 0.4rem; }
.stButton>button { background: linear-gradient(135deg, #4f46e5, #7c3aed); color: white; border: none; border-radius: 8px; padding: 0.85rem 2rem; font-family: 'Space Mono', monospace; font-size: 1.1rem; }
.stButton>button:hover { opacity: 0.88; }
label, .stTextInput label, .stNumberInput label, .stSlider label, .stSelectbox label, .stMultiSelect label { color: #333 !important; font-size: 1.15rem !important; font-weight: 500 !important; }
div[data-testid="stNumberInput"] input, div[data-testid="stTextInput"] input { font-size: 1.1rem !important; padding: 0.6rem !important; }
p, li { font-size: 1.1rem; line-height: 1.8; }
hr { border-color: #dde1f0; }
</style>
""", unsafe_allow_html=True)

UNIT_OPTIONS = ["Minutes", "Hours", "Days", "Weeks", "Months", "Years"]

def pert_mean(a, m, b): return (a + 4*m + b) / 6
def pert_std(a, b): return (b - a) / 6

def topological_sort(activities):
    in_degree = {act: 0 for act in activities}
    adj = defaultdict(list)
    for act, info in activities.items():
        for pred in info["predecessors"]:
            adj[pred].append(act)
            in_degree[act] += 1
    queue = [a for a in activities if in_degree[a] == 0]
    order = []
    while queue:
        node = queue.pop(0)
        order.append(node)
        for neighbor in adj[node]:
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)
    return order

def simulate_project(activities, n_simulations=10_000):
    order = topological_sort(activities)
    project_durations = []
    for _ in range(n_simulations):
        finish = {}
        for act in order:
            a, m, b = activities[act]["min"], activities[act]["avg"], activities[act]["max"]
            duration = np.random.triangular(a, m, b)
            preds = activities[act]["predecessors"]
            start = max((finish[p] for p in preds), default=0)
            finish[act] = start + duration
        project_durations.append(max(finish.values()))
    return np.array(project_durations)

def compute_pert_critical_path(activities):
    order = topological_sort(activities)
    exp_dur = {a: pert_mean(activities[a]["min"], activities[a]["avg"], activities[a]["max"]) for a in activities}
    earliest_finish = {}
    for act in order:
        preds = activities[act]["predecessors"]
        start = max((earliest_finish[p] for p in preds), default=0)
        earliest_finish[act] = start + exp_dur[act]
    end_node = max(earliest_finish, key=earliest_finish.get)
    def backtrack(node):
        preds = activities[node]["predecessors"]
        if not preds: return [node]
        return backtrack(max(preds, key=lambda p: earliest_finish[p])) + [node]
    return max(earliest_finish.values()), backtrack(end_node), exp_dur, earliest_finish

def export_to_excel(activities, durations, pert_dur, crit_path, sl, unit):
    output = BytesIO()
    mean_dur = float(np.mean(durations))
    std_dur  = float(np.std(durations))
    sl_val   = float(np.percentile(durations, sl))

    wb = xlsxwriter.Workbook(output, {"in_memory": True})

    title_fmt  = wb.add_format({"bold": True, "font_size": 16, "font_color": "#4f46e5", "bottom": 2, "bottom_color": "#4f46e5"})
    hdr_fmt    = wb.add_format({"bold": True, "bg_color": "#4f46e5", "font_color": "#ffffff", "font_size": 12, "border": 1, "align": "center"})
    cell_fmt   = wb.add_format({"font_size": 11, "border": 1, "border_color": "#dde1f0"})
    num_fmt    = wb.add_format({"font_size": 11, "border": 1, "border_color": "#dde1f0", "num_format": "0.00", "align": "center"})
    hi_fmt     = wb.add_format({"font_size": 11, "border": 1, "bg_color": "#fef2f2", "font_color": "#dc2626", "bold": True})
    ml_fmt     = wb.add_format({"bold": True, "font_size": 12, "bg_color": "#eef2ff", "border": 1})
    mv_fmt     = wb.add_format({"font_size": 12, "border": 1, "num_format": "0.00", "font_color": "#4f46e5", "bold": True})
    red_fmt    = wb.add_format({"font_size": 11, "border": 1, "font_color": "#dc2626", "bold": True})

    # Sheet 1: Summary
    ws1 = wb.add_worksheet("Summary")
    ws1.set_column("A:A", 34); ws1.set_column("B:B", 22)
    ws1.write("A1", "ProjectPERT — Simulation Summary", title_fmt)
    ws1.write("A2", f"Time unit: {unit}")
    for i, (lbl, val) in enumerate([
        ("Mean Project Duration", mean_dur),
        ("Std Deviation", std_dur),
        (f"{sl}% Service Level Duration", sl_val),
        ("PERT Expected Duration", pert_dur),
    ], start=3):
        ws1.write(i, 0, lbl, ml_fmt)
        ws1.write(i, 1, val, mv_fmt)
    ws1.write(7, 0, "Critical Path", ml_fmt)
    ws1.write(7, 1, " > ".join(crit_path), red_fmt)

    # Sheet 2: Activities
    ws2 = wb.add_worksheet("Activities")
    ws2.set_column("A:A", 8); ws2.set_column("B:B", 28); ws2.set_column("C:C", 22); ws2.set_column("D:I", 14)
    for col, h in enumerate(["Label","Activity","Predecessors",f"Min ({unit})",f"Avg ({unit})",f"Max ({unit})","PERT Mean","Std Dev","Critical"]):
        ws2.write(0, col, h, hdr_fmt)
    for row, (lbl, info) in enumerate(activities.items(), start=1):
        mu  = pert_mean(info["min"], info["avg"], info["max"])
        sig = pert_std(info["min"], info["max"])
        fmt = hi_fmt if lbl in crit_path else cell_fmt
        ws2.write(row, 0, lbl, fmt)
        ws2.write(row, 1, info["name"], fmt)
        ws2.write(row, 2, ", ".join(info["predecessors"]) or "-", fmt)
        ws2.write(row, 3, info["min"], num_fmt)
        ws2.write(row, 4, info["avg"], num_fmt)
        ws2.write(row, 5, info["max"], num_fmt)
        ws2.write(row, 6, round(mu, 2), num_fmt)
        ws2.write(row, 7, round(sig, 2), num_fmt)
        ws2.write(row, 8, "YES" if lbl in crit_path else "", fmt)

    # Sheet 3: Simulation Data (capped at 5000 rows)
    ws3 = wb.add_worksheet("Simulation Data")
    ws3.set_column("A:B", 20)
    ws3.write(0, 0, "Simulation #", hdr_fmt)
    ws3.write(0, 1, f"Duration ({unit})", hdr_fmt)
    for i, val in enumerate(durations[:5000], start=1):
        ws3.write(i, 0, i, cell_fmt)
        ws3.write(i, 1, round(float(val), 4), num_fmt)

    # Sheet 4: Histogram with chart
    ws4 = wb.add_worksheet("Histogram")
    ws4.set_column("A:B", 22)
    ws4.write(0, 0, f"Duration Bin ({unit})", hdr_fmt)
    ws4.write(0, 1, "Frequency", hdr_fmt)
    counts, bin_edges = np.histogram(durations, bins=40)
    for i, (count, edge) in enumerate(zip(counts, bin_edges), start=1):
        ws4.write(i, 0, round(float(edge), 2), num_fmt)
        ws4.write(i, 1, int(count), cell_fmt)
    chart = wb.add_chart({"type": "column"})
    chart.add_series({
        "name": "Frequency",
        "categories": ["Histogram", 1, 0, len(counts), 0],
        "values":     ["Histogram", 1, 1, len(counts), 1],
        "fill": {"color": "#6366f1"}, "border": {"color": "#ffffff"},
    })
    chart.set_title({"name": "Project Duration Distribution"})
    chart.set_x_axis({"name": f"Duration ({unit})"})
    chart.set_y_axis({"name": "Frequency"})
    chart.set_style(10)
    ws4.insert_chart("D2", chart, {"x_scale": 1.8, "y_scale": 1.5})

    wb.close()
    output.seek(0)
    return output

# Session state
if "activities" not in st.session_state:
    st.session_state.activities = {
        "A": {"name": "Design",                "predecessors": [],        "min": 16, "avg": 21, "max": 26},
        "B": {"name": "Build prototype",       "predecessors": ["A"],     "min": 3,  "avg": 6,  "max": 9},
        "C": {"name": "Evaluate equipment",    "predecessors": ["A"],     "min": 5,  "avg": 7,  "max": 9},
        "D": {"name": "Test prototype",        "predecessors": ["B"],     "min": 2,  "avg": 3,  "max": 4},
        "E": {"name": "Write equipment report","predecessors": ["C","D"], "min": 4,  "avg": 6,  "max": 8},
        "F": {"name": "Write methods report",  "predecessors": ["C","D"], "min": 6,  "avg": 8,  "max": 10},
        "G": {"name": "Write final report",    "predecessors": ["E","F"], "min": 1,  "avg": 2,  "max": 3},
    }
if "results"   not in st.session_state: st.session_state.results   = None
if "time_unit" not in st.session_state: st.session_state.time_unit = "Weeks"

# Hero
st.markdown('''<div class="hero">
  <div class="hero-title">ProjectPERT</div>
  <p class="hero-sub">Monte Carlo · Critical Path · Duration Forecaster</p>
</div>''', unsafe_allow_html=True)

left_col, right_col = st.columns([1.1, 1.9], gap="large")

with left_col:
    st.markdown('<div class="section-label">Activity Network</div>', unsafe_allow_html=True)
    time_unit = st.selectbox("Time Unit", UNIT_OPTIONS, index=UNIT_OPTIONS.index(st.session_state.time_unit))
    st.session_state.time_unit = time_unit
    acts = st.session_state.activities
    rows = [{"Label": l, "Activity": i["name"], "Predecessors": ", ".join(i["predecessors"]) or "-",
             f"Min ({time_unit})": i["min"], f"Avg ({time_unit})": i["avg"], f"Max ({time_unit})": i["max"]}
            for l, i in acts.items()]
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.markdown("---")

    with st.expander("Add / Edit an Activity"):
        existing_labels = list(acts.keys())
        new_label = st.text_input("Label (e.g. H)", max_chars=5, placeholder="H").strip().upper()
        new_name  = st.text_input("Activity name", placeholder="e.g. User testing")
        selected_preds = st.multiselect("Immediate predecessors", options=[l for l in existing_labels if l != new_label])
        c1, c2, c3 = st.columns(3)
        with c1: new_min = st.number_input(f"Min ({time_unit})", min_value=0, value=1)
        with c2: new_avg = st.number_input(f"Avg ({time_unit})", min_value=0, value=3)
        with c3: new_max = st.number_input(f"Max ({time_unit})", min_value=0, value=5)
        if st.button("Save Activity"):
            if not new_label: st.error("Please enter a label.")
            elif new_min > new_avg or new_avg > new_max: st.error("Need: Min <= Avg <= Max")
            elif not new_name: st.error("Please enter an activity name.")
            else:
                st.session_state.activities[new_label] = {"name": new_name, "predecessors": selected_preds, "min": new_min, "avg": new_avg, "max": new_max}
                st.session_state.results = None
                st.rerun()

    with st.expander("Remove an Activity"):
        to_remove = st.selectbox("Select activity to remove", options=["--"] + list(acts.keys()))
        if st.button("Remove") and to_remove != "--":
            del st.session_state.activities[to_remove]
            for a in st.session_state.activities:
                st.session_state.activities[a]["predecessors"] = [p for p in st.session_state.activities[a]["predecessors"] if p != to_remove]
            st.session_state.results = None
            st.rerun()

    if st.button("Reset to Example Project"):
        del st.session_state["activities"]
        st.session_state.results = None
        st.rerun()

    st.markdown("---")
    st.markdown('<div class="section-label">Simulation Settings</div>', unsafe_allow_html=True)
    n_sim = st.select_slider("Monte Carlo iterations", options=[1_000, 5_000, 10_000, 50_000, 100_000], value=10_000, format_func=lambda x: f"{x:,}")
    service_level = st.slider("Service level (%)", min_value=50, max_value=99, value=95, step=1)
    run_btn = st.button("Run Simulation", use_container_width=True)

with right_col:
    if run_btn:
        with st.spinner("Running simulation..."):
            durations = simulate_project(st.session_state.activities, n_simulations=n_sim)
            pert_dur, crit_path, exp_durs, ef = compute_pert_critical_path(st.session_state.activities)
            st.session_state.results = {"durations": durations, "pert_dur": pert_dur, "crit_path": crit_path, "service_level": service_level}

    if st.session_state.results:
        res      = st.session_state.results
        durations = res["durations"]
        sl        = res["service_level"]
        unit      = st.session_state.time_unit
        mean_dur  = np.mean(durations)
        std_dur   = np.std(durations)
        sl_val    = np.percentile(durations, sl)

        st.markdown('<div class="section-label">Forecast Results</div>', unsafe_allow_html=True)
        st.markdown(f'''<div class="metric-row">
          <div class="metric-tile"><div class="metric-val">{mean_dur:.1f}</div><div class="metric-lbl">Mean Duration ({unit})</div></div>
          <div class="metric-tile"><div class="metric-val">{std_dur:.1f}</div><div class="metric-lbl">Std Deviation</div></div>
          <div class="metric-tile"><div class="metric-val">{sl_val:.1f}</div><div class="metric-lbl">{sl}% Service Level ({unit})</div></div>
          <div class="metric-tile"><div class="metric-val">{res["pert_dur"]:.1f}</div><div class="metric-lbl">PERT Expected ({unit})</div></div>
        </div>''', unsafe_allow_html=True)

        acts_ref = st.session_state.activities
        path_str = " > ".join(f"{l} ({acts_ref[l]['name']})" for l in res["crit_path"])
        st.markdown(f'''<div class="card"><div class="section-label">Critical Path</div>
          <div style="font-size:1.15rem;color:#dc2626;line-height:2.1;">{path_str}</div></div>''', unsafe_allow_html=True)

        st.markdown('<div class="section-label">Duration Distribution</div>', unsafe_allow_html=True)
        fig, ax = plt.subplots(figsize=(9, 4))
        fig.patch.set_facecolor("#ffffff")
        ax.set_facecolor("#f8f9ff")
        n_bins = min(60, int(np.sqrt(len(durations))))
        counts, bin_edges, patches = ax.hist(durations, bins=n_bins, color="#6366f1", edgecolor="#ffffff", linewidth=0.4, alpha=0.85)
        for patch, left in zip(patches, bin_edges[:-1]):
            if left >= sl_val:
                patch.set_facecolor("#ef4444"); patch.set_alpha(0.8)
        ax.axvline(mean_dur, color="#4f46e5", linewidth=2, linestyle="--", label=f"Mean: {mean_dur:.1f}")
        ax.axvline(sl_val,   color="#dc2626", linewidth=2, linestyle=":",  label=f"{sl}th pct: {sl_val:.1f}")
        ax.set_xlabel(f"Project Duration ({unit})", color="#555", fontsize=14)
        ax.set_ylabel("Frequency", color="#555", fontsize=14)
        ax.tick_params(colors="#555", labelsize=13)
        for spine in ax.spines.values(): spine.set_edgecolor("#dde1f0")
        ax.legend(facecolor="#ffffff", edgecolor="#dde1f0", labelcolor="#333", fontsize=13)
        fig.tight_layout(pad=1.5)
        st.pyplot(fig)
        plt.close(fig)

        st.markdown('<div class="section-label">PERT Activity Breakdown</div>', unsafe_allow_html=True)
        breakdown = [{"Label": lbl, "Activity": info["name"],
                      f"PERT Mean ({unit})": round(pert_mean(info["min"], info["avg"], info["max"]), 2),
                      "Std Dev": round(pert_std(info["min"], info["max"]), 2),
                      "Critical": "YES" if lbl in res["crit_path"] else ""}
                     for lbl, info in acts_ref.items()]
        st.dataframe(pd.DataFrame(breakdown), use_container_width=True, hide_index=True)

        st.markdown(f'''<div class="card" style="margin-top:1rem;">
          <div class="section-label">Interpretation</div>
          <p style="color:#333;font-size:1.15rem;line-height:1.9;margin:0">
            Based on <strong style="color:#4f46e5">{n_sim:,}</strong> simulations, the project is expected to take
            <strong style="color:#4f46e5">{mean_dur:.1f} {unit.lower()}</strong> on average.
            For a <strong style="color:#dc2626">{sl}% service level</strong>, plan for
            <strong style="color:#dc2626">{sl_val:.1f} {unit.lower()}</strong>.
            Critical path: <strong style="color:#dc2626">{" > ".join(res["crit_path"])}</strong>.
          </p></div>''', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<div class="section-label">Export Results</div>', unsafe_allow_html=True)
        try:
            excel_data = export_to_excel(acts_ref, durations, res["pert_dur"], res["crit_path"], sl, unit)
            st.download_button(
                label="Download Excel Report",
                data=excel_data,
                file_name="projectpert_results.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
            )
        except Exception as e:
            st.error(f"Export error: {e}")

    else:
        st.markdown('''<div style="height:420px;display:flex;flex-direction:column;align-items:center;justify-content:center;
            border:2px dashed #c7cce8;border-radius:14px;background:#ffffff;text-align:center;gap:1rem;">
          <div style="font-size:3.5rem;">📊</div>
          <div style="font-size:1.2rem;color:#999;">Configure activities on the left<br>then click Run Simulation</div>
        </div>''', unsafe_allow_html=True)
