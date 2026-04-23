import sys
from pathlib import Path

# Add src to path for relative imports
sys.path.append(str(Path(__file__).resolve().parent.parent))
from common.config import RAW_DIR

def fetch_smhi_data():
    """
    Downloads station data from SMHI Open Data API.
    Ref: https://opendata.smhi.se/apidocs/metobs/index.html
    """
    print("Fetching data from SMHI API...")
    # Placeholder for API request logic
    output_path = RAW_DIR / "smhi"
    output_path.mkdir(exist_ok=True)
    print(f"SMHI data stored in: {output_path}")

if __name__ == "__main__":
    fetch_smhi_data()
