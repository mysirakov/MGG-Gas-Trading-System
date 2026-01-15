import streamlit as st
from datetime import datetime
from database import (
    initialize_database_system, get_sales, get_supplier_payments, get_payments_received,
    get_dashboard_metrics, sales_to_df, payments_to_df, supplier_payments_to_df
)
from components import load_material_icons, page_header, metric_card, section_header, empty_state, sidebar_logo

st.set_page_config(
    page_title="Mix Gas Group | Dashboard",
    page_icon="https://slelguoygbfzlpylpxfs.supabase.co/storage/v1/render/image/public/project-uploads/704afe63-0b4a-4050-803e-5116d1754a58/Untitled-Project-1768468114127.png?width=8000&height=8000&resize=contain",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Render sidebar logo
sidebar_logo()

# Initialize database system
initialize_database_system()

try:
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except:
    pass

load_material_icons()

# Fetch data with error handling and default values
try:
    metrics = get_dashboard_metrics()
except Exception as e:
    st.error(f"Error fetching metrics: {e}")
    metrics = {
        'total_revenue': 0.0, 'total_margin': 0.0, 'total_quantity': 0.0, 
        'outstanding_receivables': 0.0, 'total_sent_to_suppliers': 0.0,
        'supplier_balance': 0.0, 'payments_received': 0.0
    }

try:
    sales = get_sales()
except Exception as e:
    st.error(f"Error fetching sales: {e}")
    sales = []

sales_df = sales_to_df(sales)

page_header("Dashboard", "Comprehensive Overview of Your Natural Gas Trading Business")

col1, col2, col3, col4 = st.columns(4)

total_revenue = metrics.get('total_revenue', 0.0)
total_margin = metrics.get('total_margin', 0.0)
total_quantity_sold = metrics.get('total_quantity', 0.0)
outstanding = metrics.get('outstanding_receivables', 0.0)

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

total_sent = metrics.get('total_sent_to_suppliers', 0.0)
supplier_balance = metrics.get('supplier_balance', 0.0)
payments_received = metrics.get('payments_received', 0.0)
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
                    d = datetime.strptime(d.split('T')[0] if 'T' in d else d, '%Y-%m-%d').date()
                except:
                    pass
            
            # Format date for Vega-Lite
            if hasattr(d, 'isoformat'):
                d_str = d.isoformat()
            else:
                d_str = str(d)

            if d_str not in daily_metrics_dict:
                daily_metrics_dict[d_str] = {'Revenue': 0.0, 'Profit': 0.0}
            daily_metrics_dict[d_str]['Revenue'] += float(row.get('total_revenue', 0))
            daily_metrics_dict[d_str]['Profit'] += float(row.get('total_margin', 0))
        
        # Sort by date
        sorted_dates = sorted(daily_metrics_dict.keys())
        chart_data = []
        for d in sorted_dates:
            chart_data.append({
                'date': d,
                'Value': daily_metrics_dict[d]['Revenue'],
                'Type': 'Revenue'
            })
            chart_data.append({
                'date': d,
                'Value': daily_metrics_dict[d]['Profit'],
                'Type': 'Profit'
            })
        
        st.markdown("##### Revenue vs Profit Over Time")
        if chart_data:
            st.vega_lite_chart(chart_data, {
                'mark': {'type': 'line', 'point': True},
                'encoding': {
                    'x': {'field': 'date', 'type': 'temporal', 'title': 'Date'},
                    'y': {'field': 'Value', 'type': 'quantitative', 'title': 'Amount (€)'},
                    'color': {'field': 'Type', 'type': 'nominal', 'scale': {'range': ['#1E88E5', '#43A047']}}
                },
                'width': 'container',
                'height': 300
            })
    
    with col2:
        # Group by date for bar chart
        daily_volume_dict = {}
        for row in sales_df:
            d = row['contract_date']
            if isinstance(d, str):
                try:
                    d = datetime.strptime(d.split('T')[0] if 'T' in d else d, '%Y-%m-%d').date()
                except:
                    pass
            
            if hasattr(d, 'isoformat'):
                d_str = d.isoformat()
            else:
                d_str = str(d)

            if d_str not in daily_volume_dict:
                daily_volume_dict[d_str] = 0.0
            daily_volume_dict[d_str] += float(row.get('quantity_mwh', 0))
        
        # Sort by date
        sorted_dates = sorted(daily_volume_dict.keys())
        volume_data = []
        for d in sorted_dates:
            volume_data.append({
                'date': d,
                'Quantity': daily_volume_dict[d]
            })
            
        st.markdown("##### Daily Trading Volume")
        if volume_data:
            st.vega_lite_chart(volume_data, {
                'mark': {'type': 'bar', 'color': '#FB8C00'},
                'encoding': {
                    'x': {'field': 'date', 'type': 'temporal', 'title': 'Date'},
                    'y': {'field': 'Quantity', 'type': 'quantitative', 'title': 'MWh'}
                },
                'width': 'container',
                'height': 300
            })
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
        purchase_cost = metrics.get('total_purchase_cost', 0.0)
        
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
