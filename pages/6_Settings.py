import streamlit as st
from database import load_settings, save_settings

st.set_page_config(page_title="Settings", page_icon="⚙️", layout="wide")

# Load custom CSS
try:
    with open('style.css') as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
except:
    pass

# Theme selector
try:
    from theme_manager import theme_selector
    theme_selector()
except:
    pass

st.title("⚙️ Settings")
st.markdown("Manage suppliers, buyers, and payment methods")

settings = load_settings()

col1, col2 = st.columns(2)

with col1:
    st.subheader("👥 Suppliers")
    st.markdown("Manage the list of gas suppliers")
    
    suppliers = settings.get("suppliers", [])
    
    for i, supplier in enumerate(suppliers):
        col_a, col_b = st.columns([3, 1])
        with col_a:
            st.text(supplier)
        with col_b:
            if st.button("🗑️", key=f"del_supplier_{i}"):
                suppliers.pop(i)
                settings["suppliers"] = suppliers
                save_settings(settings)
                st.rerun()
    
    new_supplier = st.text_input("Add new supplier", key="new_supplier")
    if st.button("Add Supplier", type="primary", key="add_supplier_btn"):
        if new_supplier and new_supplier not in suppliers:
            suppliers.append(new_supplier)
            settings["suppliers"] = suppliers
            save_settings(settings)
            st.success(f"Added supplier: {new_supplier}")
            st.rerun()
        elif new_supplier in suppliers:
            st.warning("Supplier already exists")
    
    st.markdown("---")
    
    st.subheader("💳 Payment Methods")
    st.markdown("Manage payment methods for supplier transactions")
    
    payment_methods = settings.get("payment_methods", [])
    
    for i, method in enumerate(payment_methods):
        col_a, col_b = st.columns([3, 1])
        with col_a:
            st.text(method)
        with col_b:
            if st.button("🗑️", key=f"del_method_{i}"):
                payment_methods.pop(i)
                settings["payment_methods"] = payment_methods
                save_settings(settings)
                st.rerun()
    
    new_method = st.text_input("Add new payment method", key="new_method")
    if st.button("Add Payment Method", type="primary", key="add_method_btn"):
        if new_method and new_method not in payment_methods:
            payment_methods.append(new_method)
            settings["payment_methods"] = payment_methods
            save_settings(settings)
            st.success(f"Added payment method: {new_method}")
            st.rerun()
        elif new_method in payment_methods:
            st.warning("Payment method already exists")

with col2:
    st.subheader("🏢 Buyers")
    st.markdown("Manage the list of gas buyers")
    
    buyers = settings.get("buyers", [])
    
    for i, buyer in enumerate(buyers):
        col_a, col_b = st.columns([3, 1])
        with col_a:
            st.text(buyer)
        with col_b:
            if st.button("🗑️", key=f"del_buyer_{i}"):
                buyers.pop(i)
                settings["buyers"] = buyers
                save_settings(settings)
                st.rerun()
    
    new_buyer = st.text_input("Add new buyer", key="new_buyer")
    if st.button("Add Buyer", type="primary", key="add_buyer_btn"):
        if new_buyer and new_buyer not in buyers:
            buyers.append(new_buyer)
            settings["buyers"] = buyers
            save_settings(settings)
            st.success(f"Added buyer: {new_buyer}")
            st.rerun()
        elif new_buyer in buyers:
            st.warning("Buyer already exists")

st.markdown("---")

st.subheader("📋 Current Configuration Summary")

col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Suppliers", len(settings.get("suppliers", [])))
with col2:
    st.metric("Payment Methods", len(settings.get("payment_methods", [])))
with col3:
    st.metric("Buyers", len(settings.get("buyers", [])))

st.markdown("---")

st.subheader("⚠️ Data Management")

col1, col2 = st.columns(2)

with col1:
    st.markdown("**Reset Settings to Default**")
    st.caption("This will reset all dropdown options to their default values")
    if st.button("Reset Settings", type="secondary"):
        default_settings = {
            "suppliers": ["GPE"],
            "payment_methods": ["Unicredit", "Financial Agent"],
            "buyers": ["Keler"]
        }
        save_settings(default_settings)
        st.success("Settings reset to defaults!")
        st.rerun()

with col2:
    st.markdown("**Export Configuration**")
    st.caption("Download current settings as JSON")
    import json
    settings_json = json.dumps(settings, indent=2)
    st.download_button("Download Settings", settings_json, "settings.json", "application/json")
