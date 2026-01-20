import pandas as pd

def test_krx():
    print("Downloading KRX Corp List...")
    try:
        url = "http://kind.krx.co.kr/corpgeneral/corpList.do?method=download&searchType=13"
        # pandas read_html returns list of DataFrames
        dfs = pd.read_html(url, header=0) 
        df = dfs[0]
        
        print(f"Loaded {len(df)} rows.")
        print(df.columns)
        
        # Check mapping
        # Columns usually: '회사명', '종목코드', '업종', ...
        # '종목코드' needs zero-padding to 6 chars
        
        df = df[['회사명', '종목코드']]
        df['종목코드'] = df['종목코드'].astype(str).str.zfill(6)
        
        # Test Search
        company = "삼성전자"
        row = df[df['회사명'] == company]
        if not row.empty:
            print(f"Found: {company} -> {row.iloc[0]['종목코드']}")
        else:
            print(f"Not found: {company}")
            
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    test_krx()
