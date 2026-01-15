import streamlit as st
import csv
import io
from datetime import datetime
from database import get_sales, sales_to_df
from components import load_material_icons, page_header, metric_card, section_header, empty_state, setup_page
from auth import require_auth

st.set_page_config(
    page_title="Mix Gas Group | Purchases",
    page_icon="https://slelguoygbfzlpylpxfs.supabase.co/storage/v1/render/image/public/project-uploads/704afe63-0b4a-4050-803e-5116d1754a58/Untitled-Project-1768468114127.png?width=8000&height=8000&resize=contain",
    layout="wide"
)

require_auth()
setup_page()

try:
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except:
    pass

load_material_icons()

page_header("Purchases", "Daily Gas Purchase Details & History")

sales = get_sales()
sales_df = sales_to_df(sales)

if sales_df and any(row.get('quantity_mwh', 0) > 0 for row in sales_df):
    valid_sales = [
        row for row in sales_df 
        if float(row.get('quantity_mwh', 0)) > 0 and float(row.get('purchase_price_eur_mwh', 0)) > 0
    ]

    if valid_sales:
        total_quantity = sum(float(row.get('quantity_mwh', 0)) for row in valid_sales)
        total_purchase_cost = sum(float(row.get('quantity_mwh', 0)) * float(row.get('purchase_price_eur_mwh', 0)) for row in valid_sales)
        avg_purchase_price = total_purchase_cost / total_quantity if total_quantity > 0 else 0
        num_transactions = len(valid_sales)

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
            output = io.StringIO()
            if valid_sales:
                writer = csv.DictWriter(output, fieldnames=valid_sales[0].keys())
                writer.writeheader()
                writer.writerows(valid_sales)
            csv_data = output.getvalue()
            st.download_button(
                "Export",
                csv_data,
                "purchases.csv",
                "text/csv",
                key="export_btn"
            )
        
        st.markdown("</div>", unsafe_allow_html=True)

        display_data = []
        for row in valid_sales:
            date_val = row.get('contract_date')
            if isinstance(date_val, str):
                try:
                    date_val = datetime.strptime(date_val, '%Y-%m-%d').strftime('%b %d, %Y')
                except:
                    pass
            elif hasattr(date_val, 'strftime'):
                date_val = date_val.strftime('%b %d, %Y')
                
            display_row = {
                'Date': date_val,
                'Quantity (MWh)': f"{float(row.get('quantity_mwh', 0)):,.0f}",
                'Price per MWh': f"€{float(row.get('purchase_price_eur_mwh', 0)):,.2f}",
                'Total Cost': f"€{float(row.get('purchase_cost', 0)):,.0f}"
            }
            if 'supplier' in row:
                display_row['Supplier'] = row['supplier']
            display_data.append(display_row)

        st.dataframe(
            display_data,
            width="stretch",
            height=400
        )
        
        st.markdown("</div>", unsafe_allow_html=True)

        st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
        
        st.markdown(f"""
            <div class="summary-container">
                <span>Showing 1-{min(len(display_data), 10)} of {len(display_data)} records</span>
            </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)

        section_header("show_chart", "Purchase Price Trend")

        chart_data = []
        for row in valid_sales:
            d = row.get('contract_date')
            if isinstance(d, str):
                try:
                    d = datetime.strptime(d, '%Y-%m-%d').date()
                except:
                    pass
            
            # Format date for Vega-Lite
            if hasattr(d, 'isoformat'):
                d_str = d.isoformat()
            else:
                d_str = str(d)

            chart_data.append({
                'date': d_str,
                'Price': float(row.get('purchase_price_eur_mwh', 0))
            })
        
        try:
            # Sort by date
            chart_data.sort(key=lambda x: x['date'])
            
            st.vega_lite_chart(chart_data, {
                'mark': {'type': 'line', 'point': True, 'color': '#1E88E5'},
                'encoding': {
                    'x': {'field': 'date', 'type': 'temporal', 'title': 'Date'},
                    'y': {'field': 'Price', 'type': 'quantitative', 'title': 'Price (€/MWh)'}
                },
                'width': 'container',
                'height': 300
            })
        except Exception as e:
            st.info("Unable to display price trend chart")
else:
    empty_state("inventory_2", "No purchase data available")
