import streamlit as st
import pandas as pd
from database import (
    load_purchases, load_sales, load_settings,
    purchases_to_df, sales_to_df
)

st.set_page_config(page_title="Seller Balance", page_icon="🏦", layout="wide")

st.title("🏦 Seller Balance")
st.markdown("Track the balance available with your gas supplier")

settings = load_settings()
purchases = load_purchases()
sales = load_sales()

purchases_df = purchases_to_df(purchases)
sales_df = sales_to_df(sales)

total_purchase_cost = 0
if not sales_df.empty and 'quantity_mwh' in sales_df.columns and 'purchase_price_eur_mwh' in sales_df.columns:
    total_purchase_cost = (sales_df['quantity_mwh'] * sales_df['purchase_price_eur_mwh']).sum()

total_received_by_supplier = 0
if not purchases_df.empty and 'amount_received_eur' in purchases_df.columns:
    total_received_by_supplier = purchases_df['amount_received_eur'].sum()

supplier_balance = total_received_by_supplier - total_purchase_cost

st.header("📊 Overall Balance")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Total Received by Supplier", f"€{total_received_by_supplier:,.2f}", 
              help="Total amount received by the supplier (GPE) from your payments")

with col2:
    st.metric("Total Purchase Cost", f"€{total_purchase_cost:,.2f}",
              help="Total value of gas purchased = Sum of (Quantity MWh × Purchase Price EUR/MWh) from Sales")

with col3:
    delta_text = "Available" if supplier_balance >= 0 else "Overdraw"
    st.metric("Supplier Balance", f"€{supplier_balance:,.2f}", 
              delta=delta_text,
              help="Balance available with supplier = Amount Received - Purchase Cost")

st.markdown("---")

st.header("📋 Balance Breakdown by Supplier")

if not purchases_df.empty:
    suppliers = purchases_df['supplier'].unique().tolist()
    
    balance_data = []
    for supplier in suppliers:
        sup_purchases = purchases_df[purchases_df['supplier'] == supplier]
        amount_received = sup_purchases['amount_received_eur'].sum()
        
        balance_data.append({
            'Supplier': supplier,
            'Amount Received (EUR)': amount_received,
            'Purchase Cost (EUR)': total_purchase_cost,
            'Available Balance (EUR)': amount_received - total_purchase_cost
        })
    
    balance_df = pd.DataFrame(balance_data)
    
    st.dataframe(
        balance_df.style.format({
            'Amount Received (EUR)': '€{:,.2f}',
            'Purchase Cost (EUR)': '€{:,.2f}',
            'Available Balance (EUR)': '€{:,.2f}'
        }),
        use_container_width=True,
        hide_index=True
    )
else:
    st.info("No purchase data available. Add purchases to see supplier balances.")

st.markdown("---")

st.header("📈 Purchase Cost Details (from Sales)")

if not sales_df.empty:
    st.markdown("Purchase cost is calculated from the Sales data as: **Quantity (MWh) × Purchase Price (EUR/MWh)**")
    
    if 'contract_date' in sales_df.columns:
        display_df = sales_df[['contract_date', 'quantity_mwh', 'purchase_price_eur_mwh']].copy()
        display_df['purchase_cost'] = display_df['quantity_mwh'] * display_df['purchase_price_eur_mwh']
        display_df.columns = ['Contract Date', 'Quantity (MWh)', 'Purchase Price (EUR/MWh)', 'Purchase Cost (EUR)']
        
        st.dataframe(
            display_df.style.format({
                'Quantity (MWh)': '{:,.2f}',
                'Purchase Price (EUR/MWh)': '€{:,.2f}',
                'Purchase Cost (EUR)': '€{:,.2f}'
            }),
            use_container_width=True,
            hide_index=True
        )
        
        st.markdown(f"**Total Purchase Cost: €{total_purchase_cost:,.2f}**")
else:
    st.info("No sales data available. Add sales to see purchase cost breakdown.")

st.markdown("---")

st.header("💳 Payments to Supplier (from Purchases)")

if not purchases_df.empty:
    display_cols = ['payment_date', 'supplier', 'amount_sent_eur', 'amount_received_eur']
    available_cols = [c for c in display_cols if c in purchases_df.columns]
    
    st.dataframe(purchases_df[available_cols], use_container_width=True, hide_index=True)
    
    st.markdown(f"**Total Received by Supplier: €{total_received_by_supplier:,.2f}**")
else:
    st.info("No purchase data available.")
