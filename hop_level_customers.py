import streamlit as st
import pandas as pd
import re
from collections import defaultdict
import plotly.express as px
import os
from dotenv import load_dotenv

def render_hop_level_page():
        
        load_dotenv()
        DEBUG = os.getenv("DEBUG_MODE", "false").lower() == "true"
        UPSTREAM_COLOR = os.getenv("UPSTREAM_COLOR", "#D96F32")
        DOWNSTREAM_COLOR = os.getenv("DOWNSTREAM_COLOR", "#4C78A8")


        def clean_val(v):
            return str(v).strip() if isinstance(v, str) else ''

        def safe_int(val):
            try:
                return int(str(val).replace(',', '').strip())
            except Exception:
                return 0

        def deep_clean(s):
            if not isinstance(s, str): return ''
            return re.sub(r'[\u200B-\u200D\uFEFF]', '', s).encode('ascii', errors='ignore').decode().strip().lower()

        @st.cache_data
        def load_df(path):
            df = pd.read_csv(path)
            df.fillna('', inplace=True)
            df['customer'] = df['customer'].astype(str).apply(clean_val)
            for i in range(1, 7):
                df[f'customer_{i}'] = df[f'customer_{i}'].astype(str).apply(clean_val)
            df['customer_cleaned'] = df['customer'].apply(deep_clean)
            return df

        def chain_matches(row, hop_filters, selected_customer):
            active_hops = {k: v for k, v in hop_filters.items() if v}
            chain = [row['customer']] + [row.get(f'customer_{i}', '') for i in range(1, 7)]
            chain = [c for c in chain if c.strip()]

            try:
                pos = next(i for i, val in enumerate(chain) if deep_clean(val) == selected_customer)
                if pos != 0:
                    return False  # Only allow root match
            except StopIteration:
                return False

            if not active_hops:
                return True  # ✅ Accept all chains rooted at customer

            max_specified = max(active_hops.keys(), default=0)
            for hop in range(1, max_specified + 1):
                expected = active_hops.get(hop, [])
                idx = pos + hop
                if idx >= len(chain):
                    return False
                if expected and deep_clean(chain[idx]) not in {deep_clean(x) for x in expected}:
                    return False

            return True


        def build_upstream_chart(df, selected_customer, hop_filters):
            labels, parents, values, ids = [], [], [], []
            node_children = {}
            leaf_values = {}
            calculated_totals = {}
            aggregated = defaultdict(int)

            root_id = "root"
            labels.append("")
            parents.append("")
            ids.append(root_id)
            node_children[root_id] = set()

            for record in df.to_dict(orient="records"):
                event_count = safe_int(record.get("event_count", 0))
                if event_count == 0:
                    continue

                customer = clean_val(record.get("customer", ""))
                if selected_customer != "All Customers" and deep_clean(customer) != deep_clean(selected_customer):
                    continue

                chain = [customer]
                for i in range(1, 7):
                    val = clean_val(record.get(f"customer_{i}", ""))
                    if val:
                        chain.append(val)

                if len(chain) <= 1:
                    continue

                aggregated[tuple(chain)] += event_count

            for chain, count in aggregated.items():
                path = [root_id]
                for i, name in enumerate(chain):
                    parent = "/".join(path)
                    label = name if i == 0 else f"{name} (Hop {i})"
                    node_id = parent + "/" + label

                    node_children.setdefault(parent, set()).add(node_id)
                    node_children.setdefault(node_id, set())

                    if node_id not in ids:
                        labels.append(label)
                        parents.append(parent)
                        ids.append(node_id)

                    path.append(label)

                final_id = "/".join(path)
                leaf_values[final_id] = count

            def calc_total(node_id):
                if node_id in calculated_totals:
                    return calculated_totals[node_id]
                total = leaf_values.get(node_id, 0)
                for child in node_children.get(node_id, []):
                    total += calc_total(child)
                calculated_totals[node_id] = total
                return total

            for node in ids:
                calc_total(node)

            for node in ids:
                values.append(0 if node_children.get(node) else leaf_values.get(node, 0))

            return labels, parents, values, ids, calculated_totals, leaf_values


        def build_downstream_chart(df, selected_customer):
            labels, parents, values, ids = [], [], [], []
            node_children = {}
            leaf_values = {}
            calculated_totals = {}
            aggregated = defaultdict(int)

            root_id = "root"
            labels.append("")
            parents.append("")
            ids.append(root_id)
            node_children[root_id] = set()

            for record in df.to_dict(orient='records'):
                event_count = safe_int(record.get('event_count', 0))
                if event_count == 0:
                    continue

                customer = clean_val(record.get('customer', ''))
                chain = [customer]
                for i in range(1, 7):
                    cust = clean_val(record.get(f'customer_{i}', ''))
                    if cust:
                        chain.append(cust)
                if len(chain) <= 1:
                    continue         

                if selected_customer != "All Customers":
                    if deep_clean(customer) != deep_clean(selected_customer):
                        continue

                aggregated[tuple(chain)] += event_count

            for chain, count in aggregated.items():
                path = [root_id]
                for i, name in enumerate(chain):
                    parent = "/".join(path)
                    label = name if i == 0 else f"{name} (Hop {i})"
                    node_id = parent + "/" + label

                    node_children.setdefault(parent, set()).add(node_id)
                    node_children.setdefault(node_id, set())

                    if node_id not in ids:
                        labels.append(label)
                        parents.append(parent)
                        ids.append(node_id)

                    path.append(label)

                final_id = "/".join(path)
                leaf_values[final_id] = count

            def calc_total(node_id):
                if node_id in calculated_totals:
                    return calculated_totals[node_id]
                total = leaf_values.get(node_id, 0)
                for child in node_children.get(node_id, []):
                    total += calc_total(child)
                calculated_totals[node_id] = total
                return total

            for node in ids:
                calc_total(node)

            for node in ids:
                values.append(0 if node_children.get(node) else leaf_values.get(node, 0))

            return labels, parents, values, ids, calculated_totals, leaf_values

            # ---------- UI ----------
        st.title("Hop Level Analysis")

        # 1️⃣ Duration selection
        st.markdown("### ⏱️ Select Duration")
        duration = st.selectbox("Duration", ["1 Month", "3 Months", "6 Months", "1 Year"], key="duration_select")

        # 2️⃣ TEMP LOAD to extract customer list for dropdown (static files just to build the list)
        temp_df_up = load_df("upstream_duration/up_1month_data.csv")
        temp_df_down = load_df("duration/1month_data.csv")
        all_customers_up = set(temp_df_up['customer'].dropna().astype(str).map(clean_val))
        all_customers_down = set(temp_df_down['customer'].dropna().astype(str).map(clean_val))
        original_customers = sorted(all_customers_up | all_customers_down)

        clean_map = {deep_clean(c): c for c in original_customers}
        all_options = ["All Customers"] + original_customers
        selected_customer = st.selectbox("Select customer", all_options)
        selected_customer_cleaned = deep_clean(selected_customer)

        # 3️⃣ File mappings
        upstream_file_map = {
            "1 Month": "up_1month_data.csv",
            "3 Months": "up_3month_data.csv",
            "6 Months": "up_6month_data.csv",
            "1 Year": "up_1year_data.csv"
        }

        shifted_upstream_file_map = {
            "1 Month": "shifted_upstream_duration_1month.csv",
            "3 Months": "shifted_upstream_duration_3month.csv",
            "6 Months": "shifted_upstream_duration_6month.csv",
            "1 Year": "shifted_upstream_duration_1year.csv"
        }

        downstream_file_map = {
            "1 Month": "1month_data.csv",
            "3 Months": "3month_data.csv",
            "6 Months": "6month_data.csv",
            "1 Year": "1year_data.csv"
        }

        shifted_downstream_file_map = {
            "1 Month": "shifted_downstream_duration_1month.csv",
            "3 Months": "shifted_downstream_duration_3month.csv",
            "6 Months": "shifted_downstream_duration_6month.csv",
            "1 Year": "shifted_downstream_duration_1year.csv"
        }

        # 4️⃣ Select file paths based on customer selection and duration
        if selected_customer == "All Customers":
            upstream_path = f"upstream_duration/{upstream_file_map[duration]}"
            downstream_path = f"duration/{downstream_file_map[duration]}"
        else:
            upstream_path = f"shifted_upstream_duration/{shifted_upstream_file_map[duration]}"
            downstream_path = f"shifted_downstream_duration/{shifted_downstream_file_map[duration]}"

        # 5️⃣ Load the actual data
        df = load_df(upstream_path)
        downstream_df = load_df(downstream_path)





        # ✅ Hop map: only from chains where selected_customer is the root
        hop_map = defaultdict(set)
        max_hop = 0
        if selected_customer != "All Customers":
            for row in df.itertuples():
                if deep_clean(row.customer) != selected_customer_cleaned:
                    continue
                chain = [row.customer] + [getattr(row, f"customer_{i}", '') for i in range(1, 7)]
                chain = [c for c in chain if c.strip()]
                for hop_offset, name in enumerate(chain[1:], start=1):
                    hop_map[hop_offset].add(name)
                    max_hop = max(max_hop, hop_offset)



        # ✅ Downstream Hop filters
        hop_map_down = defaultdict(set)
        max_hop_down = 0
        if selected_customer != "All Customers":
            for row in downstream_df.itertuples():
                if deep_clean(row.customer) != selected_customer_cleaned:
                    continue
                chain = [row.customer] + [getattr(row, f"customer_{i}", '') for i in range(1, 7)]
                chain = [c for c in chain if c.strip()]
                for hop_offset, name in enumerate(chain[1:], start=1):
                    hop_map_down[hop_offset].add(name)
                    max_hop_down = max(max_hop_down, hop_offset)

        # Downstream Hop Filters
        downstream_filters = {}
        if selected_customer != "All Customers" and max_hop_down > 0:

            st.markdown("---")
            st.markdown("### 🔽 Filter Downstream by Hop Level")
            for hop_level in range(1, max_hop_down + 1):
                hop_customers = list(hop_map_down[hop_level])
                if hop_customers:
                    selected_hop_customers = st.multiselect(
                        f"Hop {hop_level}:"
,
                        sorted(hop_customers),
                        key=f"downstream_hop_{hop_level}_filter"
                    )
                    downstream_filters[hop_level] = selected_hop_customers



        # Upstream Hop Filters
        hop_filters = {}
        if selected_customer != "All Customers" and max_hop > 0:

            st.markdown("---")
            st.markdown("### 🔼 Filter Upstream by Hop Level")
            for hop_level in range(1, max_hop + 1):
                hop_customers = list(hop_map[hop_level])
                if hop_customers:
                    selected_hop_customers = st.multiselect(
                        f"Hop {hop_level}:",
                        sorted(hop_customers),
                        key=f"hop_{hop_level}_filter"
                    )
                    hop_filters[hop_level] = selected_hop_customers


        st.markdown("---")

        # Filtered data
        if selected_customer == "All Customers":
            filtered_df = df.copy()
            downstream_filtered = downstream_df.copy()
        else:
            filtered_df = df[df.apply(lambda row: chain_matches(row, hop_filters, selected_customer_cleaned), axis=1)]


            
            downstream_filtered = downstream_df[downstream_df.apply(lambda row: chain_matches(row, downstream_filters, selected_customer_cleaned), axis=1)]




        if DEBUG:
            st.markdown("#### 🔼 From Upstream CSV")
            st.dataframe(filtered_df[['customer', 'customer_1', 'customer_2', 'event_count']].reset_index(drop=True).head(20))

            st.markdown("#### 🔽 From Downstream CSV")
            st.dataframe(downstream_filtered[['customer', 'customer_1', 'customer_2', 'event_count']].reset_index(drop=True).head(20))



        # Charts
        st.markdown("### 📍 Hop-Level Partner Flow")

        col1, col2 = st.columns(2)
        with col1:
            labels, parents, values, ids, totals, leaf_values = [], [], [], [], {}, {}
            if not filtered_df.empty:
                labels, parents, values, ids, totals, leaf_values = build_upstream_chart(
                    filtered_df, selected_customer, hop_filters
                )

            if ids and len(ids) > 1:
                

                total_events = sum(leaf_values.values())
                customdata = [
                    [totals.get(node_id, 0),
                    (totals.get(node_id, 0) / total_events * 100) if total_events > 0 else 0]
                    for node_id in ids
                ]
                fig = px.icicle(
                    names=labels,
                    parents=parents,
                    values=values,
                    ids=ids,
                    title=f"Upstream Partners – {selected_customer}",
                    color_discrete_sequence=[UPSTREAM_COLOR],
                    height=600
                )
                fig.update_traces(
                    hovertemplate=(
                        "<b>%{label}</b><br>" +
                        "Event Count: %{customdata[0]:,}<br>" +
                        "Percent of Total: %{customdata[1]:.2f}%<br>" +
                        "<extra></extra>"
                    ),
                    customdata=customdata,
                    marker=dict(colorscale=None, showscale=False)
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.warning("🚫 No upstream partners.")


        with col2:
            labels_d, parents_d, values_d, ids_d, totals_d, leaf_d = [], [], [], [], {}, {}
            if not downstream_filtered.empty:
                labels_d, parents_d, values_d, ids_d, totals_d, leaf_d = build_downstream_chart(
                    downstream_filtered, selected_customer
                )
            
            if ids_d and len(ids_d) > 1:
                

                total_events_d = sum(leaf_d.values())
                customdata_d = [
                    [totals_d.get(node_id, 0),
                    (totals_d.get(node_id, 0) / total_events_d * 100) if total_events_d > 0 else 0]
                    for node_id in ids_d
                ]
                fig_d = px.icicle(
                    names=labels_d,
                    parents=parents_d,
                    values=values_d,
                    ids=ids_d,
                    title=f"Downstream Partners  – {selected_customer}",
                    color_discrete_sequence=[DOWNSTREAM_COLOR],
                    height=600
                )
                fig_d.update_traces(
                    hovertemplate=(
                        "<b>%{label}</b><br>" +
                        "Event Count: %{customdata[0]:,}<br>" +
                        "Percent of Total: %{customdata[1]:.2f}%<br>" +
                        "<extra></extra>"
                    ),
                    customdata=customdata_d,
                    marker=dict(colorscale=None, showscale=False)
                )
                st.plotly_chart(fig_d, use_container_width=True)
            else:
                st.warning("🚫 No downstream partners.")





