import os
from dotenv import load_dotenv
import streamlit as st
import pandas as pd
import plotly.express as px

from urllib.parse import unquote
import requests
import difflib
import re
import time
import hashlib
import secrets
def render_upstream_chart_page():
    UPSTREAM_COLOR = os.getenv("UPSTREAM_COLOR", "#D96F32")
    DOWNSTREAM_COLOR = os.getenv("DOWNSTREAM_COLOR", "#4C78A8")
    st.set_page_config(page_title="Customer Chain Analysis beta version", layout="wide")



    # ---------------------- Load Secret ----------------------
    load_dotenv()
    debug_mode = os.getenv("DEBUG_MODE", "False") == "True"
    expected_secret = os.getenv("ICICLE_API_KEY")

    # ---------------------- Token Authentication Functions ----------------------
    def generate_token():
        """Generate a secure random token"""
        return secrets.token_urlsafe(32)

    def validate_token_with_backend(token):
        if not expected_secret:
            return None, None, None
        
        backend_url = os.getenv("VALIDATION_ENDPOINT")
        headers = {"x-api-key": expected_secret, "Content-Type": "application/json"}
        
        try:
            payload = {"token": token}
            response = requests.post(backend_url, json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return data.get('customer_id'), None, data.get('expires_at')
            else:
                return None, None, None
        except Exception as e:
            st.error(f"Token validation error: {e}")
            return None, None, None


    def check_token_authentication():
        """Check for token-based authentication from URL"""
        query_params = st.query_params
        token = query_params.get("token", None)
        
        if token:
            customer_id, _, expires_at = validate_token_with_backend(token)
            
            if customer_id:
                if expires_at and time.time() > expires_at:
                    st.error("🔒 Token has expired. Please request a new access link.")
                    st.stop()
                
                st.session_state.authenticated = True
                st.session_state.token_customer_id = customer_id
                st.session_state.auth_method = "token"
                return True
            else:
                st.error("🔒 Invalid or expired token. Please check your access link.")
                st.stop()
        
        return False


    # ---------------------- Enhanced Authentication Check ----------------------
    def check_authentication():
        """Enhanced authentication supporting both token and API key methods"""
        
        # First, check for token authentication
        if check_token_authentication():
            return
        
        # If no valid token and no API key required, allow access
        if not expected_secret:
            st.session_state.auth_method = "none"
            return
        
        # Check if user is already authenticated with API key
        if st.session_state.get("authenticated", False) and st.session_state.get("auth_method") == "api_key":
            return
        
        # Show API key authentication form
        st.markdown("### 🔒 Authentication Required")
        st.info("💡 **Tip**: If you have a direct access link with a token, use that instead of entering an API key here.")
        
        with st.form("auth_form"):
            secret_input = st.text_input("Enter API Key:", type="password")
            submitted = st.form_submit_button("Authenticate")
            
            if submitted:
                if secret_input == expected_secret:
                    st.session_state.authenticated = True
                    st.session_state.auth_method = "api_key"
                    st.success("✅ Authentication successful!")
                    st.rerun()
                else:
                    st.error("❌ Invalid API key. Please try again.")
                    st.stop()
        
        # Stop execution if not authenticated
        if not st.session_state.get("authenticated", False):
            st.stop()

    # Run authentication check
    check_authentication()

    # ---------------------- Helper functions ----------------------

    def clean_key(k):
        return k.strip().strip('"').strip()

    def clean_val(v):
        if not v or not isinstance(v, str):
            return ''
        return v.strip()

    def safe_int(val):
        try:
            return int(str(val).replace(',', '').strip())
        except Exception:
            return 0

    def deep_clean(s):
        if not isinstance(s, str):
            return ''
        s = re.sub(r'[\u200B-\u200D\uFEFF]', '', s)
        s = s.encode('ascii', errors='ignore').decode()
        return s.strip().lower()

    # ---------------------- Styling: Page & Custom CSS ----------------------
    st.markdown("""
        <style>
            /* Hide the default Streamlit header and menu */
            .stApp > header {
                background-color: transparent;
            }

            /* Fix main container spacing - ENHANCED */
            .main .block-container {
                padding-top: 0rem !important;
                padding-bottom: 1rem;
                max-width: 100%;
                margin-top: 0 !important;
                gap: 0 !important; 
            }

            /* CRITICAL: Hide ALL empty elements that create white blocks */
            .main .block-container > div:empty {
                display: none !important;
                height: 0 !important;
                margin: 0 !important;
                padding: 0 !important;
            }

            /* Hide divs that only contain whitespace */
            .main .block-container > div:not(:has(*)) {
                display: none !important;
            }

            /* Target specific Streamlit containers that create spacing */
            .main .block-container > div[data-testid="stVerticalBlock"] > div:empty {
                display: none !important;
            }

            /* Remove ALL margins from Streamlit elements */
            .element-container {
                margin: 0 !important;
                padding: 0 !important;
            }

            /* Remove default margins from markdown */
            .stMarkdown {
                margin: 0 !important;
                padding: 0 !important;
            }

            /* Remove spacing from selectbox containers */
            .stSelectbox {
                margin: 0 !important;
                padding: 0 !important;
            }

            /* Remove spacing from columns */
            .stColumn {
                padding: 0 !important;
            }

            /* AGGRESSIVE: Remove all top margins and padding from first elements */
            .main .block-container > div:first-child {
                margin-top: 0 !important;
                padding-top: 0 !important;
            }

            .main .block-container > div[data-testid="stVerticalBlock"]:first-child {
                margin-top: 0 !important;
                padding-top: 0 !important;
            }

            /* Custom title styling */
            .main-title {
                background: linear-gradient(90deg, #4C78A8, #D96F32);
                color: white;
                padding: 1rem 1.5rem;
                border-radius: 8px;
                margin: 0 auto 1.5rem auto !important;
                text-align: center;
                max-width: 1200px;
                font-size: 2rem;
                font-weight: 600;
            }

            .filter-section {
                background-color: #f9f9f9;
                padding: 0.75rem 1rem;
                border-radius: 6px;
                border: 1px solid #d0d0d0;
                max-width: 700px;
                margin: 0 auto 1rem auto;
                box-shadow: 0px 1px 3px rgba(0,0,0,0.03);
            }

            .chart-container {
                border: 1px solid #e0e0e0;
                border-radius: 10px;
                padding: 1rem;
                margin: 0.5rem;
                background-color: #fafafa;
            }

            .customer-info {
                background-color: #e8f4fd;
                padding: 1rem;
                border-radius: 5px;
                margin: 1rem 0;
                border-left: 4px solid #4C78A8;
            }

            .auth-info {
                background-color: #f0f8f0;
                padding: 0.5rem 1rem;
                border-radius: 5px;
                margin: 0.5rem 0;
                border-left: 3px solid #28a745;
                font-size: 0.9em;
                color: #155724;
            }

            /* ✅ Kill extra spacing blocks between top filters and charts */
            .main .block-container > div:has(.stPlotlyChart) {
                margin-top: 0 !important;
                padding-top: 0 !important;
            }

            .main .block-container > div:empty {
                display: none !important;
                height: 0 !important;
                margin: 0 !important;
                padding: 0 !important;
            }

            /* ✅ Eliminate white bar under API Key or Token block */
            div[data-testid="stVerticalBlock"] > div:only-child:empty {
                display: none !important;
                height: 0 !important;
                margin: 0 !important;
                padding: 0 !important;
            }
                html {
            scroll-behavior: smooth;
        }
                
        </style>
    """, unsafe_allow_html=True)


        # ---------------------- Title ----------------------
    st.markdown('<div class="main-title">🔗 Reach Partner View (Beta)</div>', unsafe_allow_html=True)

    # ---------------------- Duration Filter Section ----------------------
    st.markdown(" Select Duration")

    duration = st.selectbox(
        "Duration",
        ["1 Month", "3 Months", "6 Months", "1 Year"]
    )







    


    # ---------------------- Enhanced URL Parameter Check & Customer Selection ----------------------
    query_params = st.query_params
    customer_from_url = query_params.get("customer-name", None)
    customer_id_from_url = query_params.get("customer-id", None)

    # First, we need to load some initial data to get customer lists
    # Use default 1-month files for initial customer discovery
    initial_downstream_df = pd.read_csv("duration/1month_data.csv")
    initial_upstream_df = pd.read_csv("upstream_duration/up_1month_data.csv")

    # Clean the initial data
    initial_downstream_df.columns = [clean_key(col) for col in initial_downstream_df.columns]
    initial_downstream_df.fillna('', inplace=True)
    initial_downstream_df['original_customer'] = initial_downstream_df['customer']
    initial_downstream_df['customer_cleaned'] = initial_downstream_df['customer'].astype(str).apply(deep_clean)

    initial_upstream_df.columns = [clean_key(col) for col in initial_upstream_df.columns]
    initial_upstream_df.fillna('', inplace=True)
    initial_upstream_df['original_customer'] = initial_upstream_df['customer']
    initial_upstream_df['customer_cleaned'] = initial_upstream_df['customer'].astype(str).apply(deep_clean)

    # Add customer_id if it doesn't exist
    if 'customer_id' not in initial_downstream_df.columns:
        initial_downstream_df['customer_id'] = initial_downstream_df['customer_cleaned'].apply(lambda x: abs(hash(x)) % 10000)
    if 'customer_id' not in initial_upstream_df.columns:
        initial_upstream_df['customer_id'] = initial_upstream_df['customer_cleaned'].apply(lambda x: abs(hash(x)) % 10000)

    # Get unique customers from both datasets
    downstream_customers = set(initial_downstream_df['customer_cleaned'].unique())
    upstream_customers = set(initial_upstream_df['customer_cleaned'].unique())
    all_customers = sorted(downstream_customers.union(upstream_customers))

    selected_customer = None
    customer_source = None  # Track how customer was selected
    customer_id = None

    # Enhanced customer selection logic
    if st.session_state.get("auth_method") == "token" and st.session_state.get("token_customer_id"):
        # Token authentication - auto-select the customer
        customer_id = st.session_state.get("token_customer_id")
        
        # Look for customer ID in both datasets
        downstream_match = initial_downstream_df[initial_downstream_df['customer_id'] == customer_id]
        upstream_match = initial_upstream_df[initial_upstream_df['customer_id'] == customer_id]
        
        if not downstream_match.empty:
            selected_customer = downstream_match['customer_cleaned'].iloc[0]
            original_display = downstream_match['original_customer'].iloc[0]
            customer_source = "token_downstream"
        elif not upstream_match.empty:
            selected_customer = upstream_match['customer_cleaned'].iloc[0]
            original_display = upstream_match['original_customer'].iloc[0]
            customer_source = "token_upstream"
        else:
            st.error(f"❌ Token customer ID '{customer_id}' not found in any dataset.")
            st.stop()
            
        st.markdown(f'<div class="customer-info">🔗 <strong>Token Customer:</strong> <code>{original_display}</code> (ID: {customer_id})</div>', unsafe_allow_html=True)

    elif customer_id_from_url:
        # URL customer ID parameter
        try:
            customer_id = int(customer_id_from_url)
            
            # Look for customer ID in both datasets
            downstream_match = initial_downstream_df[initial_downstream_df['customer_id'] == customer_id]
            upstream_match = initial_upstream_df[initial_upstream_df['customer_id'] == customer_id]
            
            if not downstream_match.empty:
                selected_customer = downstream_match['customer_cleaned'].iloc[0]
                original_display = downstream_match['original_customer'].iloc[0]
                customer_source = "url_downstream"
            elif not upstream_match.empty:
                selected_customer = upstream_match['customer_cleaned'].iloc[0]
                original_display = upstream_match['original_customer'].iloc[0]
                customer_source = "url_upstream"
            else:
                st.error(f"❌ Customer ID '{customer_id}' not found in any dataset.")
                st.stop()
                
            st.markdown(f'<div class="customer-info">🔗 <strong>Customer loaded from URL:</strong> <code>{original_display}</code> (ID: {customer_id})</div>', unsafe_allow_html=True)
    
            
        except ValueError:
            st.error(f"❌ Invalid customer ID format: '{customer_id_from_url}'. Expected a number.")
            st.stop()

    elif customer_from_url:
        # URL customer name parameter
        customer_from_url = deep_clean(unquote(customer_from_url))
        if customer_from_url in all_customers:
            selected_customer = customer_from_url
            # Try to get original display name from either dataset
            if customer_from_url in downstream_customers:
                original_display = initial_downstream_df[initial_downstream_df['customer_cleaned'] == selected_customer]['original_customer'].iloc[0]
                customer_id = initial_downstream_df[initial_downstream_df['customer_cleaned'] == selected_customer]['customer_id'].iloc[0]
                customer_source = "url_name_downstream"
            else:
                original_display = initial_upstream_df[initial_upstream_df['customer_cleaned'] == selected_customer]['original_customer'].iloc[0]
                customer_id = initial_upstream_df[initial_upstream_df['customer_cleaned'] == selected_customer]['customer_id'].iloc[0]
                customer_source = "url_name_upstream"
            
            st.markdown(f'<div class="customer-info">🔗 <strong>Customer loaded from URL:</strong> <code>{original_display}</code> (ID: {customer_id})</div>', unsafe_allow_html=True)
            # ✅ Unified debug banner after all customer types
            if selected_customer and debug_mode:
                st.warning("⚙️ Debug mode is ON – extra analysis and validation sections are automatically shown.")

        else:
            matches = difflib.get_close_matches(customer_from_url, all_customers, n=10, cutoff=0.3)
            st.error(f"❌ Customer '{customer_from_url}' not found.")
            if matches:
                selected_customer = st.selectbox("Did you mean one of these?", matches)
                customer_source = "manual_corrected"
            else:
                st.stop()

    else:
        # Manual selection (only for non-token users or when token doesn't specify customer)
        if st.session_state.get("auth_method") == "token":
            st.warning("🔗 Token authentication active but no specific customer provided.")
        
        # Create display options with original names and IDs
        display_options = ["All Customers"]
        customer_id_map = {}  # Map display names to IDs for reference
        
        for cust in all_customers:
            if cust in downstream_customers:
                original_name = initial_downstream_df[initial_downstream_df['customer_cleaned'] == cust]['original_customer'].iloc[0]
                customer_id_temp = initial_downstream_df[initial_downstream_df['customer_cleaned'] == cust]['customer_id'].iloc[0]
            else:
                original_name = initial_upstream_df[initial_upstream_df['customer_cleaned'] == cust]['original_customer'].iloc[0]
                customer_id_temp = initial_upstream_df[initial_upstream_df['customer_cleaned'] == cust]['customer_id'].iloc[0]
            
            display_text = f"{original_name} (ID: {customer_id_temp})"
            display_options.append(display_text)
            customer_id_map[display_text] = (cust, customer_id_temp)

        selected_display = st.selectbox("Select Customer", display_options)
        if selected_display == "All Customers":
            selected_customer = "All Customers"
            customer_source = "manual_all"
        else:
            selected_customer, customer_id = customer_id_map[selected_display]
            customer_source = "manual_specific"
            




    # File mappings
    downstream_file_map = {
        "1 Month": "1month_data.csv",
        "3 Months": "3month_data.csv", 
        "6 Months": "6month_data.csv",
        "1 Year": "1year_data.csv"
    }

    upstream_file_map = {
        "1 Month": "up_1month_data.csv",
        "3 Months": "up_3month_data.csv",
        "6 Months": "up_6month_data.csv", 
        "1 Year": "up_1year_data.csv"
    }

    # NEW: Shifted file mappings
    shifted_downstream_file_map = {
        "1 Month": "shifted_downstream_duration_1month.csv",
        "3 Months": "shifted_downstream_duration_3month.csv",
        "6 Months": "shifted_downstream_duration_6month.csv",
        "1 Year": "shifted_downstream_duration_1year.csv"
    }

    shifted_upstream_file_map = {
        "1 Month": "shifted_upstream_duration_1month.csv",
        "3 Months": "shifted_upstream_duration_3month.csv",
        "6 Months": "shifted_upstream_duration_6month.csv",
        "1 Year": "shifted_upstream_duration_1year.csv"
    }

    # NOW: Choose file paths based on customer selection (after selected_customer is defined)
    if selected_customer == "All Customers":
        # Use original files for "All Customers"
        downstream_csv_path = f"duration/{downstream_file_map[duration]}"
        upstream_csv_path = f"upstream_duration/{upstream_file_map[duration]}"
    else:
        # Use shifted files for specific customers
        downstream_csv_path = f"shifted_downstream_duration/{shifted_downstream_file_map[duration]}"
        upstream_csv_path = f"shifted_upstream_duration/{shifted_upstream_file_map[duration]}"

    # ---------------------- Load & Clean Data ----------------------
    try:
        downstream_df = pd.read_csv(downstream_csv_path)
        downstream_df.columns = [clean_key(col) for col in downstream_df.columns]
        downstream_df.fillna('', inplace=True)
        downstream_df['original_customer'] = downstream_df['customer']
        downstream_df['customer_cleaned'] = downstream_df['customer'].astype(str).apply(deep_clean)
        
        # Add customer_id if it doesn't exist (assuming it might be in the CSV)
        if 'customer_id' not in downstream_df.columns:
            # Create a simple ID based on cleaned customer name for demo
            downstream_df['customer_id'] = downstream_df['customer_cleaned'].apply(lambda x: abs(hash(x)) % 10000)
            
    except FileNotFoundError:
        st.error("⚠️ No Downstream data available for the selected duration.")

        st.stop()

    try:
        upstream_df = pd.read_csv(upstream_csv_path)
        upstream_df.columns = [clean_key(col) for col in upstream_df.columns]
        upstream_df.fillna('', inplace=True)
        upstream_df['original_customer'] = upstream_df['customer']
        upstream_df['customer_cleaned'] = upstream_df['customer'].astype(str).apply(deep_clean)
        
        # Add customer_id if it doesn't exist (assuming it might be in the CSV)
        if 'customer_id' not in upstream_df.columns:
            # Create a simple ID based on cleaned customer name for demo
            upstream_df['customer_id'] = upstream_df['customer_cleaned'].apply(lambda x: abs(hash(x)) % 10000)
            
    except FileNotFoundError:
        st.error("⚠️ No upstream data available for the selected duration.")

        st.stop()

    # ---------------------- Show authentication method info ----------------------
    auth_method = st.session_state.get("auth_method", "none")
    if auth_method == "token":
        try:
            display_name = downstream_df[downstream_df["customer_id"] == st.session_state.token_customer_id]["original_customer"].iloc[0]
        except IndexError:
            display_name = "Unknown"
        st.markdown(f'<div class="auth-info">🔗 <strong>Token Access</strong> - Authenticated for: {display_name}</div>', unsafe_allow_html=True)
    elif auth_method == "api_key":
        st.markdown('<div class="auth-info">🔑 <strong>API Key Access</strong> - Full system access</div>', unsafe_allow_html=True)

    # ---------------------- Shared Filtering (DO NOT REPEAT ANYWHERE ELSE) ----------------------
    def get_debug_data(df, chart_type, selected_customer, customer_id):
        """FIXED: Proper filtering for upstream and downstream"""
        if selected_customer == "All Customers":
            return df
        
        if chart_type == "downstream":
            # For downstream: filter by root customer only
            return df[df['customer_cleaned'] == selected_customer]
        else:  # upstream
            return df[df['customer_cleaned'] == selected_customer]


    # FIXED: Proper availability check for upstream
    if selected_customer == "All Customers":
        downstream_available = True  
        upstream_available = True    
    else:
        # For downstream: customer appears as ROOT in shifted files
        downstream_available = selected_customer in set(downstream_df['customer_cleaned'].unique())
        
        # For upstream: customer appears ANYWHERE in the chain (more flexible)
        upstream_available = False
        if selected_customer in set(upstream_df['customer_cleaned'].unique()):
            upstream_available = True
        else:
            # Check if customer appears anywhere in upstream chain
            for i in range(1, 7):
                col_name = f'customer_{i}'
                if col_name in upstream_df.columns:
                    upstream_df[f'{col_name}_cleaned'] = upstream_df[col_name].astype(str).apply(deep_clean)
                    if selected_customer in set(upstream_df[f'{col_name}_cleaned'].unique()):
                        upstream_available = True
                        break


    downstream_filtered = get_debug_data(downstream_df, "downstream", selected_customer, customer_id) if downstream_available else pd.DataFrame()
    upstream_filtered = get_debug_data(upstream_df, "upstream", selected_customer, customer_id) if upstream_available else pd.DataFrame()
   

    if selected_customer != "All Customers" and upstream_available and not upstream_filtered.empty:
        # Calculate maximum hop depth from the data
        max_hop_depth = 0
        for _, row in upstream_filtered.iterrows():
            # Check if selected customer is the base customer
            if deep_clean(row['customer']) == selected_customer:
                # Count how many hops exist in this chain
                hop_count = 0
                for i in range(1, 7):
                    if row.get(f'customer_{i}') and str(row.get(f'customer_{i}')).strip():
                        hop_count += 1
                    else:
                        break
                max_hop_depth = max(max_hop_depth, hop_count)
            else:
                # If selected customer appears later in chain, calculate from that position
                customer_position = -1
                for i in range(1, 7):
                    if deep_clean(str(row.get(f'customer_{i}', ''))) == selected_customer:
                        customer_position = i
                        break
                
                if customer_position != -1:
                    # Count remaining hops after the selected customer
                    remaining_hops = 0
                    for i in range(customer_position + 1, 7):
                        if row.get(f'customer_{i}') and str(row.get(f'customer_{i}')).strip():
                            remaining_hops += 1
                        else:
                            break
                    max_hop_depth = max(max_hop_depth, remaining_hops)
        
        # Create hop options dynamically
        if max_hop_depth > 0:
            hop_options = ["All Hops"] + [f"Hop {i}" for i in range(1, max_hop_depth + 1)]
            hop_filter = st.selectbox(
                "Upstream Hop Filter",
                hop_options,
                help=f"Filter upstream connections by hop distance (Max: {max_hop_depth} hops available)"
            )
            
            # Show info about what each hop means
            if hop_filter != "All Hops":
                hop_num = int(hop_filter.split()[1])
                st.info(f"🔍 Showing {selected_customer} and suppliers up to {hop_num} hop{'s' if hop_num > 1 else ''} away")
        else:
            hop_filter = "All Hops"
            st.info("ℹ️ No upstream hops available for this customer")
    else:
        hop_filter = "All Hops"

    st.markdown('</div>', unsafe_allow_html=True)


    # ---------------------- Function to Build Icicle Chart Data ----------------------

    def build_downstream_chart(df, selected_customer):
        """Build downstream icicle chart data"""
        # Filter data 
        if selected_customer == "All Customers":
            filtered_df = df
        else:
            filtered_df = df[df['customer_id'] == customer_id]

        data = filtered_df.to_dict(orient='records')
        
        labels, parents, values, ids = [], [], [], []
        node_children = {}
        leaf_values = {}
        calculated_totals = {}

        root_id = "Customer Chain"
        labels.append(root_id)
        parents.append("")
        ids.append(root_id)
        node_children[root_id] = set()

        # Build tree structure
        for record in data:
            customer = clean_val(record.get('original_customer', ''))
            event_count = safe_int(record.get('event_count', 0))
            if not customer or event_count == 0:
                continue

            # Build the chain
            chain = [customer]
            for i in range(1, 7):
                key = f'customer_{i}'
                cust = clean_val(record.get(key, ''))
                if cust:
                    chain.append(cust)
                else:
                    break

            # Create nodes for the chain
            path_ids = [root_id]
            for i, name in enumerate(chain):
                parent_id = "/".join(path_ids)
                current_id = parent_id + "/" + name

                # Track parent-child relationships
                if parent_id not in node_children:
                    node_children[parent_id] = set()
                node_children[parent_id].add(current_id)

                if current_id not in node_children:
                    node_children[current_id] = set()

                # Add to lists if not already present
                if current_id not in ids:
                    labels.append(name)
                    parents.append(parent_id)
                    ids.append(current_id)

                path_ids.append(name)

            # The final node in the chain gets the event count
            leaf_id = "/".join(path_ids)
            if leaf_id not in leaf_values:
                leaf_values[leaf_id] = 0
            leaf_values[leaf_id] += event_count

        # Calculate totals
        def calculate_node_total(node_id):
            if node_id in calculated_totals:
                return calculated_totals[node_id]
            total = leaf_values.get(node_id, 0)
            children = node_children.get(node_id, set())
            for child_id in children:
                total += calculate_node_total(child_id)
            calculated_totals[node_id] = total
            return total

        for node_id in ids:
            calculate_node_total(node_id)

        # Assign values for chart sizing
        values = []
        for node_id in ids:
            children = node_children.get(node_id, set())
            if children:  # Parent node
                values.append(0)
            else:  # Leaf node
                values.append(leaf_values.get(node_id, 0))

        return labels, parents, values, ids, calculated_totals
        
    # REPLACE your build_upstream_chart function with this FIXED version:

    def build_upstream_chart(df, selected_customer, hop_filter="All Hops"):
        """Build upstream icicle chart data with PROPER hop filtering"""
        has_expanded_chain = False

        filtered_df = get_debug_data(df, "upstream", selected_customer, None)
        filtered_df = filtered_df[filtered_df['event_count'].notnull()]
        data = filtered_df.to_dict(orient='records')

        from collections import defaultdict

        labels, parents, values, ids = [], [], [], []
        node_children = {}
        leaf_values = {}
        calculated_totals = {}
        aggregated = defaultdict(int)

        root_id = "Customer Chain"
        labels.append(root_id)
        parents.append("")
        ids.append(root_id)
        node_children[root_id] = set()

        max_hops = 6
        if hop_filter != "All Hops":
            max_hops = int(hop_filter.split()[1])

        for record in data:
            event_count = safe_int(record.get('event_count', 0))
            if event_count == 0:
                continue

            full_chain = []
            base_customer = clean_val(record.get('customer', ''))
            if base_customer:
                full_chain.append(base_customer)

            for i in range(1, 7):
                cust = clean_val(record.get(f'customer_{i}', ''))
                if cust:
                    full_chain.append(cust)

            if selected_customer == "All Customers":
                final_chain = full_chain
            else:
                try:
                    customer_position = next(i for i, c in enumerate(full_chain) if deep_clean(c) == selected_customer)
                    final_chain = full_chain[customer_position:customer_position + max_hops + 1]
                except StopIteration:
                    continue  # skip this row if customer not found

            if final_chain and len(final_chain) > 1:
                has_expanded_chain = True

            aggregated[tuple(final_chain)] += event_count

        for chain, event_count in aggregated.items():
            current_path = [root_id]
            for i, customer_name in enumerate(chain):
                parent_id = "/".join(current_path)
                display_name = customer_name if i == 0 else f"{customer_name} (Hop {i})"
                current_id = parent_id + "/" + display_name

                node_children.setdefault(parent_id, set()).add(current_id)
                node_children.setdefault(current_id, set())

                if current_id not in ids:
                    labels.append(display_name)
                    parents.append(parent_id)
                    ids.append(current_id)

                current_path.append(display_name)

            final_id = "/".join(current_path)
            leaf_values[final_id] = event_count

        def calculate_node_total(node_id):
            if node_id in calculated_totals:
                return calculated_totals[node_id]

            total = leaf_values.get(node_id, 0)
            children = node_children.get(node_id, set())

            for child_id in children:
                total += calculate_node_total(child_id)

            calculated_totals[node_id] = total
            return total

        for node_id in ids:
            calculate_node_total(node_id)

        values = []
        for node_id in ids:
            children = node_children.get(node_id, set())
            if children:
                values.append(0)
            else:
                values.append(leaf_values.get(node_id, 0))

        return labels, parents, values, ids, calculated_totals, leaf_values, has_expanded_chain





    # ---------------------- Create Charts Side by Side ----------------------

    col1, col2 = st.columns(2)
    st.markdown("""
    <style>
        .block-container > div:has(.element-container:only-child):empty {
            height: 0px !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        .block-container > div:nth-child(8) {
            margin-top: 0 !important;
            padding-top: 0 !important;
        }
    </style>
""", unsafe_allow_html=True)



    # Get display name for titles
    if selected_customer == "All Customers":
        display_name = "All Customers"
    else:
        if selected_customer in downstream_customers:
            match = downstream_df[downstream_df['customer_cleaned'] == selected_customer]
            display_name = match['original_customer'].iloc[0] if not match.empty else selected_customer
        elif selected_customer in upstream_customers:
            match = upstream_df[upstream_df['customer_cleaned'] == selected_customer]
            display_name = match['original_customer'].iloc[0] if not match.empty else selected_customer
        else:
            display_name = selected_customer


    # 👉 Show UPSTREAM chart on the LEFT
    with col1:
        if upstream_available:
            labels_up, parents_up, values_up, ids_up, totals_up, leaf_values_up, has_chain_up = build_upstream_chart(
                upstream_df, selected_customer, hop_filter
            )

            title_suffix = f" – {hop_filter}" if hop_filter != "All Hops" else ""

            fig_upstream = px.icicle(
                names=labels_up,
                parents=parents_up,
                values=values_up,
                ids=ids_up,
                title=f"📈 Upstream Partners – {display_name} – {duration}{title_suffix}",
                color_discrete_sequence=[UPSTREAM_COLOR]

            )

            fig_upstream.update_traces(
                hovertemplate=(
                    "<b>%{label}</b><br>" +
                    "Event Count: %{customdata}<br>" +
        
                    "Percent of Total: %{percentRoot:.2%}<br>" +
                    "<extra></extra>"
                ),
                customdata=[totals_up.get(node_id, 0) for node_id in ids_up],
                marker=dict(colorscale=None, showscale=False)
            )

            fig_upstream.update_layout(
                height=600,
                font_size=10,
                title_font_size=16,
                title_font_color="#2c3e50",
                margin=dict(t=50, l=20, r=20, b=20),
                paper_bgcolor="#ffffff"
            )
            

            st.plotly_chart(
                fig_upstream,
                use_container_width=True,
                config={
                    "scrollZoom": True,
                    "displayModeBar": True,
                    "displaylogo": False,
                    "modeBarButtonsToAdd": ["pan2d", "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d"]
                }
            )


        else:
            st.info("No upstream partners.")


    # 👇 Show DOWNSTREAM chart on the RIGHT
    with col2:
        if downstream_available:

            labels_down, parents_down, values_down, ids_down, totals_down = build_downstream_chart(downstream_df, selected_customer)

            filtered_df_for_total = get_debug_data(downstream_df, "downstream", selected_customer, customer_id)
            total_downstream_events = filtered_df_for_total['event_count'].sum()

            custom_percentages = []
            for node_id in ids_down:
                node_total = totals_down.get(node_id, 0)
                pct = (node_total / total_downstream_events * 100) if total_downstream_events > 0 else 0
                custom_percentages.append(pct)

            customdata = [
                [totals_down.get(node_id, 0), custom_percentages[i]]
                for i, node_id in enumerate(ids_down)
            ]

            fig_downstream = px.icicle(
                names=labels_down,
                parents=parents_down,
                values=values_down,
                ids=ids_down,
                title=f"📊 Downstream Partners – {display_name} – {duration}",
                color_discrete_sequence=[DOWNSTREAM_COLOR]

            )

            fig_downstream.update_traces(
                hovertemplate=(
                    "<b>%{label}</b><br>" +
                    "Event Count: %{customdata[0]:,}<br>" +
                    "Percent of Total: %{customdata[1]:.2f}%<br>" +
                    "<extra></extra>"
                ),
                customdata=customdata,
                marker=dict(colorscale=None, showscale=False)
            )
            fig_downstream.update_layout(
                height=600,
                font_size=10,
                title_font_size=16,
                title_font_color="#2c3e50",
                margin=dict(t=50, l=20, r=20, b=20),
                paper_bgcolor="#ffffff"
            )

            st.plotly_chart(
                fig_downstream,
                use_container_width=True,
                config={
                    "scrollZoom": True,
                    "displayModeBar": True,
                    "displaylogo": False,
                    "modeBarButtonsToAdd": ["pan2d", "zoomIn2d", "zoomOut2d", "autoScale2d", "resetScale2d"]
                }
            )


        else:
            st.info("No downstream partners.")





    # ---------------------- COMBINED EVENT VALIDATION ----------------------

    # ✅ Move function OUTSIDE the checkbox block to avoid scoping issues
    def validate_tree_data(df, chart_type, selected_customer, customer_id, is_available):
        if not is_available:
            return 0, 0, 0

        filtered_df = df.copy()
        filtered_df.columns = [clean_key(c) for c in filtered_df.columns]
        filtered_df.fillna('', inplace=True)
        filtered_df['customer_cleaned'] = filtered_df['customer'].astype(str).apply(deep_clean)

        if selected_customer != "All Customers":
            if chart_type == "upstream":
                filtered_df = filtered_df[filtered_df['customer_cleaned'] == selected_customer]
            else:
                filtered_df['original_customer_cleaned'] = filtered_df['original_customer'].astype(str).apply(deep_clean)
                filtered_df = filtered_df[filtered_df['original_customer_cleaned'] == selected_customer]

        if 'event_id' in filtered_df.columns:
            filtered_df = filtered_df.drop_duplicates(subset=['event_id'])
        else:
            filtered_df = filtered_df.drop_duplicates()

        raw_total = filtered_df['event_count'].sum()

        from collections import defaultdict
        data = filtered_df.to_dict(orient='records')
        aggregated = defaultdict(int)
        root_id = "Customer Chain"

        for record in data:
            event_count = safe_int(record.get('event_count', 0))
            if event_count == 0:
                continue

            if chart_type == "upstream":
                chain = [clean_val(record.get('customer', ''))]
            else:
                chain = [clean_val(record.get('original_customer', ''))]

            for i in range(1, 7):
                cust = clean_val(record.get(f'customer_{i}', ''))
                if cust:
                    chain.append(cust)

            aggregated[tuple(chain)] += event_count

        tree_total = sum(aggregated.values())
        return raw_total, tree_total, raw_total - tree_total


    # ✅ Now this part stays inside the checkbox block
    if debug_mode and selected_customer != "All Customers":
        st.write("## 🔬 Show Detailed Analysis")


        st.write("---")
        st.write("## ✅ Event Count Validation")

        # Run validations
        downstream_raw, downstream_tree, downstream_diff = validate_tree_data(
            downstream_df, "downstream", selected_customer, customer_id, downstream_available
        )
        upstream_raw, upstream_tree, upstream_diff = validate_tree_data(
            upstream_df, "upstream", selected_customer, customer_id, upstream_available
        )

        # Build results table
        validation_data = []

        if downstream_available:
            validation_data.append({
                "Chart Type": "📈 Downstream",
                "Raw CSV Total": f"{downstream_raw:,}",
                "Tree Total": f"{downstream_tree:,}",
                "Difference": f"{downstream_diff:,}",
                "Status": "✅ Valid" if downstream_diff == 0 else "❌ Invalid"
            })

        if upstream_available:
            validation_data.append({
                "Chart Type": "📊 Upstream",
                "Raw CSV Total": f"{upstream_raw:,}",
                "Tree Total": f"{upstream_tree:,}",
                "Difference": f"{upstream_diff:,}",
                "Status": "✅ Valid" if upstream_diff == 0 else "❌ Invalid"
            })

        if not downstream_available and not upstream_available:
            st.warning("⚠️ No charts available for validation with the selected customer.")
        else:
            validation_df = pd.DataFrame(validation_data)
            st.dataframe(
                validation_df,
                use_container_width=True,
                hide_index=True,
                column_config={
                    "Chart Type": st.column_config.TextColumn("📊 Type", width="small"),
                    "Raw CSV Total": st.column_config.TextColumn("📁 Raw Total", width="medium"),
                    "Tree Total": st.column_config.TextColumn("🌳 Tree Total", width="medium"),
                    "Difference": st.column_config.TextColumn("🔍 Difference", width="medium"),
                    "Status": st.column_config.TextColumn("✅ Status", width="small")
                }
            )

            # Overall summary
            available_diffs = []
            if downstream_available:
                available_diffs.append(downstream_diff)
            if upstream_available:
                available_diffs.append(upstream_diff)

            total_issues = sum(1 for diff in available_diffs if diff != 0)

            if total_issues == 0:
                st.success("🎉 **ALL VALIDATIONS PASSED**: Available charts perfectly match their data sources!")
            else:
                st.error(f"⚠️ **{total_issues} VALIDATION ISSUE(S)**: Some charts have data mismatches.")









    # ---------------------- DETAILED BREAKDOWN ----------------------
    if debug_mode and selected_customer != "All Customers":


        
        # Position analysis for available charts only
        def analyze_positions(df, chart_type, selected_customer):
            positions = {}
            events = {}
            
            for _, row in df.iterrows():
                event_count = safe_int(row.get('event_count', 0))
                
                if chart_type == "downstream":
                    if deep_clean(row.get('original_customer', '')) == selected_customer:
                        pos = 'Root'
                        positions[pos] = positions.get(pos, 0) + 1
                        events[pos] = events.get(pos, 0) + event_count
                    
                    for i in range(1, 7):
                        if deep_clean(row.get(f'customer_{i}', '')) == selected_customer:
                            pos = f'Pos-{i}'
                            positions[pos] = positions.get(pos, 0) + 1
                            events[pos] = events.get(pos, 0) + event_count
                else:  # upstream
                    if deep_clean(row.get('customer', '')) == selected_customer:
                        pos = 'Base'
                        positions[pos] = positions.get(pos, 0) + 1
                        events[pos] = events.get(pos, 0) + event_count
                    
                    for i in range(1, 7):
                        if deep_clean(row.get(f'customer_{i}', '')) == selected_customer:
                            pos = f'Up-{i}'
                            positions[pos] = positions.get(pos, 0) + 1
                            events[pos] = events.get(pos, 0) + event_count
            
            return positions, events
        
        # Create columns based on availability
        if downstream_available and upstream_available:
            col1, col2 = st.columns(2)
        elif downstream_available or upstream_available:
            col1 = st.container()
            col2 = None
        
        # Downstream analysis
        if downstream_available:
            with col1 if col2 else col1:
                st.write("#### 📈 Downstream Positions")
                down_pos, down_events = analyze_positions(downstream_filtered, "downstream", selected_customer)
                if down_pos:
                    for pos, count in down_pos.items():
                        st.write(f"**{pos}**: {count:,} records, {down_events[pos]:,} events")
                else:
                    st.info("No downstream positions found")
        
        # Upstream analysis
        if upstream_available:
            with col2 if col2 else col1:
                st.write("#### 📊 Upstream Positions")
                up_pos, up_events = analyze_positions(upstream_filtered, "upstream", selected_customer)
                if up_pos:
                    for pos, count in up_pos.items():
                        st.write(f"**{pos}**: {count:,} records, {up_events[pos]:,} events")
                else:
                    st.info("No upstream positions found")
        
    # ---------------------- ALWAYS SHOW MATCHING CSV ROWS ----------------------
    if selected_customer != "All Customers":
        st.write("## 📄 Matching Records from CSV")

        if downstream_available and len(ids_down) <= 1:
            st.info("ℹ️ No downstream chain beyond the customer — skipping raw downstream CSV records.")
        else:
            if downstream_available and not downstream_filtered.empty:
                st.write("### 📈 Downstream Records")
                downstream_display = downstream_filtered[
                    [col for col in downstream_filtered.columns
                    if col in ['event_count']
                    or (col.startswith('customer_') and not col.endswith('_id')
                        and col != 'customer' and col != 'customer_cleaned')]
                ]
                downstream_display = downstream_display.sort_values(by="event_count", ascending=False)
                total_event_count = downstream_display["event_count"].sum()
                downstream_display["percentage"] = (
                    downstream_display["event_count"] / total_event_count * 100
                ).round(2).astype(str) + '%'
                st.dataframe(downstream_display, use_container_width=True, hide_index=True)

    # ✅ Upstream CSV display (silently skip for All Customers)
    if selected_customer != "All Customers":
        if not has_chain_up:
            st.info("ℹ️ No upstream chain beyond the customer — skipping raw upstream CSV records.")
        elif upstream_available and not upstream_filtered.empty:
            st.write("### 📊 Upstream Records")
            upstream_display = upstream_filtered[
                [col for col in upstream_filtered.columns
                if col in ['event_count']
                or (col.startswith('customer_') and not col.endswith('_id')
                    and col != 'customer' and col != 'customer_cleaned')]
            ]
            upstream_display = upstream_display.sort_values(by="event_count", ascending=False)
            total_event_count = upstream_display["event_count"].sum()
            upstream_display["percentage"] = (
                upstream_display["event_count"] / total_event_count * 100
            ).round(2).astype(str) + '%'
            st.dataframe(upstream_display, use_container_width=True, hide_index=True)








            # Create tabs based on availability
        tab_names = []
        if downstream_available:
            tab_names.append("📈 Downstream Sample")
        if upstream_available:
            tab_names.append("📊 Upstream Sample")
        
        if tab_names:
            if len(tab_names) == 1:
                # Single tab case
                if downstream_available:
                    st.write("##### 📈 Downstream Sample")
                    if len(downstream_filtered) > 0:
                        if selected_customer == "All Customers":
                            total_down = downstream_filtered["event_count"].sum()
                            st.write(f"**📈 Total Downstream Events:** {total_down:,}")
                        else:
                            sample = downstream_filtered.head(5)
                            for idx, row in sample.iterrows():
                                chain_parts = [str(row.get('original_customer', ''))[:20]]
                                for i in range(1, 4):
                                    val = row.get(f'customer_{i}', '')
                                    if val:
                                        chain_parts.append(str(val)[:15])
                                st.write(f"**{safe_int(row.get('event_count', 0)):,} events**: {' → '.join(chain_parts)}")
                    else:
                        st.info("No downstream records")
                else:
                    st.write("##### 📊 Upstream Sample")
                    if len(upstream_filtered) > 0:
                        if selected_customer == "All Customers":
                            total_up = upstream_filtered["event_count"].sum()
                            st.write(f"**📊 Total Upstream Events:** {total_up:,}")
                        else:
                            sample = upstream_filtered.head(5)
                            for idx, row in sample.iterrows():
                                chain_parts = [str(row.get('customer', ''))[:20]]
                                for i in range(1, 4):
                                    val = row.get(f'customer_{i}', '')
                                    if val:
                                        chain_parts.append(str(val)[:15])
                                st.write(f"**{safe_int(row.get('event_count', 0)):,} events**: {' → '.join(chain_parts)}")
                    else:
                        st.info("No upstream records")

            else:
                # Multiple tabs case
                tabs = st.tabs(tab_names)
                
                tab_index = 0
                if downstream_available:
                    with tabs[tab_index]:
                        if len(downstream_filtered) > 0:
                            if selected_customer == "All Customers":
                                total_down = downstream_filtered["event_count"].sum()
                                st.write(f"**📈 Total Downstream Events:** {total_down:,}")
                            else:
                                sample = downstream_filtered.head(5)
                                for idx, row in sample.iterrows():
                                    chain_parts = [str(row.get('original_customer', ''))[:20]]
                                    for i in range(1, 4):
                                        val = row.get(f'customer_{i}', '')
                                        if val:
                                            chain_parts.append(str(val)[:15])
                                    st.write(f"**{safe_int(row.get('event_count', 0)):,} events**: {' → '.join(chain_parts)}")
                        else:
                            st.info("No downstream records")
                    tab_index += 1
                
                if upstream_available:
                    with tabs[tab_index]:
                        if len(upstream_filtered) > 0:
                            if selected_customer == "All Customers":
                                total_up = upstream_filtered["event_count"].sum()
                                st.write(f"**📊 Total Upstream Events:** {total_up:,}")
                            else:
                                sample = upstream_filtered.head(5)
                                for idx, row in sample.iterrows():
                                    chain_parts = [str(row.get('customer', ''))[:20]]
                                    for i in range(1, 4):
                                        val = row.get(f'customer_{i}', '')
                                        if val:
                                            chain_parts.append(str(val)[:15])
                                    st.write(f"**{safe_int(row.get('event_count', 0)):,} events**: {' → '.join(chain_parts)}")
                        else:
                            st.info("No upstream records")
        else:
            st.warning("No charts available for sample record analysis.")


    # -- ---------------------- BEST PATHS ONLY ----------------------
    if selected_customer != "All Customers":


        if downstream_available and not downstream_filtered.empty:
            downstream_data = downstream_filtered.to_dict(orient='records')
            downstream_leaf_values = {}
            root_id = "Customer Chain"

            for record in downstream_data:
                customer = clean_val(record.get('original_customer', ''))
                event_count = safe_int(record.get('event_count', 0))
                if not customer or event_count == 0:
                    continue

                chain = [customer]
                for i in range(1, 7):
                    cust = clean_val(record.get(f'customer_{i}', ''))
                    if cust:
                        chain.append(cust)
                    else:
                        break

                path_ids = [root_id] + chain
                leaf_id = "/".join(path_ids)
                downstream_leaf_values[leaf_id] = downstream_leaf_values.get(leaf_id, 0) + event_count

            if downstream_leaf_values:
                st.write("#### 🏆 Top 10 Downstream Paths")
                sorted_downstream = sorted(downstream_leaf_values.items(), key=lambda x: x[1], reverse=True)[:10]
                for i, (path, count) in enumerate(sorted_downstream, 1):
                    display_path = path.replace("Customer Chain/", "")
                    if len(display_path) > 60:
                        display_path = display_path[:57] + "..."
                    st.write(f"**{i}.** {display_path} – *{count:,} events*")

        if upstream_available and not upstream_filtered.empty:
            upstream_data = upstream_filtered.to_dict(orient='records')
            upstream_leaf_values = {}
            root_id = "Customer Chain"

            for record in upstream_data:
                event_count = safe_int(record.get('event_count', 0))
                if event_count == 0:
                    continue

                base_customer = clean_val(record.get('customer', ''))
                chain = [base_customer]
                for i in range(1, 7):
                    cust = clean_val(record.get(f'customer_{i}', ''))
                    if cust:
                        chain.append(cust)

                path_ids = [root_id] + chain
                leaf_id = "/".join(path_ids)
                upstream_leaf_values[leaf_id] = upstream_leaf_values.get(leaf_id, 0) + event_count

            if upstream_leaf_values:
                st.write("#### 🏆 Top 10 Upstream Paths")
                sorted_upstream = sorted(upstream_leaf_values.items(), key=lambda x: x[1], reverse=True)[:10]
                for i, (path, count) in enumerate(sorted_upstream, 1):
                    display_path = path.replace("Customer Chain/", "")
                    if len(display_path) > 60:
                        display_path = display_path[:57] + "..."
                    st.write(f"**{i}.** {display_path} – *{count:,} events*")



    # ---------------------- DEBUG: Validate Upstream Totals ----------------------
    if debug_mode and selected_customer != "All Customers":
        st.write("## 🛠 Debug: Validate Upstream Totals")

        try:
            # ✅ FIXED: Use the SAME file that the chart is using
            debug_upstream_csv_path = upstream_csv_path  # This matches your chart's data source
            csv_upstream = pd.read_csv(debug_upstream_csv_path)
            
            
            # ✅ FIXED: Use the SAME filtering logic as your chart
            csv_upstream.columns = [clean_key(col) for col in csv_upstream.columns]
            csv_upstream.fillna('', inplace=True)
            csv_upstream['customer_cleaned'] = csv_upstream['customer'].astype(str).apply(deep_clean)
            
            # ✅ Match chart logic: only rows relevant to selected customer
            upstream_filtered_debug = get_debug_data(csv_upstream, "upstream", selected_customer, customer_id)


            
            # ✅ Match CLI dedup logic exactly
            # ❌ Don't deduplicate – match CLI logic (raw total only)
            st.info("ℹ️ No deduplication applied – using raw event count like CLI")
            raw_upstream_total = upstream_filtered_debug['event_count'].sum()


            # ✅ Get chart total (this should be correct already)
            try:
                chart_total = sum(leaf_values_up.get(node_id, 0) for node_id in ids_up if node_id in leaf_values_up)


            except:
                chart_total = 0

            st.markdown(f"- **Raw CSV total from upstream file:** `{raw_upstream_total:,}`")
            st.markdown(f"- **Chart total based on tree structure:** `{chart_total:,}`")
            st.markdown(f"- **File used:** `{debug_upstream_csv_path}`")
            st.markdown(f"- **Records found:** `{len(upstream_filtered_debug):,}`")

            # ✅ Show difference and mismatched records
            if raw_upstream_total != chart_total:
                st.warning(f"⚠️ Mismatch: Difference = {raw_upstream_total - chart_total:,}")
                with st.expander("🔍 See upstream records from CSV"):
                    display_cols = ['customer', 'customer_1', 'customer_2', 'customer_3', 'customer_4', 'customer_5', 'customer_6', 'event_count']
                    display_cols = [col for col in display_cols if col in upstream_filtered_debug.columns]
                    st.dataframe(upstream_filtered_debug[display_cols].head(10))
            else:
                st.success("✅ The chart total matches the CSV total perfectly.")

        except Exception as e:
            st.error(f"🔴 Error validating upstream totals: {e}")
            st.error(f"Expected file path: {upstream_csv_path}")