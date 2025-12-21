import streamlit as st
import pandas as pd
import plotly.express as px
from database import get_sales, sales_to_df
from components import load_material_icons, page_header, metric_card, section_header

st.set_page_config(page_title="Purchases", page_icon="🛒", layout="wide")

try:
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except:
    pass

load_material_icons()

page_header("Purchases", "Daily Gas Purchase Details & History")

sales = get_sales()
sales_df = sales_to_df(sales)

if not sales_df.empty and 'quantity_mwh' in sales_df.columns and 'purchase_price_eur_mwh' in sales_df.columns:
    valid_df = sales_df[
        (sales_df['quantity_mwh'] > 0) &
        (sales_df['purchase_price_eur_mwh'] > 0)
    ].copy()

    if not valid_df.empty:
        total_quantity = valid_df['quantity_mwh'].sum()
        total_purchase_cost = (valid_df['quantity_mwh'] * valid_df['purchase_price_eur_mwh']).sum()
        avg_purchase_price = total_purchase_cost / total_quantity if total_quantity > 0 else 0
        num_transactions = len(valid_df)

        col1, col2, col3 = st.columns(3)
        
        with col1:
            metric_card("local_gas_station", "Total Today:", f"{total_quantity:,.0f} MWh", "blue")
        with col2:
            metric_card("attach_money", "Total Cost:", f"€{total_purchase_cost:,.0f}", "green")
        with col3:
            metric_card("schedule", "Transactions:", f"{num_transactions} Orders", "orange")

        st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
        
        col_btn1, col_btn2, col_spacer = st.columns([1, 1, 4])
        with col_btn1:
            csv = valid_df.to_csv(index=False)
            st.download_button(
                "Export",
                csv,
                "purchases.csv",
                "text/csv",
                key="export_btn"
            )
        
        st.markdown("</div>", unsafe_allow_html=True)

        display_df = valid_df[['contract_date', 'supplier' if 'supplier' in valid_df.columns else 'buyer', 'quantity_mwh', 'purchase_price_eur_mwh', 'purchase_cost']].copy()
        
        if 'supplier' not in valid_df.columns:
            display_df = valid_df[['contract_date', 'quantity_mwh', 'purchase_price_eur_mwh', 'purchase_cost']].copy()
            display_df.columns = ['Date', 'Quantity (MWh)', 'Price per MWh', 'Total Cost']
        else:
            display_df.columns = ['Date', 'Supplier', 'Quantity (MWh)', 'Price per MWh', 'Total Cost']

        if 'Date' in display_df.columns:
            try:
                display_df['Date'] = pd.to_datetime(display_df['Date']).dt.strftime('%b %d, %Y')
            except:
                pass

        st.dataframe(
            display_df.style.format({
                'Quantity (MWh)': '{:,.0f}',
                'Price per MWh': '€{:,.2f}',
                'Total Cost': '€{:,.0f}'
            }),
            use_container_width=True,
            hide_index=True,
            height=400
        )
        
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
        
        st.markdown(f"""
            <div style="
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 0 0.5rem;
                color: #64748b;
                font-size: 0.875rem;
            ">
                <span>Showing 1-{min(len(display_df), 10)} of {len(display_df)} records</span>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

        section_header("show_chart", "Purchase Price Trend")

        chart_df = valid_df[['contract_date', 'purchase_price_eur_mwh']].copy()
        try:
            chart_df['contract_date'] = pd.to_datetime(chart_df['contract_date'])
            chart_df = chart_df.sort_values('contract_date')

            fig = px.line(
                chart_df, 
                x='contract_date', 
                y='purchase_price_eur_mwh',
                labels={'contract_date': 'Date', 'purchase_price_eur_mwh': 'Price (EUR/MWh)'}
            )
            fig.update_traces(
                mode='lines+markers',
                line=dict(color='#3b82f6', width=3),
                marker=dict(size=6)
            )
            fig.update_layout(
                title=dict(text='Purchase Price Over Time', font=dict(size=16, color='#1e293b')),
                height=350,
                margin=dict(l=40, r=20, t=50, b=40),
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font=dict(family='Inter', size=12, color='#64748b'),
                showlegend=False,
                xaxis=dict(gridcolor='rgba(148,163,184,0.1)', zerolinecolor='rgba(148,163,184,0.1)'),
                yaxis=dict(gridcolor='rgba(148,163,184,0.1)', zerolinecolor='rgba(148,163,184,0.1)'),
                autosize=True
            )
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'responsive': True})
        except Exception as e:
            st.info("Unable to display price trend chart")
    else:
        st.markdown("""
            <div style="
                background: rgba(255, 255, 255, 0.7);
                border: 1px solid rgba(255, 255, 255, 0.5);
                border-radius: 16px;
                padding: 4rem 2rem;
                text-align: center;
                color: #64748b;
                backdrop-filter: blur(12px);
            ">
                <span class="material-icons-round" style="font-size: 56px; opacity: 0.4; color: #3b82f6;">inventory_2</span>
                <p style="margin: 1.5rem 0 0 0; font-size: 1.1rem; font-weight: 500;">No purchase data available</p>
                <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem; opacity: 0.7;">Sales records with quantity and purchase price will appear here.</p>
            </div>
        """, unsafe_allow_html=True)
else:
    st.markdown("""
        <div style="
            background: rgba(255, 255, 255, 0.7);
            border: 1px solid rgba(255, 255, 255, 0.5);
            border-radius: 16px;
            padding: 4rem 2rem;
            text-align: center;
            color: #64748b;
            backdrop-filter: blur(12px);
        ">
            <span class="material-icons-round" style="font-size: 56px; opacity: 0.4; color: #3b82f6;">inventory_2</span>
            <p style="margin: 1.5rem 0 0 0; font-size: 1.1rem; font-weight: 500;">No purchase data available</p>
            <p style="margin: 0.5rem 0 0 0; font-size: 0.9rem; opacity: 0.7;">Add sales with quantity and purchase price to see daily purchases.</p>
        </div>
    """, unsafe_allow_html=True)
