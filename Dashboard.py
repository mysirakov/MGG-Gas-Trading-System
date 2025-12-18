import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import (
    get_sales, get_supplier_payments, get_payments_received, get_settings,
    get_dashboard_metrics, sales_to_df, payments_to_df, supplier_payments_to_df
)

st.set_page_config(
    page_title="Gas Trading Dashboard",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

try:
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except:
    pass

metrics = get_dashboard_metrics()
sales = get_sales()
purchases = get_supplier_payments()
payments = get_payments_received()

purchases_df = supplier_payments_to_df(purchases)
sales_df = sales_to_df(sales)
payments_df = payments_to_df(payments)

st.markdown("""
    <div style='margin-bottom: 1rem;'>
        <h1 style='margin: 0; font-size: 2.5rem; font-weight: 700; color: #0f172a;'>⛽ Gas Trading Dashboard</h1>
        <p style='margin: 0.5rem 0 0 0; font-size: 1.1rem; color: #6b7280; font-weight: 400;'>Comprehensive Overview of Your Natural Gas Trading Business</p>
    </div>
""", unsafe_allow_html=True)

st.markdown("---")

st.markdown("### 📊 Key Metrics Overview")

col1, col2, col3, col4 = st.columns(4)

total_revenue = metrics['total_revenue']
total_margin = metrics['total_margin']
total_quantity_sold = metrics['total_quantity']
outstanding = metrics['outstanding_receivables']

with col1:
    st.metric("💵 Total Revenue", f"€{total_revenue:,.2f}")
with col2:
    st.metric("📈 Total Profit", f"€{total_margin:,.2f}")
with col3:
    st.metric("⚡ Quantity Traded", f"{total_quantity_sold:,.0f} MWh")
with col4:
    st.metric("📋 Outstanding", f"€{outstanding:,.2f}")

st.markdown("---")

st.markdown("### 💰 Supplier & Payment Metrics")

col1, col2, col3, col4 = st.columns(4)

total_sent = metrics['total_sent_to_suppliers']
supplier_balance = metrics['supplier_balance']
payments_received = metrics['payments_received']

with col1:
    st.metric("💳 Paid to Suppliers", f"€{total_sent:,.2f}")
with col2:
    st.metric("🏦 Supplier Balance", f"€{supplier_balance:,.2f}")
with col3:
    st.metric("✅ Payments Received", f"€{payments_received:,.2f}")
with col4:
    margin_pct = (total_margin / total_revenue * 100) if total_revenue > 0 else 0
    st.metric("📊 Profit Margin", f"{margin_pct:.2f}%")

st.markdown("---")

st.markdown("### 📈 Performance Charts")

if not sales_df.empty and 'contract_date' in sales_df.columns:
    col1, col2 = st.columns(2)
    
    with col1:
        sales_df_chart = sales_df.copy()
        sales_df_chart['contract_date'] = pd.to_datetime(sales_df_chart['contract_date'])
        daily_metrics = sales_df_chart.groupby('contract_date').agg({
            'total_revenue': 'sum',
            'total_margin': 'sum'
        }).reset_index()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=daily_metrics['contract_date'], y=daily_metrics['total_revenue'],
                                mode='lines+markers', name='Revenue', line=dict(color='#3b82f6', width=3),
                                marker=dict(size=6)))
        fig.add_trace(go.Scatter(x=daily_metrics['contract_date'], y=daily_metrics['total_margin'],
                                mode='lines+markers', name='Profit', line=dict(color='#10b981', width=3),
                                marker=dict(size=6)))
        fig.update_layout(title='Revenue vs Profit Over Time',
                        xaxis_title='Date', yaxis_title='Amount (EUR)',
                        hovermode='x unified',
                        height=350,
                        margin=dict(l=60, r=40, t=50, b=50),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(family='Inter', size=12))
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    with col2:
        daily_volume = sales_df_chart.groupby('contract_date')['quantity_mwh'].sum().reset_index()
        
        fig = px.bar(daily_volume, x='contract_date', y='quantity_mwh',
                    title='Daily Trading Volume', color_discrete_sequence=['#3b82f6'])
        fig.update_layout(xaxis_title='Date', yaxis_title='Volume (MWh)',
                        height=350,
                        margin=dict(l=60, r=40, t=50, b=50),
                        paper_bgcolor='rgba(0,0,0,0)',
                        plot_bgcolor='rgba(0,0,0,0)',
                        font=dict(family='Inter', size=12),
                        showlegend=False)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
else:
    st.info("📊 Add sales data to see charts")

st.markdown("---")

st.markdown("### 💼 Financial Summary")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Cash Position")
    cash_data = {
        'Category': ['Payments to Suppliers', 'Payments Received', 'Net Cash Flow'],
        'Amount (EUR)': [f"€{total_sent:,.2f}", f"€{payments_received:,.2f}", f"€{payments_received - total_sent:,.2f}"]
    }
    cash_df = pd.DataFrame(cash_data)
    st.dataframe(cash_df, use_container_width=True, hide_index=True)

with col2:
    st.markdown("#### P&L Summary")
    if not sales_df.empty:
        capacity_cost = (sales_df['cost_capacity_eur_mwh'] * sales_df['quantity_mwh']).sum() if 'cost_capacity_eur_mwh' in sales_df.columns else 0
        transport_cost = (sales_df['cost_transport_eur_mwh'] * sales_df['quantity_mwh']).sum() if 'cost_transport_eur_mwh' in sales_df.columns else 0
        purchase_cost = metrics['total_purchase_cost']
        
        pnl_data = {
            'Category': ['Gross Revenue', 'Purchase Costs', 'Capacity Costs', 'Transport Costs', 'Net Profit'],
            'Amount (EUR)': [f"€{total_revenue:,.2f}", f"-€{purchase_cost:,.2f}", f"-€{capacity_cost:,.2f}", f"-€{transport_cost:,.2f}", f"€{total_margin:,.2f}"]
        }
        pnl_df = pd.DataFrame(pnl_data)
        st.dataframe(pnl_df, use_container_width=True, hide_index=True)
    else:
        st.info("Add sales data to see P&L summary")

st.markdown("---")

st.markdown("### 📋 Recent Activity")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown("#### Recent Supplier Payments")
    if not purchases_df.empty:
        recent_purchases = purchases_df.head(3)
        display_cols = ['payment_date', 'supplier', 'amount_sent_eur']
        available_cols = [c for c in display_cols if c in recent_purchases.columns]
        display_df = recent_purchases[available_cols].copy()
        if 'payment_date' in display_df.columns:
            display_df['payment_date'] = pd.to_datetime(display_df['payment_date']).dt.strftime('%d/%m/%Y')
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=150)
    else:
        st.info("No supplier payments recorded")

with col2:
    st.markdown("#### Recent Sales")
    if not sales_df.empty:
        recent_sales = sales_df.head(3)
        display_cols = ['contract_date', 'buyer', 'total_revenue']
        available_cols = [c for c in display_cols if c in recent_sales.columns]
        display_df = recent_sales[available_cols].copy()
        if 'contract_date' in display_df.columns:
            display_df['contract_date'] = pd.to_datetime(display_df['contract_date']).dt.strftime('%d/%m/%Y')
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=150)
    else:
        st.info("No sales recorded")

with col3:
    st.markdown("#### Recent Payments Received")
    if not payments_df.empty:
        recent_payments = payments_df.head(3)
        display_cols = ['payment_date', 'buyer', 'amount_eur']
        available_cols = [c for c in display_cols if c in recent_payments.columns]
        display_df = recent_payments[available_cols].copy()
        if 'payment_date' in display_df.columns:
            display_df['payment_date'] = pd.to_datetime(display_df['payment_date']).dt.strftime('%d/%m/%Y')
        st.dataframe(display_df, use_container_width=True, hide_index=True, height=150)
    else:
        st.info("No payments recorded")

st.markdown("---")

st.markdown("### 🔔 Status Overview")

col1, col2 = st.columns(2)

with col1:
    if outstanding > 0:
        st.warning(f"⚠️ Outstanding receivables: €{outstanding:,.2f}")
    else:
        st.success("✅ All receivables collected")

with col2:
    if supplier_balance < 0:
        st.warning(f"⚠️ Supplier balance is negative: €{supplier_balance:,.2f}")
    elif supplier_balance < 10000:
        st.info(f"ℹ️ Low supplier balance: €{supplier_balance:,.2f}")
    else:
        st.success(f"✅ Healthy supplier balance: €{supplier_balance:,.2f}")

st.markdown("---")
st.caption("🌟 Gas Trading Financial Dashboard | Built with Streamlit | Powered by PostgreSQL")
