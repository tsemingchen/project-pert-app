import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

st.set_page_config(
    page_title="✈️ Flight Revenue Simulator",
    page_icon="✈️",
    layout="wide",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', sans-serif;
    font-size: 16px;
}

.stApp { background: #f9fafb; color: #1a1f36; }
section[data-testid="stSidebar"] { display: none; }

/* All input labels bigger */
label, div[data-testid="stNumberInput"] label {
    font-size: 15px !important;
    font-weight: 600 !important;
    color: #374151 !important;
}

/* Number input boxes */
div[data-testid="stNumberInput"] input {
    font-size: 16px !important;
    border-radius: 8px !important;
    border: 1.5px solid #d1d5db !important;
    padding: 10px 12px !important;
    background: #ffffff !important;
}
div[data-testid="stNumberInput"] input:focus {
    border-color: #6b7280 !important;
    box-shadow: 0 0 0 3px rgba(107,114,128,0.12) !important;
}

.hero {
    background: #1e293b;
    border-radius: 16px;
    padding: 30px 40px;
    color: white;
    margin-bottom: 28px;
}
.hero h1 { font-size: 28px; font-weight: 800; margin: 0 0 6px 0; }
.hero p  { font-size: 16px; margin: 0; opacity: 0.65; }

.card {
    background: #ffffff;
    border-radius: 14px;
    padding: 24px 26px;
    margin-bottom: 18px;
    border: 1.5px solid #e5e7eb;
}
.card-title {
    font-size: 16px;
    font-weight: 700;
    color: #111827;
    margin-bottom: 18px;
    padding-bottom: 10px;
    border-bottom: 1.5px solid #f3f4f6;
}

.divider {
    border: none;
    border-top: 1px solid #f3f4f6;
    margin: 18px 0;
}

.kpi-card {
    background: #fff;
    border-radius: 12px;
    padding: 18px 14px;
    text-align: center;
    border: 1.5px solid #e5e7eb;
}
.kpi-label {
    font-size: 12px;
    font-weight: 700;
    color: #9ca3af;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 8px;
}
.kpi-value {
    font-size: 24px;
    font-weight: 800;
    color: #111827;
    line-height: 1;
}
.kpi-value.muted { color: #6b7280; }
.kpi-value.warn  { color: #b45309; }
.kpi-value.danger{ color: #991b1b; }

.badge-green {
    background: #f0fdf4;
    border: 1.5px solid #86efac;
    border-radius: 12px;
    padding: 16px 20px;
    font-size: 15px;
    color: #166534;
    line-height: 1.8;
    margin-bottom: 14px;
}
.badge-yellow {
    background: #fffbeb;
    border: 1.5px solid #fcd34d;
    border-radius: 12px;
    padding: 16px 20px;
    font-size: 15px;
    color: #92400e;
    line-height: 1.8;
    margin-bottom: 14px;
}
.note {
    background: #f9fafb;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 13px;
    color: #6b7280;
    margin-top: 6px;
    line-height: 1.6;
}

.stButton > button {
    background: #1e293b;
    color: white !important;
    border: none;
    border-radius: 10px;
    padding: 14px 0;
    font-size: 16px !important;
    font-weight: 700;
    width: 100%;
    transition: all 0.15s;
}
.stButton > button:hover {
    background: #0f172a;
    transform: translateY(-1px);
}

.stTabs [data-baseweb="tab"] {
    font-size: 15px !important;
    font-weight: 600;
    color: #6b7280;
}
.stTabs [aria-selected="true"] {
    color: #111827 !important;
    border-bottom-color: #111827 !important;
}

p { font-size: 15px; line-height: 1.6; }

div[data-testid="stDataFrame"] th { font-size: 14px !important; font-weight: 700 !important; }
div[data-testid="stDataFrame"] td { font-size: 14px !important; }

/* Hide stepper arrows for cleaner look */
div[data-testid="stNumberInput"] button { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ── Simulation ────────────────────────────────────────────────────────────────
def run_sim(total_seats, total_tickets, bl_f2,
            fare1, fare2, ns1, ns2,
            f1_mu, f1_sd, f2_mu, f2_sd,
            vol_p, voucher, idb_c, n, seed=42):
    rng = np.random.default_rng(seed)
    f2d = np.clip(np.round(rng.normal(f2_mu, f2_sd, n)).astype(int), 0, None)
    f1d = np.clip(np.round(rng.normal(f1_mu, f1_sd, n)).astype(int), 0, None)
    f2s = np.minimum(f2d, bl_f2)
    f1s = np.minimum(f1d, np.maximum(total_tickets - f2s, 0))
    f2ns = rng.binomial(f2s, ns2);  f1ns = rng.binomial(f1s, ns1)
    f2sh = f2s - f2ns;              f1sh = f1s - f1ns
    ov  = np.maximum(f2sh + f1sh - total_seats, 0)
    vdb = np.where(ov > 0, np.minimum(rng.binomial(f2sh, vol_p), ov), 0)
    idb = np.maximum(ov - vdb, 0)
    profit = f2s*fare2 + f1s*fare1 - f1ns*fare1 - vdb*voucher - idb*idb_c
    return dict(profit=profit, f2_sold=f2s, f1_sold=f1s,
                f2_shows=f2sh, f1_shows=f1sh, overflow=ov,
                vdb=vdb, idb=idb, f1ns=f1ns,
                f2_rev=f2s*fare2, f1_rev=f1s*fare1, f1_refund=f1ns*fare1)

def chart_style(ax, title="", xlabel="", ylabel=""):
    ax.set_facecolor("#ffffff")
    for sp in ax.spines.values(): sp.set_edgecolor("#e5e7eb")
    ax.tick_params(colors="#6b7280", labelsize=11)
    ax.xaxis.label.set_color("#6b7280"); ax.xaxis.label.set_size(12)
    ax.yaxis.label.set_color("#6b7280"); ax.yaxis.label.set_size(12)
    ax.title.set_color("#111827"); ax.title.set_size(13); ax.title.set_weight("bold")
    if title:  ax.set_title(title)
    if xlabel: ax.set_xlabel(xlabel)
    if ylabel: ax.set_ylabel(ylabel)

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>✈️ Flight Revenue Simulator</h1>
    <p>Enter your flight parameters, find the best booking limit, and run a Monte Carlo simulation.</p>
</div>
""", unsafe_allow_html=True)

left, right = st.columns([1, 1.65], gap="large")

with left:

    # ── 1. Flight Setup ───────────────────────────────────────────
    st.markdown('<div class="card"><div class="card-title">🪑 Flight Setup</div>', unsafe_allow_html=True)
    c1, c2 = st.columns(2)
    with c1:
        total_seats   = st.number_input("Seats on the plane", min_value=50, max_value=400, value=150, step=1)
    with c2:
        total_tickets = st.number_input("Tickets to sell", min_value=50, max_value=500, value=162, step=1,
                                        help="Selling more than seats = overbooking")
    overbook = total_tickets - total_seats
    if overbook > 0:
        st.markdown(f'<div class="note">⚠️ Overbooking by <strong>{overbook}</strong> seats to offset no-shows.</div>', unsafe_allow_html=True)
    else:
        st.markdown(f'<div class="note">No overbooking.</div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── 2. Business Tickets ───────────────────────────────────────
    st.markdown('<div class="card"><div class="card-title">💼 Business Tickets — booked within 2 weeks of departure</div>', unsafe_allow_html=True)
    b1, b2 = st.columns(2)
    with b1: fare1_price = st.number_input("Price per ticket ($)", min_value=100, max_value=10000, value=1500, step=50, key="f1p")
    with b2: f1_noshow   = st.number_input("No-show rate (%)", min_value=0, max_value=100, value=15, step=1, key="f1ns",
                                            help="These passengers get a full refund")
    b3, b4 = st.columns(2)
    with b3: f1_mu = st.number_input("Average demand (passengers)", min_value=1, max_value=200, value=20, step=1, key="f1mu")
    with b4: f1_sd = st.number_input("Demand std deviation", min_value=1, max_value=100, value=5, step=1, key="f1sd")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── 3. Leisure Tickets ────────────────────────────────────────
    st.markdown('<div class="card"><div class="card-title">🏖️ Leisure Tickets — booked 2+ weeks before departure</div>', unsafe_allow_html=True)
    d1, d2 = st.columns(2)
    with d1: fare2_price = st.number_input("Price per ticket ($)", min_value=50, max_value=5000, value=500, step=50, key="f2p")
    with d2: f2_noshow   = st.number_input("No-show rate (%)", min_value=0, max_value=100, value=5, step=1, key="f2ns",
                                            help="No refund for these passengers")
    d3, d4 = st.columns(2)
    with d3: f2_mu = st.number_input("Average demand (passengers)", min_value=1, max_value=1000, value=200, step=1, key="f2mu")
    with d4: f2_sd = st.number_input("Demand std deviation", min_value=1, max_value=200, value=20, step=1, key="f2sd")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── 4. Overbooking Costs ──────────────────────────────────────
    with st.expander("⚙️ Overbooking cost settings"):
        e1, e2 = st.columns(2)
        with e1:
            vol_prob    = st.number_input("Volunteer probability (%)", 0, 100, 2, 1, key="vp",
                                          help="Chance a leisure passenger volunteers to give up their seat") 
            voucher_amt = st.number_input("Voucher for volunteers ($)", 0, 10000, 800, 100, key="vc")
        with e2:
            idb_amt = st.number_input("Cost of forced bump ($)", 0, 20000, 3000, 100, key="ic",
                                      help="$1,200 voucher + ~$1,800 estimated goodwill loss")
            st.markdown('<div class="note" style="margin-top:28px;">Forced bumps happen when not enough passengers volunteer.</div>', unsafe_allow_html=True)
        vol_prob_frac = vol_prob / 100
    # Defaults if expander never touched
    if 'vol_prob_frac' not in locals(): vol_prob_frac = 0.02
    if 'voucher_amt'   not in locals(): voucher_amt   = 800
    if 'idb_amt'       not in locals(): idb_amt       = 3000

    # ── 5. Booking Limit ──────────────────────────────────────────
    st.markdown('<div class="card"><div class="card-title">🎯 Booking Limit for Leisure Tickets</div>', unsafe_allow_html=True)
    st.markdown(
        '<p style="color:#6b7280;margin-bottom:16px;">The booking limit caps how many cheap leisure tickets you sell, '
        'saving the remaining slots for higher-paying business passengers.</p>',
        unsafe_allow_html=True
    )

    with st.spinner("Finding optimal booking limit..."):
        bl_range = range(max(0, total_tickets - 60), total_tickets + 1)
        scan_profits = []
        for bl in bl_range:
            r_q = run_sim(total_seats, total_tickets, bl,
                          fare1_price, fare2_price,
                          f1_noshow/100, f2_noshow/100,
                          f1_mu, f1_sd, f2_mu, f2_sd,
                          vol_prob_frac, voucher_amt, idb_amt, 3000)
            scan_profits.append(np.mean(r_q["profit"]))

    bl_arr  = np.array(list(bl_range))
    pf_arr  = np.array(scan_profits)
    best_bl = int(bl_arr[np.argmax(pf_arr)])
    best_pf = pf_arr[np.argmax(pf_arr)]

    st.markdown(f"""
    <div class="badge-green">
        ⭐ <strong>Recommended booking limit: {best_bl}</strong><br>
        Reserves <strong>{total_tickets - best_bl} seats</strong> for business passengers<br>
        Expected average profit: <strong>${best_pf:,.0f} per flight</strong>
    </div>
    """, unsafe_allow_html=True)

    # Profit curve chart
    fig_bl, ax_bl = plt.subplots(figsize=(6.5, 2.8))
    fig_bl.patch.set_facecolor("#ffffff")
    ax_bl.set_facecolor("#ffffff")
    for sp in ax_bl.spines.values(): sp.set_edgecolor("#e5e7eb")
    ax_bl.plot(bl_arr, pf_arr, color="#374151", lw=2)
    ax_bl.fill_between(bl_arr, pf_arr, alpha=0.06, color="#374151")
    ax_bl.axvline(best_bl, color="#374151", lw=1.5, ls="--")
    ax_bl.scatter([best_bl], [best_pf], color="#374151", s=60, zorder=5)
    ax_bl.set_xlabel("Booking limit (leisure tickets)", color="#9ca3af", fontsize=11)
    ax_bl.set_ylabel("Avg profit ($)", color="#9ca3af", fontsize=11)
    ax_bl.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"${x/1000:.0f}k"))
    ax_bl.tick_params(colors="#9ca3af", labelsize=10)
    ax_bl.set_title("Profit vs. Booking Limit — dashed line = recommended", color="#374151", fontsize=12)
    plt.tight_layout(pad=0.8)
    st.pyplot(fig_bl)
    plt.close()

    booking_limit = st.number_input(
        "Booking limit — enter a value (or keep the recommended one)",
        min_value=0, max_value=int(total_tickets), value=int(best_bl), step=1
    )

    reserved = total_tickets - booking_limit
    cur_idx  = np.argmin(np.abs(bl_arr - booking_limit))
    cur_pf   = pf_arr[cur_idx] if 0 <= cur_idx < len(pf_arr) else best_pf
    diff     = cur_pf - best_pf

    cc1, cc2 = st.columns(2)
    with cc1:
        st.markdown(f"""
        <div class="note">
            Leisure limit: <strong>{booking_limit}</strong><br>
            Saved for business: <strong>{reserved}</strong>
        </div>""", unsafe_allow_html=True)
    with cc2:
        badge_cls = "badge-green" if diff >= -1000 else "badge-yellow"
        arrow = "✅" if diff >= -1000 else "⚠️"
        st.markdown(f"""
        <div class="{badge_cls}" style="padding:10px 14px;font-size:14px;margin-bottom:0;">
            {arrow} Est. profit: <strong>${cur_pf:,.0f}</strong><br>
            vs best: {'+' if diff>=0 else ''}<strong>${diff:,.0f}</strong>
        </div>""", unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # ── 6. Simulations + Run ──────────────────────────────────────
    st.markdown('<div class="card"><div class="card-title">🎲 Run Simulation</div>', unsafe_allow_html=True)
    n_sims = st.number_input("Number of simulations", min_value=500, max_value=50000, value=10000, step=500,
                              help="More = more accurate, but slower. 10,000 is a good default.")
    st.markdown(f'<div class="note" style="margin-bottom:16px;">Each simulation models one flight. {n_sims:,} simulations gives a reliable estimate.</div>', unsafe_allow_html=True)
    run_btn = st.button("▶  Run Simulation")
    st.markdown('</div>', unsafe_allow_html=True)


# ── RIGHT COLUMN: Results ─────────────────────────────────────────────────────
with right:
    if "results" not in st.session_state:
        st.session_state.results = None

    if run_btn:
        with st.spinner("Running simulation..."):
            st.session_state.results = run_sim(
                total_seats, total_tickets, booking_limit,
                fare1_price, fare2_price,
                f1_noshow/100, f2_noshow/100,
                f1_mu, f1_sd, f2_mu, f2_sd,
                vol_prob_frac, voucher_amt, idb_amt, n_sims
            )
            st.session_state.cfg = dict(voucher=voucher_amt, idb=idb_amt)

    if st.session_state.results is None:
        st.markdown("""
        <div style="text-align:center;padding:120px 30px;">
            <div style="font-size:56px;margin-bottom:20px;opacity:0.2;">📊</div>
            <div style="font-size:18px;color:#9ca3af;font-weight:600;">
                Results appear here after you run the simulation
            </div>
            <div style="font-size:15px;color:#d1d5db;margin-top:8px;">
                Fill in the parameters on the left, then click Run Simulation
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        r   = st.session_state.results
        cfg = st.session_state.cfg
        p   = r["profit"]

        st.markdown("### Results")

        # KPI row
        kc = st.columns(3)
        kpis = [
            ("Average Profit / Flight", f"${np.mean(p):,.0f}", ""),
            ("Worst 5% of Flights",     f"${np.percentile(p,5):,.0f}", "danger"),
            ("Best 5% of Flights",      f"${np.percentile(p,95):,.0f}", "muted"),
        ]
        for col, (label, val, cls) in zip(kc, kpis):
            with col:
                st.markdown(f"""<div class="kpi-card">
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value {cls}">{val}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        kc2 = st.columns(3)
        kpis2 = [
            ("Avg Tickets Sold",        f"{np.mean(r['f2_sold']+r['f1_sold']):.1f}", "muted"),
            ("Avg Voluntary Bumps",     f"{np.mean(r['vdb']):.2f}", "warn"),
            ("Avg Forced Bumps",        f"{np.mean(r['idb']):.2f}", "danger"),
        ]
        for col, (label, val, cls) in zip(kc2, kpis2):
            with col:
                st.markdown(f"""<div class="kpi-card">
                    <div class="kpi-label">{label}</div>
                    <div class="kpi-value {cls}">{val}</div>
                </div>""", unsafe_allow_html=True)

        st.markdown("<br>", unsafe_allow_html=True)

        # Plain-English summary
        p_idb = np.mean(r['idb'] > 0) * 100
        badge = "badge-green" if p_idb < 5 else "badge-yellow"
        st.markdown(f"""
        <div class="{badge}">
            With these settings, the average flight earns <strong>${np.mean(p):,.0f}</strong>.
            There's a <strong>{p_idb:.1f}%</strong> chance of having to forcibly bump a passenger.
            On average, <strong>{np.mean(r['f1_sold']):.1f} business</strong> and
            <strong>{np.mean(r['f2_sold']):.1f} leisure</strong> tickets are sold per flight.
        </div>
        """, unsafe_allow_html=True)

        t1, t2, t3 = st.tabs(["Profit Distribution", "Tickets & Boarding", "Revenue Breakdown"])

        with t1:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
            fig.patch.set_facecolor("#f9fafb")

            chart_style(ax1, "Profit Distribution", "Profit ($)", "Number of simulations")
            ax1.hist(p, bins=70, color="#6b7280", alpha=0.6, edgecolor="white", lw=0.3)
            ax1.axvline(np.mean(p),           color="#111827", lw=2,   ls="--", label=f"Average: ${np.mean(p):,.0f}")
            ax1.axvline(np.percentile(p,  5), color="#9ca3af", lw=1.5, ls=":",  label=f"Worst 5%: ${np.percentile(p,5):,.0f}")
            ax1.axvline(np.percentile(p, 95), color="#9ca3af", lw=1.5, ls=":",  label=f"Best 5%: ${np.percentile(p,95):,.0f}")
            ax1.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"${x/1000:.0f}k"))
            ax1.legend(fontsize=11, framealpha=0.95)

            chart_style(ax2, "What % of flights earn this much or less?", "Profit ($)", "% of flights")
            sp = np.sort(p); cdf = np.arange(1, len(sp)+1)/len(sp)
            ax2.plot(sp, cdf, color="#374151", lw=2)
            ax2.fill_between(sp, 0, cdf, alpha=0.06, color="#374151")
            ax2.axhline(0.5, color="#9ca3af", lw=1.5, ls="--", label="50% of flights")
            ax2.xaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"${x/1000:.0f}k"))
            ax2.yaxis.set_major_formatter(mticker.PercentFormatter(1.0))
            ax2.legend(fontsize=11)
            ax2.grid(True, alpha=0.25, color="#e5e7eb")

            plt.tight_layout(pad=1.5)
            st.pyplot(fig)
            plt.close()

        with t2:
            fig, axes = plt.subplots(2, 3, figsize=(13, 8))
            fig.patch.set_facecolor("#f9fafb")
            items = [
                (r['f2_sold'],                "#9ca3af", "Leisure Tickets Sold"),
                (r['f1_sold'],                "#6b7280", "Business Tickets Sold"),
                (r['f2_shows']+r['f1_shows'], "#4b5563", "Passengers Who Show Up"),
                (r['overflow'],               "#d1d5db", "Passengers Over Seat Limit"),
                (r['vdb'],                    "#9ca3af", "Voluntary Bumps"),
                (r['idb'],                    "#6b7280", "Forced Bumps"),
            ]
            for ax, (data, color, title) in zip(axes.flat, items):
                chart_style(ax, title, "Count", "Simulations")
                ax.hist(data, bins=40, color=color, alpha=0.85, edgecolor="white", lw=0.2)
                ax.axvline(np.mean(data), color="#111827", lw=1.8, ls="--",
                           label=f"Avg: {np.mean(data):.1f}")
                ax.legend(fontsize=10, framealpha=0.9)
            plt.tight_layout(pad=2)
            st.pyplot(fig)
            plt.close()

        with t3:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(13, 5))
            fig.patch.set_facecolor("#f9fafb")

            chart_style(ax1, "Where Does the Money Go? (Per Flight Average)", "", "Amount ($)")
            labels = ["Leisure\nRevenue","Business\nRevenue","Business\nRefunds","Volunteer\nCost","Forced\nBump Cost","Net\nProfit"]
            vals   = [np.mean(r['f2_rev']), np.mean(r['f1_rev']),
                      -np.mean(r['f1_refund']),
                      -np.mean(r['vdb']*cfg['voucher']),
                      -np.mean(r['idb']*cfg['idb']),
                      np.mean(p)]
            bar_colors = ["#9ca3af","#6b7280","#d1d5db","#d1d5db","#9ca3af","#374151"]
            bars = ax1.bar(labels, vals, color=bar_colors, edgecolor="white", width=0.6)
            ax1.axhline(0, color="#e5e7eb", lw=1.5)
            ax1.yaxis.set_major_formatter(mticker.FuncFormatter(lambda x,_: f"${x/1000:.0f}k"))
            for bar, v in zip(bars, vals):
                ax1.text(bar.get_x()+bar.get_width()/2,
                         v + (400 if v>=0 else -4000),
                         f'${abs(v):,.0f}', ha='center', fontsize=10, color="#374151", fontweight="600")
            ax1.tick_params(axis='x', colors="#6b7280", labelsize=10)

            chart_style(ax2, "Revenue Split: Leisure vs Business", "", "")
            pie_vals   = [np.mean(r['f2_rev']), np.mean(r['f1_rev'])]
            pie_labels = [f"Leisure\n${np.mean(r['f2_rev']):,.0f}", f"Business\n${np.mean(r['f1_rev']):,.0f}"]
            wedges, texts, autotexts = ax2.pie(
                pie_vals, labels=pie_labels, colors=["#9ca3af","#4b5563"],
                autopct="%1.1f%%", startangle=90,
                textprops=dict(fontsize=13, color="#374151"),
                wedgeprops=dict(edgecolor="white", linewidth=2.5)
            )
            for at in autotexts: at.set_fontsize(13); at.set_fontweight("bold"); at.set_color("white")

            plt.tight_layout(pad=2)
            st.pyplot(fig)
            plt.close()

        st.markdown("---")
        st.markdown("#### Full Results Table")
        df = pd.DataFrame({
            "Metric": [
                "Leisure tickets sold", "Business tickets sold",
                "Leisure passengers show up", "Business passengers show up",
                "Total passengers show up", "Passengers over seat limit",
                "Voluntary bumps", "Forced bumps",
                "Revenue from leisure tickets", "Revenue from business tickets",
                "Business refunds paid", "Volunteer voucher costs",
                "Forced bump costs", "💰 Net profit"
            ],
            "Average per flight": [
                f"{np.mean(r['f2_sold']):.1f}", f"{np.mean(r['f1_sold']):.1f}",
                f"{np.mean(r['f2_shows']):.1f}", f"{np.mean(r['f1_shows']):.1f}",
                f"{np.mean(r['f2_shows']+r['f1_shows']):.1f}",
                f"{np.mean(r['overflow']):.2f}",
                f"{np.mean(r['vdb']):.2f}", f"{np.mean(r['idb']):.2f}",
                f"${np.mean(r['f2_rev']):,.0f}", f"${np.mean(r['f1_rev']):,.0f}",
                f"${np.mean(r['f1_refund']):,.0f}",
                f"${np.mean(r['vdb']*cfg['voucher']):,.0f}",
                f"${np.mean(r['idb']*cfg['idb']):,.0f}",
                f"${np.mean(p):,.0f}"
            ],
            "Std deviation": [
                f"{np.std(r['f2_sold']):.1f}", f"{np.std(r['f1_sold']):.1f}",
                f"{np.std(r['f2_shows']):.1f}", f"{np.std(r['f1_shows']):.1f}",
                f"{np.std(r['f2_shows']+r['f1_shows']):.1f}",
                f"{np.std(r['overflow']):.2f}",
                f"{np.std(r['vdb']):.2f}", f"{np.std(r['idb']):.2f}",
                f"${np.std(r['f2_rev']):,.0f}", f"${np.std(r['f1_rev']):,.0f}",
                f"${np.std(r['f1_refund']):,.0f}",
                f"${np.std(r['vdb']*cfg['voucher']):,.0f}",
                f"${np.std(r['idb']*cfg['idb']):,.0f}",
                f"${np.std(p):,.0f}"
            ],
        })
        st.dataframe(df, use_container_width=True, hide_index=True)
