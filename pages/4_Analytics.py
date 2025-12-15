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
total_quantity_bought = purchases_df['quantity_mwh'].sum() if not purchases_df.empty and 'quantity_mwh' in purchases_df.columns else 0

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
total_cost = purchases_df['total_cost'].sum() if not purchases_df.empty and 'total_cost' in purchases_df.columns else 0
supplier_balance = total_received_supplier - total_cost

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

if not sales_df.empty and not purchases_df.empty:
    col1, col2 = st.columns(2)
    
    with col1:
        if 'contract_date' in sales_df.columns:
            sales_df['contract_date'] = pd.to_datetime(sales_df['contract_date'], dayfirst=True)
            sales_daily = sales_df.groupby('contract_date').agg({
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
                            hovermode='x unified')
            st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        if 'contract_date' in sales_df.columns:
            fig = go.Figure()
            fig.add_trace(go.Bar(x=sales_daily['contract_date'], y=sales_daily['margin_eur_mwh'],
                                name='Margin', marker_color=sales_daily['margin_eur_mwh'].apply(
                                    lambda x: 'green' if x >= 0 else 'red')))
            fig.update_layout(title='Daily Margin per MWh',
                            xaxis_title='Date', yaxis_title='Margin (EUR/MWh)')
            st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Add sales and purchase data to see price analysis charts")

st.markdown("---")

st.header("💰 P&L Summary")

col1, col2 = st.columns(2)

with col1:
    st.subheader("Revenue Breakdown")
    if not sales_df.empty:
        pnl_data = {
            'Category': ['Gross Revenue', 'Capacity Costs', 'Transport Costs', 'Purchase Costs', 'Net Profit'],
            'Amount (EUR)': [
                total_revenue,
                -(sales_df['cost_capacity_eur_mwh'] * sales_df['quantity_mwh']).sum() if 'cost_capacity_eur_mwh' in sales_df.columns else 0,
                -(sales_df['cost_transport_eur_mwh'] * sales_df['quantity_mwh']).sum() if 'cost_transport_eur_mwh' in sales_df.columns else 0,
                -(sales_df['purchase_price_eur_mwh'] * sales_df['quantity_mwh']).sum() if 'purchase_price_eur_mwh' in sales_df.columns else 0,
                total_margin
            ]
        }
        pnl_df = pd.DataFrame(pnl_data)
        st.dataframe(pnl_df, use_container_width=True, hide_index=True)
        
        fig = px.pie(values=[abs(x) for x in pnl_data['Amount (EUR)'][1:4]], 
                    names=['Capacity', 'Transport', 'Purchase'],
                    title='Cost Distribution')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Add sales data to see P&L breakdown")

with col2:
    st.subheader("Trading Volume")
    if not sales_df.empty and 'contract_date' in sales_df.columns:
        volume_daily = sales_df.groupby('contract_date').agg({
            'quantity_mwh': 'sum',
            'total_revenue': 'sum',
            'total_margin': 'sum'
        }).reset_index()
        
        fig = go.Figure()
        fig.add_trace(go.Bar(x=volume_daily['contract_date'], y=volume_daily['quantity_mwh'],
                            name='Volume (MWh)', marker_color='steelblue'))
        fig.update_layout(title='Daily Trading Volume',
                        xaxis_title='Date', yaxis_title='Volume (MWh)')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Add sales data to see volume charts")

st.markdown("---")

st.header("📋 Detailed Trading Summary")

if not sales_df.empty:
    sales_df_display = sales_df.copy()
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

col1, col2 = st.columns(2)

with col1:
    st.subheader("Cash Outflows (to Suppliers)")
    if not purchases_df.empty and 'payment_date' in purchases_df.columns:
        purchases_df['payment_date'] = pd.to_datetime(purchases_df['payment_date'])
        outflow_daily = purchases_df.groupby('payment_date')['amount_sent_eur'].sum().reset_index()
        
        fig = px.bar(outflow_daily, x='payment_date', y='amount_sent_eur',
                    title='Daily Payments to Suppliers', color_discrete_sequence=['red'])
        fig.update_layout(xaxis_title='Date', yaxis_title='Amount (EUR)')
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Add purchase data to see cash outflows")

with col2:
    st.subheader("Cash Inflows (from Buyers)")
    if not payments_df.empty and 'payment_date' in payments_df.columns:
        payments_df['payment_date'] = pd.to_datetime(payments_df['payment_date'])
        inflow_daily = payments_df.groupby('payment_date')['amount_eur'].sum().reset_index()
        
        fig = px.bar(inflow_daily, x='payment_date', y='amount_eur',
                    title='Daily Payments Received', color_discrete_sequence=['green'])
        fig.update_layout(xaxis_title='Date', yaxis_title='Amount (EUR)')
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
    
    col1, col2 = st.columns(2)
    with col1:
        st.dataframe(status_summary, use_container_width=True, hide_index=True)
    with col2:
        fig = px.pie(status_summary, values='Total Amount (EUR)', names='Status',
                    title='Revenue by Payment Status')
        st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Add sales data to see payment status overview")
