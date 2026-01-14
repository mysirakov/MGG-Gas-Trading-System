import streamlit as st
import pandas as pd
from database import (
    initialize_database_system, get_sales, get_supplier_payments, get_payments_received,
    get_dashboard_metrics, sales_to_df, payments_to_df, supplier_payments_to_df
)
from components import load_material_icons, page_header, metric_card, section_header, empty_state

st.set_page_config(
    page_title="Gas Trading Dashboard",
    page_icon="⛽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize database system
initialize_database_system()

try:
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except:
    pass

load_material_icons()

metrics = get_dashboard_metrics()
sales = get_sales()
purchases = get_supplier_payments()
payments = get_payments_received()

purchases_df = supplier_payments_to_df(purchases)
sales_df = sales_to_df(sales)
payments_df = payments_to_df(payments)

page_header("Dashboard", "Comprehensive Overview of Your Natural Gas Trading Business")

col1, col2, col3, col4 = st.columns(4)

total_revenue = metrics['total_revenue']
total_margin = metrics['total_margin']
total_quantity_sold = metrics['total_quantity']
outstanding = metrics['outstanding_receivables']

with col1:
    metric_card("attach_money", "Total Revenue", f"€{total_revenue:,.2f}", "blue")
with col2:
    metric_card("trending_up", "Total Profit", f"€{total_margin:,.2f}", "green")
with col3:
    metric_card("bolt", "Quantity Traded", f"{total_quantity_sold:,.0f} MWh", "orange")
with col4:
    metric_card("receipt_long", "Outstanding", f"€{outstanding:,.2f}", "purple")

st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

total_sent = metrics['total_sent_to_suppliers']
supplier_balance = metrics['supplier_balance']
payments_received = metrics['payments_received']
margin_pct = (total_margin / total_revenue * 100) if total_revenue > 0 else 0

with col1:
    metric_card("account_balance_wallet", "Paid to Suppliers", f"€{total_sent:,.2f}", "teal")
with col2:
    metric_card("savings", "Supplier Balance", f"€{supplier_balance:,.2f}", "blue")
with col3:
    metric_card("check_circle", "Payments Received", f"€{payments_received:,.2f}", "green")
with col4:
    metric_card("percent", "Profit Margin", f"{margin_pct:.1f}%", "purple")

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

section_header("insights", "Performance Charts")

if not sales_df.empty and 'contract_date' in sales_df.columns:
    col1, col2 = st.columns(2)
    
    with col1:
        sales_df_chart = sales_df.copy()
        sales_df_chart['contract_date'] = pd.to_datetime(sales_df_chart['contract_date'])
        daily_metrics = sales_df_chart.groupby('contract_date').agg({
            'total_revenue': 'sum',
            'total_margin': 'sum'
        }).rename(columns={'total_revenue': 'Revenue', 'total_margin': 'Profit'})
        
        st.markdown("##### Revenue vs Profit Over Time")
        st.line_chart(daily_metrics, y=['Revenue', 'Profit'], color=["#3b82f6", "#10b981"])
    
    with col2:
        daily_volume = sales_df_chart.groupby('contract_date')['quantity_mwh'].sum().reset_index()
        daily_volume = daily_volume.set_index('contract_date')
        
        st.markdown("##### Daily Trading Volume")
        st.bar_chart(daily_volume['quantity_mwh'], color="#3b82f6")
else:
    empty_state("insert_chart", "Add sales data to see performance charts")


st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

section_header("account_balance", "Financial Summary")

col1, col2 = st.columns(2)

with col1:
    st.markdown("##### Cash Position")
    cash_data = {
        'Category': ['Payments to Suppliers', 'Payments Received', 'Net Cash Flow'],
        'Amount': [f"€{total_sent:,.2f}", f"€{payments_received:,.2f}", f"€{payments_received - total_sent:,.2f}"]
    }
    st.dataframe(pd.DataFrame(cash_data), width="stretch", hide_index=True)

with col2:
    st.markdown("##### P&L Summary")
    if not sales_df.empty:
        capacity_cost = (sales_df['cost_capacity_eur_mwh'] * sales_df['quantity_mwh']).sum() if 'cost_capacity_eur_mwh' in sales_df.columns else 0
        transport_cost = (sales_df['cost_transport_eur_mwh'] * sales_df['quantity_mwh']).sum() if 'cost_transport_eur_mwh' in sales_df.columns else 0
        purchase_cost = metrics['total_purchase_cost']
        
        pnl_data = {
            'Category': ['Gross Revenue', 'Purchase Costs', 'Capacity Costs', 'Transport Costs', 'Net Profit'],
            'Amount': [f"€{total_revenue:,.2f}", f"-€{purchase_cost:,.2f}", f"-€{capacity_cost:,.2f}", f"-€{transport_cost:,.2f}", f"€{total_margin:,.2f}"]
        }
        st.dataframe(pd.DataFrame(pnl_data), width="stretch", hide_index=True)
    else:
        st.info("Add sales data to see P&L summary")

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

section_header("notifications", "Status Overview")

col1, col2 = st.columns(2)

with col1:
    if outstanding > 0:
        st.warning(f"Outstanding receivables: €{outstanding:,.2f}")
    else:
        st.success("All receivables collected")

with col2:
    if supplier_balance < 0:
        st.warning(f"Supplier balance is negative: €{supplier_balance:,.2f}")
    elif supplier_balance < 10000:
        st.info(f"Low supplier balance: €{supplier_balance:,.2f}")
    else:
        st.success(f"Healthy supplier balance: €{supplier_balance:,.2f}")
