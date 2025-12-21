
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from database import (
    get_sales, get_supplier_payments, get_payments_received, get_dashboard_metrics,
    sales_to_df, payments_to_df, supplier_payments_to_df
)
from components import load_material_icons, page_header, metric_card, section_header

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
                fig = go.Figure()
                fig.add_trace(go.Scatter(x=sales_daily['contract_date'], y=sales_daily['sales_price_eur_mwh'],
                                        mode='lines+markers', name='Sales Price', line=dict(color='#10b981', width=3)))
                fig.add_trace(go.Scatter(x=sales_daily['contract_date'], y=sales_daily['purchase_price_eur_mwh'],
                                        mode='lines+markers', name='Purchase Price', line=dict(color='#ef4444', width=3)))
                fig.update_layout(
                    title=dict(text='Sales vs Purchase Price', font=dict(size=14, color='#1e293b')),
                    xaxis_title='Date', yaxis_title='Price (EUR/MWh)',
                    hovermode='x unified',
                    height=320,
                    width=None,
                    autosize=True,
                    margin=dict(l=60, r=30, t=50, b=80),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(family='Inter', size=11, color='#64748b'),
                    legend=dict(orientation='h', yanchor='bottom', y=-0.35, xanchor='center', x=0.5),
                    xaxis=dict(gridcolor='rgba(148,163,184,0.1)', fixedrange=True),
                    yaxis=dict(gridcolor='rgba(148,163,184,0.1)', fixedrange=True)
                )
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'staticPlot': True, 'responsive': True})

            with col2:
                fig = go.Figure()
                colors = ['#10b981' if x >= 0 else '#ef4444' for x in sales_daily['margin_eur_mwh']]
                fig.add_trace(go.Bar(x=sales_daily['contract_date'], y=sales_daily['margin_eur_mwh'],
                                    name='Margin', marker_color=colors, showlegend=False))
                fig.update_layout(
                    title=dict(text='Daily Margin per MWh', font=dict(size=14, color='#1e293b')),
                    xaxis_title='Date', yaxis_title='Margin (EUR/MWh)',
                    height=320,
                    width=None,
                    autosize=True,
                    margin=dict(l=60, r=30, t=50, b=60),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(family='Inter', size=11, color='#64748b'),
                    xaxis=dict(gridcolor='rgba(148,163,184,0.1)', fixedrange=True),
                    yaxis=dict(gridcolor='rgba(148,163,184,0.1)', fixedrange=True)
                )
                fig.update_traces(marker_cornerradius=6)
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'staticPlot': True, 'responsive': True})
    else:
        st.markdown("""
            <div style="
                background: rgba(255, 255, 255, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.5);
                border-radius: 16px;
                padding: 3rem 2rem;
                text-align: center;
                color: #64748b;
                backdrop-filter: blur(12px);
            ">
                <span class="material-icons-round" style="font-size: 48px; opacity: 0.4; color: #3b82f6;">insert_chart</span>
                <p style="margin: 1rem 0 0 0;">Add sales data to see price analysis charts</p>
            </div>
        """, unsafe_allow_html=True)

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
            st.dataframe(pd.DataFrame(pnl_data), width='stretch', hide_index=True)

        with col2:
            st.markdown("##### Cost Distribution")
            cost_values = [abs(purchase_cost_total), abs(capacity_cost), abs(transport_cost)]
            cost_labels = ['Purchase', 'Capacity', 'Transport']

            if sum(cost_values) > 0:
                fig = px.pie(values=cost_values, names=cost_labels, 
                            color_discrete_sequence=['#3b82f6', '#10b981', '#f59e0b'])
                fig.update_layout(
                    height=300,
                    width=None,
                    autosize=True,
                    margin=dict(l=10, r=10, t=30, b=10),
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(family='Inter', size=11)
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'staticPlot': True, 'responsive': True})
    else:
        st.info("Add sales data to see P&L breakdown")

    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

    section_header("bar_chart", "Trading Volume")

    if not sales_df.empty and 'contract_date' in sales_df.columns:
        sales_df_copy = sales_df.copy()
        sales_df_copy['contract_date'] = pd.to_datetime(sales_df_copy['contract_date'])
        volume_daily = sales_df_copy.groupby('contract_date').agg({
            'quantity_mwh': 'sum',
            'total_revenue': 'sum',
            'total_margin': 'sum'
        }).reset_index()

        fig = go.Figure()
        fig.add_trace(go.Bar(x=volume_daily['contract_date'], y=volume_daily['quantity_mwh'],
                            name='Volume (MWh)', marker_color='#3b82f6'))
        fig.update_layout(
            title=dict(text='Daily Trading Volume', font=dict(size=16, color='#1e293b')),
            xaxis_title='Date', yaxis_title='Volume (MWh)',
            height=380,
            width=None,
            autosize=True,
            margin=dict(l=60, r=40, t=70, b=60),
            paper_bgcolor='rgba(0,0,0,0)',
            plot_bgcolor='rgba(0,0,0,0)',
            font=dict(family='Inter', size=12, color='#64748b'),
            xaxis=dict(gridcolor='rgba(148,163,184,0.1)', fixedrange=True),
            yaxis=dict(gridcolor='rgba(148,163,184,0.1)', fixedrange=True)
        )
        fig.update_traces(marker_cornerradius=6)
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'staticPlot': True, 'responsive': True})
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
            outflow_daily = purchases_df_copy.groupby('payment_date')['amount_sent_eur'].sum().reset_index()

            fig = px.bar(outflow_daily, x='payment_date', y='amount_sent_eur',
                        color_discrete_sequence=['#ef4444'])
            fig.update_layout(
                xaxis_title='Date', yaxis_title='Amount (EUR)',
                height=320,
                width=None,
                autosize=True,
                margin=dict(l=60, r=30, t=40, b=60),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter', size=12, color='#64748b'),
                showlegend=False,
                xaxis=dict(gridcolor='rgba(148,163,184,0.1)', fixedrange=True),
                yaxis=dict(gridcolor='rgba(148,163,184,0.1)', fixedrange=True)
            )
            fig.update_traces(marker_cornerradius=6)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'staticPlot': True, 'responsive': True})
        else:
            st.info("Add purchase data to see cash outflows")

    with col2:
        st.markdown("##### Cash Inflows (from Buyers)")
        if not payments_df.empty and 'payment_date' in payments_df.columns:
            payments_df_copy = payments_df.copy()
            payments_df_copy['payment_date'] = pd.to_datetime(payments_df_copy['payment_date'])
            inflow_daily = payments_df_copy.groupby('payment_date')['amount_eur'].sum().reset_index()

            fig = px.bar(inflow_daily, x='payment_date', y='amount_eur',
                        color_discrete_sequence=['#10b981'])
            fig.update_layout(
                xaxis_title='Date', yaxis_title='Amount (EUR)',
                height=320,
                width=None,
                autosize=True,
                margin=dict(l=60, r=30, t=40, b=60),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter', size=12, color='#64748b'),
                showlegend=False,
                xaxis=dict(gridcolor='rgba(148,163,184,0.1)', fixedrange=True),
                yaxis=dict(gridcolor='rgba(148,163,184,0.1)', fixedrange=True)
            )
            fig.update_traces(marker_cornerradius=6)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'staticPlot': True, 'responsive': True})
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
