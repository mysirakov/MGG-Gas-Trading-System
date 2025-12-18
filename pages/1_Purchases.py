import streamlit as st
import pandas as pd
from database import get_sales, sales_to_df

st.set_page_config(page_title="Purchases", page_icon="📦", layout="wide")

try:
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except:
    pass

st.title("📦 Daily Gas Purchases")
st.markdown("View daily gas purchase details calculated from sales data")

sales = get_sales()
sales_df = sales_to_df(sales)

if not sales_df.empty and 'quantity_mwh' in sales_df.columns and 'purchase_price_eur_mwh' in sales_df.columns:
    valid_df = sales_df[
        (sales_df['quantity_mwh'] > 0) &
        (sales_df['purchase_price_eur_mwh'] > 0)
    ].copy()

    if not valid_df.empty:
        st.header("📊 Purchase Summary")

        col1, col2, col3, col4 = st.columns(4)

        total_quantity = valid_df['quantity_mwh'].sum()
        total_purchase_cost = (valid_df['quantity_mwh'] * valid_df['purchase_price_eur_mwh']).sum()
        avg_purchase_price = total_purchase_cost / total_quantity if total_quantity > 0 else 0
        num_transactions = len(valid_df)

        with col1:
            st.metric("Total Quantity", f"{total_quantity:,.2f} MWh")
        with col2:
            st.metric("Total Purchase Cost", f"€{total_purchase_cost:,.2f}")
        with col3:
            st.metric("Avg Purchase Price", f"€{avg_purchase_price:,.2f}/MWh")
        with col4:
            st.metric("Transactions", f"{num_transactions}")

        st.markdown("---")

        st.header("📋 Daily Purchase Details")
        st.markdown("Purchase cost is calculated as: **Quantity (MWh) × Purchase Price (EUR/MWh)**")

        display_df = valid_df[['contract_date', 'quantity_mwh', 'purchase_price_eur_mwh', 'purchase_cost']].copy()
        display_df.columns = ['Contract Date', 'Quantity (MWh)', 'Purchase Price (EUR/MWh)', 'Purchase Cost (EUR)']

        if 'Contract Date' in display_df.columns:
            try:
                display_df['Contract Date'] = pd.to_datetime(display_df['Contract Date']).dt.strftime('%d/%m/%Y')
            except:
                pass

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

        csv = display_df.to_csv(index=False)
        st.download_button("📥 Export to CSV", csv, "daily_purchases.csv", "text/csv")

        st.markdown("---")

        st.header("📈 Purchase Price Trend")

        chart_df = valid_df[['contract_date', 'purchase_price_eur_mwh']].copy()
        try:
            chart_df['contract_date'] = pd.to_datetime(chart_df['contract_date'])
            chart_df = chart_df.sort_values('contract_date')

            import plotly.express as px
            fig = px.line(chart_df, x='contract_date', y='purchase_price_eur_mwh',
                         title='Purchase Price Over Time',
                         labels={'contract_date': 'Date', 'purchase_price_eur_mwh': 'Purchase Price (EUR/MWh)'})
            fig.update_traces(mode='lines+markers')
            st.plotly_chart(fig, use_container_width=True)
        except Exception as e:
            st.info("Unable to display price trend chart")
    else:
        st.info("No valid purchase data available. Sales records with quantity and purchase price will appear here.")
else:
    st.info("No purchase data available. Add sales with quantity and purchase price to see daily purchases.")
