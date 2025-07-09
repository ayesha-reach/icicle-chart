import os
import pandas as pd
import psycopg2
from dotenv import load_dotenv
import shutil
from datetime import datetime
from sshtunnel import SSHTunnelForwarder

# Load environment variables
load_dotenv()

import os
import psycopg2
from sshtunnel import SSHTunnelForwarder

def get_db_connection():
    """Establish SSH tunnel and test PostgreSQL connection"""
    try:
       tunnel = SSHTunnelForwarder(
            (os.getenv("SSH_HOST"), 22),
            ssh_username=os.getenv("SSH_USER"),
            ssh_pkey=os.getenv("SSH_KEY_PATH"),
            remote_bind_address=(os.getenv("DB_HOST"), int(os.getenv("DB_PORT"))),
            local_bind_address=('localhost',),
            set_keepalive=60 
        )
       tunnel.start()
       conn = psycopg2.connect(
       dbname=os.getenv('DB_NAME'),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            host='localhost',
            port=tunnel.local_bind_port
        )
       with conn.cursor() as cur:
            cur.execute("SELECT 1;")
            assert cur.fetchone()[0] == 1
            print("✅ Database connection successful via SSH tunnel.")
            return conn, tunnel

    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        if 'tunnel' in locals():
            tunnel.stop()
        raise



def get_icicle_data(query, period, filename):   

    conn, tunnel = get_db_connection()

    # Fetch the new and updated data
    #query="select count(*) from tenants"
    df_new = pd.read_sql(query, conn)
    print(df_new)
    conn.close()
    tunnel.stop()

    if df_new.empty:
        print("No new or updated records found.")
        return

    # If existing CSV file exists, update the records instead of appending
    if os.path.exists(filename):
        # Destination folder
        destination_folder = 'archive'

        # Ensure destination folder exists
        os.makedirs(destination_folder, exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

        # Get filename and extension

        # Create new filename with timestamp
        new_filename = f"{timestamp}_{os.path.basename(filename)}"

        destination_path = os.path.join(destination_folder, new_filename)

        # Move and rename file
        shutil.move(filename, destination_path)

        print(f"Moved {filename} to {destination_folder}/")
        # Save updated file
        # Ensure parent folder exists
        os.makedirs(os.path.dirname(filename), exist_ok=True)

        # Save main file
        os.makedirs(os.path.dirname(filename), exist_ok=True)  
        df_new.to_csv(filename, index=False)

    else:
        os.makedirs(os.path.dirname(filename), exist_ok=True)
        df_new.to_csv(filename, index=False)

    print(f"Updated file saved at: {filename}")



def build_downstream_query(period):
    query = ""    
    with open("queries/downstream.sql", "r") as file:
        query_template = file.read()

    query = query_template.format(period=period)
    
    return query


def build_upstream_query(period):
    query = ""    
    with open("queries/upstream.sql", "r") as file:
        query_template = file.read()
    
    query = query_template.format(period=period)
    return query



def main():

################### DOWNSTREAM ################
    #Build One Month Downstream
#     query = build_downstream_query(1)
#     # print(query)
#     get_icicle_data(query, 1, "D:/icicle_chart/data/shifted_downstream_duration_1month.csv"
# )


    # # Build 3 Months Downstream
    # query = build_downstream_query(3)
    # get_icicle_data(query, 1, "D:/icicle_chart/data/shifted_downstream_duration_3month.csv")

    # # Build Six Months Downstream
    # query = build_downstream_query(6)
    # get_icicle_data(query, 1, "D:/icicle_chart/data/shifted_downstream_duration_6month.csv")

    # # Build One Year Downstream
    # query = build_downstream_query(12)
    # get_icicle_data(query, 1, "D:/icicle_chart/data/shifted_downstream_duration_1year.csv")


################### UPSTREAM ################
    # # Build One Month Upstream
    # query = build_upstream_query(1)
    # get_icicle_data(query, 1, "D:/icicle_chart/data/shifted_upstream_duration_1month.csv")

    # # Build 3 Months Upstream
    query = build_upstream_query(3)
    get_icicle_data(query, 1, "D:/icicle_chart/data/shifted_upstream_duration_3month.csv")

    # # Build Six Months Upstream
    # query = build_upstream_query(6)
    # get_icicle_data(query, 1, "D:/icicle_chart/data/shifted_upstream_duration_6month.csv")

    # # Build One Year Upstream
    # query = build_upstream_query(12)
    # get_icicle_data(query, 1, "D:/icicle_chart/data/shifted_upstream_duration_1year.csv")



if __name__ == "__main__":
    main()
