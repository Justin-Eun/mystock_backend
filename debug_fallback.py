import FinanceDataReader as fdr
import pandas as pd
from datetime import datetime

code = "005930" # Samsung Electronics
start = "2024-01-01"
end = "2024-01-20"

print(f"Testing FDR for {code} from {start} to {end}...")

try:
    df = fdr.DataReader(code, start, end)
    print("FDR Result:")
    print(df.head())
    print(f"Empty? {df.empty}")
    if not df.empty:
        print("Columns:", df.columns)
except Exception as e:
    print(f"FDR Error: {e}")
