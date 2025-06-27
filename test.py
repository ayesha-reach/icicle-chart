import pandas as pd
import re

def deep_clean(s):
    if not isinstance(s, str): return ''
    return re.sub(r'[\u200B-\u200D\uFEFF]', '', s).encode('ascii', errors='ignore').decode().strip().lower()

# -----------------------
# Part 1: Common customers in both shifted upstream & downstream
# -----------------------

down_df = pd.read_csv("shifted_downstream_duration/shifted_downstream_duration_1month.csv")
up_df = pd.read_csv("shifted_upstream_duration/shifted_upstream_duration_1month.csv")

down_roots = set(down_df['customer'].dropna().astype(str).apply(deep_clean))
up_roots = set(up_df['customer'].dropna().astype(str).apply(deep_clean))

common_cleaned = down_roots.intersection(up_roots)

down_display = set(down_df[down_df['customer'].astype(str).apply(deep_clean).isin(common_cleaned)]['customer'].astype(str).str.strip())
up_display = set(up_df[up_df['customer'].astype(str).apply(deep_clean).isin(common_cleaned)]['customer'].astype(str).str.strip())

final_customers = sorted(down_display.intersection(up_display))

print("✅ Customers with BOTH upstream and downstream charts (1 Month):")
for customer in final_customers:
    print(" -", customer)

# -----------------------
# Part 2: Hop 1 customers for a given target
# -----------------------

df = pd.read_csv("upstream_duration/up_1month_data.csv")
df.fillna('', inplace=True)

target = "direct chassislink inc"  # change as needed
hop_1 = set()

for _, row in df.iterrows():
    chain = [row["customer"]] + [row.get(f"customer_{i}", '') for i in range(1, 7)]
    chain = [c for c in chain if c.strip()]
    try:
        pos = next(i for i, val in enumerate(chain) if deep_clean(val) == target)
        if pos + 1 < len(chain):
            hop_1.add(chain[pos + 1])
    except StopIteration:
        continue

print(f"\n✅ Hop 1 customers downstream from: {target}")
for name in sorted(hop_1):
    print(" -", name)
