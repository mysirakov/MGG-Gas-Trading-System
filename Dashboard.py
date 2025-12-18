import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from database import (
    get_sales, get_supplier_payments, get_payments_received,
    get_dashboard_metrics, sales_to_df, payments_to_df, supplier_payments_to_df
)
from components import load_material_icons, page_header, metric_card, section_header

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
        }).reset_index()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=daily_metrics['contract_date'], 
            y=daily_metrics['total_revenue'],
            mode='lines+markers', 
            name='Revenue', 
            line=dict(color='#3b82f6', width=3),
            marker=dict(size=6)
        ))
        fig.add_trace(go.Scatter(
            x=daily_metrics['contract_date'], 
            y=daily_metrics['total_margin'],
            mode='lines+markers', 
            name='Profit', 
            line=dict(color='#10b981', width=3),
            marker=dict(size=6)
        ))
        fig.update_layout(
            title=dict(text='Revenue vs Profit Over Time', font=dict(size=16, color='#1e293b')),
            xaxis_title='Date',
            yaxis_title='Amount (EUR)',
            hovermode='x unified',
            height=350,
            margin=dict(l=40, r=20, t=50, b=40),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', size=12, color='#64748b'),
            legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1),
            xaxis=dict(gridcolor='rgba(148,163,184,0.1)', zerolinecolor='rgba(148,163,184,0.1)'),
            yaxis=dict(gridcolor='rgba(148,163,184,0.1)', zerolinecolor='rgba(148,163,184,0.1)')
        )
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    
    with col2:
        daily_volume = sales_df_chart.groupby('contract_date')['quantity_mwh'].sum().reset_index()
        
        fig = px.bar(
            daily_volume, 
            x='contract_date', 
            y='quantity_mwh',
            color_discrete_sequence=['#3b82f6']
        )
        fig.update_layout(
            title=dict(text='Daily Trading Volume', font=dict(size=16, color='#1e293b')),
            xaxis_title='Date',
            yaxis_title='Volume (MWh)',
            height=350,
            margin=dict(l=40, r=20, t=50, b=40),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', size=12, color='#64748b'),
            showlegend=False,
            xaxis=dict(gridcolor='rgba(148,163,184,0.1)', zerolinecolor='rgba(148,163,184,0.1)'),
            yaxis=dict(gridcolor='rgba(148,163,184,0.1)', zerolinecolor='rgba(148,163,184,0.1)')
        )
        fig.update_traces(marker_cornerradius=6)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
else:
    st.markdown("""
        <div style="
            background: rgba(255, 255, 255, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.5);
            border-radius: 16px;
            padding: 3rem;
            text-align: center;
            color: #64748b;
        ">
            <span class="material-icons-round" style="font-size: 48px; opacity: 0.5;">insert_chart</span>
            <p style="margin: 1rem 0 0 0;">Add sales data to see performance charts</p>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

section_header("account_balance", "Financial Summary")

col1, col2 = st.columns(2)

with col1:
    st.markdown("##### Cash Position")
    cash_data = {
        'Category': ['Payments to Suppliers', 'Payments Received', 'Net Cash Flow'],
        'Amount': [f"€{total_sent:,.2f}", f"€{payments_received:,.2f}", f"€{payments_received - total_sent:,.2f}"]
    }
    st.dataframe(pd.DataFrame(cash_data), use_container_width=True, hide_index=True)

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
        st.dataframe(pd.DataFrame(pnl_data), use_container_width=True, hide_index=True)
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
