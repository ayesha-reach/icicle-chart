import pandas as pd
import json
import os
import numpy as np

# Input and output paths
csv_file = r'C:\Users\ansaa\OneDrive\Desktop\final_fleet_downstream_data.csv'
json_file = r'C:\Users\ansaa\OneDrive\Desktop\icicle chart\output3.json'

# Load CSV
df = pd.read_csv(csv_file)

# Show initial structure
print("🔍 Original DataFrame shape:", df.shape)
print("🧾 Columns:", df.columns.tolist())

# Clean column names
df.columns = df.columns.str.strip()

# Drop all columns that end with '_id'
df = df[[col for col in df.columns if not col.endswith('_id')]]

# Clean string values
for col in df.select_dtypes(include='object').columns:
    df[col] = df[col].map(lambda x: x.strip() if isinstance(x, str) else x)

# Function to clean each value
def clean_value(value):
    if pd.isna(value):
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        if cleaned == "" or cleaned.lower() == "nan":
            return None
        return cleaned
    return value

# Clean entire DataFrame
for col in df.columns:
    df[col] = df[col].map(clean_value)

# Define forwarding columns (excluding IDs)
forwarding_fields = ['customer_1', 'customer_2', 'customer_3', 'customer_4', 'customer_5', 'customer_6']

# Build cleaned records
records = []
for record in df.to_dict(orient='records'):
    cleaned_record = {}
    for k, v in record.items():
        if v is not None and not pd.isna(v):
            if isinstance(v, str) and v.lower().strip() == "nan":
                continue
            cleaned_record[k] = v

    # Keep record only if there's a customer and at least one forwarded customer
    if 'customer' in cleaned_record and any(f in cleaned_record for f in forwarding_fields):
        records.append(cleaned_record)

# Export to JSON
with open(json_file, 'w', encoding='utf-8') as f:
    json.dump(records, f, indent=4)

# Final log
print(f"\n✅ CSV successfully converted to JSON (without IDs) at:\n{json_file}")
print(f"📊 Records processed: {len(records)}")
print(f"🧹 Cleaned data: removed NaN, empty strings, and ID fields")
