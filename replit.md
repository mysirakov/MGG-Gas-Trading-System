# Gas Trading Financial Dashboard

## Overview

This is a Streamlit-based financial dashboard application for managing a natural gas trading business. The application tracks purchases from suppliers, sales to buyers, payment reconciliation, and provides analytics on trading performance and profit margins.

The core business domain involves:
- Recording gas purchases with supplier payments and invoice tracking
- Managing sales with margin calculations (sales price minus purchase price, capacity costs, and transport costs)
- Tracking payments received from buyers and reconciling outstanding balances
- Providing P&L analytics and performance visualization

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Streamlit Multi-Page Application**: The app uses Streamlit's native multi-page structure with pages stored in the `pages/` directory
- **Page Structure**:
  - `Dashboard.py` - Main Dashboard with key metrics overview
  - `pages/1_Purchases.py` - View daily gas purchase details (derived from Sales data)
  - `pages/2_Sales.py` - Sales tracking with margin calculations
  - `pages/3_Payments.py` - Payment reconciliation and tracking from buyers
  - `pages/4_Seller_Balance.py` - Supplier payment management and invoices
  - `pages/5_Analytics.py` - P&L charts and performance metrics using Plotly
  - `pages/6_Settings.py` - Configuration for suppliers, buyers, and payment methods
- **Tab Ordering**: All pages with tabs show View/Statistics tabs first, followed by entry forms

### Data Storage (PostgreSQL)
- **PostgreSQL Database**: All data is now stored in a Neon PostgreSQL database for reliability and cross-referencing
- **Database Tables**:
  - `suppliers` - Supplier entities
  - `buyers` - Buyer entities
  - `payment_methods` - Payment method options
  - `sales` - Sales transaction records with computed columns (margin, total_revenue, purchase_cost)
  - `supplier_payments` - Payments made to suppliers
  - `invoices` - Invoice tracking
  - `payments_received` - Payments received from buyers
  - `payment_allocations` - Links payments to sales for accurate tracking

### Data Layer Pattern
- The `database.py` module provides PostgreSQL database access:
  - `get_*` functions to query data from PostgreSQL
  - `add_*` functions to insert new records
  - `delete_*` functions to remove records
  - `*_to_df` functions to convert query results to Pandas DataFrames for analysis
  - `get_dashboard_metrics()` function for aggregated metrics

### Key Business Logic
- **Invoice Tracking**: Supports partial payments on invoices with remaining balance calculation
- **Margin Calculation**: Sales margin = Sales Price - Purchase Price - Capacity Cost - Transport Cost (computed columns in PostgreSQL)
- **Payment Allocation**: Automatic FIFO allocation of received payments to oldest outstanding sales
- **Outstanding Receivables**: Calculated from payment_allocations table (total_revenue - allocated amounts)
- **Supplier Balance**: Amount Received by Supplier - Total Purchase Cost (from sales)

### Database Schema Features
- Foreign key relationships between tables for data integrity
- Computed columns for margin, total_revenue, total_margin, and purchase_cost
- Unique constraints to prevent duplicate allocations
- Cascading deletes on payment_allocations when payments are removed

## External Dependencies

### Python Packages
- **Streamlit** - Web application framework and UI components
- **Pandas** - Data manipulation and DataFrame operations
- **Plotly** (Express and Graph Objects) - Interactive charts and visualizations
- **psycopg2-binary** - PostgreSQL database connector

### Data Storage
- **PostgreSQL (Neon)** - Cloud-hosted PostgreSQL database via DATABASE_URL environment variable

### No External APIs
- The application is self-contained with no external API integrations
- All data is managed through the PostgreSQL database
