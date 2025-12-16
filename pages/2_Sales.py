import streamlit as st
import pandas as pd
from datetime import datetime, date
from database import (
    load_sales, save_sales, load_settings, load_purchases,
    sales_to_df, purchases_to_df, generate_id
)

st.set_page_config(page_title="Sales", page_icon="💰", layout="wide")

st.title("💰 Sales Management")
st.markdown("Track natural gas sales, margins, and buyer transactions")

settings = load_settings()
sales = load_sales()
purchases = load_purchases()

purchases_df = purchases_to_df(purchases)
if not purchases_df.empty and 'quantity_mwh' in purchases_df.columns:
    avg_purchase_price = float((purchases_df['price_eur_mwh'] * purchases_df['quantity_mwh']).sum() / purchases_df['quantity_mwh'].sum()) if purchases_df['quantity_mwh'].sum() > 0 else 0.0
else:
    avg_purchase_price = 0.0

tab1, tab2, tab3 = st.tabs(["📊 View Sales", "📝 Add Sale", "📤 Bulk Upload"])

with tab1:
    st.subheader("All Sales")
    
    df = sales_to_df(sales)
    
    if not df.empty:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_revenue = df['total_revenue'].sum()
            st.metric("Total Revenue", f"€{total_revenue:,.2f}")
        with col2:
            total_margin = df['total_margin'].sum()
            st.metric("Total Margin", f"€{total_margin:,.2f}")
        with col3:
            total_quantity = df['quantity_mwh'].sum()
            st.metric("Total Quantity Sold", f"{total_quantity:,.2f} MWh")
        with col4:
            if total_quantity > 0:
                avg_margin = total_margin / total_quantity
                st.metric("Avg Margin", f"€{avg_margin:,.2f}/MWh")
            else:
                st.metric("Avg Margin", "€0.00/MWh")
        
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        with col1:
            filter_buyer = st.multiselect("Filter by Buyer", options=df['buyer'].unique().tolist())
        with col2:
            filter_status = st.multiselect("Filter by Payment Status", options=df['payment_status'].unique().tolist())
        
        filtered_df = df.copy()
        if filter_buyer:
            filtered_df = filtered_df[filtered_df['buyer'].isin(filter_buyer)]
        if filter_status:
            filtered_df = filtered_df[filtered_df['payment_status'].isin(filter_status)]
        
        display_cols = ['contract_date', 'buyer', 'quantity_mwh', 'sales_price_eur_mwh', 
                       'purchase_price_eur_mwh', 'cost_capacity_eur_mwh', 'cost_transport_eur_mwh',
                       'margin_eur_mwh', 'total_revenue', 'total_margin', 'payment_status']
        available_cols = [col for col in display_cols if col in filtered_df.columns]
        
        st.dataframe(filtered_df[available_cols], use_container_width=True, hide_index=True)
        
        csv = filtered_df.to_csv(index=False)
        st.download_button("Export to CSV", csv, "sales_export.csv", "text/csv")
        
        st.markdown("---")
        st.subheader("Update Payment Status")
        if len(sales) > 0:
            sale_options = [f"{s['contract_date']} - {s['buyer']} - €{s['total_revenue']:.2f}" for s in sales]
            selected_sale = st.selectbox("Select sale to update", options=sale_options)
            new_status = st.selectbox("New Status", options=["Pending", "Partial", "Paid"])
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Update Status", type="primary"):
                    idx = sale_options.index(selected_sale)
                    sales[idx]['payment_status'] = new_status
                    save_sales(sales)
                    st.success("Status updated!")
                    st.rerun()
            with col2:
                if st.button("Delete Sale", type="secondary"):
                    idx = sale_options.index(selected_sale)
                    sales.pop(idx)
                    save_sales(sales)
                    st.success("Sale deleted!")
                    st.rerun()
    else:
        st.info("No sales recorded yet. Add your first sale in the 'Add Sale' tab!")

with tab2:
    st.subheader("Add Single Sale Entry")
    
    col1, col2 = st.columns(2)
    
    with col1:
        contract_date = st.date_input("Contract Date (Delivery Date)", value=date.today(), key="single_contract_date")
        sales_price = st.number_input("Sales Price (EUR/MWh)", min_value=0.0, step=0.01, value=0.0, key="single_sales_price")
        quantity_mwh = st.number_input("Quantity (MWh)", min_value=0.0, step=1.0, key="single_sale_quantity")
        buyer = st.selectbox("Buyer", options=settings.get("buyers", ["Keler"]), key="single_buyer")
    
    with col2:
        purchase_price = st.number_input("Purchase Price (EUR/MWh)", min_value=0.0, step=0.01, value=avg_purchase_price, key="single_purchase_price", help="The cost at which gas was purchased")
        cost_capacity = st.number_input("Cost of Capacity (EUR/MWh)", min_value=0.0, step=0.01, key="single_capacity")
        cost_transport = st.number_input("Cost of Transport (EUR/MWh)", min_value=0.0, step=0.01, key="single_transport")
    
    margin = sales_price - purchase_price - cost_capacity - cost_transport
    total_revenue = sales_price * quantity_mwh
    total_margin = margin * quantity_mwh
    
    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Margin (EUR/MWh)", f"€{margin:,.2f}")
    with col2:
        st.metric("Total Revenue", f"€{total_revenue:,.2f}")
    with col3:
        st.metric("Total Margin", f"€{total_margin:,.2f}", delta=f"{'Profit' if total_margin > 0 else 'Loss'}")
    
    if st.button("Add Sale", type="primary", key="add_single_sale"):
        new_sale = {
            "id": generate_id(),
            "contract_date": str(contract_date),
            "sales_price_eur_mwh": sales_price,
            "quantity_mwh": quantity_mwh,
            "cost_capacity_eur_mwh": cost_capacity,
            "cost_transport_eur_mwh": cost_transport,
            "purchase_price_eur_mwh": purchase_price,
            "margin_eur_mwh": margin,
            "total_revenue": total_revenue,
            "total_margin": total_margin,
            "buyer": buyer,
            "amount_paid": 0,
            "payment_status": "Pending"
        }
        sales.append(new_sale)
        save_sales(sales)
        st.success("Sale added successfully!")
        st.rerun()

with tab3:
    st.subheader("Bulk Upload Sales")
    st.markdown("Upload a CSV or Excel file with sales data")
    
    with st.expander("📋 Required Columns Format"):
        st.markdown("""
        Your file should contain the following columns:
        - `contract_date` - Date of contract/delivery (DD/MM/YYYY)
        - `sales_price_eur_mwh` - Sales price in EUR per MWh
        - `quantity_mwh` - Quantity in MWh
        - `cost_capacity_eur_mwh` - Cost of capacity in EUR per MWh
        - `cost_transport_eur_mwh` - Cost of transport in EUR per MWh
        - `purchase_price_eur_mwh` - Purchase price in EUR per MWh
        - `buyer` - Buyer name
        """)
        
        sample_data = pd.DataFrame({
            'contract_date': ['01/11/2024'],
            'sales_price_eur_mwh': [40.00],
            'quantity_mwh': [280],
            'cost_capacity_eur_mwh': [0.50],
            'cost_transport_eur_mwh': [0.30],
            'purchase_price_eur_mwh': [35.50],
            'buyer': ['Keler']
        })
        st.dataframe(sample_data)
        
        csv = sample_data.to_csv(index=False)
        st.download_button("Download Template CSV", csv, "sales_template.csv", "text/csv")
    
    uploaded_file = st.file_uploader("Upload Sales File", type=['csv', 'xlsx'], key="bulk_sales")
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df = pd.read_csv(uploaded_file)
            else:
                df = pd.read_excel(uploaded_file)
            
            st.subheader("Preview of Uploaded Data")
            st.dataframe(df, use_container_width=True)
            
            if st.button("Import All Rows", type="primary", key="import_sales"):
                count = 0
                for _, row in df.iterrows():
                    sales_price = float(row.get('sales_price_eur_mwh', 0))
                    purchase_price = float(row.get('purchase_price_eur_mwh', 0))
                    cost_capacity = float(row.get('cost_capacity_eur_mwh', 0))
                    cost_transport = float(row.get('cost_transport_eur_mwh', 0))
                    quantity = float(row.get('quantity_mwh', 0))
                    
                    margin = sales_price - purchase_price - cost_capacity - cost_transport
                    
                    new_sale = {
                        "id": generate_id(),
                        "contract_date": str(row.get('contract_date', '')),
                        "sales_price_eur_mwh": sales_price,
                        "quantity_mwh": quantity,
                        "cost_capacity_eur_mwh": cost_capacity,
                        "cost_transport_eur_mwh": cost_transport,
                        "purchase_price_eur_mwh": purchase_price,
                        "margin_eur_mwh": margin,
                        "total_revenue": sales_price * quantity,
                        "total_margin": margin * quantity,
                        "buyer": str(row.get('buyer', settings['buyers'][0])),
                        "amount_paid": 0,
                        "payment_status": "Pending"
                    }
                    sales.append(new_sale)
                    count += 1
                
                save_sales(sales)
                st.success(f"Successfully imported {count} sales!")
                st.rerun()
        except Exception as e:
            st.error(f"Error reading file: {str(e)}")
