import streamlit as st
import io
import csv
from datetime import date, datetime
from database import (
    get_sales, get_supplier_payments, get_payments_received, get_dashboard_metrics,
    sales_to_df, payments_to_df, supplier_payments_to_df
)
from components import load_material_icons, page_header, metric_card, section_header, empty_state, sidebar_logo

st.set_page_config(
    page_title="Mix Gas Group | Analytics",
    page_icon="https://slelguoygbfzlpylpxfs.supabase.co/storage/v1/render/image/public/project-uploads/704afe63-0b4a-4050-803e-5116d1754a58/Untitled-Project-1768468114127.png?width=8000&height=8000&resize=contain",
    layout="wide"
)

# Render sidebar logo
sidebar_logo()

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

purchases_data = supplier_payments_to_df(purchases)
sales_data = sales_to_df(sales)
payments_data = payments_to_df(payments)

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
payments_received_total = metrics['payments_received']
outstanding = metrics['outstanding_receivables']

col1, col2, col3, col4 = st.columns(4)

with col1:
    metric_card("account_balance_wallet", "Paid to Suppliers", f"€{total_sent:,.0f}", "teal")
with col2:
    metric_card("savings", "Supplier Balance", f"€{supplier_balance:,.0f}", "blue")
with col3:
    metric_card("check_circle", "Payments Received", f"€{payments_received_total:,.0f}", "green")
with col4:
    metric_card("receipt_long", "Outstanding", f"€{outstanding:,.0f}", "orange")

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

section_header("show_chart", "Price Analysis")

if sales_data:
    # Group by date for line chart
    daily_prices = {}
    for s in sales_data:
        d = s.get('contract_date')
        if not d: continue
        if isinstance(d, str):
            try: d = datetime.strptime(d, '%Y-%m-%d').date()
            except: continue
        
        # Format date for Vega-Lite
        if hasattr(d, 'isoformat'):
            d_str = d.isoformat()
        else:
            d_str = str(d)
            
        if d_str not in daily_prices:
            daily_prices[d_str] = {'sales_price': [], 'purchase_price': [], 'margin': []}
        
        daily_prices[d_str]['sales_price'].append(float(s.get('sales_price_eur_mwh', 0) or 0))
        daily_prices[d_str]['purchase_price'].append(float(s.get('purchase_price_eur_mwh', 0) or 0))
        daily_prices[d_str]['margin'].append(float(s.get('margin_eur_mwh', 0) or 0))

    # Calculate means
    chart_data = []
    margin_data = []
    sorted_dates = sorted(daily_prices.keys())
    for d in sorted_dates:
        s_price = sum(daily_prices[d]['sales_price']) / len(daily_prices[d]['sales_price'])
        p_price = sum(daily_prices[d]['purchase_price']) / len(daily_prices[d]['purchase_price'])
        m_price = sum(daily_prices[d]['margin']) / len(daily_prices[d]['margin'])
        
        chart_data.append({'date': d, 'Price': s_price, 'Type': 'Sales Price'})
        chart_data.append({'date': d, 'Price': p_price, 'Type': 'Purchase Price'})
        margin_data.append({'date': d, 'Margin': m_price})

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Sales vs Purchase Price")
        if chart_data:
            st.vega_lite_chart(chart_data, {
                'mark': {'type': 'line', 'point': True},
                'encoding': {
                    'x': {'field': 'date', 'type': 'temporal', 'title': 'Date'},
                    'y': {'field': 'Price', 'type': 'quantitative', 'title': 'Price (€/MWh)'},
                    'color': {'field': 'Type', 'type': 'nominal'}
                },
                'width': 'container',
                'height': 300
            })

    with col2:
        st.markdown("##### Daily Margin per MWh")
        if margin_data:
            st.vega_lite_chart(margin_data, {
                'mark': {'type': 'bar', 'color': '#43A047'},
                'encoding': {
                    'x': {'field': 'date', 'type': 'temporal', 'title': 'Date'},
                    'y': {'field': 'Margin', 'type': 'quantitative', 'title': 'Margin (€/MWh)'}
                },
                'width': 'container',
                'height': 300
            })
else:
    empty_state("insert_chart", "Add sales data to see price analysis charts")

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

section_header("account_balance", "P&L Summary")

if sales_data:
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("##### Revenue Breakdown")
        capacity_cost = sum(float(s.get('cost_capacity_eur_mwh', 0) or 0) * float(s.get('quantity_mwh', 0) or 0) for s in sales_data)
        transport_cost = sum(float(s.get('cost_transport_eur_mwh', 0) or 0) * float(s.get('quantity_mwh', 0) or 0) for s in sales_data)
        purchase_cost_total = metrics['total_purchase_cost']

        pnl_display = [
            {'Category': 'Gross Revenue', 'Amount': f"€{total_revenue:,.2f}"},
            {'Category': 'Capacity Costs', 'Amount': f"-€{capacity_cost:,.2f}"},
            {'Category': 'Transport Costs', 'Amount': f"-€{transport_cost:,.2f}"},
            {'Category': 'Purchase Costs', 'Amount': f"-€{purchase_cost_total:,.2f}"},
            {'Category': 'Net Profit', 'Amount': f"€{total_margin:,.2f}"}
        ]
        st.dataframe(pnl_display)

    with col2:
        st.markdown("##### Cost Distribution")
        cost_values = [abs(purchase_cost_total), abs(capacity_cost), abs(transport_cost)]
        cost_labels = ['Purchase', 'Capacity', 'Transport']
        
        if sum(cost_values) > 0:
            distribution = []
            for label, val in zip(cost_labels, cost_values):
                distribution.append({'Category': label, 'Amount': val})
            
            st.vega_lite_chart(distribution, {
                'mark': {'type': 'bar', 'color': '#FB8C00'},
                'encoding': {
                    'x': {'field': 'Category', 'type': 'nominal', 'title': 'Cost Category'},
                    'y': {'field': 'Amount', 'type': 'quantitative', 'title': 'Amount (€)'}
                },
                'width': 'container',
                'height': 300
            })
else:
    st.info("Add sales data to see P&L breakdown")

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

section_header("bar_chart", "Trading Volume")

if sales_data:
    volume_dict = {}
    for s in sales_data:
        d = s.get('contract_date')
        if not d: continue
        if isinstance(d, str):
            try: d = datetime.strptime(d, '%Y-%m-%d').date()
            except: continue
        
        if hasattr(d, 'isoformat'):
            d_str = d.isoformat()
        else:
            d_str = str(d)
        
        volume_dict[d_str] = volume_dict.get(d_str, 0) + float(s.get('quantity_mwh', 0) or 0)
    
    volume_chart = [{'date': d, 'Quantity': v} for d, v in sorted(volume_dict.items())]
    if volume_chart:
        st.vega_lite_chart(volume_chart, {
            'mark': {'type': 'bar', 'color': '#1E88E5'},
            'encoding': {
                'x': {'field': 'date', 'type': 'temporal', 'title': 'Date'},
                'y': {'field': 'Quantity', 'type': 'quantitative', 'title': 'MWh'}
            },
            'width': 'container',
            'height': 300
        })
else:
    st.info("Add sales data to see volume charts")

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

section_header("swap_horiz", "Cash Flow Analysis")

col1, col2 = st.columns(2)

with col1:
    st.markdown("##### Cash Outflows (to Suppliers)")
    if purchases_data:
        outflow_dict = {}
        for p in purchases_data:
            d = p.get('payment_date')
            if not d: continue
            if isinstance(d, str):
                try: d = datetime.strptime(d, '%Y-%m-%d').date()
                except: continue
            
            if hasattr(d, 'isoformat'):
                d_str = d.isoformat()
            else:
                d_str = str(d)
                
            outflow_dict[d_str] = outflow_dict.get(d_str, 0) + float(p.get('amount_sent_eur', 0) or 0)
        
        outflow_chart = [{'date': d, 'Amount': v} for d, v in sorted(outflow_dict.items())]
        if outflow_chart:
            st.vega_lite_chart(outflow_chart, {
                'mark': {'type': 'bar', 'color': '#E53935'},
                'encoding': {
                    'x': {'field': 'date', 'type': 'temporal', 'title': 'Date'},
                    'y': {'field': 'Amount', 'type': 'quantitative', 'title': 'Amount (€)'}
                },
                'width': 'container',
                'height': 300
            })
    else:
        st.info("Add purchase data to see cash outflows")

with col2:
    st.markdown("##### Cash Inflows (from Buyers)")
    if payments_data:
        inflow_dict = {}
        for p in payments_data:
            d = p.get('payment_date')
            if not d: continue
            if isinstance(d, str):
                try: d = datetime.strptime(d, '%Y-%m-%d').date()
                except: continue
            
            if hasattr(d, 'isoformat'):
                d_str = d.isoformat()
            else:
                d_str = str(d)
                
            inflow_dict[d_str] = inflow_dict.get(d_str, 0) + float(p.get('amount_eur', 0) or 0)
            
        inflow_chart = [{'date': d, 'Amount': v} for d, v in sorted(inflow_dict.items())]
        if inflow_chart:
            st.vega_lite_chart(inflow_chart, {
                'mark': {'type': 'bar', 'color': '#43A047'},
                'encoding': {
                    'x': {'field': 'date', 'type': 'temporal', 'title': 'Date'},
                    'y': {'field': 'Amount', 'type': 'quantitative', 'title': 'Amount (€)'}
                },
                'width': 'container',
                'height': 300
            })
    else:
        st.info("Add payment data to see cash inflows")

st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

section_header("table_chart", "Detailed Trading Summary")

if sales_data:
    display_cols = ['contract_date', 'buyer', 'quantity_mwh', 'sales_price_eur_mwh', 
                   'purchase_price_eur_mwh', 'margin_eur_mwh', 'total_margin', 'amount_paid']
    
    summary_display = []
    for s in sales_data:
        if float(s.get('quantity_mwh', 0) or 0) <= 0:
            continue
            
        row = {}
        for col in display_cols:
            val = s.get(col)
            if col == 'contract_date' and val:
                if isinstance(val, (date, datetime)):
                    row[col] = val.strftime('%b %d, %Y')
                else:
                    row[col] = str(val)
            else:
                row[col] = val
        summary_display.append(row)

    st.dataframe(summary_display)

    # Simple CSV export
    output = io.StringIO()
    if summary_display:
        writer = csv.DictWriter(output, fieldnames=summary_display[0].keys())
        writer.writeheader()
        writer.writerows(summary_display)
        csv_data = output.getvalue()
        st.download_button("Export Full Report", csv_data, "trading_report.csv", "text/csv")
else:
    st.info("No trading data available yet")
