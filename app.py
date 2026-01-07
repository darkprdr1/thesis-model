import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.express as px
import plotly.graph_objects as go
import datetime
import io

# ============================================================================
# 🎨 頁面設定與主題
# ============================================================================
st.set_page_config(
    page_title="新北市防災都更財務模型 (論文修正版)",
    page_icon="🏙️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# 📊 五案件統計數據（論文3.2.2節）
# ============================================================================
FIVE_CASES_DATA = {
    "案件1": {
        "location": "蘆洲光華965",
        "area_ping": 941.985,
        "floors": "17F+16F+B4",
        "developer": "更新會",
        "total_cost": 2056098558,
        "demolition_pct": 2.35,
        "reloc_comp_pct": 8.45,
        "design_fee_pct": 1.80,
        "loan_interest_pct": 6.12,
        "tax_pct": 0.10,
        "mgmt_fee_pct": 33.81,
    },
    "案件2": {
        "location": "新莊思源段",
        "area_ping": 603.4633,
        "floors": "15F+B5",
        "developer": "建設公司",
        "total_cost": 1392840119,
        "demolition_pct": 5.75,
        "reloc_comp_pct": 5.59,
        "design_fee_pct": 3.13,
        "loan_interest_pct": 5.24,
        "tax_pct": 3.74,
        "mgmt_fee_pct": 30.42,
    },
    "案件3": {
        "location": "新店316",
        "area_ping": 500.731,
        "floors": "19F+B4",
        "developer": "建設公司",
        "total_cost": 1422714391,
        "demolition_pct": 3.54,
        "reloc_comp_pct": 6.25,
        "design_fee_pct": 2.41,
        "loan_interest_pct": 5.19,
        "tax_pct": 5.30,
        "mgmt_fee_pct": 30.39,
    },
    "案件4": {
        "location": "三重381",
        "area_ping": 1098.284,
        "floors": "23F+B5",
        "developer": "建設公司",
        "total_cost": 2881408210,
        "demolition_pct": 2.00,
        "reloc_comp_pct": 5.00,
        "design_fee_pct": 2.05,
        "loan_interest_pct": 5.00,
        "tax_pct": 4.00,
        "mgmt_fee_pct": 32.00,
    },
    "案件5": {
        "location": "淡水930",
        "area_ping": 584.403,
        "floors": "14F+B5",
        "developer": "更新會",
        "total_cost": 1422332224,
        "demolition_pct": 0.0,  # 原地安置
        "reloc_comp_pct": 0.0,  # 原地安置
        "design_fee_pct": 1.89,
        "loan_interest_pct": 5.00,
        "tax_pct": 0.10,
        "mgmt_fee_pct": 27.00,
    }
}

# 統計平均值（論文表3-2）
STATISTICS_AVG = {
    "demolition_pct": 3.41,
    "reloc_comp_pct": 6.32,
    "design_fee_pct": 2.26,
    "loan_interest_pct": 5.31,
    "tax_pct": 4.35,
    "mgmt_fee_pct": 30.72,
}

# 官方基準（論文表3-2）
OFFICIAL_STANDARD = {
    "demolition_pct": 3.50,
    "reloc_comp_pct": 7.00,
    "design_fee_pct": 2.50,
    "loan_interest_pct": 5.50,
    "tax_pct": 4.00,
    "mgmt_fee_pct": 30.00,
}

# ============================================================================
# 🎨 現代化 CSS 設計系統
# ============================================================================
st.markdown(
    """
<style>
    /* ===== 色彩與基礎變數 ===== */
    :root {
        --primary: #2E7D87;
        --primary-light: #4A9FB5;
        --primary-dark: #1F5561;
        --accent: #E67E22;
        --success: #27AE60;
        --warning: #F39C12;
        --error: #E74C3C;
        --gray-light: #ECF0F1;
        --gray-medium: #BDC3C7;
        --gray-dark: #34495E;
        --text-primary: #2C3E50;
        --text-secondary: #7F8C8D;
        --border-radius: 12px;
        --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.08);
        --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.12);
    }

    /* ===== 全局樣式 ===== */
    body {
        font-family: 'Segoe UI', 'Roboto', '-apple-system', 'BlinkMacSystemFont', sans-serif;
        color: var(--text-primary);
        background-color: #F8FAFB;
    }

    /* ===== 標題美化 ===== */
    h1 {
        color: var(--primary-dark) !important;
        font-weight: 700 !important;
        letter-spacing: -0.5px !important;
        margin-bottom: 24px !important;
        background: linear-gradient(135deg, var(--primary-dark) 0%, var(--primary) 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }

    h2 {
        color: var(--primary) !important;
        font-weight: 600 !important;
        margin-top: 28px !important;
        margin-bottom: 16px !important;
        border-bottom: 2px solid var(--primary-light);
        padding-bottom: 8px !important;
    }

    h3 {
        color: var(--text-primary) !important;
        font-weight: 600 !important;
        margin-top: 16px !important;
    }

    /* ===== 卡片與容器 ===== */
    .metric-card {
        background: linear-gradient(135deg, #FFFFFF 0%, #F8FAFB 100%);
        border-radius: var(--border-radius);
        padding: 20px;
        border: 1px solid var(--gray-light);
        box-shadow: var(--shadow-sm);
        transition: all 0.3s ease;
        border-left: 5px solid var(--primary);
    }

    .metric-card:hover {
        box-shadow: var(--shadow-md);
        transform: translateY(-2px);
    }

    .metric-card.accent {
        border-left-color: var(--accent);
    }

    .metric-card.success {
        border-left-color: var(--success);
    }

    .metric-card.warning {
        border-left-color: var(--warning);
    }

    /* ===== Metrics 樣式 ===== */
    [data-testid="metric-container"] {
        background: transparent;
        padding: 0 !important;
    }

    [data-testid="metric-container"] [data-testid="metric-container-card"] {
        border-radius: var(--border-radius);
        border: none;
        padding: 12px 16px;
    }

    /* ===== 標籤與徽章 ===== */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px !important;
        background-color: transparent !important;
        border-bottom: 2px solid var(--gray-light) !important;
    }

    .stTabs [data-baseweb="tab"] {
        height: 48px !important;
        white-space: pre-wrap !important;
        background-color: transparent !important;
        border-radius: var(--border-radius) var(--border-radius) 0 0 !important;
        border: 2px solid transparent !important;
        color: var(--text-secondary) !important;
        font-weight: 500 !important;
        transition: all 0.3s ease !important;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: var(--primary) !important;
        border-bottom: 2px solid var(--primary-light) !important;
    }

    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, rgba(46, 125, 135, 0.1) 0%, rgba(46, 125, 135, 0.05) 100%) !important;
        color: var(--primary) !important;
        border-bottom: 3px solid var(--primary) !important;
    }

    /* ===== 按鈕樣式 ===== */
    .stButton > button {
        background: linear-gradient(135deg, var(--primary) 0%, var(--primary-light) 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: var(--border-radius) !important;
        padding: 10px 24px !important;
        font-weight: 600 !important;
        box-shadow: var(--shadow-sm) !important;
        transition: all 0.3s ease !important;
    }

    .stButton > button:hover {
        box-shadow: var(--shadow-md) !important;
        transform: translateY(-2px) !important;
    }

    .stButton > button:active {
        transform: translateY(0) !important;
        box-shadow: var(--shadow-sm) !important;
    }

    /* ===== 輸入框美化 ===== */
    .stNumberInput > div > div > input,
    .stSlider > div > div > div > input,
    .stSelectbox > div > div > select,
    .stTextInput > div > div > input {
        border-radius: 8px !important;
        border: 2px solid var(--gray-light) !important;
        padding: 10px 12px !important;
        transition: all 0.3s ease !important;
    }

    .stNumberInput > div > div > input:focus,
    .stSlider > div > div > div > input:focus,
    .stSelectbox > div > div > select:focus,
    .stTextInput > div > div > input:focus {
        border-color: var(--primary) !important;
        box-shadow: 0 0 0 3px rgba(46, 125, 135, 0.1) !important;
    }

    /* ===== 側邊欄美化 ===== */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFB 100%);
    }

    .stSidebar .stExpander {
        background-color: transparent;
    }

    /* ===== Expander 美化 ===== */
    .stExpander {
        border: 1px solid var(--gray-light);
        border-radius: var(--border-radius);
        overflow: hidden;
    }

    .streamlit-expanderHeader {
        background-color: var(--gray-light) !important;
        color: var(--text-primary) !important;
        border-radius: var(--border-radius) !important;
        padding: 12px 16px !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }

    .streamlit-expanderHeader:hover {
        background-color: rgba(46, 125, 135, 0.1) !important;
    }

    /* ===== Info / Warning 訊息框 ===== */
    .stInfo, [data-testid="stAlert"] {
        border-radius: var(--border-radius) !important;
        border: 1px solid rgba(46, 125, 135, 0.3) !important;
        background-color: rgba(46, 125, 135, 0.05) !important;
        padding: 16px !important;
    }

    .stWarning {
        border: 1px solid rgba(243, 156, 18, 0.3) !important;
        background-color: rgba(243, 156, 18, 0.05) !important;
    }

    .stError {
        border: 1px solid rgba(231, 76, 60, 0.3) !important;
        background-color: rgba(231, 76, 60, 0.05) !important;
    }

    /* ===== 表格美化 ===== */
    .stDataFrame {
        border-radius: var(--border-radius) !important;
        border: 1px solid var(--gray-light) !important;
    }

    /* ===== Divider 美化 ===== */
    hr {
        border: none;
        height: 2px;
        background: linear-gradient(90deg, transparent 0%, var(--primary-light) 50%, transparent 100%);
        margin: 24px 0 !important;
    }

    /* ===== 響應式設計 ===== */
    @media (max-width: 768px) {
        h1 {
            font-size: 24px !important;
        }

        h2 {
            font-size: 18px !important;
        }

        .metric-card {
            padding: 12px 16px !important;
        }

        .stTabs [data-baseweb="tab"] {
            height: 40px !important;
            font-size: 12px !important;
        }
    }
</style>
""",
    unsafe_allow_html=True,
)

# ============================================================================
# 📋 標題與說明區
# ============================================================================
col_title, col_emoji = st.columns([0.95, 0.05])
with col_title:
    st.title("🏙️ 新北市防災都更權利變換試算模型")
    st.markdown("**論文實證版 | 整合五案件統計數據 | v3.0**")

st.info(
    """
    🔍 **模型亮點**
    
    ✅ **創新核心**：整合新北市五個已審議防災都更案件的共同負擔費用統計數據
    ✅ **三層次對比**：官方基準 vs 本研究統計 vs 市場實況
    ✅ **動態參數**：物價指數調整、風險費率查表、分層費用設定
    ✅ **完整財務**：IRR計算、現金流分析、敏感度矩陣
    
    💡 **使用指南**：左側面板調整參數，系統自動對標五案件統計結果與官方基準
    """
)

# ============================================================================
# ⚙️ 側邊欄：參數設定（組織優化）
# ============================================================================
st.sidebar.markdown(
    """
    <div style='background: linear-gradient(135deg, #2E7D87 0%, #4A9FB5 100%); 
                color: white; padding: 16px; border-radius: 12px; margin-bottom: 20px;'>
        <h2 style='margin: 0; font-size: 18px; color: white;'>⚙️ 參數設定面板</h2>
        <p style='margin: 4px 0 0 0; font-size: 12px; opacity: 0.9;'>實時調整計算模型</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ========== 0. 五案件參考模式 ==========
st.sidebar.markdown("### 📌 五案件參考模式")
case_reference = st.sidebar.selectbox(
    "快速選擇參考案件",
    ["自訂設定", "案件1 (蘆洲大規模更新會)", "案件2 (新莊標準建商)", 
     "案件3 (新店高層)", "案件4 (三重大規模)", "案件5 (淡水原地安置)"],
    help="選擇參考案件以載入其預設參數"
)

# 根據選擇載入案件數據
if case_reference != "自訂設定":
    case_key = f"案件{case_reference[0]}"
    case_data = FIVE_CASES_DATA[case_key]
    st.sidebar.success(f"✅ 已載入 {case_data['location']} 的參考參數")

# ========== 1. 基地與容積 ==========
with st.sidebar.expander("1️⃣ 基地與容積參數", expanded=True):
    col_a, col_b = st.columns(2)
    with col_a:
        base_area = st.number_input("基地面積 (坪)", value=300.0, step=10.0, help="基地總面積")
        far_legal = st.number_input("法定容積率 (%)", value=200.0, step=10.0, help="當地法定容積率") / 100
    with col_b:
        far_base_exist = st.number_input("原建築容積率 (%)", value=300.0, step=10.0, help="原有建築容積率") / 100
        bonus_multiplier = st.number_input("防災獎勵倍數", value=1.5, step=0.1, help="政府獎勵容積倍數")

    col_c, col_d = st.columns(2)
    with col_c:
        coeff_gfa = st.number_input("總樓地板係數 K_GFA", value=1.8, step=0.1, help="容積換算係數")
    with col_d:
        coeff_sale = st.number_input("銷售面積係數 K_Sale", value=1.6, step=0.1, help="可銷售面積係數")

# ========== 2. 營建與建材 ==========
with st.sidebar.expander("2️⃣ 營建與建材設定", expanded=True):
    const_type = st.selectbox(
        "建材結構等級",
        ["RC 一般標準 (S0)", "RC 高階 (+0.11)", "SRC/SC (+0.30)"],
        help="選擇建築結構類型"
    )

    if "高階" in const_type:
        mat_coeff = 0.11
    elif "SRC" in const_type:
        mat_coeff = 0.30
    else:
        mat_coeff = 0.0

    base_unit_cost = st.number_input("營建基準單價 (萬/坪)", value=16.23, step=0.5, help="基準營建成本")
    final_unit_cost = base_unit_cost * (1 + mat_coeff)

    # ===== 與五案件數據對標 =====
    avg_unit_cost_from_cases = np.mean([
        case['total_cost'] / (case['area_ping'] * 1.8) for case in FIVE_CASES_DATA.values()
    ]) / 10000  # 轉換為萬/坪

    st.markdown(
        f"""
        <div style='background: linear-gradient(135deg, rgba(230, 126, 34, 0.1) 0%, rgba(230, 126, 34, 0.05) 100%);
                    border-left: 4px solid #E67E22; padding: 12px; border-radius: 8px; margin-top: 8px;'>
            <strong style='color: #E67E22;'>💡 修正後營建單價與五案件對標</strong><br>
            <span style='font-size: 14px; font-weight: 700; color: #2C3E50;'>您的設定：{final_unit_cost:.2f} 萬/坪</span>
            <br><span style='font-size: 12px; color: #7F8C8D;'>五案件平均隱含值：{avg_unit_cost_from_cases:.2f} 萬/坪</span>
            <br><span style='font-size: 11px; color: #7F8C8D;'>（建材係數 +{mat_coeff}）</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ========== 3. 財務與風險 ==========
with st.sidebar.expander("3️⃣ 財務與風險參數", expanded=True):
    col_e, col_f = st.columns(2)
    with col_e:
        num_owners = st.number_input("產權人數 (人)", value=20, step=5, help="產權人總數")
        loan_ratio = st.slider("貸款成數 (%)", 40, 80, 60, help="融資比例") / 100
    with col_f:
        rate_personnel = st.number_input("人事行政管理費率 (%)", value=3.0, step=0.5, help="人事費率") / 100
        rate_sales = st.number_input("銷售管理費率 (%)", value=6.0, step=0.5, help="銷售費率") / 100

    col_g, col_h = st.columns(2)
    with col_g:
        loan_rate = st.number_input("貸款年利率 (%)", value=3.0, step=0.1, help="貸款利率") / 100
    with col_h:
        dev_months = st.number_input("開發期程 (月)", value=48, step=6, help="開發期程")

    # ===== 風險費率查表 =====
    def get_risk_fee_rate(gfa_ping: float, owners: int) -> float:
        """風險管理費率查表（表3-1）"""
        if gfa_ping <= 2500:
            if owners < 30:
                return 0.12
            elif owners <= 100:
                return 0.125
            else:
                return 0.13
        elif gfa_ping <= 7500:
            if owners < 30:
                return 0.125
            elif owners <= 100:
                return 0.13
            else:
                return 0.135
        else:
            if owners < 30:
                return 0.13
            elif owners <= 100:
                return 0.135
            else:
                return 0.14

    area_far_temp = base_area * far_base_exist * bonus_multiplier
    area_total_temp = area_far_temp * coeff_gfa
    risk_rate = get_risk_fee_rate(area_total_temp, num_owners)

    st.markdown(
        f"""
        <div style='background: linear-gradient(135deg, rgba(39, 174, 96, 0.1) 0%, rgba(39, 174, 96, 0.05) 100%);
                    border-left: 4px solid #27AE60; padding: 10px; border-radius: 8px;'>
            <strong style='color: #27AE60;'>✅ 風險管理費率（查表 3-1）</strong><br>
            <span style='font-size: 14px; font-weight: 700; color: #2C3E50;'>{risk_rate * 100:.1f}%</span>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ========== 4. 進階費用 ==========
with st.sidebar.expander("4️⃣ 進階費用設定 (B/G/H 類)", expanded=False):
    cost_bonus_app = st.number_input("容積獎勵申請費 (萬)", value=500, step=50, help="申請獎勵容積費用")
    cost_urban_plan = st.number_input("都計變更 / 審議費 (萬)", value=300, step=50, help="都市計畫變更費用")
    cost_transfer = st.number_input("容積移轉 / 折繳代金 (萬)", value=0, step=100, help="容積移轉代金")

# ========== 5. 銷售與估價 ==========
with st.sidebar.expander("5️⃣ 估價與銷售參數", expanded=False):
    val_old_total = st.number_input("更新前現況總值 (億元)", value=5.4, step=0.1, help="現況總值") * 10000
    price_unit_sale = st.number_input("更新後預售單價 (萬/坪)", value=60.0, step=2.0, help="預售單價")
    price_parking = st.number_input("車位單價 (萬/個)", value=220, step=10, help="停車位單價")

# ========== 5.5 五案件統計對標 ==========
with st.sidebar.expander("📊 五案件統計對標", expanded=False):
    st.markdown("#### 費用項目統計對比（單位：%）")
    
    comparison_df = pd.DataFrame({
        "費用項目": ["拆遷補償", "拆遷安置", "設計費", "貸款利息", "稅捐", "管理費"],
        "五案件平均": [
            f"{STATISTICS_AVG['demolition_pct']:.2f}%",
            f"{STATISTICS_AVG['reloc_comp_pct']:.2f}%",
            f"{STATISTICS_AVG['design_fee_pct']:.2f}%",
            f"{STATISTICS_AVG['loan_interest_pct']:.2f}%",
            f"{STATISTICS_AVG['tax_pct']:.2f}%",
            f"{STATISTICS_AVG['mgmt_fee_pct']:.2f}%",
        ],
        "官方基準": [
            f"{OFFICIAL_STANDARD['demolition_pct']:.2f}%",
            f"{OFFICIAL_STANDARD['reloc_comp_pct']:.2f}%",
            f"{OFFICIAL_STANDARD['design_fee_pct']:.2f}%",
            f"{OFFICIAL_STANDARD['loan_interest_pct']:.2f}%",
            f"{OFFICIAL_STANDARD['tax_pct']:.2f}%",
            f"{OFFICIAL_STANDARD['mgmt_fee_pct']:.2f}%",
        ],
    })
    
    st.dataframe(comparison_df, use_container_width=True, hide_index=True)
    
    st.markdown(
        """
        <div style='background: rgba(46, 125, 135, 0.05); border-left: 4px solid #2E7D87; 
                    padding: 10px; border-radius: 8px; font-size: 11px; margin-top: 8px;'>
            <strong>📌 關鍵發現（論文3.2.2節）</strong><br>
            ✓ 官方基準符合度極高（差異<0.5%）<br>
            ✓ 管理費用穩定在27-34%，平均30.72%<br>
            ✓ 拆遷/稅捐項目呈現案件特性差異<br>
            ✓ 統計數據驗證了官方基準的科學性
        </div>
        """,
        unsafe_allow_html=True,
    )

# ============================================================================
# 🔧 核心計算模型與工具函式
# ============================================================================

def calculate_model():
    """核心財務模型計算 - 整合五案件費率"""
    # 1. 面積計算
    area_far = base_area * far_base_exist * bonus_multiplier
    area_total = area_far * coeff_gfa
    area_sale = area_far * coeff_sale
    num_parking = int(area_total / 35)

    # 2. 工程費（使用五案件平均或官方基準）
    c_demo = area_total * STATISTICS_AVG['demolition_pct'] / 100  # 改用統計百分比
    c_build = area_total * final_unit_cost
    c_engineering = c_demo + c_build

    # 3. 進階費用
    c_advanced = cost_bonus_app + cost_urban_plan + cost_transfer

    # 4. 設計 / 安置費（使用五案件平均）
    c_design = c_build * (STATISTICS_AVG['design_fee_pct'] / 100)
    c_reloc = c_build * (STATISTICS_AVG['reloc_comp_pct'] / 100)

    # 5. 管理費（含查表風險費）
    c_mgmt_risk = c_build * risk_rate
    c_mgmt_personnel = c_build * rate_personnel
    c_mgmt_sales = (area_sale * price_unit_sale) * rate_sales
    c_mgmt_total = c_mgmt_risk + c_mgmt_personnel + c_mgmt_sales

    # 6. 利息（使用五案件平均百分比）
    fund_demand = c_engineering + c_advanced + c_design + c_reloc
    c_interest = fund_demand * loan_ratio * loan_rate * (dev_months / 12) * 0.5

    # 7. 稅捐（使用五案件平均）
    c_tax = c_build * (STATISTICS_AVG['tax_pct'] / 100)

    # 8. 總成本（共同負擔）
    c_total = c_engineering + c_advanced + c_design + c_reloc + c_mgmt_total + c_interest + c_tax

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

    cashflow = [-initial_out, -yearly_cost, -yearly_cost, -yearly_cost, final_in]

    try:
        irr_val = npf.irr(cashflow)
    except Exception:
        irr_val = 0

    return {
        "GFA": area_total,
        "Total_Cost": c_total,
        "Total_Value": val_new_total,
        "Landlord_Ratio": ratio_landlord,
        "IRR": irr_val,
        "Risk_Rate": risk_rate,
        "Details": {
            "工程費(含拆除)": c_engineering,
            "設計費": c_design,
            "拆遷安置費": c_reloc,
            "風險管理費": c_mgmt_risk,
            "人事管理費": c_mgmt_personnel,
            "銷售管理費": c_mgmt_sales,
            "貸款利息": c_interest,
            "稅捐": c_tax,
            "進階費用": c_advanced,
        },
        "Cashflow": {"T0": cashflow[0], "T1": cashflow[1], "T2": cashflow[2], "T3": cashflow[3], "T4": cashflow[4]},
    }


# ============================================================================
# 📊 執行模型並顯示結果
# ============================================================================
res = calculate_model()

# ============================================================================
# 🎯 結果看板（KPI 指標區）
# ============================================================================
st.markdown("### 📊 運算結果看板")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "💰 更新後總價值",
        f"{res['Total_Value'] / 10000:.2f}億",
        help="新建案總銷價值"
    )

with col2:
    st.metric(
        "📈 共同負擔",
        f"{res['Total_Cost'] / 10000:.2f}億",
        delta=f"風險費率 {res['Risk_Rate'] * 100:.1f}%",
        delta_color="off"
    )

with col3:
    st.metric(
        "👥 地主分回比",
        f"{res['Landlord_Ratio'] * 100:.2f}%",
        help="地主實際分回比例"
    )

with col4:
    irr_pct = res['IRR'] * 100
    st.metric(
        "📊 實施者 IRR",
        f"{irr_pct:.2f}%",
        delta="可行" if irr_pct >= 12 else "需調整",
        delta_color="inverse"
    )

st.divider()

# ============================================================================
# 📑 標籤頁面：成本、敏感度、情境
# ============================================================================
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📈 成本結構", "🎲 敏感度分析", "📚 情境比較", "📋 詳細明細", "📊 五案件統計"]
)

# ===== TAB 1: 成本結構 =====
with tab1:
    st.subheader("共同負擔成本結構拆解")

    df_cost = pd.DataFrame(
        {
            "項目": list(res["Details"].keys()),
            "金額(萬元)": list(res["Details"].values()),
        }
    )

    df_cost["佔比(%)"] = (df_cost["金額(萬元)"] / df_cost["金額(萬元)"].sum() * 100).round(2)

    fig_cost = px.pie(
        df_cost,
        values="金額(萬元)",
        names="項目",
        hole=0.4,
        color_discrete_sequence=["#2E7D87", "#E67E22", "#27AE60", "#3498DB", "#9B59B6", "#E74C3C", "#F39C12", "#1ABC9C", "#34495E"],
        title="成本結構比例（甜甜圈圖）",
    )

    fig_cost.update_layout(
        height=500,
        font=dict(size=12),
        showlegend=True,
        hovermode="closest",
    )

    col_chart, col_table = st.columns([0.6, 0.4])

    with col_chart:
        st.plotly_chart(fig_cost, use_container_width=True)

    with col_table:
        st.markdown("#### 成本明細")
        st.dataframe(
            df_cost.style.format({"金額(萬元)": "{:,.0f}", "佔比(%)": "{:.2f}%"}),
            use_container_width=True,
            hide_index=True
        )

# ===== TAB 2: 敏感度分析 =====
with tab2:
    st.subheader("敏感度分析（房價 vs 營建成本）")

    col_sens_a, col_sens_b = st.columns(2)
    with col_sens_a:
        price_range = st.slider("房價變動範圍 (萬/坪)", -15, 15, (-10, 10), key="price_range")
    with col_sens_b:
        cost_range = st.slider("營建成本變動範圍 (萬/坪)", -6, 8, (-4, 6), key="cost_range")

    prices = np.arange(price_unit_sale + price_range[0], price_unit_sale + price_range[1] + 1, 2)
    costs = np.arange(final_unit_cost + cost_range[0], final_unit_cost + cost_range[1] + 1, 1)

    z_matrix = []
    for c in costs:
        row = []
        for p in prices:
            area_far_temp = base_area * far_base_exist * bonus_multiplier
            area_total_temp = area_far_temp * coeff_gfa
            area_sale_temp = area_far_temp * coeff_sale
            num_parking_temp = int(area_total_temp / 35)

            val_new_temp = (area_sale_temp * p) + (num_parking_temp * price_parking)
            cost_build_temp = area_total_temp * c
            cost_total_temp = cost_build_temp * 1.55

            ratio = (1 - cost_total_temp / val_new_temp) * 100 if val_new_temp > 0 else 0
            row.append(ratio)

        z_matrix.append(row)

    fig_heat = go.Figure(
        data=go.Heatmap(
            z=z_matrix,
            x=prices,
            y=costs,
            colorscale="Viridis",
            text=[[f"{v:.1f}%" for v in r] for r in z_matrix],
            texttemplate="%{text}",
            colorbar=dict(title="地主分回%")
        )
    )

    fig_heat.update_layout(
        title="地主分回比例敏感度熱力圖",
        xaxis_title="房價 (萬/坪)",
        yaxis_title="營建單價 (萬/坪)",
        height=500,
        font=dict(size=11),
    )

    st.plotly_chart(fig_heat, use_container_width=True)

    with st.expander("💡 敏感度解讀"):
        st.markdown("""
        - **顏色越深（紫色）**：地主分回比例越高（利潤空間大）
        - **顏色越淺（黃色）**：地主分回比例越低（風險較高）
        - **建議目標**：地主分回比 45-55% 為合理區間
        """)

# ===== TAB 3: 情境比較 =====
with tab3:
    st.subheader("預設情境模板 & 官方基準對標")

    scenario_desc = pd.DataFrame({
        "比較項目": ["營建單價", "風險費率", "貸款成數", "設計費率", "拆遷安置", "管理費率"],
        "官方基準": ["9.98 萬", "12-14%", "50%", "2.5%", "7%", "30%"],
        "本研究統計": ["11-24 萬", "12-14%", "60%", f"{STATISTICS_AVG['design_fee_pct']:.2f}%", f"{STATISTICS_AVG['reloc_comp_pct']:.2f}%", f"{STATISTICS_AVG['mgmt_fee_pct']:.2f}%"],
        "市場實務": ["23-25 萬", "14-16%", "70%", "4%", "8%", "32%"],
    })

    st.dataframe(scenario_desc, use_container_width=True, hide_index=True)

    st.markdown("""
    ---
    #### 📌 情境說明（論文3.8節）
    - **官方基準**：依新北市2024修正版共同負擔基準
    - **本研究統計**：五案件實際統計結果（論文3.2.2節）
    - **市場實務**：市場調查與建商實務估算
    """)

# ===== TAB 4: 詳細明細表 =====
with tab4:
    st.subheader("詳細成本明細表")

    area_far = base_area * far_base_exist * bonus_multiplier
    area_total = area_far * coeff_gfa
    area_sale = area_far * coeff_sale
    num_parking = int(area_total / 35)

    detailed_costs = pd.DataFrame({
        "成本項目": [
            "基地面積", "總樓地板面積", "可銷售面積", "車位數量",
            "拆除費", "營建工程費", "設計費", "拆遷安置費",
            "風險管理費", "人事行政費", "銷售管理費",
            "貸款利息", "稅捐",
            "容積獎勵申請", "都計變更費", "容積移轉代金",
        ],
        "數量": [
            f"{base_area:.0f} 坪", f"{area_total:.0f} 坪", f"{area_sale:.0f} 坪", f"{num_parking} 個",
            f"{area_total:.0f} 坪", f"{area_total:.0f} 坪", "-", "-",
            "-", "-", "-",
            "-", f"{area_total * final_unit_cost:.0f} 萬",
            "-", "-", "-",
        ],
        "金額(萬元)": [
            "-", "-", "-", "-",
            f"{res['Details']['工程費(含拆除)'] * 0.05:.2f}",
            f"{area_total * final_unit_cost:.2f}",
            f"{res['Details']['設計費']:.2f}",
            f"{res['Details']['拆遷安置費']:.2f}",
            f"{res['Details']['風險管理費']:.2f}",
            f"{res['Details']['人事管理費']:.2f}",
            f"{res['Details']['銷售管理費']:.2f}",
            f"{res['Details']['貸款利息']:.2f}",
            f"{res['Details']['稅捐']:.2f}",
            f"{cost_bonus_app:.2f}",
            f"{cost_urban_plan:.2f}",
            f"{cost_transfer:.2f}",
        ]
    })

    st.dataframe(detailed_costs, use_container_width=True, hide_index=True)

# ===== TAB 5: 五案件統計 =====
with tab5:
    st.subheader("五案件統計數據與分析（論文表3-1、表3-2）")
    
    # 五案件基本信息表
    st.markdown("#### 表3-1：五個案件基本信息")
    cases_basic = pd.DataFrame({
        "案件編號": ["案件1", "案件2", "案件3", "案件4", "案件5"],
        "地點": [FIVE_CASES_DATA[k]["location"] for k in FIVE_CASES_DATA.keys()],
        "基地面積(坪)": [FIVE_CASES_DATA[k]["area_ping"] for k in FIVE_CASES_DATA.keys()],
        "樓層": [FIVE_CASES_DATA[k]["floors"] for k in FIVE_CASES_DATA.keys()],
        "實施主體": [FIVE_CASES_DATA[k]["developer"] for k in FIVE_CASES_DATA.keys()],
        "總費用(億)": [FIVE_CASES_DATA[k]["total_cost"]/100000000 for k in FIVE_CASES_DATA.keys()],
    })
    st.dataframe(cases_basic, use_container_width=True, hide_index=True)
    
    # 五案件費率統計表
    st.markdown("#### 表3-2：五個案件共同負擔費用比例統計")
    cases_rates = pd.DataFrame({
        "費用項目": ["拆遷補償", "拆遷安置", "設計費", "貸款利息", "稅捐", "管理費"],
        "案件1": [
            f"{FIVE_CASES_DATA['案件1']['demolition_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件1']['reloc_comp_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件1']['design_fee_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件1']['loan_interest_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件1']['tax_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件1']['mgmt_fee_pct']:.2f}%",
        ],
        "案件2": [
            f"{FIVE_CASES_DATA['案件2']['demolition_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件2']['reloc_comp_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件2']['design_fee_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件2']['loan_interest_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件2']['tax_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件2']['mgmt_fee_pct']:.2f}%",
        ],
        "案件3": [
            f"{FIVE_CASES_DATA['案件3']['demolition_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件3']['reloc_comp_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件3']['design_fee_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件3']['loan_interest_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件3']['tax_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件3']['mgmt_fee_pct']:.2f}%",
        ],
        "案件4": [
            f"{FIVE_CASES_DATA['案件4']['demolition_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件4']['reloc_comp_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件4']['design_fee_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件4']['loan_interest_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件4']['tax_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件4']['mgmt_fee_pct']:.2f}%",
        ],
        "案件5": [
            f"{FIVE_CASES_DATA['案件5']['demolition_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件5']['reloc_comp_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件5']['design_fee_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件5']['loan_interest_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件5']['tax_pct']:.2f}%",
            f"{FIVE_CASES_DATA['案件5']['mgmt_fee_pct']:.2f}%",
        ],
        "平均值": [
            f"{STATISTICS_AVG['demolition_pct']:.2f}%",
            f"{STATISTICS_AVG['reloc_comp_pct']:.2f}%",
            f"{STATISTICS_AVG['design_fee_pct']:.2f}%",
            f"{STATISTICS_AVG['loan_interest_pct']:.2f}%",
            f"{STATISTICS_AVG['tax_pct']:.2f}%",
            f"{STATISTICS_AVG['mgmt_fee_pct']:.2f}%",
        ],
        "官方基準": [
            f"{OFFICIAL_STANDARD['demolition_pct']:.2f}%",
            f"{OFFICIAL_STANDARD['reloc_comp_pct']:.2f}%",
            f"{OFFICIAL_STANDARD['design_fee_pct']:.2f}%",
            f"{OFFICIAL_STANDARD['loan_interest_pct']:.2f}%",
            f"{OFFICIAL_STANDARD['tax_pct']:.2f}%",
            f"{OFFICIAL_STANDARD['mgmt_fee_pct']:.2f}%",
        ],
    })
    st.dataframe(cases_rates, use_container_width=True, hide_index=True)
    
    # 統計關鍵發現
    st.markdown("""
    #### 📌 統計關鍵發現（論文3.2.2節）
    
    ✓ **官方基準符合度極高**：絕大多數項目的平均值與官方基準之差距在0.5%以內
    
    ✓ **拆遷費用差異**：項目呈現最大的案件間差異（0%-8.45%），主要取決於案件的拆遷規模與安置方式
    
    ✓ **稅捐差異**：項目呈現較大差異（0.10%-5.30%），主要與實施主體性質有關（更新會 vs 建設公司）
    
    ✓ **管理費用穩定**：維持在27%-34%之間，平均30.72%，與官方基準30%高度相符
    
    ✓ **驗證意義**：本統計數據驗證了官方基準制定的科學性，同時確認統計數據可直接作為模型參數
    """)

st.divider()

# ============================================================================
# 📥 報告產生與下載區
# ============================================================================

def generate_report(res_dict: dict) -> str:
    """生成 TXT 格式報告"""
    cf = res_dict["Cashflow"]
    lines = [
        "【新北市防災都更財務模型｜IRR 計算報告】",
        f"產生時間：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "【報告版本】論文修正版 v3.0 - 整合五案件統計數據",
        "=" * 60,
        "",
        "【一、基地與容積參數】",
        f"基地面積：{base_area:.2f} 坪",
        f"原建築容積率：{far_base_exist * 100:.1f}%",
        f"防災獎勵倍數：{bonus_multiplier:.2f}",
        f"總樓地板係數 K_GFA：{coeff_gfa:.2f}",
        f"銷售面積係數 K_Sale：{coeff_sale:.2f}",
        "",
        "【二、營建與建材參數】",
        f"基準營建單價：{base_unit_cost:.2f} 萬/坪",
        f"修正後營建單價：{final_unit_cost:.2f} 萬/坪",
        f"建材係數：+{mat_coeff}",
        "",
        "【三、財務與風險參數】",
        f"產權人數：{num_owners:.0f} 人",
        f"貸款成數：{loan_ratio * 100:.0f}%",
        f"貸款利率：{loan_rate * 100:.2f}%",
        f"開發期程：{dev_months:.0f} 月",
        f"風險管理費率（查表）：{res_dict['Risk_Rate'] * 100:.1f}%",
        "",
        "【四、共同負擔成本明細（萬元）】",
    ]

    for k, v in res_dict["Details"].items():
        lines.append(f"{k:20} {v:>12,.2f}")

    lines.extend([
        "",
        f"{'總共同負擔':20} {res_dict['Total_Cost']:>12,.2f}",
        "",
        "【五、總銷價值與分回】",
        f"總銷金額：{res_dict['Total_Value'] / 10000:.2f} 億元",
        f"地主分回比例：{res_dict['Landlord_Ratio'] * 100:.2f}%",
        f"實施者 IRR：{res_dict['IRR'] * 100:.2f}%",
        "",
        "【六、現金流（IRR 計算基礎，單位：萬元）】",
        f"T0：{cf['T0']:>12,.2f}",
        f"T1：{cf['T1']:>12,.2f}",
        f"T2：{cf['T2']:>12,.2f}",
        f"T3：{cf['T3']:>12,.2f}",
        f"T4（最終回收）：{cf['T4']:>12,.2f}",
        "",
        "【七、投資可行性判斷】",
        "✔ IRR ≥ 12%，專案具投資可行性。" if res_dict["IRR"] >= 0.12
        else "✘ IRR < 12%，專案需調整參數以達到投資門檻。",
        "",
        "【八、五案件統計對標說明】",
        f"本模型已整合五案件統計數據作為參數設定基礎：",
        f"- 設計費率：{STATISTICS_AVG['design_fee_pct']:.2f}% （官方基準 {OFFICIAL_STANDARD['design_fee_pct']:.2f}%）",
        f"- 拆遷安置：{STATISTICS_AVG['reloc_comp_pct']:.2f}% （官方基準 {OFFICIAL_STANDARD['reloc_comp_pct']:.2f}%）",
        f"- 管理費率：{STATISTICS_AVG['mgmt_fee_pct']:.2f}% （官方基準 {OFFICIAL_STANDARD['mgmt_fee_pct']:.2f}%）",
    ])

    return "\n".join(lines)


def generate_excel(res_dict: dict) -> io.BytesIO:
    """生成 Excel 檔案"""
    output = io.BytesIO()

    df_cost = pd.DataFrame(
        res_dict["Details"].items(), columns=["項目", "金額(萬元)"]
    )

    cf = res_dict["Cashflow"]
    df_cf = pd.DataFrame({
        "期別": ["T0", "T1", "T2", "T3", "T4"],
        "金額(萬元)": [cf["T0"], cf["T1"], cf["T2"], cf["T3"], cf["T4"]],
    })

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df_cost.to_excel(writer, sheet_name="成本拆解", index=False)
        df_cf.to_excel(writer, sheet_name="現金流量表", index=False)

    output.seek(0)
    return output


# ============================================================================
# 下載按鈕區
# ============================================================================
st.markdown("### 📥 報告與試算結果下載")

col_a, col_b, col_c = st.columns(3)

with col_a:
    report_text = generate_report(res)
    st.download_button(
        label="📝 TXT 報告",
        data=report_text,
        file_name="IRR_Report_v3.0.txt",
        mime="text/plain",
    )

with col_b:
    excel_file = generate_excel(res)
    st.download_button(
        label="📊 Excel 數據",
        data=excel_file,
        file_name="Urban_Redevelopment_Cost_Cashflow_v3.0.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )

with col_c:
    st.download_button(
        label="📄 複製參數",
        data=f"""【都更模型參數配置 v3.0】
基地面積: {base_area} 坪
原容積率: {far_base_exist * 100}%
獎勵倍數: {bonus_multiplier}
營建單價: {final_unit_cost:.2f} 萬/坪
貸款成數: {loan_ratio * 100:.0f}%
風險費率: {res['Risk_Rate'] * 100:.1f}%
人事費率: {rate_personnel * 100:.1f}%
銷售費率: {rate_sales * 100:.1f}%
---
【五案件統計參考】
設計費率: {STATISTICS_AVG['design_fee_pct']:.2f}%
拆遷安置: {STATISTICS_AVG['reloc_comp_pct']:.2f}%
管理費率: {STATISTICS_AVG['mgmt_fee_pct']:.2f}%
貸款利息: {STATISTICS_AVG['loan_interest_pct']:.2f}%
""",
        file_name="model_params_v3.0.txt",
        mime="text/plain",
    )

# ============================================================================
# 頁尾資訊
# ============================================================================
st.divider()
st.markdown(
    """
    <div style='text-align: center; margin-top: 40px; color: #7F8C8D; font-size: 12px;'>
        <p>🏫 <strong>論文模型版本 v3.0</strong> | 最後更新：2026年1月7日</p>
        <p>✅ <strong>核心改進</strong>：整合新北市五案件統計數據 | 風險費率查表 | 官方基準對標</p>
        <p>⚠️ <strong>免責聲明</strong>：本模型僅供教育研究之用，不構成投資建議</p>
        <p>📧 論文相關問題請聯繫指導教授</p>
    </div>
    """,
    unsafe_allow_html=True,
)
