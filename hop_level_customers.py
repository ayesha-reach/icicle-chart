import streamlit as st
import pandas as pd
import re
from collections import defaultdict
import plotly.express as px

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
    except StopIteration:
        return False

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

    active_hops = {k: v for k, v in hop_filters.items() if v}
    max_hop = max(active_hops.keys(), default=6)

    for record in df.to_dict(orient="records"):
        event_count = safe_int(record.get("event_count", 0))
        if event_count == 0:
            continue

        chain = [clean_val(record.get("customer", ""))]
        for i in range(1, 7):
            val = clean_val(record.get(f"customer_{i}", ""))
            if val:
                chain.append(val)

        if selected_customer != "All Customers":
            try:
                pos = next(i for i, val in enumerate(chain) if deep_clean(val) == deep_clean(selected_customer))
                chain = chain[pos : pos + max_hop + 1]
            except StopIteration:
                continue

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

# ---------- UI ----------

st.title("Hop-Level Customer Viewer")

df = load_df("upstream_duration/up_1month_data.csv")
original_customers = sorted(set(df['customer']))
clean_map = {deep_clean(c): c for c in original_customers}
all_options = ["All Customers"] + original_customers
selected_customer = st.selectbox("Select customer", all_options)
selected_customer_cleaned = deep_clean(selected_customer)

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

# Hop filters
hop_filters = {}
if selected_customer != "All Customers":
    st.markdown("---")
    st.markdown("### Filter by Hop Level")
    for hop_level in range(1, max_hop + 1):
        hop_customers = list(hop_map[hop_level])
        if hop_customers:
            selected_hop_customers = st.multiselect(
                f"Filter Hop {hop_level} customers:",
                sorted(hop_customers),
                key=f"hop_{hop_level}_filter"
            )
            hop_filters[hop_level] = selected_hop_customers

st.markdown("---")

# Filtered data
if selected_customer == "All Customers":
    filtered_df = df.copy()
else:
    filtered_df = df[df.apply(lambda row: chain_matches(row, hop_filters, selected_customer_cleaned), axis=1)]
    filtered_df = filtered_df[df['customer_cleaned'] == selected_customer_cleaned]

# 🔍 Debug matched rows
st.markdown("### 🔍 Debug Filtered Rows")
st.dataframe(filtered_df[['customer', 'customer_1', 'customer_2', 'event_count']].reset_index(drop=True).head(20))


# Chart
st.markdown("### 📊 Upstream Icicle Chart for Filtered Chains")

if not filtered_df.empty:
    labels, parents, values, ids, totals, leaf_values = build_upstream_chart(
        filtered_df, selected_customer, hop_filters
    )

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
        title="Upstream Chain – All Customers" if selected_customer == "All Customers" else f"Upstream Chain – {selected_customer}",
        color_discrete_sequence=["#D96F32"],
        height=500
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
    st.info("No matching chains to display.")

# Hop summary
if selected_customer != "All Customers":
    for hop, names in sorted(hop_map.items()):
        st.markdown(f"### Hop {hop}")
        if hop in hop_filters and hop_filters[hop]:
            filtered_names = [name for name in names if name in hop_filters[hop]]
            st.write(sorted(filtered_names) if filtered_names else "No matches with current filter")
            st.caption(f"Showing {len(filtered_names)} of {len(names)} customers")
        else:
            st.write(sorted(names) if names else "—")
            if names:
                st.caption(f"Total: {len(names)} customers")
