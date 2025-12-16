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
  - `app.py` - Main Dashboard with key metrics overview
  - `pages/1_Purchases.py` - View daily gas purchase details (derived from Sales data)
  - `pages/2_Sales.py` - Sales tracking with margin calculations
  - `pages/3_Payments.py` - Payment reconciliation and tracking from buyers
  - `pages/4_Seller_Balance.py` - Supplier payment management and invoices
  - `pages/5_Analytics.py` - P&L charts and performance metrics using Plotly
  - `pages/6_Settings.py` - Configuration for suppliers, buyers, and payment methods
- **Tab Ordering**: All pages with tabs show View/Statistics tabs first, followed by entry forms

### Data Storage
- **JSON File-Based Storage**: All data is persisted as JSON files in a `data/` directory
- **Data Files**:
  - `purchases.json` - Purchase transaction records
  - `sales.json` - Sales transaction records
  - `payments_received.json` - Payment records from buyers
  - `invoices.json` - Invoice tracking with partial payment support
  - `settings.json` - Configuration (suppliers, buyers, payment methods)

### Data Layer Pattern
- The `database.py` module provides a simple abstraction layer with:
  - `load_*` functions to read JSON files (returns empty list if file doesn't exist)
  - `save_*` functions to write JSON files
  - `*_to_df` functions to convert JSON data to Pandas DataFrames for analysis
  - `generate_id` function for creating unique record identifiers

### Key Business Logic
- **Invoice Tracking**: Supports partial payments on invoices with remaining balance calculation
- **Margin Calculation**: Sales margin = Sales Price - Purchase Price - Capacity Cost - Transport Cost
- **Outstanding Receivables**: Calculated by comparing total revenue from sales against payments received

### Known Issues
- Some sales/purchase records contain inconsistent date formats (both Excel serial numbers like "45937" and date strings like "DD/MM/YYYY"). The system uses dayfirst=True for date parsing.
- Zero-value rows are filtered out from Analytics and purchase cost calculations

## External Dependencies

### Python Packages
- **Streamlit** - Web application framework and UI components
- **Pandas** - Data manipulation and DataFrame operations
- **Plotly** (Express and Graph Objects) - Interactive charts and visualizations

### Data Storage
- **Local File System** - JSON files stored in `data/` directory (no external database)

### No External APIs
- The application is self-contained with no external API integrations
- All data is managed locally through JSON file storage