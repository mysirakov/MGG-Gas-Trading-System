
import streamlit as st
import pandas as pd
import altair as alt
from datetime import datetime
from database import (
    get_sales, get_supplier_payments, get_payments_received, get_dashboard_metrics,
    sales_to_df, payments_to_df, supplier_payments_to_df
)
from components import load_material_icons, page_header, metric_card, section_header, empty_state

st.set_page_config(page_title="Analytics", page_icon="📈", layout="wide")

try:
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except:
    pass

load_material_icons()

page_header("Analytics", "Comprehensive P&L analysis, trading performance, and financial metrics")

sales = get_sales()
purchases = get_supplier_payments()
payments = get_payments_received()
metrics = get_dashboard_metrics()

purchases_df = supplier_payments_to_df(purchases)
sales_df = sales_to_df(sales)
payments_df = payments_to_df(payments)

total_revenue = metrics['total_revenue']
total_margin = metrics['total_margin']
total_quantity_sold = metrics['total_quantity']
margin_pct = (total_margin / total_revenue * 100) if total_revenue > 0 else 0

col1, col2, col3, col4 = st.columns(4)

with col1:
    metric_card("attach_money", "Total Revenue", f"€{total_revenue:,.0f}", "blue")
with col2:
    metric_card("trending_up", "Total Profit", f"€{total_margin:,.0f}", "green")
with col3:
    metric_card("percent", "Profit Margin", f"{margin_pct:.1f}%", "purple")
with col4:
    metric_card("bolt", "Quantity Traded", f"{total_quantity_sold:,.0f} MWh", "orange")

st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)

total_sent = metrics['total_sent_to_suppliers']
supplier_balance = metrics['supplier_balance']
payments_received = metrics['payments_received']
outstanding = metrics['outstanding_receivables']

col1, col2, col3, col4 = st.columns(4)

with col1:
    metric_card("account_balance_wallet", "Paid to Suppliers", f"€{total_sent:,.0f}", "teal")
with col2:
    metric_card("savings", "Supplier Balance", f"€{supplier_balance:,.0f}", "blue")
with col3:
    metric_card("check_circle", "Payments Received", f"€{payments_received:,.0f}", "green")
with col4:
    metric_card("receipt_long", "Outstanding", f"€{outstanding:,.0f}", "orange")

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

section_header("show_chart", "Price Analysis")

if not sales_df.empty:
    if 'contract_date' in sales_df.columns:
        sales_df_copy = sales_df.copy()
        sales_df_copy['contract_date'] = pd.to_datetime(sales_df_copy['contract_date'])
        sales_daily = sales_df_copy.groupby('contract_date').agg({
            'sales_price_eur_mwh': 'mean',
            'purchase_price_eur_mwh': 'mean',
            'margin_eur_mwh': 'mean'
        }).reset_index()

        col1, col2 = st.columns(2)

        with col1:
            sales_daily_chart = sales_daily.set_index('contract_date')[['sales_price_eur_mwh', 'purchase_price_eur_mwh']]
            sales_daily_chart = sales_daily_chart.rename(columns={
                'sales_price_eur_mwh': 'Sales Price',
                'purchase_price_eur_mwh': 'Purchase Price'
            })
            st.markdown("##### Sales vs Purchase Price")
            st.line_chart(sales_daily_chart, color=["#10b981", "#ef4444"])

        with col2:
            st.markdown("##### Daily Margin per MWh")
            margin_daily = sales_daily.set_index('contract_date')['margin_eur_mwh']
            st.bar_chart(margin_daily, color="#10b981")
else:
    empty_state("insert_chart", "Add sales data to see price analysis charts")

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

section_header("account_balance", "P&L Summary")

if not sales_df.empty:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Revenue Breakdown")
        capacity_cost = (sales_df['cost_capacity_eur_mwh'] * sales_df['quantity_mwh']).sum() if 'cost_capacity_eur_mwh' in sales_df.columns else 0
        transport_cost = (sales_df['cost_transport_eur_mwh'] * sales_df['quantity_mwh']).sum() if 'cost_transport_eur_mwh' in sales_df.columns else 0
        purchase_cost_total = metrics['total_purchase_cost']

        pnl_data = {
            'Category': ['Gross Revenue', 'Capacity Costs', 'Transport Costs', 'Purchase Costs', 'Net Profit'],
            'Amount': [
                f"€{total_revenue:,.2f}",
                f"-€{capacity_cost:,.2f}",
                f"-€{transport_cost:,.2f}",
                f"-€{purchase_cost_total:,.2f}",
                f"€{total_margin:,.2f}"
            ]
        }
        st.dataframe(pd.DataFrame(pnl_data), width="stretch", hide_index=True)

    with col2:
        st.markdown("##### Cost Distribution")
        cost_values = [abs(purchase_cost_total), abs(capacity_cost), abs(transport_cost)]
        cost_labels = ['Purchase', 'Capacity', 'Transport']

        if sum(cost_values) > 0:
            cost_df = pd.DataFrame({
                'Category': cost_labels,
                'Amount': cost_values
            })
            
            pie_chart = alt.Chart(cost_df).mark_arc(innerRadius=50).encode(
                theta=alt.Theta(field="Amount", type="quantitative"),
                color=alt.Color(field="Category", type="nominal", 
                               scale=alt.Scale(range=['#3b82f6', '#10b981', '#f59e0b'])),
                tooltip=['Category', 'Amount']
            ).properties(height=350)
            
            st.altair_chart(pie_chart, use_container_width=True)
else:
    st.info("Add sales data to see P&L breakdown")

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

section_header("bar_chart", "Trading Volume")

if not sales_df.empty and 'contract_date' in sales_df.columns:
    sales_df_copy = sales_df.copy()
    sales_df_copy['contract_date'] = pd.to_datetime(sales_df_copy['contract_date'])
    volume_daily = sales_df_copy.groupby('contract_date')['quantity_mwh'].sum()
    st.bar_chart(volume_daily, color='#3b82f6')
else:
    st.info("Add sales data to see volume charts")

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

section_header("swap_horiz", "Cash Flow Analysis")

col1, col2 = st.columns(2)

with col1:
    st.markdown("##### Cash Outflows (to Suppliers)")
    if not purchases_df.empty and 'payment_date' in purchases_df.columns:
        purchases_df_copy = purchases_df.copy()
        purchases_df_copy['payment_date'] = pd.to_datetime(purchases_df_copy['payment_date'])
        outflow_daily = purchases_df_copy.groupby('payment_date')['amount_sent_eur'].sum()
        st.bar_chart(outflow_daily, color='#ef4444')
    else:
        st.info("Add purchase data to see cash outflows")

with col2:
    st.markdown("##### Cash Inflows (from Buyers)")
    if not payments_df.empty and 'payment_date' in payments_df.columns:
        payments_df_copy = payments_df.copy()
        payments_df_copy['payment_date'] = pd.to_datetime(payments_df_copy['payment_date'])
        inflow_daily = payments_df_copy.groupby('payment_date')['amount_eur'].sum()
        st.bar_chart(inflow_daily, color='#10b981')
    else:
        st.info("Add payment data to see cash inflows")

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

section_header("table_chart", "Detailed Trading Summary")

if not sales_df.empty:
    sales_df_display = sales_df.copy()
    if 'quantity_mwh' in sales_df_display.columns:
        sales_df_display = sales_df_display[sales_df_display['quantity_mwh'] > 0]
    if 'contract_date' in sales_df_display.columns:
        sales_df_display['contract_date'] = pd.to_datetime(sales_df_display['contract_date']).dt.strftime('%b %d, %Y')

    display_cols = ['contract_date', 'buyer', 'quantity_mwh', 'sales_price_eur_mwh', 
                   'purchase_price_eur_mwh', 'margin_eur_mwh', 'total_margin', 'amount_paid']
    available_cols = [col for col in display_cols if col in sales_df_display.columns]

    st.dataframe(sales_df_display[available_cols], width='stretch', hide_index=True, height=300)

    csv = sales_df_display.to_csv(index=False)
    st.download_button("Export Full Report", csv, "trading_report.csv", "text/csv")
else:
    st.info("No trading data available yet")
