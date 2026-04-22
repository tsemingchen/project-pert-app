import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from scipy import stats
import io

# ─────────────────────────────────────────────
# Page config
# ─────────────────────────────────────────────
st.set_page_config(
    page_title="Miller Construction – RFP Bid Analyzer",
    page_icon="🏗️",
    layout="wide",
)

# ─────────────────────────────────────────────
# Custom CSS
# ─────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background: #f4f6f9; }
    .main-title {
        background: linear-gradient(135deg, #1a3a5c 0%, #2e6da4 100%);
        color: white; padding: 1.6rem 2rem; border-radius: 12px;
        margin-bottom: 1.5rem;
    }
    .main-title h1 { margin: 0; font-size: 2rem; }
    .main-title p  { margin: 0.3rem 0 0; opacity: 0.85; font-size: 1rem; }
    .metric-card {
        background: white; border-radius: 10px; padding: 1.2rem 1.4rem;
        box-shadow: 0 2px 8px rgba(0,0,0,.08); text-align: center;
    }
    .metric-card .val { font-size: 1.8rem; font-weight: 700; color: #1a3a5c; }
    .metric-card .lbl { font-size: 0.82rem; color: #666; margin-top: 0.2rem; }
    .section-header {
        border-left: 4px solid #2e6da4; padding-left: 0.8rem;
        font-size: 1.15rem; font-weight: 700; color: #1a3a5c;
        margin: 1.4rem 0 0.8rem;
    }
    .info-box {
        background: #e8f0fb; border-radius: 8px; padding: 0.9rem 1.1rem;
        font-size: 0.88rem; color: #1a3a5c; margin-bottom: 0.7rem;
    }
    .warn-box {
        background: #fff8e1; border-radius: 8px; padding: 0.9rem 1.1rem;
        font-size: 0.88rem; color: #7a5800; margin-bottom: 0.7rem;
    }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Header
# ─────────────────────────────────────────────
st.markdown("""
<div class="main-title">
  <h1>🏗️ Miller Construction – RFP Bid Analyzer</h1>
  <p>Monte Carlo simulation tool for competitive bidding strategy</p>
</div>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────
# Sidebar – data upload & simulation settings
# ─────────────────────────────────────────────
with st.sidebar:
    st.title("🏗️ Configuration")

    st.markdown("### 📂 Historical Cost Data")
    uploaded = st.file_uploader(
        "Upload project_costs CSV", type=["csv"],
        help="CSV with columns: 'Bid Preparation Costs' and 'Total Project Costs (exluding bid preparation costs)'"
    )

    use_default = st.checkbox("Use built-in Miller dataset", value=True)

    st.markdown("---")

    optimistic = st.toggle("🌟 Optimistic Scenario", value=False,
                           help="Competitors bid near their max, uncertain competitors less likely to enter")
    if optimistic:
        st.markdown('<div style="background:#e6f4ea;border-radius:8px;padding:0.6rem 0.9rem;font-size:0.82rem;color:#1e5631;margin-bottom:0.5rem;">🌟 <b>Optimistic mode on:</b> competitors bid high, fewer likely to enter.</div>', unsafe_allow_html=True)

    st.markdown("### 🎯 Bid Strategy")
    miller_bid = st.number_input(
        "Miller's Bid Amount ($)", min_value=70_000, max_value=500_000,
        value=120_000, step=1_000,
        help="The amount Miller is considering submitting"
    )

    st.markdown("### 🏢 Competitor Settings")
    n_sims = st.selectbox("Number of simulations", [10_000, 50_000, 100_000], index=1)

    st.markdown("**Known competitor (always bids)**")
    comp1_min  = st.number_input("Min bid ($)",         value=90_000,  step=1_000, key="c1min")
    comp1_mode = st.number_input("Most likely bid ($)", value=160_000 if optimistic else 130_000, step=1_000, key="c1mode")
    comp1_max  = st.number_input("Max bid ($)",         value=180_000, step=1_000, key="c1max")

    st.markdown("**Two uncertain competitors (each 50% chance)**")
    default_prob = 25 if optimistic else 50
    comp2_prob = st.slider("Probability each enters (%)", 0, 100, default_prob, key="c2prob") / 100
    comp2_min  = st.number_input("Min bid ($)",         value=90_000,  step=1_000, key="c2min")
    comp2_mode = st.number_input("Most likely bid ($)", value=160_000 if optimistic else 130_000, step=1_000, key="c2mode")
    comp2_max  = st.number_input("Max bid ($)",         value=180_000, step=1_000, key="c2max")

    st.markdown("---")
    st.markdown("### 📊 Sweep Analysis")
    sweep_min  = st.number_input("Sweep from ($)", value=90_000,  step=5_000)
    sweep_max  = st.number_input("Sweep to ($)",   value=180_000, step=5_000)
    sweep_step = st.number_input("Step size ($)",  value=5_000,   step=1_000)

    run_btn = st.button("▶ Run Simulation", type="primary", use_container_width=True)

# ─────────────────────────────────────────────
# Load & fit historical data
# ─────────────────────────────────────────────
BUILTIN_CSV = """\
Bid Preparation Costs,Total Project Costs (exluding bid preparation costs)
2622,95663
2054,111610
1143,103665
2884,97134
1913,90868
2899,106963
1961,148338
2049,93061
1750,100006
2684,123679
2870,99692
2775,124429
1841,100524
2850,103171
1812,120898
1959,103959
2667,166031
1816,116081
2267,94348
1034,100499
2023,130698
1570,111156
1778,119094
2810,111601
2933,92303
2642,111212
1691,136891
2549,88861
2579,91222
2792,125066
1140,93939
1080,130266
1463,105611
2134,117027
1368,88979
2827,114291
1436,115961
2063,92010
2645,102441
2448,113970
2115,109089
1841,99469
1867,111870
2230,138980
1247,104419
1311,123145
2933,119477
2559,97923
1074,95350
1922,135239
2279,96267
1927,106414
2404,148876
1289,95695
1320,146197
2181,92235
2600,140301
1339,101596
2577,98876
1904,101228
1308,97649
2911,108166
1584,147597
1282,107348
2689,101603
2820,89759
2633,108533
2937,92291
1689,120568
1404,140508
1805,126018
1917,124116
1206,151905
2508,124671
2925,121559
1360,108434
1254,108200
2583,126518
2815,85577
1588,107923
1278,133313
1036,105725
2271,98158
2650,89176
1529,106767
2335,119159
2185,107129
2319,113178
1861,102955
2214,124587
1723,133787
2443,119087
1058,130295
1076,89661
2298,110527
2839,131346
2157,90992
2617,97180
2474,141560
2056,116791
1341,108341
1632,109255
1976,95304
2485,124871
2737,121498
2256,96399
1682,108468
1725,126532
2497,98423
2121,97902
1807,187060
2906,112054
1178,120618
2238,98070
2947,101683
1462,84322
2593,136338
2108,103386
1493,146676
2462,94573
1264,105317
2995,107818
2251,113319
2241,91348
1283,92468
"""

@st.cache_data
def load_data(csv_bytes=None):
    if csv_bytes:
        df = pd.read_csv(io.BytesIO(csv_bytes))
    else:
        df = pd.read_csv(io.StringIO(BUILTIN_CSV))
    df.columns = [c.strip() for c in df.columns]
    bid_col  = [c for c in df.columns if "Bid" in c][0]
    cost_col = [c for c in df.columns if "Project" in c][0]
    df = df.rename(columns={bid_col: "bid_prep_cost", cost_col: "project_cost"})
    df["bid_prep_cost"] = pd.to_numeric(df["bid_prep_cost"], errors="coerce")
    df["project_cost"]  = pd.to_numeric(df["project_cost"],  errors="coerce")
    complete = df.dropna(subset=["bid_prep_cost", "project_cost"]).copy()
    return df, complete

if uploaded:
    df_all, df_complete = load_data(uploaded.read())
else:
    df_all, df_complete = load_data()

bid_prep_data = df_all["bid_prep_cost"].dropna().values
proj_cost_data = df_complete["project_cost"].values

# Fit lognormal to project costs (clamped at 70k)
log_costs = np.log(proj_cost_data)
mu_log, sigma_log = np.mean(log_costs), np.std(log_costs)

# Fit uniform-ish to bid prep costs using empirical distribution
bp_min, bp_max = bid_prep_data.min(), bid_prep_data.max()
bp_mean, bp_std = bid_prep_data.mean(), bid_prep_data.std()

# ─────────────────────────────────────────────
# Triangular helper
# ─────────────────────────────────────────────
def triangular_sample(low, mode, high, size):
    c = (mode - low) / (high - low)
    return np.random.triangular(low, mode, high, size=size)

# ─────────────────────────────────────────────
# Core simulation function
# ─────────────────────────────────────────────
def run_simulation(miller_bid, n_sims,
                   c1_min, c1_mode, c1_max,
                   c2_prob, c2_min, c2_mode, c2_max):
    rng = np.random
    
    # --- Miller's costs ---
    bid_prep  = rng.choice(bid_prep_data, size=n_sims, replace=True)
    proj_cost = np.maximum(70_000, np.exp(rng.normal(mu_log, sigma_log, n_sims)))

    # --- Competitor bids ---
    comp1_bids = triangular_sample(c1_min, c1_mode, c1_max, n_sims)
    
    comp2_enters = rng.random(n_sims) < c2_prob
    comp3_enters = rng.random(n_sims) < c2_prob
    comp2_bids = np.where(comp2_enters, triangular_sample(c2_min, c2_mode, c2_max, n_sims), np.inf)
    comp3_bids = np.where(comp3_enters, triangular_sample(c2_min, c2_mode, c2_max, n_sims), np.inf)

    competitor_min = np.minimum(np.minimum(comp1_bids, comp2_bids), comp3_bids)

    # --- Win / loss ---
    miller_wins = miller_bid < competitor_min

    # --- Profit when winning ---
    profit_if_win  = miller_bid - proj_cost - bid_prep
    profit_if_lose = -bid_prep                             # sunk cost

    profit = np.where(miller_wins, profit_if_win, profit_if_lose)

    win_rate     = miller_wins.mean()
    exp_profit   = profit.mean()
    med_profit   = np.median(profit)
    profit_win   = profit_if_win                           # distribution when win
    prob_loss_if_win = (profit_if_win < 0).mean()

    return {
        "win_rate":         win_rate,
        "exp_profit":       exp_profit,
        "med_profit":       med_profit,
        "profit":           profit,
        "profit_if_win":    profit_if_win,
        "proj_cost":        proj_cost,
        "bid_prep":         bid_prep,
        "miller_wins":      miller_wins,
        "prob_loss_if_win": prob_loss_if_win,
        "competitor_min":   competitor_min,
        "n_sims":           n_sims,
    }

def sweep_bids(bid_range, n_sims, c1_min, c1_mode, c1_max, c2_prob, c2_min, c2_mode, c2_max):
    rows = []
    for b in bid_range:
        r = run_simulation(b, n_sims, c1_min, c1_mode, c1_max, c2_prob, c2_min, c2_mode, c2_max)
        rows.append({
            "Bid": b,
            "Win Rate (%)": round(r["win_rate"]*100, 2),
            "Exp. Profit ($)": round(r["exp_profit"], 0),
            "Median Profit ($)": round(r["med_profit"], 0),
            "P(loss | win) (%)": round(r["prob_loss_if_win"]*100, 2),
        })
    return pd.DataFrame(rows)

# ─────────────────────────────────────────────
# Tabs
# ─────────────────────────────────────────────
tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Historical Data", "🎲 Simulation Results", "📈 Bid Sweep", "📋 Summary Table"
])

# ══════════════════════════════════════════════
# TAB 1 – Historical Data
# ══════════════════════════════════════════════
with tab1:
    st.markdown('<div class="section-header">Historical Data Overview</div>', unsafe_allow_html=True)
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"""<div class="metric-card">
            <div class="val">{len(df_all)}</div>
            <div class="lbl">Total Historical Bids</div></div>""", unsafe_allow_html=True)
    with col2:
        st.markdown(f"""<div class="metric-card">
            <div class="val">{len(df_complete)}</div>
            <div class="lbl">Projects Won (w/ costs)</div></div>""", unsafe_allow_html=True)
    with col3:
        st.markdown(f"""<div class="metric-card">
            <div class="val">${proj_cost_data.mean():,.0f}</div>
            <div class="lbl">Avg Project Cost</div></div>""", unsafe_allow_html=True)
    with col4:
        st.markdown(f"""<div class="metric-card">
            <div class="val">${bid_prep_data.mean():,.0f}</div>
            <div class="lbl">Avg Bid Prep Cost</div></div>""", unsafe_allow_html=True)

    fig, axes = plt.subplots(1, 3, figsize=(15, 4))
    fig.patch.set_facecolor("#f4f6f9")
    palette = "#2e6da4"

    # Project cost histogram
    axes[0].hist(proj_cost_data, bins=25, color=palette, edgecolor="white", linewidth=0.5)
    axes[0].set_title("Project Completion Costs\n(won projects)", fontweight="bold")
    axes[0].set_xlabel("Cost ($)")
    axes[0].set_ylabel("Frequency")
    axes[0].xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x/1000:.0f}k"))
    axes[0].set_facecolor("#fafbfc")

    # Bid prep histogram
    axes[1].hist(bid_prep_data, bins=25, color="#e07b39", edgecolor="white", linewidth=0.5)
    axes[1].set_title("Bid Preparation Costs\n(all bids)", fontweight="bold")
    axes[1].set_xlabel("Cost ($)")
    axes[1].set_ylabel("Frequency")
    axes[1].xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:,.0f}"))
    axes[1].set_facecolor("#fafbfc")

    # Lognormal fit overlay
    x_fit = np.linspace(proj_cost_data.min(), proj_cost_data.max(), 300)
    pdf_fit = stats.lognorm.pdf(x_fit, s=sigma_log, scale=np.exp(mu_log))
    ax3tw = axes[2].twinx()
    axes[2].hist(proj_cost_data, bins=25, color=palette, edgecolor="white",
                 linewidth=0.5, density=True, alpha=0.6, label="Empirical")
    axes[2].plot(x_fit, pdf_fit, color="#c0392b", linewidth=2, label="Lognormal fit")
    axes[2].set_title("Lognormal Fit to\nProject Costs", fontweight="bold")
    axes[2].set_xlabel("Cost ($)")
    axes[2].xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x/1000:.0f}k"))
    axes[2].legend(fontsize=8)
    axes[2].set_facecolor("#fafbfc")

    plt.tight_layout()
    st.pyplot(fig, use_container_width=True)

    st.markdown('<div class="section-header">Statistical Summary</div>', unsafe_allow_html=True)
    col_a, col_b = st.columns(2)
    with col_a:
        st.caption("**Project Completion Costs (won bids)**")
        st.dataframe(pd.DataFrame({
            "Statistic": ["Count","Mean","Median","Std Dev","Min","Max","P10","P90"],
            "Value": [
                f"{len(proj_cost_data)}",
                f"${proj_cost_data.mean():,.0f}",
                f"${np.median(proj_cost_data):,.0f}",
                f"${proj_cost_data.std():,.0f}",
                f"${proj_cost_data.min():,.0f}",
                f"${proj_cost_data.max():,.0f}",
                f"${np.percentile(proj_cost_data,10):,.0f}",
                f"${np.percentile(proj_cost_data,90):,.0f}",
            ]
        }), hide_index=True, use_container_width=True)
    with col_b:
        st.caption("**Bid Preparation Costs (all historical bids)**")
        st.dataframe(pd.DataFrame({
            "Statistic": ["Count","Mean","Median","Std Dev","Min","Max","P10","P90"],
            "Value": [
                f"{len(bid_prep_data)}",
                f"${bid_prep_data.mean():,.0f}",
                f"${np.median(bid_prep_data):,.0f}",
                f"${bid_prep_data.std():,.0f}",
                f"${bid_prep_data.min():,.0f}",
                f"${bid_prep_data.max():,.0f}",
                f"${np.percentile(bid_prep_data,10):,.0f}",
                f"${np.percentile(bid_prep_data,90):,.0f}",
            ]
        }), hide_index=True, use_container_width=True)

    with st.expander("📄 View Raw Data"):
        st.dataframe(df_all, use_container_width=True)

# ══════════════════════════════════════════════
# TAB 2 – Simulation Results
# ══════════════════════════════════════════════
with tab2:
    if not run_btn:
        st.markdown('<div class="info-box">👈 Configure settings in the sidebar and click <b>Run Simulation</b> to see results.</div>', unsafe_allow_html=True)
    else:
        if optimistic:
            st.markdown('<div style="background:#e6f4ea;border-radius:8px;padding:0.7rem 1rem;font-size:0.9rem;color:#1e5631;margin-bottom:1rem;">🌟 <b>Optimistic Scenario active</b> — competitors bidding near their maximum ($160k most likely), uncertain competitors only 25% likely to enter.</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div style="background:#e8f0fb;border-radius:8px;padding:0.7rem 1rem;font-size:0.9rem;color:#1a3a5c;margin-bottom:1rem;">📊 <b>Base Scenario</b> — competitors most likely at $130k, uncertain competitors 50% likely to enter.</div>', unsafe_allow_html=True)

        with st.spinner(f"Running {n_sims:,} simulations…"):
            res = run_simulation(
                miller_bid, n_sims,
                comp1_min, comp1_mode, comp1_max,
                comp2_prob, comp2_min, comp2_mode, comp2_max
            )

        st.markdown('<div class="section-header">Key Metrics</div>', unsafe_allow_html=True)
        c1, c2, c3, c4, c5 = st.columns(5)
        def mcard(col, val, lbl, color="#1a3a5c"):
            col.markdown(f"""<div class="metric-card">
                <div class="val" style="color:{color}">{val}</div>
                <div class="lbl">{lbl}</div></div>""", unsafe_allow_html=True)
        
        mcard(c1, f"${miller_bid:,.0f}", "Miller's Bid", "#2e6da4")
        mcard(c2, f"{res['win_rate']*100:.1f}%", "Win Probability",
              "#27ae60" if res['win_rate'] > 0.4 else "#e74c3c")
        mcard(c3, f"${res['exp_profit']:,.0f}", "Expected Profit",
              "#27ae60" if res['exp_profit'] > 0 else "#e74c3c")
        mcard(c4, f"${res['med_profit']:,.0f}", "Median Profit",
              "#27ae60" if res['med_profit'] > 0 else "#e74c3c")
        mcard(c5, f"{res['prob_loss_if_win']*100:.1f}%", "P(lose money | win bid)",
              "#e74c3c" if res['prob_loss_if_win'] > 0.15 else "#f39c12")

        st.markdown('<div class="section-header">Profit Distribution</div>', unsafe_allow_html=True)

        fig2, axes2 = plt.subplots(1, 2, figsize=(14, 4.5))
        fig2.patch.set_facecolor("#f4f6f9")

        # All outcomes
        wins_profit  = res["profit"][res["miller_wins"]]
        loses_profit = res["profit"][~res["miller_wins"]]
        axes2[0].hist(loses_profit, bins=30, color="#e74c3c", alpha=0.7,
                      label=f"Lost bid ({(~res['miller_wins']).mean()*100:.1f}%)", density=True)
        axes2[0].hist(wins_profit, bins=50, color="#27ae60", alpha=0.7,
                      label=f"Won bid ({res['win_rate']*100:.1f}%)", density=True)
        axes2[0].axvline(0, color="black", linestyle="--", linewidth=1.2, label="Break-even")
        axes2[0].axvline(res["exp_profit"], color="#2e6da4", linestyle="-", linewidth=1.5,
                         label=f"E[Profit] = ${res['exp_profit']:,.0f}")
        axes2[0].set_title("Profit Distribution – All Scenarios", fontweight="bold")
        axes2[0].set_xlabel("Profit ($)")
        axes2[0].xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x/1000:.0f}k"))
        axes2[0].legend(fontsize=8)
        axes2[0].set_facecolor("#fafbfc")

        # Profit conditional on winning
        axes2[1].hist(res["profit_if_win"], bins=50, color="#2e6da4", edgecolor="white",
                      linewidth=0.4, alpha=0.85)
        axes2[1].axvline(0, color="#e74c3c", linestyle="--", linewidth=1.5, label="Break-even")
        axes2[1].axvline(res["profit_if_win"].mean(), color="#f39c12", linewidth=1.5,
                         label=f"Mean = ${res['profit_if_win'].mean():,.0f}")
        p10 = np.percentile(res["profit_if_win"], 10)
        axes2[1].axvline(p10, color="#8e44ad", linewidth=1.5, linestyle=":",
                         label=f"P10 = ${p10:,.0f}")
        axes2[1].set_title("Profit Distribution | Miller Wins", fontweight="bold")
        axes2[1].set_xlabel("Profit ($)")
        axes2[1].xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x/1000:.0f}k"))
        axes2[1].legend(fontsize=8)
        axes2[1].set_facecolor("#fafbfc")

        plt.tight_layout()
        st.pyplot(fig2, use_container_width=True)

        # Percentile table
        percs = [5, 10, 25, 50, 75, 90, 95]
        perc_vals = np.percentile(res["profit"], percs)
        st.caption("**Profit Percentiles (all scenarios)**")
        st.dataframe(pd.DataFrame({
            "Percentile": [f"P{p}" for p in percs],
            "Profit": [f"${v:,.0f}" for v in perc_vals]
        }).T, hide_index=False, use_container_width=True)

        if res["exp_profit"] < 0:
            st.markdown(f'<div class="warn-box">⚠️ At a bid of <b>${miller_bid:,.0f}</b>, the expected profit is <b>negative</b>. Consider a higher bid.</div>', unsafe_allow_html=True)
        elif res["win_rate"] < 0.1:
            st.markdown(f'<div class="warn-box">⚠️ Win probability is only <b>{res["win_rate"]*100:.1f}%</b> – this bid is unlikely to win.</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════
# TAB 3 – Bid Sweep
# ══════════════════════════════════════════════
with tab3:
    if not run_btn:
        st.markdown('<div class="info-box">👈 Click <b>Run Simulation</b> in the sidebar first.</div>', unsafe_allow_html=True)
    else:
        bid_range = np.arange(sweep_min, sweep_max + sweep_step, sweep_step)
        with st.spinner(f"Sweeping {len(bid_range)} bid amounts…"):
            sweep_df = sweep_bids(
                bid_range, min(n_sims, 20_000),
                comp1_min, comp1_mode, comp1_max,
                comp2_prob, comp2_min, comp2_mode, comp2_max
            )

        best_idx   = sweep_df["Exp. Profit ($)"].idxmax()
        best_bid   = sweep_df.loc[best_idx, "Bid"]
        best_profit= sweep_df.loc[best_idx, "Exp. Profit ($)"]

        st.markdown(f'<div class="info-box">✅ <b>Optimal bid (max expected profit):</b> ${best_bid:,.0f} → Expected Profit = ${best_profit:,.0f}</div>', unsafe_allow_html=True)

        fig3, axes3 = plt.subplots(2, 2, figsize=(14, 9))
        fig3.patch.set_facecolor("#f4f6f9")

        def fmt_ax(ax, title, ylabel, xfmt=True):
            ax.set_title(title, fontweight="bold")
            ax.set_xlabel("Miller's Bid ($)")
            ax.set_ylabel(ylabel)
            if xfmt:
                ax.xaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x/1000:.0f}k"))
            ax.axvline(best_bid, color="#e74c3c", linestyle="--", linewidth=1.2,
                       label=f"Optimal ${best_bid:,.0f}")
            ax.axvline(miller_bid, color="#27ae60", linestyle="-.", linewidth=1.2,
                       label=f"Current ${miller_bid:,.0f}")
            ax.legend(fontsize=8)
            ax.set_facecolor("#fafbfc")

        axes3[0,0].plot(sweep_df["Bid"], sweep_df["Exp. Profit ($)"], color="#2e6da4", linewidth=2)
        axes3[0,0].fill_between(sweep_df["Bid"], sweep_df["Exp. Profit ($)"],
                                 alpha=0.15, color="#2e6da4")
        axes3[0,0].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x/1000:.0f}k"))
        fmt_ax(axes3[0,0], "Expected Profit vs. Bid Amount", "Expected Profit ($)")

        axes3[0,1].plot(sweep_df["Bid"], sweep_df["Win Rate (%)"], color="#27ae60", linewidth=2)
        axes3[0,1].set_ylabel("Win Rate (%)")
        fmt_ax(axes3[0,1], "Win Rate vs. Bid Amount", "Win Rate (%)", xfmt=True)
        axes3[0,1].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}%"))

        axes3[1,0].plot(sweep_df["Bid"], sweep_df["Median Profit ($)"], color="#8e44ad", linewidth=2)
        axes3[1,0].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x/1000:.0f}k"))
        fmt_ax(axes3[1,0], "Median Profit vs. Bid Amount", "Median Profit ($)")

        axes3[1,1].plot(sweep_df["Bid"], sweep_df["P(loss | win) (%)"], color="#e07b39", linewidth=2)
        axes3[1,1].set_ylabel("P(loss | win) (%)")
        fmt_ax(axes3[1,1], "Risk of Losing Money (if Win) vs. Bid", "P(loss | win) (%)", xfmt=True)
        axes3[1,1].yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"{x:.0f}%"))

        plt.tight_layout()
        st.pyplot(fig3, use_container_width=True)

# ══════════════════════════════════════════════
# TAB 4 – Summary Table
# ══════════════════════════════════════════════
with tab4:
    if not run_btn:
        st.markdown('<div class="info-box">👈 Click <b>Run Simulation</b> in the sidebar first.</div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="section-header">Bid Sweep Results Table</div>', unsafe_allow_html=True)

        styled = sweep_df.copy()
        styled["Bid"] = styled["Bid"].apply(lambda x: f"${x:,.0f}")
        styled["Exp. Profit ($)"] = styled["Exp. Profit ($)"].apply(lambda x: f"${x:,.0f}")
        styled["Median Profit ($)"] = styled["Median Profit ($)"].apply(lambda x: f"${x:,.0f}")

        st.dataframe(styled, hide_index=True, use_container_width=True)

        csv_out = sweep_df.to_csv(index=False).encode()
        st.download_button("⬇ Download Results CSV", csv_out,
                           "miller_bid_sweep.csv", "text/csv")

        st.markdown('<div class="section-header">Model Assumptions</div>', unsafe_allow_html=True)
        st.markdown(f"""
- **Project completion cost** sampled from a **lognormal distribution** fitted to {len(proj_cost_data)} historical won-project costs (μ={mu_log:.3f}, σ={sigma_log:.3f}), clamped at $70,000.
- **Bid preparation cost** sampled by bootstrapping from {len(bid_prep_data)} historical bid prep observations (mean ≈ ${bid_prep_data.mean():,.0f}).
- **Known competitor** always bids; bid drawn from Triangular({comp1_min:,.0f}, {comp1_mode:,.0f}, {comp1_max:,.0f}).
- **Two uncertain competitors** each independently enter with {comp2_prob*100:.0f}% probability; same triangular distribution if they enter.
- **Award rule**: lowest bid wins.
- **Profit** = Miller's bid − project cost − bid prep cost (if win); = −bid prep cost (if lose).
        """)
