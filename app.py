import streamlit as st
import numpy as np
import plotly.graph_objects as go

# --- 策略說明字典 (無變動) ---
STRATEGY_DESCRIPTIONS = {
    "Bull Call Spread": "<b>看法:</b> 看漲 (Bullish)<br><b>資金:</b> 支付權利金 (Debit)<br>買進較低履約價的Call，同時賣出較高履約價的Call，以支付的權利金賭股價上漲。",
    "Bear Put Spread": "<b>看法:</b> 看跌 (Bearish)<br><b>資金:</b> 支付權利金 (Debit)<br>買進較高履約價的Put，同時賣出較低履約價的Put，以支付的權利金賭股價下跌。",
    "Bull Put Spread": "<b>看法:</b> 看漲或盤整 (Bullish/Neutral)<br><b>資金:</b> 收入權利金 (Credit)<br>賣出較高履約價的Put，同時買進較低履約價的Put來保護，以賺取時間價值。",
    "Bear Call Spread": "<b>看法:</b> 看跌或盤整 (Bearish/Neutral)<br><b>資金:</b> 收入權利金 (Credit)<br>賣出較低履約價的Call，同時買進較高履約價的Call來保護，以賺取時間價值。",
    "Butterfly Spread": "<b>看法:</b> 盤整 (Neutral)<br><b>資金:</b> 支付權利金 (Debit)<br>賭股價在特定小範圍內波動。通常是買一個低位、一個高位，賣出兩個中間價位的選擇權。",
    "Iron Condor": "<b>看法:</b> 盤整 (Neutral)<br><b>資金:</b> 收入權利金 (Credit)<br>同時賣出一個看跌的信用價差和一個看漲的信用價差，賭股價在寬廣的區間內波動。"
}


# --- 核心計算函式 (無變動) ---
def calculate_payoff(S, strategy_details):
    total_payoff_points = np.zeros_like(S, dtype=float)
    for leg in strategy_details:
        K, premium, direction, option_type = leg['strike'], leg['premium'], (1 if leg['type'].startswith('long') else -1), ('call' in leg['type'])
        intrinsic_value = np.maximum(0, S - K) if option_type else np.maximum(0, K - S)
        total_payoff_points += direction * intrinsic_value
    return total_payoff_points

def find_break_even_points(S, PnL):
    indices = np.where(np.diff(np.sign(PnL)))[0]
    break_evens = [S[i] - PnL[i] * (S[i+1] - S[i]) / (PnL[i+1] - PnL[i]) for i in indices if PnL[i+1] - PnL[i] != 0]
    return break_evens

def calculate_us_margin(strategy_name, strategy_details, multiplier):
    net_premium = sum([leg['premium'] if leg['type'].startswith('short') else -leg['premium'] for leg in strategy_details])
    if net_premium <= 0: return 0
    margin = 0
    if strategy_name in ["Iron Condor", "Bull Put Spread", "Bear Call Spread"]:
        k_values = [leg['strike'] for leg in strategy_details]
        margin = (max(k_values) - min(k_values)) * multiplier
        if strategy_name == "Iron Condor":
            k_calls = sorted([leg['strike'] for leg in strategy_details if 'call' in leg['type']])
            margin = (k_calls[1] - k_calls[0]) * multiplier
    return margin

# --- Streamlit UI 介面 (無變動) ---
st.set_page_config(layout="wide")
st.title("📈 美股選擇權策略分析器 (US Options Strategy Analyzer)")
st.write("此工具根據標準美股選擇權規則，視覺化策略的損益與分析所需資金。")

# --- 側邊欄輸入 (無變動) ---
st.sidebar.header("⚙️ 參數設定")
multiplier = st.sidebar.number_input("契約乘數 (Contract Multiplier)", value=100, help="美股選擇權的契約乘數固定為 100。")
strategy_name = st.sidebar.selectbox(
    "選擇策略 (Select Strategy)",
    ["Bull Call Spread", "Bear Put Spread", "Bull Put Spread", "Bear Call Spread", "Butterfly Spread", "Iron Condor"]
)
st.sidebar.markdown("---")
with st.sidebar.expander(f"📖 查看「{strategy_name}」策略說明"):
    st.markdown(STRATEGY_DESCRIPTIONS[strategy_name], unsafe_allow_html=True)
st.sidebar.markdown("---")

# --- 參數輸入區塊 (無變動) ---
strategy_details, strikes, error_message = [], [], ""
if strategy_name == "Bull Call Spread":
    st.sidebar.subheader("買權多頭價差 (看漲)")
    k_low = st.sidebar.number_input("買進買權履約價 (Long Call)", value=100.0, step=1.0)
    p_low = st.sidebar.number_input("權利金 (Premium)", value=2.50, step=0.01, format="%.2f")
    k_high = st.sidebar.number_input("賣出買權履約價 (Short Call)", value=110.0, step=1.0)
    p_high = st.sidebar.number_input("權利金 (Premium)", value=0.80, step=0.01, format="%.2f")
    if k_low >= k_high: error_message = "邏輯錯誤：Long Call 的履約價必須低於 Short Call。"
    strategy_details = [{'type': 'long_call', 'strike': k_low, 'premium': p_low}, {'type': 'short_call', 'strike': k_high, 'premium': p_high}]
    strikes = [k_low, k_high]

elif strategy_name == "Bear Put Spread":
    st.sidebar.subheader("賣權空頭價差 (看跌)")
    k_high = st.sidebar.number_input("買進賣權履約價 (Long Put)", value=100.0, step=1.0)
    p_high = st.sidebar.number_input("權利金 (Premium)", value=3.00, step=0.01, format="%.2f")
    k_low = st.sidebar.number_input("賣出賣權履約價 (Short Put)", value=90.0, step=1.0)
    p_low = st.sidebar.number_input("權利金 (Premium)", value=1.20, step=0.01, format="%.2f")
    if k_low >= k_high: error_message = "邏輯錯誤：Long Put 的履約價必須高於 Short Put。"
    strategy_details = [{'type': 'long_put', 'strike': k_high, 'premium': p_high}, {'type': 'short_put', 'strike': k_low, 'premium': p_low}]
    strikes = [k_low, k_high]

elif strategy_name == "Bull Put Spread":
    st.sidebar.subheader("賣權牛市價差 (看漲)")
    k_high = st.sidebar.number_input("賣出賣權履約價 (Short Put)", value=100.0, step=1.0)
    p_high = st.sidebar.number_input("權利金 (Premium)", value=3.00, step=0.01, format="%.2f")
    k_low = st.sidebar.number_input("買進賣權履約價 (Long Put)", value=90.0, step=1.0)
    p_low = st.sidebar.number_input("權利金 (Premium)", value=1.20, step=0.01, format="%.2f")
    if k_low >= k_high: error_message = "邏輯錯誤：Short Put 的履約價必須高於 Long Put。"
    strategy_details = [{'type': 'short_put', 'strike': k_high, 'premium': p_high}, {'type': 'long_put', 'strike': k_low, 'premium': p_low}]
    strikes = [k_low, k_high]

elif strategy_name == "Bear Call Spread":
    st.sidebar.subheader("買權熊市價差 (看跌)")
    k_low = st.sidebar.number_input("賣出買權履約價 (Short Call)", value=100.0, step=1.0)
    p_low = st.sidebar.number_input("權利金 (Premium)", value=2.50, step=0.01, format="%.2f")
    k_high = st.sidebar.number_input("買進買權履約價 (Long Call)", value=110.0, step=1.0)
    p_high = st.sidebar.number_input("權利金 (Premium)", value=0.80, step=0.01, format="%.2f")
    if k_low >= k_high: error_message = "邏輯錯誤：Short Call 的履約價必須低於 Long Call。"
    strategy_details = [{'type': 'short_call', 'strike': k_low, 'premium': p_low}, {'type': 'long_call', 'strike': k_high, 'premium': p_high}]
    strikes = [k_low, k_high]

elif strategy_name == "Butterfly Spread":
    st.sidebar.subheader("蝶式價差 (買權)")
    k_low = st.sidebar.number_input("買進低履約價買權 (Wing 1)", value=95.0, step=1.0)
    p_low = st.sidebar.number_input("權利金 (Premium)", value=6.00, step=0.01, format="%.2f")
    k_mid = st.sidebar.number_input("賣出中間履約價買權 x2 (Body)", value=105.0, step=1.0)
    p_mid = st.sidebar.number_input("權利金 (Premium)", value=2.00, step=0.01, format="%.2f")
    k_high = st.sidebar.number_input("買進高履約價買權 (Wing 2)", value=115.0, step=1.0)
    p_high = st.sidebar.number_input("權利金 (Premium)", value=0.50, step=0.01, format="%.2f")
    if not (k_low < k_mid < k_high): error_message = "邏輯錯誤：履約價必須是 Wing 1 < Body < Wing 2。"
    strategy_details = [{'type': 'long_call', 'strike': k_low, 'premium': p_low}, {'type': 'short_call', 'strike': k_mid, 'premium': p_mid}, {'type': 'short_call', 'strike': k_mid, 'premium': p_mid}, {'type': 'long_call', 'strike': k_high, 'premium': p_high}]
    strikes = [k_low, k_mid, k_high]

elif strategy_name == "Iron Condor":
    st.sidebar.subheader("鐵兀鷹")
    k_lp = st.sidebar.number_input("買進賣權履約價 (Long Put Wing)", value=90.0, step=1.0)
    p_lp = st.sidebar.number_input("權利金 (Premium)", value=0.50, step=0.01, format="%.2f")
    k_sp = st.sidebar.number_input("賣出賣權履約價 (Short Put Body)", value=95.0, step=1.0)
    p_sp = st.sidebar.number_input("權利金 (Premium)", value=1.50, step=0.01, format="%.2f")
    k_sc = st.sidebar.number_input("賣出買權履約價 (Short Call Body)", value=105.0, step=1.0)
    p_sc = st.sidebar.number_input("權利金 (Premium)", value=1.80, step=0.01, format="%.2f")
    k_lc = st.sidebar.number_input("買進買權履約價 (Long Call Wing)", value=110.0, step=1.0)
    p_lc = st.sidebar.number_input("權利金 (Premium)", value=0.60, step=0.01, format="%.2f")
    if not (k_lp < k_sp < k_sc < k_lc): error_message = "邏輯錯誤：履約價必須依序遞增。"
    strategy_details = [{'type': 'long_put', 'strike': k_lp, 'premium': p_lp}, {'type': 'short_put', 'strike': k_sp, 'premium': p_sp}, {'type': 'short_call', 'strike': k_sc, 'premium': p_sc}, {'type': 'long_call', 'strike': k_lc, 'premium': p_lc}]
    strikes = [k_lp, k_sp, k_sc, k_lc]


# --- 主面板顯示區塊 ---
if error_message:
    st.error(f"**輸入錯誤：** {error_message}", icon="🚨")
    st.warning("請修正左側側邊欄的履約價以繼續分析。")
elif strategy_details:
    min_strike, max_strike = min(strikes), max(strikes)
    buffer = (max_strike - min_strike) * 1.5 if max_strike > min_strike else 20
    S = np.arange(min_strike - buffer, max_strike + buffer, 0.5)
    net_premium_points = sum([leg['premium'] if leg['type'].startswith('short') else -leg['premium'] for leg in strategy_details])
    pnl_currency = (calculate_payoff(S, strategy_details) + net_premium_points) * multiplier
    max_profit, max_loss = np.max(pnl_currency), np.min(pnl_currency)
    break_evens = find_break_even_points(S, pnl_currency)
    net_cost_credit = net_premium_points * multiplier
    margin = calculate_us_margin(strategy_name, strategy_details, multiplier)
    
    cost_basis = 0
    if net_cost_credit < 0:
        cost_basis = abs(net_cost_credit)
        roi_help_text = "最大獲利 / 權利金淨支出"
    else:
        cost_basis = margin
        roi_help_text = "權利金淨收入 / 所需保證金"
    
    if cost_basis > 0:
        roi_per_point = (pnl_currency / cost_basis) * 100
    else:
        roi_per_point = np.full_like(pnl_currency, np.nan) 
    
    if net_cost_credit < 0:
        total_roi = (max_profit / cost_basis) * 100 if cost_basis > 0 else float('inf')
    else:
        total_roi = (net_cost_credit / cost_basis) * 100 if cost_basis > 0 else float('inf')


    st.header(f"📊 {strategy_name} 分析結果")
    col1, col2, col3, col4 = st.columns(4)
    cost_credit_label = "權利金淨收入 (Net Credit)" if net_cost_credit >= 0 else "權利金淨支出 (Net Debit)"
    col1.metric(cost_credit_label, f"${abs(net_cost_credit):,.2f}")
    col2.metric("所需保證金 (Margin Req.)", f"${margin:,.2f}", help="對於 Debit Spreads，此值為$0。")
    col3.metric("最大獲利 (Max Profit)", f"${max_profit:,.2f}")
    col4.metric("最大虧損 (Max Loss)", f"${max_loss:,.2f}")
    st.metric("整體報酬率 (Overall ROI)", f"{total_roi:.1f}%", help=roi_help_text)
    st.write(f"**損益兩平點 (Break-even):** {', '.join([f'{be:.2f}' for be in break_evens]) if break_evens else 'N/A'}")
    
    fig = go.Figure()

    custom_data = np.stack((roi_per_point,), axis=-1)
    hovertemplate = (
        "<b>股價 (Price):</b> %{x:$.2f}<br>" +
        "<b>損益 (P/L):</b> %{y:$,.2f}<br>" +
        "<b>點位報酬率 (Point ROI):</b> %{customdata[0]:.1f}%" +
        "<extra></extra>"
    )
    
    fig.add_trace(go.Scatter(
        x=S, y=pnl_currency, customdata=custom_data, hovertemplate=hovertemplate,
        mode='lines', name='策略損益 (P/L)', line=dict(color='royalblue', width=3)
    ))
    
    fig.add_hline(y=0, line_dash="dash", line_color="grey")

    for be in break_evens:
        fig.add_vline(x=be, line_dash="dash", line_color="purple", 
                      annotation_text=f"BE: {be:.2f}",
                      annotation_position="bottom right")

    for k in set(strikes):
        fig.add_vline(x=k, line_dash="dot", line_color="red", 
                      annotation_text=f"K={k}", 
                      annotation_position="top left")
    
    # CHANGED: 在填充區塊加入 hoverinfo='skip'
    fig.add_trace(go.Scatter(
        x=S, y=pnl_currency.clip(min=0), fill='tozeroy', 
        fillcolor='rgba(0,176,80,0.2)', mode='none', name='獲利區',
        hoverinfo='skip'  # 忽略此圖層的滑鼠事件
    ))
    fig.add_trace(go.Scatter(
        x=S, y=pnl_currency.clip(max=0), fill='tozeroy', 
        fillcolor='rgba(255,82,82,0.2)', mode='none', name='虧損區',
        hoverinfo='skip'  # 忽略此圖層的滑鼠事件
    ))
    
    fig.update_layout(title=f'<b>{strategy_name} 到期損益圖 (單位: USD)</b>', xaxis_title='標的物到期價格', yaxis_title='損益 (Profit / Loss)', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("策略組成")
    for leg in strategy_details:
        leg_type_map = {'long_call': '買進 買權', 'short_call': '賣出 買權', 'long_put': '買進 賣權', 'short_put': '賣出 賣權'}
        action_text = f"{leg_type_map[leg['type']]} @ 履約價 ${leg['strike']:.2f}, 權利金 ${leg['premium']:.2f}"
        st.markdown(f"- {action_text}")
else:
    st.info("請在左方選擇一個策略開始分析。")

st.sidebar.markdown("---")
st.sidebar.warning("**免責聲明 (Disclaimer)**：此工具為基於標準美股市場規則（Reg T）的簡化模型，僅供教學與視覺化參考，**並非投資建議**。各家券商的保證金計算可能存在細微差異，實際所需資金請務必以您的券商軟體顯示為準。")
