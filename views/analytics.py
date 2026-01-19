import streamlit as st
import csv
import io
from datetime import datetime, timedelta, date
from dateutil.relativedelta import relativedelta
from database import get_sales, get_supplier_payments, get_payments_received, get_dashboard_metrics, sales_to_df, supplier_payments_to_df, payments_to_df, get_settings, get_period_comparison_statistics
from components import load_material_icons, page_header, section_header, metric_card, empty_state, stat_card_with_delta

def get_date_range_for_preset(preset):
    """Calculate date range based on preset selection"""
    today = date.today()
    
    if preset == "Today":
        return today, today, today - timedelta(days=1), today - timedelta(days=1)
    elif preset == "This Week":
        start = today - timedelta(days=today.weekday())
        prev_start = start - timedelta(weeks=1)
        prev_end = start - timedelta(days=1)
        return start, today, prev_start, prev_end
    elif preset == "This Month":
        start = today.replace(day=1)
        prev_end = start - timedelta(days=1)
        prev_start = prev_end.replace(day=1)
        return start, today, prev_start, prev_end
    elif preset == "Last Month":
        end = today.replace(day=1) - timedelta(days=1)
        start = end.replace(day=1)
        prev_end = start - timedelta(days=1)
        prev_start = prev_end.replace(day=1)
        return start, end, prev_start, prev_end
    elif preset == "Last 3 Months":
        start = today - relativedelta(months=3)
        prev_start = start - relativedelta(months=3)
        prev_end = start - timedelta(days=1)
        return start, today, prev_start, prev_end
    elif preset == "This Year":
        start = today.replace(month=1, day=1)
        prev_start = (start - relativedelta(years=1))
        prev_end = start - timedelta(days=1)
        return start, today, prev_start, prev_end
    elif preset == "All Time":
        return None, None, None, None
    else:
        return None, None, None, None

def show_analytics():
    load_material_icons()

    page_header("Analytics", "Comprehensive P&L analysis, trading performance, and financial metrics")

    settings = get_settings()
    buyers_list = settings.get('buyers', [])
    suppliers_list = settings.get('suppliers', [])

    section_header("filter_alt", "Filtered Statistics")
    
    selected_buyers = []
    selected_suppliers = []
    
    with st.container():
        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([1.5, 1, 1, 1])
        
        with filter_col1:
            date_preset = st.selectbox(
                "Period",
                ["This Month", "Today", "This Week", "Last Month", "Last 3 Months", "This Year", "All Time", "Custom"],
                index=0,
                key="stats_date_preset"
            )
        
        date_from, date_to, prev_from, prev_to = get_date_range_for_preset(date_preset)
        
        if date_preset == "Custom":
            with filter_col2:
                date_from = st.date_input("From", value=date.today().replace(day=1), key="stats_date_from")
            with filter_col3:
                date_to = st.date_input("To", value=date.today(), key="stats_date_to")
            if date_from and date_to:
                delta_days = (date_to - date_from).days + 1
                prev_to = date_from - timedelta(days=1)
                prev_from = prev_to - timedelta(days=delta_days - 1)
        else:
            with filter_col2:
                selected_buyers = st.multiselect("Buyer", buyers_list, key="stats_buyers")
            with filter_col3:
                selected_suppliers = st.multiselect("Supplier", suppliers_list, key="stats_suppliers")
        
        if date_preset == "Custom":
            filter_col_b1, filter_col_b2 = st.columns(2)
            with filter_col_b1:
                selected_buyers = st.multiselect("Buyer", buyers_list, key="stats_buyers_custom")
            with filter_col_b2:
                selected_suppliers = st.multiselect("Supplier", suppliers_list, key="stats_suppliers_custom")

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)
    
    available_stats = {
        "total_margin": {"label": "Total Margin", "icon": "trending_up", "color": "green"},
        "margin_per_mwh": {"label": "Margin/MWh", "icon": "paid", "color": "teal"},
        "avg_buy_price": {"label": "Avg Buy Price", "icon": "shopping_cart", "color": "orange"},
        "avg_sell_price": {"label": "Avg Sell Price", "icon": "storefront", "color": "blue"},
        "avg_spread": {"label": "Spread", "icon": "swap_vert", "color": "purple"},
        "total_quantity": {"label": "Volume (MWh)", "icon": "bolt", "color": "indigo"},
        "trade_count": {"label": "# Trades", "icon": "receipt_long", "color": "teal"},
        "margin_pct": {"label": "Margin %", "icon": "percent", "color": "green"},
        "total_revenue": {"label": "Revenue", "icon": "attach_money", "color": "blue"},
    }
    
    default_stats = ["total_margin", "margin_per_mwh", "avg_buy_price", "avg_sell_price", "avg_spread", "total_quantity"]
    
    with st.expander("Select Statistics to Display", expanded=False):
        stat_cols = st.columns(3)
        selected_stats = []
        for i, (key, info) in enumerate(available_stats.items()):
            with stat_cols[i % 3]:
                if st.checkbox(info["label"], value=key in default_stats, key=f"stat_{key}"):
                    selected_stats.append(key)
    
    if not selected_stats:
        selected_stats = default_stats

    buyers_filter = selected_buyers if selected_buyers else None
    suppliers_filter = selected_suppliers if selected_suppliers else None
    
    stats_data = get_period_comparison_statistics(
        date_from, date_to, prev_from, prev_to,
        buyers=buyers_filter, suppliers=suppliers_filter
    )
    
    current = stats_data['current']
    deltas = stats_data['deltas']
    
    period_label = "vs prev period"
    if date_preset == "This Month":
        period_label = "vs last month"
    elif date_preset == "This Week":
        period_label = "vs last week"
    elif date_preset == "Last Month":
        period_label = "vs prev month"
    elif date_preset == "This Year":
        period_label = "vs last year"

    st.markdown("<div style='height: 0.5rem;'></div>", unsafe_allow_html=True)

    num_cols = min(len(selected_stats), 4)
    stat_rows = [selected_stats[i:i+num_cols] for i in range(0, len(selected_stats), num_cols)]
    
    for row_stats in stat_rows:
        cols = st.columns(len(row_stats))
        for i, stat_key in enumerate(row_stats):
            with cols[i]:
                info = available_stats[stat_key]
                value = current.get(stat_key, 0)
                delta = deltas.get(f"{stat_key}_delta", None)
                
                if stat_key == "total_margin":
                    formatted = f"€{value:,.0f}"
                elif stat_key == "margin_per_mwh":
                    formatted = f"€{value:,.2f}"
                elif stat_key in ["avg_buy_price", "avg_sell_price", "avg_spread"]:
                    formatted = f"€{value:,.2f}/MWh"
                elif stat_key == "total_quantity":
                    formatted = f"{value:,.0f} MWh"
                elif stat_key == "trade_count":
                    formatted = f"{int(value)}"
                elif stat_key == "margin_pct":
                    formatted = f"{value:.1f}%"
                elif stat_key == "total_revenue":
                    formatted = f"€{value:,.0f}"
                else:
                    formatted = f"{value:,.2f}"
                
                inverse_colors = (stat_key == "avg_buy_price")
                stat_card_with_delta(
                    icon=info["icon"], 
                    label=info["label"], 
                    value=formatted, 
                    delta=delta, 
                    delta_label=period_label,
                    color=info["color"],
                    inverse_colors=inverse_colors
                )
        st.markdown("<div style='height: 0.75rem;'></div>", unsafe_allow_html=True)

    st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
    st.markdown("<hr style='border: none; border-top: 1px solid #e2e8f0; margin: 1rem 0 2rem 0;'>", unsafe_allow_html=True)
    
    section_header("assessment", "Overall Performance")

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
        daily_prices = {}
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
                
            if d_str not in daily_prices:
                daily_prices[d_str] = {'sales_price': [], 'purchase_price': [], 'margin': []}
            
            daily_prices[d_str]['sales_price'].append(float(s.get('sales_price_eur_mwh', 0) or 0))
            daily_prices[d_str]['purchase_price'].append(float(s.get('purchase_price_eur_mwh', 0) or 0))
            daily_prices[d_str]['margin'].append(float(s.get('margin_eur_mwh', 0) or 0))

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

        output = io.StringIO()
        if summary_display:
            writer = csv.DictWriter(output, fieldnames=summary_display[0].keys())
            writer.writeheader()
            writer.writerows(summary_display)
            csv_data = output.getvalue()
            st.download_button("Export Full Report", csv_data, "trading_report.csv", "text/csv", key="analytics_export")
    else:
        st.info("No trading data available yet")
