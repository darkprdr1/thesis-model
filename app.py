import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.express as px
import plotly.graph_objects as go
import datetime
import io

# ---------------------------------------------
# 頁面設定
# ---------------------------------------------
st.set_page_config(
    page_title="新北市防災都更財務模型 (論文修正版)",
    page_icon="🏙️",
    layout="wide"
)

# ---------------------------------------------
# CSS 優化（黑金風格）
# ---------------------------------------------
st.markdown(
    """
<style>
    .stApp {
        background-color: #050505;
    }
    .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        max-width: 1200px;
    }
    h1, h2, h3, h4 {
        color: #f8f8f8;
    }
    .metric-card {
        background: #151515;
        border-radius: 14px;
        padding: 16px 18px;
        border: 1px solid #333333;
        box-shadow: 0 0 20px rgba(0,0,0,0.35);
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 46px;
        white-space: pre-wrap;
        background-color: #151515;
        color: #cccccc;
        border-radius: 10px 10px 0px 0px;
        border: 1px solid #333333;
        padding: 8px 14px;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #d4af37, #7a5c15);
        color: #050505 !important;
        border-color: #d4af37;
    }
    [data-testid="stMetricValue"] {
        color: #f8f8f8;
        font-weight: 700;
    }
    [data-testid="stMetricLabel"] {
        color: #bbbbbb;
        font-size: 0.9rem;
    }
    [data-testid="stMetricDelta"] {
        color: #d4af37 !important;
    }
</style>
""",
    unsafe_allow_html=True,
)

# ---------------------------------------------
# 標題
# ---------------------------------------------
st.title("🏙️ 新北市防災都更權利變換試算模型")
st.markdown("### 第三章｜混合研究法與參數建構實證")
st.info(
    "本模型依據專家訪談與文獻回饋調整：建材係數、風險費率查表、"
    "管理費結構拆分與 IRR 現金流模型。"
)

# ---------------------------------------------
# 側邊欄：參數設定
# ---------------------------------------------
st.sidebar.header("⚙️ 參數設定面板")

# ========== 1. 基地與容積 ==========
with st.sidebar.expander("1. 基地與容積參數", expanded=True):
    base_area = st.number_input("基地面積 (坪)", value=300.0, step=10.0)
    far_legal = st.number_input("法定容積率 (%)", value=200.0, step=10.0) / 100
    far_base_exist = st.number_input("原建築容積率 (%)", value=300.0, step=10.0) / 100
    bonus_multiplier = st.number_input("防災獎勵倍數", value=1.5, step=0.1)
    coeff_gfa = st.number_input("總樓地板係數 K_GFA", value=1.8, step=0.1)
    coeff_sale = st.number_input("銷售面積係數 K_Sale", value=1.6, step=0.1)

# ========== 2. 營建與建材 ==========
with st.sidebar.expander("2. 營建與建材設定", expanded=True):
    const_type = st.selectbox(
        "建材結構等級",
        ["RC 一般標準 (S0)", "RC 高階 (+0.11)", "SRC/SC (+0.30)"]
    )

    if "高階" in const_type:
        mat_coeff = 0.11
    elif "SRC" in const_type:
        mat_coeff = 0.30
    else:
        mat_coeff = 0.0

    base_unit_cost = st.number_input("營建基準單價 (萬/坪)", value=16.23, step=0.5)
    final_unit_cost = base_unit_cost * (1 + mat_coeff)

    st.caption(
        f"💡 修正後營建單價：{final_unit_cost:.2f} 萬/坪 "
        f"(建材係數 +{mat_coeff})"
    )

# ========== 3. 財務與風險 ==========
with st.sidebar.expander("3. 財務與風險參數", expanded=True):
    num_owners = st.number_input("產權人數 (人)", value=20, step=5)
    rate_personnel = (
        st.number_input("人事行政管理費率 (%)", value=3.0, step=0.5) / 100
    )
    rate_sales = (
        st.number_input("銷售管理費率 (%)", value=6.0, step=0.5) / 100
    )
    loan_ratio = st.slider("貸款成數 (%)", 40, 80, 60) / 100
    loan_rate = st.number_input("貸款年利率 (%)", value=3.0, step=0.1) / 100
    dev_months = st.number_input("開發期程 (月)", value=48, step=6)

# ========== 4. 進階費用 ==========
with st.sidebar.expander("4. 進階費用設定 (B/G/H 類)", expanded=False):
    cost_bonus_app = st.number_input("容積獎勵申請費 (萬)", value=500, step=50)
    cost_urban_plan = st.number_input("都計變更/審議費 (萬)", value=300, step=50)
    cost_transfer = st.number_input("容積移轉/折繳代金 (萬)", value=0, step=100)

# ========== 5. 估價與銷售 ==========
with st.sidebar.expander("5. 估價與銷售", expanded=False):
    val_old_total = (
        st.number_input("更新前現況總值 (億元)", value=5.4, step=0.1) * 10000
    )
    price_unit_sale = st.number_input(
        "更新後預售單價 (萬/坪)", value=60.0, step=2.0
    )
    price_parking = st.number_input("車位單價 (萬/個)", value=220, step=10)


# ---------------------------------------------
# 風險費率查表
# ---------------------------------------------
def get_risk_fee_rate(gfa_ping: float, owners: int) -> float:
    """
    風險管理費率查表邏輯（面積越小 / 人數越多，費率越高）
    """
    if gfa_ping < 3000 or owners > 50:
        return 0.14
    elif gfa_ping < 5000:
        return 0.13
    else:
        return 0.12


# ---------------------------------------------
# 核心計算模型
# ---------------------------------------------
def calculate_model():
    # 1. 面積計算
    area_far = base_area * far_base_exist * bonus_multiplier
    area_total = area_far * coeff_gfa
    area_sale = area_far * coeff_sale
    num_parking = int(area_total / 35)

    # 2. 工程費
    c_demo = base_area * 3 * 0.15
    c_build = area_total * final_unit_cost
    c_engineering = c_demo + c_build

    # 3. 進階費用
    c_advanced = cost_bonus_app + cost_urban_plan + cost_transfer

    # 4. 設計 / 安置
    c_design = c_build * 0.06
    c_reloc = c_build * 0.05

    # 5. 管理費
    rate_risk = get_risk_fee_rate(area_total, num_owners)
    c_mgmt_risk = c_build * rate_risk
    c_mgmt_personnel = c_build * rate_personnel
    c_mgmt_sales = (area_sale * price_unit_sale) * 0.05
    c_mgmt_total = c_mgmt_risk + c_mgmt_personnel + c_mgmt_sales

    # 6. 利息
    fund_demand = c_engineering + c_advanced + c_design + c_reloc
    c_interest = (
        fund_demand * loan_ratio * loan_rate * (dev_months / 12) * 0.5
    )

    # 7. 稅
    c_tax = c_build * 0.03

    # 8. 總成本
    c_total = (
        c_engineering
        + c_advanced
        + c_design
        + c_reloc
        + c_mgmt_total
        + c_interest
        + c_tax
    )

    # 9. 總銷價值
    val_parking_total = num_parking * price_parking
    val_new_total = (area_sale * price_unit_sale) + val_parking_total

    ratio_burden = c_total / val_new_total if val_new_total > 0 else 0
    ratio_landlord = 1 - ratio_burden

    # 10. IRR 現金流
    equity_ratio = 1 - loan_ratio
    initial_out = (c_advanced + c_design) + (
        c_engineering * equity_ratio * 0.1
    )
    yearly_cost = (c_engineering * equity_ratio * 0.9) / 3
    loan_repay = fund_demand * loan_ratio

    final_in = val_new_total - loan_repay - c_tax - c_mgmt_total - c_interest

    cashflow = [
        -initial_out,
        -yearly_cost,
        -yearly_cost,
        -yearly_cost,
        final_in,
    ]

    try:
        irr_val = float(npf.irr(cashflow))
    except Exception:
        irr_val = 0.0

    return {
        "GFA": area_total,
        "Total_Cost": c_total,
        "Total_Value": val_new_total,
        "Landlord_Ratio": ratio_landlord,
        "IRR": irr_val,
        "Risk_Rate": rate_risk,
        "Details": {
            "工程費(含拆除)": c_engineering,
            "風險管理費": c_mgmt_risk,
            "人事/銷售費": c_mgmt_personnel + c_mgmt_sales,
            "貸款利息": c_interest,
            "進階費用(獎勵/都計)": c_advanced,
            "其他(稅/設計/安置)": c_tax + c_design + c_reloc,
        },
        "Cashflow": {
            "T0": cashflow[0],
            "T1": cashflow[1],
            "T2": cashflow[2],
            "T3": cashflow[3],
            "T4": cashflow[4],
        },
        "Meta": {
            "area_far": area_far,
            "area_sale": area_sale,
            "num_parking": num_parking,
            "fund_demand": fund_demand,
        },
    }


# ---------------------------------------------
# 報告文字（TXT）
# ---------------------------------------------
def generate_txt_report(res: dict) -> str:
    cf = res["Cashflow"]

    lines = []
    lines.append("【新北市防災都更財務模型｜IRR 計算報告】")
    lines.append(
        f"產生時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    lines.append("------------------------------------------------------------\n")

    lines.append("【一、基地與容積參數】")
    lines.append(f"基地面積：{base_area:.2f} 坪")
    lines.append(f"原建築容積率：{far_base_exist*100:.1f}%")
    lines.append(f"防災獎勵倍數：{bonus_multiplier:.2f}")
    lines.append(f"總樓地板係數 K_GFA：{coeff_gfa:.2f}")
    lines.append(f"銷售面積係數 K_Sale：{coeff_sale:.2f}\n")

    lines.append("【二、營建與建材參數】")
    lines.append(f"建材等級：{const_type}")
    lines.append(f"基準單價：{base_unit_cost:.2f} 萬/坪")
    lines.append(f"修正後單價：{final_unit_cost:.2f} 萬/坪\n")

    lines.append("【三、財務與風險參數】")
    lines.append(f"產權人數：{num_owners:.0f} 人")
    lines.append(f"貸款成數：{loan_ratio*100:.0f}%")
    lines.append(f"貸款利率：{loan_rate*100:.2f}%")
    lines.append(f"工期（月）：{dev_months:.0f}")
    lines.append(f"風險管理費率（查表）：{res['Risk_Rate']*100:.1f}%\n")

    lines.append("【四、共同負擔成本明細（萬元）】")
    for k, v in res["Details"].items():
        lines.append(f"{k}：{v:,.2f}")
    lines.append(f"\n總共同負擔：{res['Total_Cost']:,.2f} 萬元\n")

    lines.append("【五、總銷價值與分回】")
    lines.append(f"總銷金額：{res['Total_Value']/10000:.2f} 億元")
    lines.append(f"地主分回比例：{res['Landlord_Ratio']*100:.2f}%")
    lines.append(f"實施者 IRR：{res['IRR']*100:.2f}%\n")

    lines.append("【六、現金流（IRR 計算基礎，萬元）】")
    lines.append(f"T0：{cf['T0']:.2f}")
    lines.append(f"T1：{cf['T1']:.2f}")
    lines.append(f"T2：{cf['T2']:.2f}")
    lines.append(f"T3：{cf['T3']:.2f}")
    lines.append(f"T4（最終回收）：{cf['T4']:.2f}\n")

    lines.append("【七、可行性判斷】")
    if res["IRR"] >= 0.12:
        lines.append("✔ IRR ≥ 12%，專案具投資可行性。")
    else:
        lines.append("✘ IRR < 12%，IRR 未達 12% 門檻，需檢討容積、單價或成本結構。")

    return "\n".join(lines)


# ---------------------------------------------
# Excel 報表（成本＋現金流＋輸入參數）
# ---------------------------------------------
def generate_excel(res: dict) -> io.BytesIO:
    output = io.BytesIO()

    # 成本拆解
    df_cost = pd.DataFrame(res["Details"].items(), columns=["項目", "金額(萬元)"])

    # 現金流
    cf = res["Cashflow"]
    df_cf = pd.DataFrame(
        {
            "期別": ["T0", "T1", "T2", "T3", "T4"],
            "金額(萬元)": [
                cf["T0"],
                cf["T1"],
                cf["T2"],
                cf["T3"],
                cf["T4"],
            ],
        }
    )

    # 輸入參數總表
    df_params = pd.DataFrame(
        [
            ["基地面積(坪)", base_area],
            ["原建築容積率(%)", far_base_exist * 100],
            ["法定容積率(%)", far_legal * 100],
            ["防災獎勵倍數", bonus_multiplier],
            ["總樓地板係數 K_GFA", coeff_gfa],
            ["銷售面積係數 K_Sale", coeff_sale],
            ["建材等級", const_type],
            ["基準單價(萬/坪)", base_unit_cost],
            ["修正後單價(萬/坪)", final_unit_cost],
            ["產權人數", num_owners],
            ["人事管理費率(%)", rate_personnel * 100],
            ["銷售管理費率(%)", rate_sales * 100],
            ["貸款成數(%)", loan_ratio * 100],
            ["貸款利率(%)", loan_rate * 100],
            ["工期(月)", dev_months],
            ["容積獎勵申請費(萬)", cost_bonus_app],
            ["都計變更/審議費(萬)", cost_urban_plan],
            ["容積移轉/折繳代金(萬)", cost_transfer],
            ["預售單價(萬/坪)", price_unit_sale],
            ["車位單價(萬/個)", price_parking],
        ],
        columns=["參數名稱", "數值"],
    )

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_cost.to_excel(writer, sheet_name="成本拆解", index=False)
        df_cf.to_excel(writer, sheet_name="現金流量表", index=False)
        df_params.to_excel(writer, sheet_name="模型輸入參數", index=False)

    output.seek(0)
    return output


# ---------------------------------------------
# HTML 報告（可列印成 PDF）
# ---------------------------------------------
def generate_html_report(res: dict, fig_cost, fig_heat) -> str:
    """
    產生一份 HTML 報告（黑白論文風），可在瀏覽器列印成 PDF。
    圖表使用 Plotly 互動式嵌入。
    """
    cf = res["Cashflow"]

    fig_cost_html = fig_cost.to_html(include_plotlyjs="cdn", full_html=False)
    fig_heat_html = fig_heat.to_html(include_plotlyjs=False, full_html=False)

    html = f"""
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
    <meta charset="utf-8" />
    <title>新北市防災都更財務模型｜IRR 計算報告</title>
    <style>
        body {{
            font-family: "Noto Sans TC", Arial, "Microsoft JhengHei", sans-serif;
            margin: 40px;
            line-height: 1.7;
            color: #111111;
        }}
        h1 {{
            font-size: 24px;
            border-bottom: 2px solid #000;
            padding-bottom: 6px;
            margin-bottom: 18px;
        }}
        h2 {{
            font-size: 18px;
            margin-top: 26px;
            margin-bottom: 8px;
        }}
        table {{
            border-collapse: collapse;
            width: 100%;
            margin-top: 8px;
            margin-bottom: 14px;
        }}
        th, td {{
            border: 1px solid #444;
            padding: 6px 8px;
            font-size: 13px;
        }}
        th {{
            background-color: #f0f0f0;
        }}
        .section {{
            margin-bottom: 16px;
        }}
        .small {{
            font-size: 12px;
            color: #555;
        }}
        .code-block {{
            font-family: "Consolas", monospace;
            background: #f8f8f8;
            padding: 6px 8px;
            border-radius: 4px;
            border: 1px solid #ddd;
        }}
    </style>
</head>
<body>

<h1>新北市防災都更財務模型｜IRR 計算報告</h1>
<p class="small">產生時間：{datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>

<div class="section">
    <h2>一、基地與容積參數</h2>
    <table>
        <tr><th>項目</th><th>數值</th></tr>
        <tr><td>基地面積 (坪)</td><td>{base_area:.2f}</td></tr>
        <tr><td>原建築容積率 (%)</td><td>{far_base_exist*100:.1f}</td></tr>
        <tr><td>法定容積率 (%)</td><td>{far_legal*100:.1f}</td></tr>
        <tr><td>防災獎勵倍數</td><td>{bonus_multiplier:.2f}</td></tr>
        <tr><td>總樓地板係數 K_GFA</td><td>{coeff_gfa:.2f}</td></tr>
        <tr><td>銷售面積係數 K_Sale</td><td>{coeff_sale:.2f}</td></tr>
    </table>
</div>

<div class="section">
    <h2>二、營建與建材及財務參數</h2>
    <table>
        <tr><th>項目</th><th>數值</th></tr>
        <tr><td>建材等級</td><td>{const_type}</td></tr>
        <tr><td>營建基準單價 (萬/坪)</td><td>{base_unit_cost:.2f}</td></tr>
        <tr><td>修正後營建單價 (萬/坪)</td><td>{final_unit_cost:.2f}</td></tr>
        <tr><td>產權人數 (人)</td><td>{num_owners:.0f}</td></tr>
        <tr><td>貸款成數 (%)</td><td>{loan_ratio*100:.0f}</td></tr>
        <tr><td>貸款利率 (%)</td><td>{loan_rate*100:.2f}</td></tr>
        <tr><td>工期 (月)</td><td>{dev_months:.0f}</td></tr>
        <tr><td>風險管理費率 (查表, %)</td><td>{res["Risk_Rate"]*100:.1f}</td></tr>
    </table>
</div>

<div class="section">
    <h2>三、共同負擔成本結構</h2>
    <table>
        <tr><th>成本項目</th><th>金額 (萬元)</th></tr>
        {"".join(f"<tr><td>{k}</td><td>{v:,.2f}</td></tr>" for k, v in res["Details"].items())}
        <tr><th>合計</th><th>{res["Total_Cost"]:,.2f}</th></tr>
    </table>
    <div>{fig_cost_html}</div>
</div>

<div class="section">
    <h2>四、總銷價值與分回結果</h2>
    <table>
        <tr><th>指標</th><th>數值</th></tr>
        <tr><td>總銷金額 (億元)</td><td>{res["Total_Value"]/10000:.2f}</td></tr>
        <tr><td>地主分回比例 (%)</td><td>{res["Landlord_Ratio"]*100:.2f}</td></tr>
        <tr><td>實施者 IRR (%)</td><td>{res["IRR"]*100:.2f}</td></tr>
    </table>
</div>

<div class="section">
    <h2>五、敏感度分析（房價 × 營建成本）</h2>
    <div>{fig_heat_html}</div>
</div>

<div class="section">
    <h2>六、IRR 計算用現金流（萬元）</h2>
    <table>
        <tr><th>期別</th><th>現金流</th></tr>
        <tr><td>T0</td><td>{cf["T0"]:,.2f}</td></tr>
        <tr><td>T1</td><td>{cf["T1"]:,.2f}</td></tr>
        <tr><td>T2</td><td>{cf["T2"]:,.2f}</td></tr>
        <tr><td>T3</td><td>{cf["T3"]:,.2f}</td></tr>
        <tr><td>T4</td><td>{cf["T4"]:,.2f}</td></tr>
    </table>
</div>

<div class="section">
    <h2>七、可行性判斷摘要</h2>
    <p>
        專案內部報酬率 (IRR) 為 <strong>{res["IRR"]*100:.2f}%</strong>。
        研究中設定之門檻報酬率為 12%。<br/>
        評估結果：
        {"<strong>IRR ≥ 12%，專案具投資可行性。</strong>" if res["IRR"] >= 0.12 else "<strong>IRR 未達 12%，需檢討容積、銷售單價或成本結構。</strong>"}
    </p>
</div>

</body>
</html>
"""
    return html


# -----------------------------------------------------
# 執行模型
# -----------------------------------------------------
res = calculate_model()

# ---------------------------------------------
# 結果看板（黑金卡片）
# ---------------------------------------------
st.markdown("### 📊 運算結果總覽")

mcol1, mcol2, mcol3, mcol4 = st.columns(4)

with mcol1:
    with st.container():
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("更新後總價值", f"{res['Total_Value']/10000:.2f} 億")
        st.markdown("</div>", unsafe_allow_html=True)

with mcol2:
    with st.container():
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            "共同負擔總額",
            f"{res['Total_Cost']/10000:.2f} 億",
            delta=f"風險費率 {res['Risk_Rate']*100:.1f}%",
        )
        st.markdown("</div>", unsafe_allow_html=True)

with mcol3:
    with st.container():
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric(
            "地主分回比例",
            f"{res['Landlord_Ratio']*100:.2f} %",
        )
        st.markdown("</div>", unsafe_allow_html=True)

with mcol4:
    with st.container():
        st.markdown('<div class="metric-card">', unsafe_allow_html=True)
        st.metric("實施者 IRR", f"{res['IRR']*100:.2f} %")
        st.markdown("</div>", unsafe_allow_html=True)

st.divider()

# -----------------------------------------------------
# Tabs：成本結構、敏感度、情境比較
# -----------------------------------------------------
tab1, tab2, tab3 = st.tabs(
    ["📈 成本結構拆解", "🎲 敏感度矩陣", "📚 情境比較"]
)

# =====================================================
# TAB1：成本圓餅圖
# =====================================================
with tab1:
    st.subheader("共同負擔成本結構")

    df_cost = pd.DataFrame(
        {
            "項目": [
                "工程費(含拆除)",
                "風險管理費",
                "人事/銷售管理費",
                "貸款利息",
                "進階費用",
                "其他(稅/設計/安置)",
            ],
            "金額": [
                res["Details"]["工程費(含拆除)"],
                res["Details"]["風險管理費"],
                res["Details"]["人事/銷售費"],
                res["Details"]["貸款利息"],
                res["Details"]["進階費用(獎勵/都計)"],
                res["Details"]["其他(稅/設計/安置)"],
            ],
        }
    )

    fig_cost = px.pie(
        df_cost,
        values="金額",
        names="項目",
        hole=0.45,
    )
    fig_cost.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
    )

    st.plotly_chart(fig_cost, use_container_width=True)
    st.dataframe(df_cost, use_container_width=True)

# =====================================================
# TAB2：敏感度熱力圖
# =====================================================
with tab2:
    st.subheader("敏感度分析（房價 vs 營建單價 → 地主分回 %）")

    prices = np.arange(price_unit_sale - 10, price_unit_sale + 15, 5)
    costs = np.arange(final_unit_cost - 4, final_unit_cost + 6, 2)

    z_matrix = []

    for c in costs:
        row = []
        for p in prices:
            area_far_s = base_area * far_base_exist * bonus_multiplier
            area_total_s = area_far_s * coeff_gfa
            area_sale_s = area_far_s * coeff_sale
            num_parking_s = int(area_total_s / 35)

            val_new_s = (area_sale_s * p) + (num_parking_s * price_parking)
            cost_build_s = area_total_s * c
            cost_total_s = cost_build_s * 1.55  # 簡化共同負擔係數

            ratio_s = (1 - cost_total_s / val_new_s) * 100
            row.append(ratio_s)

        z_matrix.append(row)

    fig_heat = go.Figure(
        data=go.Heatmap(
            z=z_matrix,
            x=prices,
            y=costs,
            colorscale="Viridis",
            text=[[f"{v:.1f}%" for v in r] for r in z_matrix],
            texttemplate="%{text}",
        )
    )

    fig_heat.update_layout(
        margin=dict(l=10, r=10, t=40, b=10),
        xaxis_title="預售單價 (萬/坪)",
        yaxis_title="營建單價 (萬/坪)",
    )

    st.plotly_chart(fig_heat, use_container_width=True)

# =====================================================
# TAB3：情境比較
# =====================================================
with tab3:
    st.subheader("情境比較：官方基準 vs 市場實務（說明用示意）")

    st.markdown(
        """
| 比較項目 | 情境 A（官方基準） | 情境 B（市場實務） |
| --- | --- | --- |
| 營建單價 | 16.23 萬/坪 | 24.0 萬/坪 |
| 管理費率（含風險） | 43% | 18% |
| 貸款成數 | 50% | 60% |
| 風險管理費率 | 12% | 14% |
        """
    )
    st.caption("※ 上表為研究設計情境示意，實際數值請依個案參數調整。")

# -----------------------------------------------------
# 下載區：TXT 報告、HTML 報告、Excel
# -----------------------------------------------------
st.subheader("📥 報表下載")

# TXT 報告
txt_report = generate_txt_report(res)
st.download_button(
    label="📄 下載 IRR 計算報告（TXT）",
    data=txt_report,
    file_name="IRR_Report.txt",
    mime="text/plain",
)

# Excel
excel_bytes = generate_excel(res)
st.download_button(
    label="📊 下載成本與現金流試算表（Excel）",
    data=excel_bytes,
    file_name="IRR_Model_Cost_Cashflow.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)

# HTML 報告（列印成 PDF）
html_report = generate_html_report(res, fig_cost, fig_heat)
st.download_button(
    label="📑 下載完整模型報告（HTML，可列印為 PDF）",
    data=html_report,
    file_name="IRR_Model_Report.html",
    mime="text/html",
)
