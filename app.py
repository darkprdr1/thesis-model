import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.express as px
import plotly.graph_objects as go

# --- 頁面設定 ---
st.set_page_config(
    page_title="新北市防災都更財務模型 (碩士論文研究版)",
    page_icon="🏙️",
    layout="wide"
)

# --- CSS樣式優化 ---
st.markdown(
    """
<style>
    .metric-card {background-color: #f0f2f6; border-radius: 10px; padding: 15px; border-left: 5px solid #4e73df;}
    .stTabs [data-baseweb="tab-list"] {gap: 10px;}
    .stTabs [data-baseweb="tab"] {height: 50px; white-space: pre-wrap; background-color: #f0f2f6; border-radius: 5px 5px 0px 0px;}
    .stTabs [aria-selected="true"] {background-color: #4e73df; color: white;}
</style>
""",
    unsafe_allow_html=True
)

# --- 標題區 ---
st.title("🏙️ 新北市防災都更權利變換模型")
st.markdown("### 碩士論文研究專用：互動式財務與敏感度分析工具")
st.info(
    "本模型依據「新北市防災都更2.0」政策與「都市更新權利變換實施辦法」建構，"
    "旨在探討不同成本與房價情境下之權益分配變化。"
)

# ==========================================
# 1. 側邊欄：參數輸入層 (Input Layer)
# ==========================================
st.sidebar.header("⚙️ 參數設定面板")

with st.sidebar.expander("1. 基地與容積參數 (Base)", expanded=True):
    base_area = st.number_input("基地面積 (坪)", value=300.0, step=10.0)
    far_base = st.number_input(
        "原建築容積率 FAR2 (%)",
        value=300.0,
        step=10.0,
        help="依5層樓概算"
    ) / 100
    bonus_multiplier = st.number_input(
        "防災獎勵倍數",
        value=1.5,
        step=0.1,
        help="防災都更2.0政策"
    )

    # 係數設定
    st.markdown("---")
    st.caption("面積係數設定")
    coeff_gfa = st.number_input(
        "總樓地板係數 (營建用)",
        value=1.8,
        step=0.1,
        help="含地下室、機電、梯廳 (約1.8~1.9)"
    )
    coeff_sale = st.number_input(
        "銷售面積係數 (估價用)",
        value=1.6,
        step=0.1,
        help="樓板面積 x 1.6 (考量公設比)"
    )

with st.sidebar.expander("2. 成本與費率 (Costs)", expanded=True):
    st.caption("⚠️ 營建單價設定")
    const_unit_cost = st.number_input(
        "營建單價 (萬元/坪)",
        value=16.23,
        step=0.5,
        format="%.2f",
        help="官方基準約16.23萬，市價約23-25萬"
    )

    st.caption("⚠️ 費用參數")
    mgmt_fee_rate = st.slider(
        "管理費率 (%)",
        10.0,
        50.0,
        43.0,
        help="含人事、銷售、信託、風險管理。若營建單價低，此值通常較高。"
    ) / 100
    loan_rate = st.number_input("貸款年利率 (%)", value=3.0, step=0.1) / 100
    dev_months = st.number_input("開發期程 (月)", value=48, step=6)

with st.sidebar.expander("3. 估價與銷售 (Valuation)", expanded=True):
    val_old_total = st.number_input(
        "更新前現況總值 (億元)",
        value=5.4,
        step=0.1
    ) * 10000  # 換算為萬元
    # 推算舊建物面積供拆遷補償計算
    area_old_reg = st.number_input(
        "舊建物登記面積 (坪)",
        value=900.0,
        step=50.0
    )
    price_unit_sale = st.number_input(
        "更新後預售單價 (萬元/坪)",
        value=60.0,
        step=2.0
    )

# ==========================================
# 2. 核心運算層 (Calculation Engine)
# ==========================================
def calculate_model(
    p_base_area,
    p_far,
    p_bonus,
    p_gfa_k,
    p_sale_k,
    p_const_cost,
    p_mgmt_rate,
    p_price,
    p_months
):
    # A. 面積計算
    area_far = p_base_area * p_far * p_bonus
    area_total = area_far * p_gfa_k  # 總樓地板 (營建面積)
    area_sale = area_far * p_sale_k  # 銷售面積

    # B. 費用計算 (萬元)
    # 1. 拆遷相關
    # area_old_reg 為全域變數，從側邊欄輸入
    c_demo = area_old_reg * 10 * 0.15  # 拆遷補償
    c_reloc = (area_total * p_const_cost) * 0.125  # 安置費

    # 2. 營建與衍生
    c_build = area_total * p_const_cost
    c_design = c_build * 0.035
    c_rights = c_build * 0.035
    c_tax = c_build * 0.04
    c_mgmt = c_build * p_mgmt_rate

    # 3. 利息
    loan_fund = c_demo + c_reloc + c_build + c_design + c_rights
    c_interest = loan_fund * loan_rate * (p_months / 12) * 0.5

    # 4. 總共同負擔
    c_total = (
        c_demo
        + c_reloc
        + c_build
        + c_design
        + c_rights
        + c_tax
        + c_mgmt
        + c_interest
    )

    # C. 價值分配
    val_new_total = area_sale * p_price

    if val_new_total == 0:
        ratio_burden = 0
    else:
        ratio_burden = c_total / val_new_total

    ratio_landlord = 1 - ratio_burden
    val_landlord = val_new_total * ratio_landlord
    area_landlord = area_sale * ratio_landlord

    # D. IRR 簡易估算
    initial_investment = c_rights + c_design * 0.5 + c_demo  # Year 0
    c_flow = [
        -initial_investment,
        -(c_build * 0.3 + c_reloc * 0.3),
        -(c_build * 0.4 + c_reloc * 0.3),
        -(c_build * 0.3 + c_reloc * 0.4),
        val_new_total - (c_tax + c_mgmt + c_interest),
    ]
    try:
        irr_val = float(npf.irr(c_flow))
        if np.isnan(irr_val):
            irr_val = 0
    except Exception:
        irr_val = 0

    return {
        "area_total": area_total,
        "area_sale": area_sale,
        "c_build": c_build,
        "c_total": c_total,
        "val_new_total": val_new_total,
        "ratio_landlord": ratio_landlord,
        "area_landlord": area_landlord,
        "irr": irr_val,
        "details": {
            "營建費": c_build,
            "管理費": c_mgmt,
            "拆遷安置": c_reloc,
            "利息": c_interest,
            "其他(稅/設計/權變/補償)": c_tax + c_design + c_rights + c_demo,
        },
    }


# 執行主要計算
res = calculate_model(
    base_area,
    far_base,
    bonus_multiplier,
    coeff_gfa,
    coeff_sale,
    const_unit_cost,
    mgmt_fee_rate,
    price_unit_sale,
    dev_months,
)

# ==========================================
# 3. 輸出層 (Output Dashboard)
# ==========================================

# --- 頂部 KPI 卡片 ---
st.markdown("### 📊 關鍵指標看板")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)


def fmt_money(v):
    return f"{v / 10000:.2f} 億"


with kpi1:
    st.metric("更新後總價值", fmt_money(res["val_new_total"]), f"單價 {price_unit_sale} 萬")
with kpi2:
    st.metric(
        "共同負擔 (總成本)",
        fmt_money(res["c_total"]),
        f"負擔比 {100 - res['ratio_landlord'] * 100:.1f}%",
        delta_color="inverse",
    )
with kpi3:
    st.metric(
        "地主分回比例",
        f"{res['ratio_landlord'] * 100:.2f}%",
        f"分回 {res['area_landlord']:.1f} 坪",
    )
with kpi4:
    irr_display = f"{res['irr'] * 100:.2f}%" if res["irr"] != 0 else "N/A"
    st.metric("實施者 IRR", irr_display, "目標 > 12%")

st.markdown("---")

# --- 分頁詳細分析 ---
tab1, tab2, tab3, tab4 = st.tabs(
    ["📈 成本結構與分配", "📋 詳細試算表", "🎲 敏感度分析", "🎓 論文情境模擬"]
)

# Tab 1: 圖表分析
with tab1:
    col_chart1, col_chart2 = st.columns(2)

    with col_chart1:
        st.subheader("共同負擔結構圖")
        df_cost = pd.DataFrame(
            list(res["details"].items()), columns=["項目", "金額"]
        )
        fig_pie = px.pie(
            df_cost,
            values="金額",
            names="項目",
            hole=0.4,
            color_discrete_sequence=px.colors.sequential.RdBu,
        )
        fig_pie.update_traces(textinfo="percent+label")
        st.plotly_chart(fig_pie, use_container_width=True)

    with col_chart2:
        st.subheader("價值分配示意圖")
        df_dist = pd.DataFrame(
            {
                "角色": ["地主權益", "實施者(成本+利潤)"],
                "金額": [
                    res["val_new_total"] * res["ratio_landlord"],
                    res["val_new_total"] * (1 - res["ratio_landlord"]),
                ],
            }
        )
        fig_bar = px.bar(
            df_dist,
            x="角色",
            y="金額",
            color="角色",
            text_auto=".2s",
            title="全案價值餅塊",
        )
        st.plotly_chart(fig_bar, use_container_width=True)

# Tab 2: 詳細數據
with tab2:
    st.subheader("試算明細表")
    detail_data = {
        "項目": [
            "1. 基地面積",
            "2. 容積樓地板面積 (FAR)",
            "3. 總營建面積 (GFA)",
            "4. 銷售面積",
            "5. 營建單價",
            "6. 營建總費用",
            "7. 管理費",
            "8. 共同負擔總額",
            "9. 更新後總銷",
            "10. 地主分回比",
        ],
        "數值": [
            base_area,
            base_area * far_base * bonus_multiplier,
            res["area_total"],
            res["area_sale"],
            const_unit_cost,
            res["c_build"],
            res["details"]["管理費"],
            res["c_total"],
            res["val_new_total"],
            res["ratio_landlord"],
        ],
        "單位": [
            "坪",
            "坪",
            "坪",
            "坪",
            "萬/坪",
            "萬元",
            "萬元",
            "萬元",
            "萬元",
            "-",
        ],
    }
    st.dataframe(
        pd.DataFrame(detail_data).style.format({"數值": "{:,.2f}"}),
        use_container_width=True,
    )

# Tab 3: 敏感度分析
with tab3:
    st.subheader("敏感度分析：房價 vs 營建成本")
    x_prices = np.arange(price_unit_sale - 10, price_unit_sale + 15, 5)
    y_costs = np.arange(const_unit_cost - 4, const_unit_cost + 6, 2)

    z_data = []
    for c in y_costs:
        row = []
        for p in x_prices:
            sim_res = calculate_model(
                base_area,
                far_base,
                bonus_multiplier,
                coeff_gfa,
                coeff_sale,
                c,
                mgmt_fee_rate,
                p,
                dev_months,
            )
            row.append(sim_res["ratio_landlord"] * 100)
        z_data.append(row)

    fig_heat = go.Figure(
        data=go.Heatmap(
            z=z_data,
            x=x_prices,
            y=y_costs,
            text=[[f"{val:.1f}%" for val in r] for r in z_data],
            texttemplate="%{text}",
            colorscale="Viridis",
            colorbar=dict(title="地主分回比(%)"),
        )
    )
    fig_heat.update_layout(
        xaxis_title="預售房價 (萬元/坪)", yaxis_title="營建單價 (萬元/坪)"
    )
    st.plotly_chart(fig_heat, use_container_width=True)

# Tab 4: 論文情境模擬
with tab4:
    st.subheader("📚 論文情境比較分析")
    scenarios = [
        {
            "name": "情境A: 官方基準 (權變申報)",
            "cost": 16.23,
            "mgmt": 0.43,
            "price": 60,
        },
        {
            "name": "情境B: 市場實務 (真實成本)",
            "cost": 24.00,
            "mgmt": 0.18,
            "price": 65,
        },
        {
            "name": "情境C: 滯銷風險 (房市反轉)",
            "cost": 24.00,
            "mgmt": 0.18,
            "price": 55,
        },
    ]

    comp_data = []
    for s in scenarios:
        s_res = calculate_model(
            base_area,
            far_base,
            bonus_multiplier,
            coeff_gfa,
            coeff_sale,
            s["cost"],
            s["mgmt"],
            s["price"],
            dev_months,
        )
        comp_data.append(
            {
                "情境": s["name"],
                "營建單價": f"{s['cost']} 萬",
                "管理費率": f"{s['mgmt'] * 100:.0f}%",
                "預售房價": f"{s['price']} 萬",
                "地主分回比": f"{s_res['ratio_landlord'] * 100:.2f}%",
                "地主分回坪數": f"{s_res['area_landlord']:.1f} 坪",
                "實施者 IRR": f"{s_res['irr'] * 100:.2f}%",
                "可行性判斷": "✅ 可行" if s_res["irr"] > 0.12 else "❌ 風險高",
            }
        )

    st.table(pd.DataFrame(comp_data))
    st.info(
        "情境說明：情境A為依據官方權變基準計算；情境B為目前市場實際發包行情；"
        "情境C為假設房市下跌之壓力測試。"
    )

# --- 頁尾 ---
st.markdown("---")
st.caption("© 2024 Master Thesis Research Model | Developed with Python Streamlit")
