import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.express as px
import plotly.graph_objects as go

# ---------------------------------------------
# 頁面設定
# ---------------------------------------------
st.set_page_config(
    page_title="新北市防災都更財務模型 (論文修正版)",
    page_icon="🏙️",
    layout="wide"
)

# ---------------------------------------------
# CSS 優化
# ---------------------------------------------
st.markdown("""
<style>
    .metric-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 15px;
        border-left: 5px solid #4e73df;
    }
    .stTabs [data-baseweb="tab-list"] {gap: 10px;}
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        white-space: pre-wrap;
        background-color: #f0f2f6;
        border-radius: 5px 5px 0px 0px;
    }
    .stTabs [aria-selected="true"] {
        background-color: #4e73df;
        color: white;
    }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------
# 標題區
# ---------------------------------------------
st.title("🏙️ 新北市防災都更權利變換試算模型")
st.markdown("### 第三章：混合研究法與參數建構實證")
st.info("本模型已依據專家訪談與文獻回饋修正，包含建材係數、風險費率查表與管理費結構拆分。")

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
    const_type = st.selectbox("建材結構等級", ["RC 一般標準 (S0)", "RC 高階 (+0.11)", "SRC/SC (+0.30)"])
    if "高階" in const_type:
        mat_coeff = 0.11
    elif "SRC" in const_type:
        mat_coeff = 0.30
    else:
        mat_coeff = 0.0

    base_unit_cost = st.number_input("營建基準單價 (萬/坪)", value=16.23, step=0.5)
    final_unit_cost = base_unit_cost * (1 + mat_coeff)
    st.caption(f"💡 修正後單價：{final_unit_cost:.2f} 萬/坪 (係數 +{mat_coeff})")

# ========== 3. 財務與風險 ==========
with st.sidebar.expander("3. 財務與風險參數", expanded=True):
    num_owners = st.number_input("產權人數 (人)", value=20, step=5)
    rate_personnel = st.number_input("人事行政管理費率 (%)", value=3.0, step=0.5) / 100
    rate_sales = st.number_input("銷售管理費率 (%)", value=6.0, step=0.5) / 100
    loan_ratio = st.slider("貸款成數 (%)", 40, 80, 60) / 100
    loan_rate = st.number_input("貸款年利率 (%)", value=3.0, step=0.1) / 100
    dev_months = st.number_input("開發期程 (月)", value=48, step=6)

# ========== 4. 進階費用 ==========
with st.sidebar.expander("4. 進階費用設定 (B/G/H類)", expanded=False):
    cost_bonus_app = st.number_input("容積獎勵申請費 (萬)", value=500, step=50)
    cost_urban_plan = st.number_input("都計變更/審議費 (萬)", value=300, step=50)
    cost_transfer = st.number_input("容積移轉/折繳代金 (萬)", value=0, step=100)

# ========== 5. 估價與銷售 ==========
with st.sidebar.expander("5. 估價與銷售", expanded=False):
    val_old_total = st.number_input("更新前現況總值 (億元)", value=5.4, step=0.1) * 10000
    price_unit_sale = st.number_input("更新後預售單價 (萬/坪)", value=60.0, step=2.0)
    price_parking = st.number_input("車位平均單價 (萬/個)", value=220, step=10)

# ---------------------------------------------
# 功能：風險費率查表
# ---------------------------------------------
def get_risk_fee_rate(gfa_ping, owners):
    if gfa_ping < 3000 or owners > 50:
        return 0.14
    elif gfa_ping < 5000:
        return 0.13
    else:
        return 0.12

# ---------------------------------------------
# 核心計算函式
# ---------------------------------------------
def calculate_model():
    area_far = base_area * far_base_exist * bonus_multiplier
    area_total = area_far * coeff_gfa
    area_sale = area_far * coeff_sale
    num_parking = int(area_total / 35)

    # 工程費
    c_demo = base_area * 3 * 0.15
    c_build = area_total * final_unit_cost
    c_engineering = c_demo + c_build

    # 進階費用
    c_advanced = cost_bonus_app + cost_urban_plan + cost_transfer

    # 設計/安置
    c_design = c_build * 0.06
    c_reloc = c_build * 0.05

    # 管理費
    rate_risk = get_risk_fee_rate(area_total, num_owners)
    c_mgmt_risk = c_build * rate_risk
    c_mgmt_personnel = c_build * rate_personnel
    c_mgmt_sales = (area_sale * price_unit_sale) * 0.05
    c_mgmt_total = c_mgmt_risk + c_mgmt_personnel + c_mgmt_sales

    # 利息
    fund_demand = c_engineering + c_advanced + c_design + c_reloc
    c_interest = fund_demand * loan_ratio * loan_rate * (dev_months / 12) * 0.5

    # 稅捐
    c_tax = c_build * 0.03

    # 總成本
    c_total = (c_engineering + c_advanced + c_design + c_reloc +
               c_mgmt_total + c_interest + c_tax)

    # 價值
    val_parking_total = num_parking * price_parking
    val_new_total = (area_sale * price_unit_sale) + val_parking_total

    ratio_burden = c_total / val_new_total if val_new_total > 0 else 0
    ratio_landlord = 1 - ratio_burden

    # IRR 現金流
    equity_ratio = 1 - loan_ratio
    initial_out = (c_advanced + c_design) + (c_engineering * equity_ratio * 0.1)
    yearly_cost = (c_engineering * equity_ratio * 0.9) / 3
    loan_repay = fund_demand * loan_ratio
    final_in = val_new_total - loan_repay - c_tax - c_mgmt_total - c_interest

    c_flow = [-initial_out, -yearly_cost, -yearly_cost, -yearly_cost, final_in]
    try:
        irr_val = npf.irr(c_flow)
    except:
        irr_val = 0

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
            "其他(稅/設計/安置)": c_tax + c_design + c_reloc
        }
    }

# ---------------------------------------------
# 執行模型
# ---------------------------------------------
res = calculate_model()

# ---------------------------------------------
# 結果看板
# ---------------------------------------------
st.markdown("### 📊 運算結果看板")

col1, col2, col3, col4 = st.columns(4)
col1.metric("更新後總價值", f"{res['Total_Value']/10000:.2f} 億")
col2.metric("共同負擔總額", f"{res['Total_Cost']/10000:.2f} 億", delta=f"風險費率 {res['Risk_Rate']*100:.0f}%")
col3.metric("地主分回比例", f"{res['Landlord_Ratio']*100:.2f}%")
col4.metric("實施者 IRR", f"{res['IRR']*100:.2f}%")

st.divider()

# ---------------------------------------------
# Tabs：成本結構 / 敏感度熱力圖 / 情境比較
# ---------------------------------------------
tab1, tab2, tab3 = st.tabs(["📈 成本結構拆解", "🎲 敏感度矩陣", "📚 情境比較"])

# ======================================================
# TAB1：成本結構圖（Pie Chart）
# ======================================================
with tab1:
    st.subheader("共同負擔詳細結構 (符合表 3-1 分類)")

    df_cost = pd.DataFrame({
        "項目": [
            "工程費(含拆除)",
            "風險管理費",
            "人事管理費 + 銷售管理費",
            "貸款利息",
            "進階費用(獎勵/都計)",
            "其他(稅/設計/安置)"
        ],
        "金額(萬元)": [
            res["Details"]["工程費(含拆除)"],
            res["Details"]["風險管理費"],
            res["Details"]["人事/銷售費"],
            res["Details"]["貸款利息"],
            res["Details"]["進階費用(獎勵/都計)"],
            res["Details"]["其他(稅/設計/安置)"]
        ]
    })

    fig_cost = px.pie(
        df_cost,
        values="金額(萬元)",
        names="項目",
        title="共同負擔成本結構",
        hole=0.4,
        color_discrete_sequence=px.colors.sequential.RdBu
    )
    st.plotly_chart(fig_cost, use_container_width=True)

    st.dataframe(df_cost, use_container_width=True)

# ======================================================
# TAB2：敏感度熱力圖（Heatmap）
# ======================================================
with tab2:
    st.subheader("敏感度分析：房價 vs 營建成本（地主分回比例 %）")

    prices = np.arange(price_unit_sale - 10, price_unit_sale + 15, 5)
    costs = np.arange(final_unit_cost - 4, final_unit_cost + 6, 2)

    z_matrix = []

    for c in costs:
        row = []
        for p in prices:
            area_far = base_area * far_base_exist * bonus_multiplier
            area_total = area_far * coeff_gfa
            area_sale = area_far * coeff_sale
            num_parking = int(area_total / 35)

            val_new = (area_sale * p) + (num_parking * price_parking)
            cost_build = area_total * c
            cost_total = cost_build * 1.55  # 簡化共同負擔

            ratio = (1 - cost_total / val_new) * 100
            row.append(ratio)

        z_matrix.append(row)

    fig_heat = go.Figure(
        data=go.Heatmap(
            z=z_matrix,
            x=prices,
            y=costs,
            colorscale="Viridis",
            text=[[f"{v:.1f}%" for v in r] for r in z_matrix],
            texttemplate="%{text}"
        )
    )

    fig_heat.update_layout(
        title="敏感度熱力圖（地主分回比例 %）",
        xaxis_title="房價 (萬/坪)",
        yaxis_title="營建單價 (萬/坪)"
    )

    st.plotly_chart(fig_heat, use_container_width=True)

# ======================================================
# TAB3：情境比較
# ======================================================
with tab3:
    st.subheader("情境 A (官方) vs 情境 B (市場)")
    st.markdown("""
| 比較項目 | 情境 A：官方基準 | 情境 B：市場實務 |
| --- | --- | --- |
| **營建單價** | 16.23 萬 | 24.0 萬 |
| **管理費率** | 43% | 18% |
| **貸款成數** | 50% | 60% |
| **風險費率** | 12% | 14% |
    """)
    st.info("請使用左側調整參數模擬不同情境。")
