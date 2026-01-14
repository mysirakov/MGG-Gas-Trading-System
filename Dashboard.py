import streamlit as st
import pandas as pd
from datetime import datetime
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

if sales:
    col1, col2 = st.columns(2)
    
    with col1:
        # Group by date for line chart
        daily_metrics_dict = {}
        for row in sales_df:
            d = row['contract_date']
            if isinstance(d, str):
                try:
                    d = datetime.strptime(d, '%Y-%m-%d').date()
                except:
                    pass
            
            if d not in daily_metrics_dict:
                daily_metrics_dict[d] = {'Revenue': 0.0, 'Profit': 0.0}
            daily_metrics_dict[d]['Revenue'] += float(row.get('total_revenue', 0))
            daily_metrics_dict[d]['Profit'] += float(row.get('total_margin', 0))
        
        # Sort by date
        sorted_dates = sorted(daily_metrics_dict.keys())
        chart_data = []
        for d in sorted_dates:
            chart_data.append({
                'date': d,
                'Revenue': daily_metrics_dict[d]['Revenue'],
                'Profit': daily_metrics_dict[d]['Profit']
            })
        
        st.markdown("##### Revenue vs Profit Over Time")
        if chart_data:
            df_chart = pd.DataFrame(chart_data)
            df_chart.set_index('date', inplace=True)
            st.line_chart(df_chart)
    
    with col2:
        # Group by date for bar chart
        daily_volume_dict = {}
        for row in sales_df:
            d = row['contract_date']
            if isinstance(d, str):
                try:
                    d = datetime.strptime(d, '%Y-%m-%d').date()
                except:
                    pass
            
            if d not in daily_volume_dict:
                daily_volume_dict[d] = 0.0
            daily_volume_dict[d] += float(row.get('quantity_mwh', 0))
        
        # Sort by date
        sorted_dates = sorted(daily_volume_dict.keys())
        volume_data = []
        for d in sorted_dates:
            volume_data.append({
                'date': d,
                'quantity_mwh': daily_volume_dict[d]
            })
            
        st.markdown("##### Daily Trading Volume")
        if volume_data:
            df_vol = pd.DataFrame(volume_data)
            df_vol.set_index('date', inplace=True)
            st.bar_chart(df_vol)
else:
    empty_state("insert_chart", "Add sales data to see performance charts")


st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

section_header("account_balance", "Financial Summary")

col1, col2 = st.columns(2)

with col1:
    st.markdown("##### Cash Position")
    cash_data = [
        {'Category': 'Payments to Suppliers', 'Amount': f"€{total_sent:,.2f}"},
        {'Category': 'Payments Received', 'Amount': f"€{payments_received:,.2f}"},
        {'Category': 'Net Cash Flow', 'Amount': f"€{payments_received - total_sent:,.2f}"}
    ]
    st.dataframe(cash_data)

with col2:
    st.markdown("##### P&L Summary")
    if sales_df:
        capacity_cost = sum(row.get('cost_capacity_eur_mwh', 0) * row.get('quantity_mwh', 0) for row in sales_df)
        transport_cost = sum(row.get('cost_transport_eur_mwh', 0) * row.get('quantity_mwh', 0) for row in sales_df)
        purchase_cost = metrics['total_purchase_cost']
        
        pnl_data = [
            {'Category': 'Gross Revenue', 'Amount': f"€{total_revenue:,.2f}"},
            {'Category': 'Purchase Costs', 'Amount': f"-€{purchase_cost:,.2f}"},
            {'Category': 'Capacity Costs', 'Amount': f"-€{capacity_cost:,.2f}"},
            {'Category': 'Transport Costs', 'Amount': f"-€{transport_cost:,.2f}"},
            {'Category': 'Net Profit', 'Amount': f"€{total_margin:,.2f}"}
        ]
        st.dataframe(pnl_data)
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
