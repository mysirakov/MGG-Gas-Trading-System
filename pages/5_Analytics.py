import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from database import (
    load_purchases, load_sales, load_payments_received,
    purchases_to_df, sales_to_df, payments_to_df
)

st.set_page_config(page_title="Analytics", page_icon="📈", layout="wide")

try:
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except:
    pass

st.title("📈 Financial Analytics Dashboard")
st.markdown("Comprehensive P&L analysis, trading performance, and financial metrics")

purchases = load_purchases()
sales = load_sales()
payments = load_payments_received()

purchases_df = purchases_to_df(purchases)
sales_df = sales_to_df(sales)
payments_df = payments_to_df(payments)

st.header("📊 Key Performance Indicators")

col1, col2, col3, col4 = st.columns(4)

total_revenue = sales_df['total_revenue'].sum() if not sales_df.empty and 'total_revenue' in sales_df.columns else 0
total_margin = sales_df['total_margin'].sum() if not sales_df.empty and 'total_margin' in sales_df.columns else 0
total_quantity_sold = sales_df['quantity_mwh'].sum() if not sales_df.empty and 'quantity_mwh' in sales_df.columns else 0

with col1:
    st.metric("Total Revenue", f"€{total_revenue:,.2f}")
with col2:
    st.metric("Total Profit (Margin)", f"€{total_margin:,.2f}")
with col3:
    margin_pct = (total_margin / total_revenue * 100) if total_revenue > 0 else 0
    st.metric("Profit Margin %", f"{margin_pct:.2f}%")
with col4:
    st.metric("Quantity Traded", f"{total_quantity_sold:,.0f} MWh")

st.markdown("---")

col1, col2, col3, col4 = st.columns(4)

total_sent = purchases_df['amount_sent_eur'].sum() if not purchases_df.empty and 'amount_sent_eur' in purchases_df.columns else 0
total_received_supplier = purchases_df['amount_received_eur'].sum() if not purchases_df.empty and 'amount_received_eur' in purchases_df.columns else 0
valid_sales = sales_df[(sales_df['quantity_mwh'] > 0) & (sales_df['purchase_price_eur_mwh'] > 0)] if not sales_df.empty and 'quantity_mwh' in sales_df.columns and 'purchase_price_eur_mwh' in sales_df.columns else pd.DataFrame()
total_purchase_cost = (valid_sales['quantity_mwh'] * valid_sales['purchase_price_eur_mwh']).sum() if not valid_sales.empty else 0
supplier_balance = total_received_supplier - total_purchase_cost

payments_received = payments_df['amount_eur'].sum() if not payments_df.empty and 'amount_eur' in payments_df.columns else 0

outstanding_from_sales = 0
for sale in sales:
    sale_revenue = sale.get('total_revenue', 0)
    sale_paid = sale.get('amount_paid', 0)
    outstanding_from_sales += max(0, sale_revenue - sale_paid)

with col1:
    st.metric("Total Paid to Suppliers", f"€{total_sent:,.2f}")
with col2:
    st.metric("Supplier Balance", f"€{supplier_balance:,.2f}")
with col3:
    st.metric("Payments Received", f"€{payments_received:,.2f}")
with col4:
    st.metric("Outstanding Receivables", f"€{outstanding_from_sales:,.2f}")

st.markdown("---")

st.header("📈 Price Analysis")

if not sales_df.empty:
    if 'contract_date' in sales_df.columns:
        sales_df_copy = sales_df.copy()
        sales_df_copy['contract_date'] = pd.to_datetime(sales_df_copy['contract_date'], format='mixed', dayfirst=True)
        sales_daily = sales_df_copy.groupby('contract_date').agg({
            'sales_price_eur_mwh': 'mean',
            'purchase_price_eur_mwh': 'mean',
            'margin_eur_mwh': 'mean'
        }).reset_index()
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=sales_daily['contract_date'], y=sales_daily['sales_price_eur_mwh'],
                                mode='lines+markers', name='Sales Price', line=dict(color='green')))
        fig.add_trace(go.Scatter(x=sales_daily['contract_date'], y=sales_daily['purchase_price_eur_mwh'],
                                mode='lines+markers', name='Purchase Price', line=dict(color='red')))
        fig.update_layout(title='Sales vs Purchase Price Over Time',
                        xaxis_title='Date', yaxis_title='Price (EUR/MWh)',
                        hovermode='x unified',
                        height=400,
                        margin=dict(l=60, r=40, t=50, b=50))
        st.plotly_chart(fig, use_container_width=True)
        
        fig = go.Figure()
        colors = ['green' if x >= 0 else 'red' for x in sales_daily['margin_eur_mwh']]
        fig.add_trace(go.Bar(x=sales_daily['contract_date'], y=sales_daily['margin_eur_mwh'],
                            name='Margin', marker_color=colors))
        fig.update_layout(title='Daily Margin per MWh',
                        xaxis_title='Date', yaxis_title='Margin (EUR/MWh)',
                        height=350,
                        margin=dict(l=60, r=40, t=50, b=50))
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Add sales data to see price analysis charts")

st.markdown("---")

st.header("💰 P&L Summary")

st.subheader("Revenue Breakdown")
if not sales_df.empty:
    capacity_cost = (sales_df['cost_capacity_eur_mwh'] * sales_df['quantity_mwh']).sum() if 'cost_capacity_eur_mwh' in sales_df.columns else 0
    transport_cost = (sales_df['cost_transport_eur_mwh'] * sales_df['quantity_mwh']).sum() if 'cost_transport_eur_mwh' in sales_df.columns else 0
    purchase_cost_total = (sales_df['purchase_price_eur_mwh'] * sales_df['quantity_mwh']).sum() if 'purchase_price_eur_mwh' in sales_df.columns else 0
    
    pnl_data = {
        'Category': ['Gross Revenue', 'Capacity Costs', 'Transport Costs', 'Purchase Costs', 'Net Profit'],
        'Amount (EUR)': [
            f"€{total_revenue:,.2f}",
            f"-€{capacity_cost:,.2f}",
            f"-€{transport_cost:,.2f}",
            f"-€{purchase_cost_total:,.2f}",
            f"€{total_margin:,.2f}"
        ]
    }
    pnl_df = pd.DataFrame(pnl_data)
    st.dataframe(pnl_df, use_container_width=True, hide_index=True)
    
    cost_values = [abs(purchase_cost_total), abs(capacity_cost), abs(transport_cost)]
    cost_labels = ['Purchase Costs', 'Capacity Costs', 'Transport Costs']
    
    if sum(cost_values) > 0:
        fig = px.pie(values=cost_values, names=cost_labels, title='Cost Distribution')
        fig.update_layout(height=400, margin=dict(l=40, r=40, t=50, b=40))
        fig.update_traces(textposition='inside', textinfo='percent+label')
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Add sales data to see P&L breakdown")

st.subheader("Trading Volume")
if not sales_df.empty and 'contract_date' in sales_df.columns:
    sales_df_copy = sales_df.copy()
    sales_df_copy['contract_date'] = pd.to_datetime(sales_df_copy['contract_date'], dayfirst=True)
    volume_daily = sales_df_copy.groupby('contract_date').agg({
        'quantity_mwh': 'sum',
        'total_revenue': 'sum',
        'total_margin': 'sum'
    }).reset_index()
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=volume_daily['contract_date'], y=volume_daily['quantity_mwh'],
                        name='Volume (MWh)', marker_color='steelblue'))
    fig.update_layout(title='Daily Trading Volume',
                    xaxis_title='Date', yaxis_title='Volume (MWh)',
                    height=350,
                    margin=dict(l=60, r=40, t=50, b=50))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Add sales data to see volume charts")

st.markdown("---")

st.header("📋 Detailed Trading Summary")

if not sales_df.empty:
    sales_df_display = sales_df.copy()
    if 'quantity_mwh' in sales_df_display.columns:
        sales_df_display = sales_df_display[sales_df_display['quantity_mwh'] > 0]
    if 'contract_date' in sales_df_display.columns:
        sales_df_display = sales_df_display.sort_values('contract_date', ascending=False)
    
    display_cols = ['contract_date', 'buyer', 'quantity_mwh', 'sales_price_eur_mwh', 
                   'purchase_price_eur_mwh', 'margin_eur_mwh', 'total_margin', 'payment_status']
    available_cols = [col for col in display_cols if col in sales_df_display.columns]
    
    st.dataframe(sales_df_display[available_cols], use_container_width=True, hide_index=True)
    
    csv = sales_df_display.to_csv(index=False)
    st.download_button("Export Full Report", csv, "trading_report.csv", "text/csv")
else:
    st.info("No trading data available yet")

st.markdown("---")

st.header("📊 Cash Flow Analysis")

st.subheader("Cash Outflows (to Suppliers)")
if not purchases_df.empty and 'payment_date' in purchases_df.columns:
    purchases_df_copy = purchases_df.copy()
    purchases_df_copy['payment_date'] = pd.to_datetime(purchases_df_copy['payment_date'], dayfirst=True)
    outflow_daily = purchases_df_copy.groupby('payment_date')['amount_sent_eur'].sum().reset_index()
    
    fig = px.bar(outflow_daily, x='payment_date', y='amount_sent_eur',
                title='Daily Payments to Suppliers', color_discrete_sequence=['#ef4444'])
    fig.update_layout(xaxis_title='Date', yaxis_title='Amount (EUR)',
                    height=350,
                    margin=dict(l=60, r=40, t=50, b=50))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Add purchase data to see cash outflows")

st.subheader("Cash Inflows (from Buyers)")
if not payments_df.empty and 'payment_date' in payments_df.columns:
    payments_df_copy = payments_df.copy()
    payments_df_copy['payment_date'] = pd.to_datetime(payments_df_copy['payment_date'], format='mixed', dayfirst=True)
    inflow_daily = payments_df_copy.groupby('payment_date')['amount_eur'].sum().reset_index()
    
    fig = px.bar(inflow_daily, x='payment_date', y='amount_eur',
                title='Daily Payments Received', color_discrete_sequence=['#22c55e'])
    fig.update_layout(xaxis_title='Date', yaxis_title='Amount (EUR)',
                    height=350,
                    margin=dict(l=60, r=40, t=50, b=50))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Add payment data to see cash inflows")

st.markdown("---")

st.header("🔄 Payment Status Overview")

if not sales_df.empty and 'payment_status' in sales_df.columns:
    status_summary = sales_df.groupby('payment_status').agg({
        'total_revenue': 'sum',
        'quantity_mwh': 'sum'
    }).reset_index()
    status_summary.columns = ['Status', 'Total Amount (EUR)', 'Quantity (MWh)']
    
    st.dataframe(status_summary, use_container_width=True, hide_index=True)
    
    fig = px.pie(status_summary, values='Total Amount (EUR)', names='Status',
                title='Revenue by Payment Status')
    fig.update_layout(height=400, margin=dict(l=40, r=40, t=50, b=40))
    fig.update_traces(textposition='inside', textinfo='percent+label')
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Add sales data to see payment status overview")
