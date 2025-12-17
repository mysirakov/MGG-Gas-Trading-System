import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import (
    load_purchases, load_sales, load_payments_received, load_settings,
    purchases_to_df, sales_to_df, payments_to_df
)

st.set_page_config(
    page_title="Gas Trading Dashboard",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Load custom CSS
with open('style.css') as f:
    st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Theme selector
from theme_manager import theme_selector
theme_selector()

st.title("⛽ Dashboard")
st.markdown("### Comprehensive Overview of Your Natural Gas Trading Business")

st.sidebar.title("Navigation")
st.sidebar.markdown("Use the pages in the sidebar to access different features:")
st.sidebar.markdown("""
- **📦 Purchases** - View daily gas purchase details
- **💰 Sales** - Track sales and margins
- **💳 Payments** - Record payments received from buyers
- **🏦 Seller Balance** - Manage supplier payments and invoices
- **📈 Analytics** - View P&L and performance charts
- **⚙️ Settings** - Manage suppliers, buyers, and payment methods
""")

purchases = load_purchases()
sales = load_sales()
payments = load_payments_received()
settings = load_settings()

purchases_df = purchases_to_df(purchases)
sales_df = sales_to_df(sales)
payments_df = payments_to_df(payments)

st.header("📊 Key Metrics Overview")

col1, col2, col3, col4 = st.columns(4)

total_revenue = sales_df['total_revenue'].sum() if not sales_df.empty and 'total_revenue' in sales_df.columns else 0
total_margin = sales_df['total_margin'].sum() if not sales_df.empty and 'total_margin' in sales_df.columns else 0
total_quantity_sold = sales_df['quantity_mwh'].sum() if not sales_df.empty and 'quantity_mwh' in sales_df.columns else 0
payments_received = payments_df['amount_eur'].sum() if not payments_df.empty and 'amount_eur' in payments_df.columns else 0

outstanding_from_sales = 0
for sale in sales:
    sale_revenue = sale.get('total_revenue', 0)
    sale_paid = sale.get('amount_paid', 0)
    outstanding_from_sales += max(0, sale_revenue - sale_paid)

with col1:
    st.metric("💵 Total Revenue", f"€{total_revenue:,.2f}")
with col2:
    st.metric("📈 Total Profit", f"€{total_margin:,.2f}")
with col3:
    st.metric("⚡ Quantity Traded", f"{total_quantity_sold:,.0f} MWh")
with col4:
    st.metric("📋 Outstanding", f"€{outstanding_from_sales:,.2f}")

st.markdown("---")

col1, col2, col3, col4 = st.columns(4)

total_sent = purchases_df['amount_sent_eur'].sum() if not purchases_df.empty and 'amount_sent_eur' in purchases_df.columns else 0
total_received_supplier = purchases_df['amount_received_eur'].sum() if not purchases_df.empty and 'amount_received_eur' in purchases_df.columns else 0
valid_sales = sales_df[(sales_df['quantity_mwh'] > 0) & (sales_df['purchase_price_eur_mwh'] > 0)] if not sales_df.empty and 'quantity_mwh' in sales_df.columns and 'purchase_price_eur_mwh' in sales_df.columns else pd.DataFrame()
total_purchase_cost = (valid_sales['quantity_mwh'] * valid_sales['purchase_price_eur_mwh']).sum() if not valid_sales.empty else 0
supplier_balance = total_received_supplier - total_purchase_cost

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

st.header("📈 Performance Charts")

if not sales_df.empty and 'contract_date' in sales_df.columns:
    sales_df_chart = sales_df.copy()
    sales_df_chart['contract_date'] = pd.to_datetime(sales_df_chart['contract_date'], format='mixed', dayfirst=True)
    daily_metrics = sales_df_chart.groupby('contract_date').agg({
        'total_revenue': 'sum',
        'total_margin': 'sum',
        'quantity_mwh': 'sum'
    }).reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=daily_metrics['contract_date'], y=daily_metrics['total_revenue'],
                            mode='lines+markers', name='Revenue', line=dict(color='steelblue')))
    fig.add_trace(go.Scatter(x=daily_metrics['contract_date'], y=daily_metrics['total_margin'],
                            mode='lines+markers', name='Profit', line=dict(color='green')))
    fig.update_layout(title='Revenue vs Profit Over Time',
                    xaxis_title='Date', yaxis_title='Amount (EUR)',
                    hovermode='x unified',
                    height=400,
                    margin=dict(l=60, r=40, t=50, b=50))
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    daily_volume = sales_df_chart.groupby('contract_date')['quantity_mwh'].sum().reset_index()
    
    fig = px.bar(daily_volume, x='contract_date', y='quantity_mwh',
                title='Daily Trading Volume', color_discrete_sequence=['steelblue'])
    fig.update_layout(xaxis_title='Date', yaxis_title='Volume (MWh)',
                    height=350,
                    margin=dict(l=60, r=40, t=50, b=50))
    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
else:
    st.info("📊 Add sales data to see charts")

st.markdown("---")

st.header("💰 Financial Summary")

st.subheader("Cash Position")
cash_data = {
    'Category': ['Payments to Suppliers', 'Payments Received', 'Net Cash Flow'],
    'Amount (EUR)': [f"€{total_sent:,.2f}", f"€{payments_received:,.2f}", f"€{payments_received - total_sent:,.2f}"]
}
cash_df = pd.DataFrame(cash_data)
st.dataframe(cash_df, use_container_width=True, hide_index=True)

st.subheader("P&L Summary")
if not sales_df.empty:
    capacity_cost = (sales_df['cost_capacity_eur_mwh'] * sales_df['quantity_mwh']).sum() if 'cost_capacity_eur_mwh' in sales_df.columns else 0
    transport_cost = (sales_df['cost_transport_eur_mwh'] * sales_df['quantity_mwh']).sum() if 'cost_transport_eur_mwh' in sales_df.columns else 0
    purchase_cost = (sales_df['purchase_price_eur_mwh'] * sales_df['quantity_mwh']).sum() if 'purchase_price_eur_mwh' in sales_df.columns else 0
    
    pnl_data = {
        'Category': ['Gross Revenue', 'Purchase Costs', 'Capacity Costs', 'Transport Costs', 'Net Profit'],
        'Amount (EUR)': [f"€{total_revenue:,.2f}", f"-€{purchase_cost:,.2f}", f"-€{capacity_cost:,.2f}", f"-€{transport_cost:,.2f}", f"€{total_margin:,.2f}"]
    }
    pnl_df = pd.DataFrame(pnl_data)
    st.dataframe(pnl_df, use_container_width=True, hide_index=True)
else:
    st.info("Add sales data to see P&L summary")

st.markdown("---")

st.header("📋 Recent Activity")

st.subheader("Recent Purchases")
if not purchases_df.empty:
    recent_purchases = purchases_df.head(5)
    display_cols = ['payment_date', 'supplier', 'amount_sent_eur']
    available_cols = [c for c in display_cols if c in recent_purchases.columns]
    st.dataframe(recent_purchases[available_cols], use_container_width=True, hide_index=True)
else:
    st.info("No purchases recorded")

st.subheader("Recent Sales")
if not sales_df.empty:
    recent_sales = sales_df.head(5)
    display_cols = ['contract_date', 'buyer', 'total_revenue', 'total_margin']
    available_cols = [c for c in display_cols if c in recent_sales.columns]
    st.dataframe(recent_sales[available_cols], use_container_width=True, hide_index=True)
else:
    st.info("No sales recorded")

st.subheader("Recent Payments")
if not payments_df.empty:
    recent_payments = payments_df.head(5)
    display_cols = ['payment_date', 'buyer', 'amount_eur']
    available_cols = [c for c in display_cols if c in recent_payments.columns]
    st.dataframe(recent_payments[available_cols], use_container_width=True, hide_index=True)
else:
    st.info("No payments recorded")

st.markdown("---")

st.header("🔔 Alerts & Status")

col1, col2 = st.columns(2)

with col1:
    if outstanding_from_sales > 0:
        st.warning(f"⚠️ Outstanding receivables: €{outstanding_from_sales:,.2f}")
    else:
        st.success("✅ All receivables collected")

with col2:
    if supplier_balance < 0:
        st.warning(f"⚠️ Supplier balance is negative: €{supplier_balance:,.2f}")
    elif supplier_balance < 10000:
        st.info(f"ℹ️ Low supplier balance: €{supplier_balance:,.2f}")
    else:
        st.success(f"✅ Healthy supplier balance: €{supplier_balance:,.2f}")

pending_sales = len([s for s in sales if s.get('payment_status') == 'Pending']) if sales else 0
if pending_sales > 0:
    st.info(f"📋 {pending_sales} sales pending payment")

st.markdown("---")
st.caption("Gas Trading Financial Dashboard | Built with Streamlit")
