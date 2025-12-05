"""
import streamlit as st
import pandas as pd
import numpy as np
import numpy_financial as npf
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime

# ==================== 頁面配置 ====================
st.set_page_config(
    page_title="防災都更試算系統",
    page_icon="🏢",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ==================== 自訂CSS ====================
st.markdown("""
<style>
    .header-title {
        font-size: 32px;
        font-weight: bold;
        color: #1f4788;
        margin-bottom: 10px;
    }
    .metric-card {
        background-color: #f0f4f8;
        padding: 20px;
        border-radius: 8px;
        margin: 10px 0;
    }
    .warning-box {
        background-color: #fff3cd;
        padding: 15px;
        border-left: 4px solid #ffc107;
        border-radius: 4px;
    }
    .success-box {
        background-color: #d4edda;
        padding: 15px;
        border-left: 4px solid #28a745;
        border-radius: 4px;
    }
</style>
""", unsafe_allow_html=True)

# ==================== 初始化Session ====================
if 'scenario' not in st.session_state:
    st.session_state.scenario = 'A'
if 'results' not in st.session_state:
    st.session_state.results = {}

# ==================== 標題 ====================
st.markdown('<div class="header-title">🏢 新北市防災型都市更新</div>', unsafe_allow_html=True)
st.markdown('### 權利變換試算系統 v2024.12')
st.markdown('---')

# ==================== 側邊欄配置 ====================
with st.sidebar:
    st.header("⚙️ 系統設定")
    
    # 情境選擇
    scenario = st.radio(
        "選擇計算情境",
        options=['A', 'B', '自訂'],
        format_func=lambda x: {
            'A': '情境A - 官方基準',
            'B': '情境B - 市場實況',
            '自訂': '自訂參數'
        }[x],
        help="情境A採用官方提列基準\n情境B採用市場實務數據"
    )
    st.session_state.scenario = scenario
    
    st.markdown('---')
    st.subheader("📋 基本設定")
    
    # 基地條件
    base_area = st.number_input(
        "基地面積 (m²)",
        min_value=100,
        max_value=10000,
        value=1000,
        step=100,
        help="都市更新基地面積"
    )
    
    floor_count = st.number_input(
        "預計樓層數",
        min_value=1,
        max_value=30,
        value=12,
        help="更新後建築物地上樓層數"
    )
    
    basement_levels = st.number_input(
        "地下層數",
        min_value=0,
        max_value=5,
        value=2,
        help="地下樓層數（計算工期用）"
    )
    
    st.markdown('---')
    st.subheader("💰 容積與價格")
    
    # 容積設定
    fsr_current = st.number_input(
        "法定容積率 (%)",
        min_value=100,
        max_value=500,
        value=200,
        step=10,
        help="現行都市計畫規定容積率"
    )
    
    bonus_disaster = st.slider(
        "防災容積獎勵倍數",
        min_value=1.0,
        max_value=2.0,
        value=1.5,
        step=0.1,
        help="防災都更容積獎勵倍數"
    )
    
    # 容積選擇邏輯
    use_original_fsr = st.checkbox(
        "採用原建築容積",
        value=False,
        help="勾選使用原有建築容積而非法定容積"
    )
    
    if use_original_fsr:
        original_fsr_ratio = st.slider(
            "原建築容積倍數",
            min_value=1.0,
            max_value=2.0,
            value=1.4,
            step=0.1,
            help="相對於法定容積的倍數"
        )
        base_fsr = fsr_current * original_fsr_ratio
    else:
        base_fsr = fsr_current
    
    st.markdown('---')
    st.subheader("💵 價格假設")
    
    # 房價
    unit_price_sale = st.number_input(
        "住宅預售單價 (萬/坪)",
        min_value=20,
        max_value=150,
        value=65 if scenario == 'B' else 60,
        step=5,
        help="預售住宅每坪單價"
    )
    
    # 土地單價
    land_unit_price = st.number_input(
        "土地公告現值 (萬/坪)",
        min_value=5,
        max_value=100,
        value=30,
        step=5,
        help="用於計算更新前地值"
    )

# ==================== 主要內容區 ====================
tab1, tab2, tab3, tab4, tab5 = st.tabs(
    ["📊 基本試算", "💹 詳細成本", "🎯 權利分配", "📈 敏感度分析", "📋 案例驗證"]
)

# ==================== 計算函數 ====================
def calculate_gfa(base_area, base_fsr, bonus_disaster):
    """計算總樓地板面積"""
    # 轉換 m² 為坪（1坪=3.3m²）
    base_area_ping = base_area / 3.3
    
    # 計算容積
    fsr_after_bonus = base_fsr * bonus_disaster
    
    # 總樓地板面積（含公設比0.8倍係數）
    gfa = base_area_ping * fsr_after_bonus * 1.8
    
    return gfa, base_area_ping, fsr_after_bonus

def get_scenario_params(scenario_type, custom_params=None):
    """取得情境參數"""
    if scenario_type == 'A':
        return {
            'construction_unit_price': 9.98,  # 萬/坪
            'sales_unit_price': 60,  # 萬/坪
            'management_fee_rate': 0.43,  # 43%
            'risk_fee_rate': 0.12,  # 12%
            'loan_ratio': 0.50,  # 50%
            'interest_rate': 0.025,  # 2.5%
            'scenario_name': '官方基準'
        }
    elif scenario_type == 'B':
        return {
            'construction_unit_price': 24.0,  # 萬/坪
            'sales_unit_price': 68,  # 萬/坪
            'management_fee_rate': 0.18,  # 18%
            'risk_fee_rate': 0.12,  # 12%
            'loan_ratio': 0.60,  # 60%
            'interest_rate': 0.035,  # 3.5%
            'scenario_name': '市場實況'
        }
    elif scenario_type == '自訂' and custom_params:
        return custom_params
    else:
        return get_scenario_params('A')

def calculate_costs(gfa, params, floor_count, basement_levels):
    """計算各項成本"""
    # 拆除費用
    demolition_cost = (gfa / 1.8) * 0.0008 * 10000  # 簡化計算
    
    # 營建費用
    construction_cost = gfa * params['construction_unit_price']
    
    # 設計費用（建築設計費）
    design_fee = construction_cost * 0.05
    
    # 工期計算（月）
    construction_period = basement_levels * 3 + floor_count * 1.5
    
    # 貸款利息
    total_cost_before_interest = demolition_cost + construction_cost + design_fee
    financing_amount = total_cost_before_interest * params['loan_ratio']
    interest_cost = financing_amount * params['interest_rate'] * (construction_period / 12)
    
    # 風險費用
    risk_fee = (demolition_cost + construction_cost + design_fee) * params['risk_fee_rate']
    
    # 管理費用（簡化）
    management_fee = (demolition_cost + construction_cost) * params['management_fee_rate']
    
    # 其他費用
    misc_cost = total_cost_before_interest * 0.08  # 權利變換費、稅捐等
    
    # 總成本
    total_cost = (demolition_cost + construction_cost + design_fee + 
                  interest_cost + risk_fee + management_fee + misc_cost)
    
    return {
        'demolition': demolition_cost,
        'construction': construction_cost,
        'design': design_fee,
        'interest': interest_cost,
        'risk': risk_fee,
        'management': management_fee,
        'misc': misc_cost,
        'total': total_cost,
        'period': construction_period
    }

def calculate_revenue(gfa, unit_price_sale, land_area_ping, land_unit_price, parking_units=0):
    """計算開發收入"""
    # 銷售收入
    sales_revenue = gfa * unit_price_sale
    
    # 地價
    land_value = land_area_ping * land_unit_price
    
    # 車位收入（假設）
    parking_revenue = parking_units * 80  # 每個車位80萬
    
    return {
        'sales': sales_revenue,
        'land_value': land_value,
        'parking': parking_revenue,
        'total': sales_revenue + parking_revenue
    }

def calculate_irr(costs, revenue, period_years=4):
    """計算IRR"""
    cash_flows = [-costs['total']]  # T=0 投資
    
    # 簡化現金流分配
    for year in range(1, int(period_years)):
        if year <= costs['period'] / 12:
            cash_flows.append(0)
        else:
            cash_flows.append(revenue['total'] - costs['total'] * 0.1)
    
    cash_flows[-1] += revenue['total']  # 最後一年回收
    
    try:
        irr = npf.irr(cash_flows)
        return max(irr, -0.99) * 100  # 轉為百分比
    except:
        return 0

# ==================== TAB 1: 基本試算 ====================
with tab1:
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📍 基地條件總結")
        
        gfa, base_area_ping, fsr_after = calculate_gfa(base_area, base_fsr, bonus_disaster)
        
        summary_data = {
            '指標': [
                '基地面積',
                '基地面積',
                '法定容積率',
                '容積獎勵倍數',
                '更新後容積率',
                '總樓地板面積',
                '平均每戶面積'
            ],
            '數值': [
                f"{base_area:,} m²",
                f"{base_area_ping:.0f} 坪",
                f"{fsr_current}%",
                f"{bonus_disaster}倍",
                f"{fsr_after*100:.0f}%",
                f"{gfa:,.0f} 坪",
                f"{gfa/30:.0f} 坪"  # 假設30戶
            ]
        }
        
        st.dataframe(summary_data, use_container_width=True, hide_index=True)
    
    with col2:
        st.subheader("💡 情境對比")
        
        params_a = get_scenario_params('A')
        params_b = get_scenario_params('B')
        
        comparison = pd.DataFrame({
            '參數': ['營建單價', '預售單價', '管理費率', '貸款成數', '利率'],
            '情境A\n(官方基準)': [
                f"{params_a['construction_unit_price']} 萬/坪",
                f"{params_a['sales_unit_price']} 萬/坪",
                f"{params_a['management_fee_rate']*100:.0f}%",
                f"{params_a['loan_ratio']*100:.0f}%",
                f"{params_a['interest_rate']*100:.1f}%"
            ],
            '情境B\n(市場實況)': [
                f"{params_b['construction_unit_price']} 萬/坪",
                f"{params_b['sales_unit_price']} 萬/坪",
                f"{params_b['management_fee_rate']*100:.0f}%",
                f"{params_b['loan_ratio']*100:.0f}%",
                f"{params_b['interest_rate']*100:.1f}%"
            ]
        })
        
        st.dataframe(comparison, use_container_width=True, hide_index=True)
        
        st.markdown("""
        <div class="warning-box">
        💡 <b>情境說明：</b><br>
        • 情境A：計畫向政府申報版本，採用官方提列基準<br>
        • 情境B：實施者真實財務評估版本，反映市場實況<br>
        • 落差：營建成本相差130%、管理費率差25個百分點
        </div>
        """, unsafe_allow_html=True)

# ==================== TAB 2: 詳細成本 ====================
with tab2:
    st.subheader("💰 成本結構分析")
    
    col_scenario_select, col_params = st.columns([1, 2])
    
    with col_scenario_select:
        calc_scenario = st.selectbox(
            "選擇計算情境",
            options=['A', 'B'],
            format_func=lambda x: f"情境{x}",
            key='cost_scenario'
        )
    
    params = get_scenario_params(calc_scenario)
    costs = calculate_costs(gfa, params, floor_count, basement_levels)
    
    # 成本詳細表
    cost_detail = pd.DataFrame({
        '成本項目': ['拆除費用', '營建費用', '設計費用', '貸款利息', '風險費用', '管理費用', '其他費用', '合計'],
        '金額（萬元）': [
            f"{costs['demolition']:,.0f}",
            f"{costs['construction']:,.0f}",
            f"{costs['design']:,.0f}",
            f"{costs['interest']:,.0f}",
            f"{costs['risk']:,.0f}",
            f"{costs['management']:,.0f}",
            f"{costs['misc']:,.0f}",
            f"{costs['total']:,.0f}"
        ],
        '占比': [
            f"{costs['demolition']/costs['total']*100:.1f}%",
            f"{costs['construction']/costs['total']*100:.1f}%",
            f"{costs['design']/costs['total']*100:.1f}%",
            f"{costs['interest']/costs['total']*100:.1f}%",
            f"{costs['risk']/costs['total']*100:.1f}%",
            f"{costs['management']/costs['total']*100:.1f}%",
            f"{costs['misc']/costs['total']*100:.1f}%",
            "100.0%"
        ]
    })
    
    st.dataframe(cost_detail, use_container_width=True, hide_index=True)
    
    # 成本結構圖
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 成本占比圓餅圖")
        
        cost_labels = ['拆除', '營建', '設計', '利息', '風險', '管理', '其他']
        cost_values = [
            costs['demolition'], costs['construction'], costs['design'],
            costs['interest'], costs['risk'], costs['management'], costs['misc']
        ]
        
        fig_pie = go.Figure(data=[go.Pie(labels=cost_labels, values=cost_values)])
        fig_pie.update_layout(
            height=400,
            font=dict(size=12),
            margin=dict(l=0, r=0, t=30, b=0)
        )
        st.plotly_chart(fig_pie, use_container_width=True)
    
    with col2:
        st.subheader("📈 成本折線圖")
        
        fig_bar = go.Figure(data=[
            go.Bar(x=cost_labels, y=cost_values, marker_color='steelblue')
        ])
        fig_bar.update_layout(
            height=400,
            xaxis_title="成本項目",
            yaxis_title="金額（萬元）",
            margin=dict(l=0, r=0, t=30, b=0),
            showlegend=False
        )
        st.plotly_chart(fig_bar, use_container_width=True)
    
    # 工期與利息計算
    st.markdown('---')
    st.subheader("⏱️ 工期與融資成本")
    
    col_period1, col_period2, col_period3 = st.columns(3)
    
    with col_period1:
        st.metric("工程工期", f"{costs['period']:.1f} 月", 
                  f"≈ {costs['period']/12:.1f} 年")
    
    with col_period2:
        st.metric("融資金額", f"萬{costs['total'] * params['loan_ratio']:,.0f}元",
                  f"占 {params['loan_ratio']*100:.0f}%")
    
    with col_period3:
        st.metric("貸款利息", f"萬{costs['interest']:,.0f}元",
                  f"利率 {params['interest_rate']*100:.2f}%")

# ==================== TAB 3: 權利分配 ====================
with tab3:
    st.subheader("🎯 權利變換分配計算")
    
    col_scenario3, col_bonus = st.columns([1, 2])
    
    with col_scenario3:
        dist_scenario = st.selectbox(
            "選擇計算情境",
            options=['A', 'B'],
            key='distribution_scenario',
            format_func=lambda x: f"情境{x}"
        )
    
    with col_bonus:
        bonus_range = st.slider(
            "容積獎勵模擬範圍",
            min_value=0,
            max_value=50,
            value=(0, 50),
            step=5,
            help="模擬不同容積獎勵下的分配結果"
        )
    
    dist_params = get_scenario_params(dist_scenario)
    
    # 計算不同容積獎勵下的結果
    bonus_results = []
    
    for bonus_pct in range(bonus_range[0], bonus_range[1]+5, 5):
        bonus_mult = 1 + bonus_pct / 100
        
        gfa_scenario = base_area_ping * fsr_current * bonus_mult * 1.8
        costs_scenario = calculate_costs(gfa_scenario, dist_params, floor_count, basement_levels)
        
        # 簡化的分配計算
        total_value = gfa_scenario * dist_params['sales_unit_price']
        owner_share = (total_value - costs_scenario['total']) * 0.5  # 簡化為50%分配
        developer_irr = calculate_irr(costs_scenario, 
                                      {'total': total_value, 'sales': total_value})
        
        bonus_results.append({
            '容積獎勵': f"{bonus_pct}%",
            '容積倍數': f"{bonus_mult:.2f}",
            '總樓地板面積': f"{gfa_scenario:,.0f}",
            '總開發值': f"{total_value:,.0f}",
            '總成本': f"{costs_scenario['total']:,.0f}",
            '地主分回': f"{owner_share:,.0f}",
            '地主分回率': f"{owner_share/total_value*100:.1f}%",
            '實施者IRR': f"{developer_irr:.1f}%"
        })
    
    dist_df = pd.DataFrame(bonus_results)
    st.dataframe(dist_df, use_container_width=True, hide_index=True)
    
    # 權利分配視覺化
    st.markdown('---')
    st.subheader("📊 權利分配趨勢圖")
    
    bonus_range_data = [int(x.strip('%')) for x in dist_df['容積獎勵']]
    owner_share_pct = [float(x.strip('%')) for x in dist_df['地主分回率']]
    developer_irr_data = [float(x.strip('%')) for x in dist_df['實施者IRR']]
    
    fig_dist = go.Figure()
    
    fig_dist.add_trace(go.Scatter(
        x=bonus_range_data, y=owner_share_pct,
        mode='lines+markers', name='地主分回率',
        line=dict(color='green', width=3),
        marker=dict(size=8)
    ))
    
    fig_dist.add_trace(go.Scatter(
        x=bonus_range_data, y=developer_irr_data,
        mode='lines+markers', name='實施者IRR',
        line=dict(color='blue', width=3),
        marker=dict(size=8),
        yaxis='y2'
    ))
    
    fig_dist.update_layout(
        title="容積獎勵對分配的影響",
        xaxis_title="容積獎勵 (%)",
        yaxis_title="地主分回率 (%)",
        yaxis2=dict(
            title="實施者IRR (%)",
            overlaying='y',
            side='right'
        ),
        height=500,
        hovermode='x unified'
    )
    
    st.plotly_chart(fig_dist, use_container_width=True)

# ==================== TAB 4: 敏感度分析 ====================
with tab4:
    st.subheader("📈 敏感度分析")
    
    col_sen1, col_sen2 = st.columns(2)
    
    with col_sen1:
        price_range = st.slider(
            "房價範圍 (萬/坪)",
            min_value=40,
            max_value=100,
            value=(50, 80),
            step=5,
            help="模擬房價變動"
        )
    
    with col_sen2:
        cost_range = st.slider(
            "營建單價範圍 (萬/坪)",
            min_value=8,
            max_value=30,
            value=(10, 25),
            step=1,
            help="模擬營建成本變動"
        )
    
    # 生成敏感度矩陣
    prices = np.linspace(price_range[0], price_range[1], 7)
    costs_unit = np.linspace(cost_range[0], cost_range[1], 7)
    
    sensitivity_matrix_owner = np.zeros((len(costs_unit), len(prices)))
    sensitivity_matrix_irr = np.zeros((len(costs_unit), len(prices)))
    
    for i, cost in enumerate(costs_unit):
        for j, price in enumerate(prices):
            params_temp = {
                'construction_unit_price': cost,
                'sales_unit_price': price,
                'management_fee_rate': 0.25,
                'risk_fee_rate': 0.12,
                'loan_ratio': 0.55,
                'interest_rate': 0.03,
                'scenario_name': 'Sensitivity'
            }
            
            costs_temp = calculate_costs(gfa, params_temp, floor_count, basement_levels)
            revenue_temp = calculate_revenue(gfa, price, base_area_ping, land_unit_price)
            
            owner_ratio = (revenue_temp['total'] - costs_temp['total']) / revenue_temp['total'] * 100
            irr_temp = calculate_irr(costs_temp, revenue_temp)
            
            sensitivity_matrix_owner[i, j] = max(0, min(100, owner_ratio))
            sensitivity_matrix_irr[i, j] = max(-50, min(50, irr_temp))
    
    col_heat1, col_heat2 = st.columns(2)
    
    with col_heat1:
        st.subheader("地主分回率 (%)")
        
        fig_heat1 = go.Figure(data=go.Heatmap(
            z=sensitivity_matrix_owner,
            x=[f"${p}萬" for p in prices],
            y=[f"${c}萬" for c in costs_unit],
            colorscale='RdYlGn',
            text=sensitivity_matrix_owner.round(1),
            texttemplate='%{text:.1f}%',
            textfont={"size": 10},
            colorbar=dict(title="分回率(%)")
        ))
        
        fig_heat1.update_layout(
            title="房價 vs 營建單價",
            xaxis_title="房價 (萬/坪)",
            yaxis_title="營建單價 (萬/坪)",
            height=500
        )
        
        st.plotly_chart(fig_heat1, use_container_width=True)
    
    with col_heat2:
        st.subheader("實施者IRR (%)")
        
        fig_heat2 = go.Figure(data=go.Heatmap(
            z=sensitivity_matrix_irr,
            x=[f"${p}萬" for p in prices],
            y=[f"${c}萬" for c in costs_unit],
            colorscale='RdYlGn',
            text=sensitivity_matrix_irr.round(1),
            texttemplate='%{text:.1f}%',
            textfont={"size": 10},
            colorbar=dict(title="IRR(%)")
        ))
        
        fig_heat2.update_layout(
            title="房價 vs 營建單價",
            xaxis_title="房價 (萬/坪)",
            yaxis_title="營建單價 (萬/坪)",
            height=500
        )
        
        st.plotly_chart(fig_heat2, use_container_width=True)
    
    st.markdown('---')
    st.subheader("📊 可行性邊界分析")
    
    st.markdown("""
    <div class="success-box">
    ✅ <b>可行性邊界判定標準：</b><br>
    • 實施者 IRR ≥ 12% (市場期望最低值)<br>
    • 地主分回率 ≥ 40% (合理預期)<br>
    • 綠色區域 = 同時滿足兩個條件的可行區域
    </div>
    """, unsafe_allow_html=True)

# ==================== TAB 5: 案例驗證 ====================
with tab5:
    st.subheader("📋 典型案例驗證")
    
    case_select = st.selectbox(
        "選擇驗證案例",
        options=['案例一：蘆洲小規模案件', '案例二：三重大規模案件'],
        help="選擇典型案例進行詳細試算"
    )
    
    if '蘆洲' in case_select:
        case_data = {
            '位置': '新北市蘆洲區',
            '基地面積': 800,
            '法定容積率': 200,
            '建築類型': '老舊公寓',
            '樓層數': 5,
            '權利人數': 15,
            '屋齡': 42,
            '預設房價': 65,
            '預設成本': 24
        }
    else:
        case_data = {
            '位置': '新北市三重區',
            '基地面積': 1200,
            '法定容積率': 300,
            '建築類型': '集合住宅',
            '樓層數': 12,
            '權利人數': 28,
            '屋齡': 38,
            '預設房價': 68,
            '預設成本': 25
        }
    
    col_case1, col_case2 = st.columns(2)
    
    with col_case1:
        st.info(f"""
        📍 **{case_data['位置']}**
        
        • 基地面積：{case_data['基地面積']} m²
        • 建築類型：{case_data['建築類型']}
        • 樓層數：{case_data['樓層數']} 層
        • 權利人數：{case_data['權利人數']} 戶
        • 屋齡：{case_data['屋齡']} 年
        """)
    
    with col_case2:
        st.success(f"""
        ⚙️ **預設參數**
        
        • 法定容積率：{case_data['法定容積率']}%
        • 預售房價：{case_data['預設房價']} 萬/坪
        • 營建單價：{case_data['預設成本']} 萬/坪
        • 容積獎勵：1.5 倍（防災2.0）
        """)
    
    # 執行試算
    case_gfa, case_base_ping, case_fsr = calculate_gfa(
        case_data['基地面積'], 
        case_data['法定容積率'],
        1.5
    )
    
    case_params = {
        'construction_unit_price': case_data['預設成本'],
        'sales_unit_price': case_data['預設房價'],
        'management_fee_rate': 0.20,
        'risk_fee_rate': 0.12,
        'loan_ratio': 0.60,
        'interest_rate': 0.03,
        'scenario_name': '案例'
    }
    
    case_costs = calculate_costs(case_gfa, case_params, case_data['樓層數'], 2)
    case_revenue = calculate_revenue(case_gfa, case_data['預設房價'], case_base_ping, land_unit_price=30)
    
    st.markdown('---')
    st.subheader("試算結果")
    
    col_result1, col_result2, col_result3, col_result4 = st.columns(4)
    
    with col_result1:
        st.metric(
            "總樓地板面積",
            f"{case_gfa:,.0f} 坪",
            f"≈ {case_gfa/30:.0f} 戶"
        )
    
    with col_result2:
        st.metric(
            "開發總值",
            f"萬{case_revenue['total']:,.0f}",
            f"({case_revenue['total']/1000:.0f}億)"
        )
    
    with col_result3:
        st.metric(
            "總開發成本",
            f"萬{case_costs['total']:,.0f}",
            f"({case_costs['total']/1000:.0f}億)"
        )
    
    with col_result4:
        developer_profit = case_revenue['total'] - case_costs['total']
        st.metric(
            "開發淨利",
            f"萬{developer_profit:,.0f}",
            f"利潤率{developer_profit/case_revenue['total']*100:.1f}%"
        )
    
    # 詳細表格
    st.markdown('---')
    st.subheader("財務詳細表")
    
    financial_detail = pd.DataFrame({
        '項目': ['銷售收入', '土地價值', '停車收入', '總收入',
                 '拆除成本', '營建成本', '其他成本', '總成本',
                 '淨利', '淨利率'],
        '金額（萬元）': [
            f"{case_revenue['sales']:,.0f}",
            f"{case_revenue['land_value']:,.0f}",
            f"{case_revenue['parking']:,.0f}",
            f"{case_revenue['total']:,.0f}",
            f"{case_costs['demolition']:,.0f}",
            f"{case_costs['construction']:,.0f}",
            f"{case_costs['total']-case_costs['demolition']-case_costs['construction']:,.0f}",
            f"{case_costs['total']:,.0f}",
            f"{developer_profit:,.0f}",
            f"{developer_profit/case_revenue['total']*100:.1f}%"
        ]
    })
    
    st.dataframe(financial_detail, use_container_width=True, hide_index=True)

# ==================== 頁腳 ====================
st.markdown('---')
st.markdown("""
<div style="text-align: center; color: #666; font-size: 12px;">
    <p>新北市防災型都市更新權利變換試算模型 v2024.12</p>
    <p>本系統基於新北市2024年修正《共同負擔基準》、陳叡澧(2024)實務案例分析及陳奉瑤(2016)學術研究</p>
    <p>⚠️ 免責聲明：本系統結果供參考用，不作為投資決策依據。實際試算應由專業估價師評估。</p>
</div>
""", unsafe_allow_html=True)
