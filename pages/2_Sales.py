import streamlit as st
import csv
import io
from datetime import datetime, date
from database import (
    get_sales, add_sale, update_sale, delete_sale, get_settings, sales_to_df
)
from components import load_material_icons, page_header, metric_card, section_header, empty_state, setup_page

st.set_page_config(
    page_title="Mix Gas Group | Sales",
    page_icon="https://slelguoygbfzlpylpxfs.supabase.co/storage/v1/render/image/public/project-uploads/704afe63-0b4a-4050-803e-5116d1754a58/Untitled-Project-1768468114127.png?width=8000&height=8000&resize=contain",
    layout="wide"
)

setup_page()

try:
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except:
    pass

load_material_icons()

page_header("Sales", "Track natural gas sales, margins, and buyer transactions")

settings = get_settings()
sales = get_sales()

tab1, tab2, tab3 = st.tabs(["View Sales", "Add Sale", "Bulk Upload"])

with tab1:
    df = sales_to_df(sales)
    
    if df:
        total_revenue = sum(float(row.get('total_revenue', 0)) for row in df)
        total_margin = sum(float(row.get('total_margin', 0)) for row in df)
        total_quantity = sum(float(row.get('quantity_mwh', 0)) for row in df)
        avg_margin = total_margin / total_quantity if total_quantity > 0 else 0
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            metric_card("attach_money", "Total Revenue", f"€{total_revenue:,.0f}", "blue")
        with col2:
            metric_card("trending_up", "Total Margin", f"€{total_margin:,.0f}", "green")
        with col3:
            metric_card("bolt", "Quantity Sold", f"{total_quantity:,.0f} MWh", "orange")
        with col4:
            metric_card("percent", "Avg Margin", f"€{avg_margin:,.2f}/MWh", "purple")
        
        st.markdown("<div style='height: 1.5rem;'></div>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        with col1:
            buyers_list = sorted(list(set(row.get('buyer') for row in df if row.get('buyer'))))
            filter_buyer = st.multiselect("Filter by Buyer", options=buyers_list)
        
        filtered_df = df
        if filter_buyer:
            filtered_df = [row for row in df if row.get('buyer') in filter_buyer]
        
        display_cols = ['contract_date', 'buyer', 'supplier', 'quantity_mwh', 'sales_price_eur_mwh', 
                       'purchase_price_eur_mwh', 'cost_capacity_eur_mwh', 'cost_transport_eur_mwh',
                       'cost_customs_eur_mwh', 'margin_eur_mwh', 'total_revenue', 'total_margin', 'amount_paid']
        
        display_filtered = []
        for row in filtered_df:
            new_row = {}
            for col in display_cols:
                if col in row:
                    val = row[col]
                    if col == 'contract_date' and val:
                        if isinstance(val, str):
                            try:
                                val = datetime.strptime(val, '%Y-%m-%d').strftime('%b %d, %Y')
                            except:
                                pass
                        elif hasattr(val, 'strftime'):
                            val = val.strftime('%b %d, %Y')
                    new_row[col] = val
            display_filtered.append(new_row)
            
        st.dataframe(display_filtered, width="stretch", height=400)
        
        col1, col2 = st.columns([1, 4])
        with col1:
            output = io.StringIO()
            if filtered_df:
                writer = csv.DictWriter(output, fieldnames=filtered_df[0].keys())
                writer.writeheader()
                writer.writerows(filtered_df)
            csv_data = output.getvalue()
            st.download_button("Export", csv_data, "sales_export.csv", "text/csv")

        
        st.markdown("<div style='height: 2rem;'></div>", unsafe_allow_html=True)
        
        section_header("delete", "Delete Sale")
        if len(sales) > 0:
            sale_options = {f"{s['contract_date']} - {s.get('buyer', 'N/A')} - €{float(s['total_revenue']):.2f}": s['id'] for s in sales}
            col1, col2 = st.columns([3, 1])
            with col1:
                selected_sale = st.selectbox("Select sale to delete", options=list(sale_options.keys()), label_visibility="collapsed")
            with col2:
                if st.button("Delete", type="secondary"):
                    sale_id = sale_options[selected_sale]
                    delete_sale(sale_id)
                    st.success("Sale deleted!")
                    st.rerun()
    else:
        empty_state("leaderboard", "No sales recorded yet")

with tab2:
    section_header("add_circle", "Add Single Sale Entry")
    
    col1, col2 = st.columns(2)
    
    with col1:
        contract_date = st.date_input("Contract Date (Delivery Date)", value=date.today(), key="single_contract_date")
        sales_price = st.number_input("Sales Price (EUR/MWh)", min_value=0.0, step=0.01, value=0.0, key="single_sales_price")
        quantity_mwh = st.number_input("Quantity (MWh)", min_value=0.0, step=1.0, key="single_sale_quantity")
        buyer = st.selectbox("Buyer", options=settings.get("buyers", ["Keler"]), key="single_buyer")
    
    with col2:
        supplier = st.selectbox("Supplier", options=settings.get("suppliers", ["GPE"]), key="single_supplier", help="Select the supplier for this purchase")
        purchase_price = st.number_input("Purchase Price (EUR/MWh)", min_value=0.0, step=0.01, key="single_purchase_price", help="The cost at which gas was purchased")
        cost_capacity = st.number_input("Cost of Capacity (EUR/MWh)", min_value=0.0, step=0.01, key="single_capacity")
        cost_transport = st.number_input("Cost of Transport (EUR/MWh)", min_value=0.0, step=0.01, key="single_transport")
        cost_customs = st.number_input("Cost of Customs (EUR/MWh)", min_value=0.0, step=0.01, key="single_customs", help="Customs expense per MWh")
    
    margin = sales_price - purchase_price - cost_capacity - cost_transport - cost_customs
    total_revenue_calc = sales_price * quantity_mwh
    total_margin_calc = margin * quantity_mwh
    
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    with col1:
        metric_card("calculate", "Margin (EUR/MWh)", f"€{margin:,.2f}", "blue")
    with col2:
        metric_card("attach_money", "Total Revenue", f"€{total_revenue_calc:,.2f}", "green")
    with col3:
        color = "green" if total_margin_calc >= 0 else "red"
        metric_card("trending_up" if total_margin_calc >= 0 else "trending_down", "Total Margin", f"€{total_margin_calc:,.2f}", color)
    
    st.markdown("<div style='height: 1rem;'></div>", unsafe_allow_html=True)
    
    if st.button("Add Sale", type="primary", key="add_single_sale"):
        add_sale(contract_date, buyer, quantity_mwh, sales_price, purchase_price, cost_capacity, cost_transport, supplier, cost_customs)
        st.success("Sale added successfully!")
        st.rerun()

with tab3:
    section_header("upload_file", "Bulk Upload Sales")
    
    with st.expander("Required Columns Format"):
        st.markdown("""
        Your file should contain the following columns:
        - `contract_date` - Date of contract/delivery (DD/MM/YYYY)
        - `sales_price_eur_mwh` - Sales price in EUR per MWh
        - `quantity_mwh` - Quantity in MWh
        - `cost_capacity_eur_mwh` - Cost of capacity in EUR per MWh
        - `cost_transport_eur_mwh` - Cost of transport in EUR per MWh
        - `cost_customs_eur_mwh` - Cost of customs in EUR per MWh
        - `purchase_price_eur_mwh` - Purchase price in EUR per MWh
        - `buyer` - Buyer name
        - `supplier` - Supplier name (optional, defaults to GPE)
        """)
        
        sample_data = [
            {
                'contract_date': '01/11/2024',
                'sales_price_eur_mwh': 40.00,
                'quantity_mwh': 280,
                'cost_capacity_eur_mwh': 0.50,
                'cost_transport_eur_mwh': 0.30,
                'cost_customs_eur_mwh': 0.10,
                'purchase_price_eur_mwh': 35.50,
                'buyer': 'Keler',
                'supplier': 'GPE'
            }
        ]
        st.dataframe(sample_data)
        
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=sample_data[0].keys())
        writer.writeheader()
        writer.writerows(sample_data)
        csv_data = output.getvalue()
        st.download_button("Download Template CSV", csv_data, "sales_template.csv", "text/csv")
    
    uploaded_file = st.file_uploader("Upload Sales File", type=['csv'], key="bulk_sales")
    
    if uploaded_file:
        try:
            content = uploaded_file.read().decode('utf-8')
            reader = csv.DictReader(io.StringIO(content))
            data = list(reader)
            
            st.markdown("##### Preview of Uploaded Data")
            st.dataframe(data, width="stretch")
            
            if st.button("Import All Rows", type="primary", key="import_sales"):
                count = 0
                for row in data:
                    contract_date_str = row.get('contract_date', '')
                    contract_date = date.today()
                    for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%m/%d/%Y']:
                        try:
                            contract_date = datetime.strptime(contract_date_str, fmt).date()
                            break
                        except:
                            continue
                    
                    add_sale(
                        contract_date,
                        str(row.get('buyer', settings['buyers'][0] if settings['buyers'] else 'Unknown')),
                        float(row.get('quantity_mwh', 0) or 0),
                        float(row.get('sales_price_eur_mwh', 0) or 0),
                        float(row.get('purchase_price_eur_mwh', 0) or 0),
                        float(row.get('cost_capacity_eur_mwh', 0) or 0),
                        float(row.get('cost_transport_eur_mwh', 0) or 0),
                        str(row.get('supplier', settings['suppliers'][0] if settings['suppliers'] else 'GPE')),
                        float(row.get('cost_customs_eur_mwh', 0) or 0)
                    )
                    count += 1
                
                st.success(f"Successfully imported {count} sales!")
                st.rerun()
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
