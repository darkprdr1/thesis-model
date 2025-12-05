import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.express as px
import plotly.graph_objects as go
import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
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
# 標題
# ---------------------------------------------
st.title("🏙️ 新北市防災都更權利變換試算模型")
st.markdown("### 混合研究法與參數建構實證")
st.info("本模型依據專家訪談與文獻回饋調整：建材係數、風險費率查表、管理費結構拆分與 IRR 現金流模型。")

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

    st.caption(f"💡 修正後營建單價：{final_unit_cost:.2f} 萬/坪 (建材係數 +{mat_coeff})")

# ========== 3. 財務與風險 ==========
with st.sidebar.expander("3. 財務與風險參數", expanded=True):
    num_owners = st.number_input("產權人數 (人)", value=20, step=5)
    rate_personnel = st.number_input("人事行政管理費率 (%)", value=3.0, step=0.5) / 100
    rate_sales = st.number_input("銷售管理費率 (%)", value=6.0, step=0.5) / 100
    loan_ratio = st.slider("貸款成數 (%)", 40, 80, 60) / 100
    loan_rate = st.number_input("貸款年利率 (%)", value=3.0, step=0.1) / 100
    dev_months = st.number_input("開發期程 (月)", value=48, step=6)

# ========== 4. 費用 ==========
with st.sidebar.expander("4. 進階費用設定 (B/G/H類)", expanded=False):
    cost_bonus_app = st.number_input("容積獎勵申請費 (萬)", value=500, step=50)
    cost_urban_plan = st.number_input("都計變更/審議費 (萬)", value=300, step=50)
    cost_transfer = st.number_input("容積移轉/折繳代金 (萬)", value=0, step=100)

# ========== 5. 銷售 ==========
with st.sidebar.expander("5. 估價與銷售", expanded=False):
    val_old_total = st.number_input("更新前現況總值 (億元)", value=5.4, step=0.1) * 10000
    price_unit_sale = st.number_input("更新後預售單價 (萬/坪)", value=60.0, step=2.0)
    price_parking = st.number_input("車位單價 (萬/個)", value=220, step=10)

# ---------------------------------------------
# 風險費率查表
# ---------------------------------------------
def get_risk_fee_rate(gfa_ping, owners):
    if gfa_ping < 3000 or owners > 50:
        return 0.14
    elif gfa_ping < 5000:
        return 0.13
    else:
        return 0.12

# ---------------------------------------------
# 核心計算模型（完整 A 版）
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
    c_interest = fund_demand * loan_ratio * loan_rate * (dev_months / 12) * 0.5

    # 7. 稅
    c_tax = c_build * 0.03

    # 8. 總成本
    c_total = (
        c_engineering + c_advanced + c_design + c_reloc +
        c_mgmt_total + c_interest + c_tax
    )

    # 9. 總銷價值
    val_parking_total = num_parking * price_parking
    val_new_total = (area_sale * price_unit_sale) + val_parking_total

    ratio_burden = c_total / val_new_total if val_new_total > 0 else 0
    ratio_landlord = 1 - ratio_burden

    # 10. IRR 現金流
    equity_ratio = 1 - loan_ratio

    initial_out = (c_advanced + c_design) + (c_engineering * equity_ratio * 0.1)
    yearly_cost = (c_engineering * equity_ratio * 0.9) / 3
    loan_repay = fund_demand * loan_ratio

    final_in = val_new_total - loan_repay - c_tax - c_mgmt_total - c_interest

    cashflow = [
        -initial_out,
        -yearly_cost,
        -yearly_cost,
        -yearly_cost,
        final_in
    ]

    try:
        irr_val = npf.irr(cashflow)
    except:
        irr_val = 0

    # 回傳結果
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
        },
        "Cashflow": {
            "T0": cashflow[0],
            "T1": cashflow[1],
            "T2": cashflow[2],
            "T3": cashflow[3],
            "T4": cashflow[4]
        }
    }

# -----------------------------------------------------
# 執行模型（重要！）
# -----------------------------------------------------
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

# -----------------------------------------------------
# Tabs：成本結構、敏感度、情境比較
# -----------------------------------------------------
tab1, tab2, tab3 = st.tabs(["📈 成本結構拆解", "🎲 敏感度矩陣", "📚 情境比較"])

# =====================================================
# TAB1：成本圓餅圖
# =====================================================
with tab1:
    st.subheader("共同負擔成本結構")

    df_cost = pd.DataFrame({
        "項目": [
            "工程費(含拆除)",
            "風險管理費",
            "人事/銷售管理費",
            "貸款利息",
            "進階費用",
            "其他(稅/設計/安置)"
        ],
        "金額": [
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
        values="金額",
        names="項目",
        hole=0.4,
        title="共同負擔成本比例"
    )
    st.plotly_chart(fig_cost, use_container_width=True)
    st.dataframe(df_cost, use_container_width=True)

# =====================================================
# TAB2：敏感度熱力圖
# =====================================================
with tab2:
    st.subheader("敏感度分析（房價 vs 營建成本）")

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
            cost_total = cost_build * 1.55  

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

# =====================================================
# TAB3：情境比較
# =====================================================
with tab3:
    st.subheader("情境比較表")

    st.markdown("""
| 比較項目 | 情境 A（官方） | 情境 B（市場） |
| --- | --- | --- |
| 營建單價 | 16.23 萬 | 24.0 萬 |
| 管理費率 | 43% | 18% |
| 貸款成數 | 50% | 60% |
| 風險費率 | 12% | 14% |
""")

# =====================================================
# 報告產生器（TXT）
# =====================================================
def generate_report(res):
    cf = res["Cashflow"]

    lines = []
    lines.append("【新北市防災都更財務模型｜IRR 計算報告】")
    lines.append(f"產生時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("------------------------------------------------------------\n")

    lines.append("【一、基地與容積參數】")
    lines.append(f"基地面積：{base_area} 坪")
    lines.append(f"原建築容積率：{far_base_exist*100:.1f}%")
    lines.append(f"防災獎勵倍數：{bonus_multiplier}")
    lines.append(f"總樓地板係數：{coeff_gfa}")
    lines.append(f"銷售面積係數：{coeff_sale}\n")

    lines.append("【二、營建與建材參數】")
    lines.append(f"基準單價：{base_unit_cost} 萬/坪")
    lines.append(f"修正後單價：{final_unit_cost:.2f} 萬/坪\n")

    lines.append("【三、財務與風險參數】")
    lines.append(f"貸款成數：{loan_ratio*100:.0f}%")
    lines.append(f"貸款利率：{loan_rate*100:.2f}%")
    lines.append(f"工期（月）：{dev_months}")
    lines.append(f"風險管理費率（查表）：{res['Risk_Rate']*100:.1f}%\n")

    lines.append("【四、共同負擔成本明細（萬元）】")
    for k, v in res["Details"].items():
        lines.append(f"{k}：{v:,.2f}")
    lines.append(f"\n總共同負擔：{res['Total_Cost']:,.2f} 萬元\n")

    lines.append("【五、總銷價值與分回】")
    lines.append(f"總銷金額：{res['Total_Value']/10000:.2f} 億元")
    lines.append(f"地主分回比例：{res['Landlord_Ratio']*100:.2f}%")
    lines.append(f"實施者 IRR：{res['IRR']*100:.2f}%\n")

    lines.append("【六、現金流（IRR 計算基礎）】")
    lines.append(f"T0：{cf['T0']:.2f}")
    lines.append(f"T1：{cf['T1']:.2f}")
    lines.append(f"T2：{cf['T2']:.2f}")
    lines.append(f"T3：{cf['T3']:.2f}")
    lines.append(f"T4（最終回收）：{cf['T4']:.2f}\n")

    lines.append("【七、可行性判斷】")
    if res["IRR"] >= 0.12:
        lines.append("✔ IRR ≥ 12%，專案具投資可行性。")
    else:
        lines.append("✘ IRR < 12%，需調整參數以提升可行性。")

    return "\n".join(lines)

# -----------------------------------------------------
# 下載 TXT 報告按鈕
# -----------------------------------------------------
report_text = generate_report(res)
st.download_button(
    label="📄 下載 IRR 計算報告（TXT）",
    data=report_text,
    file_name="IRR_Report.txt",
    mime="text/plain"
)
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
import io
def generate_pdf(res, fig_cost, fig_heat):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)

    width, height = A4

    # --------- 標題 ---------
    c.setFont("Helvetica-Bold", 18)
    c.drawString(2 * cm, height - 2 * cm, "新北市防災都更財務模型｜IRR 計算報告")

    c.setFont("Helvetica", 10)
    c.drawString(2 * cm, height - 2.7 * cm, f"產生時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    y = height - 4 * cm

    # --------- 基本資料 ---------
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "一、專案基本資訊")
    y -= 0.6 * cm
    c.setFont("Helvetica", 10)
    lines = [
        f"基地面積：{base_area} 坪",
        f"防災獎勵倍數：{bonus_multiplier}",
        f"總樓地板係數：{coeff_gfa}",
        f"銷售係數：{coeff_sale}",
        f"建材修正後單價：{final_unit_cost:.2f} 萬/坪",
        f"貸款成數：{loan_ratio*100:.0f}%",
        f"工期：{dev_months} 個月",
        f"風險管理費率：{res['Risk_Rate']*100:.1f}%"
    ]
    for ln in lines:
        c.drawString(2 * cm, y, ln)
        y -= 0.5 * cm

    # --------- 加入成本圓餅圖 ---------
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, y, "二、成本結構圖")
    y -= 0.8 * cm

    img_bytes = io.BytesIO()
    fig_cost.write_image(img_bytes, format="PNG")
    img_bytes.seek(0)
    c.drawImage(ImageReader(img_bytes), 2 * cm, y - 8 * cm, width=12 * cm, height=8 * cm)
    y -= 9 * cm

    c.showPage()

    # --------- 第二頁：敏感度圖 ---------
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, height - 2 * cm, "三、敏感度分析圖（房價 × 營建成本）")

    img_bytes2 = io.BytesIO()
    fig_heat.write_image(img_bytes2, format="PNG")
    img_bytes2.seek(0)

    c.drawImage(ImageReader(img_bytes2), 2 * cm, height - 18 * cm, width=14 * cm, height=14 * cm)

    c.showPage()

    # --------- 第三頁：IRR 與現金流 ---------
    c.setFont("Helvetica-Bold", 12)
    c.drawString(2 * cm, height - 2 * cm, "四、IRR 計算與投資可行性")

    cf = res["Cashflow"]
    lines = [
        f"IRR：{res['IRR']*100:.2f}%",
        f"T0 前期投入：{cf['T0']:.2f} 萬",
        f"T1：{cf['T1']:.2f} 萬",
        f"T2：{cf['T2']:.2f} 萬",
        f"T3：{cf['T3']:.2f} 萬",
        f"T4（最終現金回收）：{cf['T4']:.2f} 萬"
    ]

    y = height - 3.2 * cm
    c.setFont("Helvetica", 11)
    for ln in lines:
        c.drawString(2 * cm, y, ln)
        y -= 0.6 * cm

    c.save()
    buffer.seek(0)

    return buffer
    # 生成 PDF
pdf_file = generate_pdf(res, fig_cost, fig_heat)

st.download_button(
    label="📄 下載 PDF 完整報告",
    data=pdf_file,
    file_name="IRR_Report.pdf",
    mime="application/pdf"
)
def generate_excel(res):
    output = io.BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:

        # 成本明細 Sheet
        df_cost = pd.DataFrame(res["Details"].items(), columns=["項目", "金額(萬元)"])
        df_cost.to_excel(writer, sheet_name="成本拆解", index=False)

        # 現金流 Sheet
        df_cf = pd.DataFrame({
            "期別": ["T0", "T1", "T2", "T3", "T4"],
            "金額(萬元)": [
                res["Cashflow"]["T0"],
                res["Cashflow"]["T1"],
                res["Cashflow"]["T2"],
                res["Cashflow"]["T3"],
                res["Cashflow"]["T4"],
            ]
        })

        df_cf.to_excel(writer, sheet_name="現金流量表", index=False)

    output.seek(0)
    return output
excel_file = generate_excel(res)

st.download_button(
    label="📊 下載 Excel 成本＆現金流",
    data=excel_file,
    file_name="Cost_and_Cashflow.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)


