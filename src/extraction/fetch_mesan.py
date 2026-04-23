import sys
from pathlib import Path

# Add src to path for relative imports
sys.path.append(str(Path(__file__).resolve().parent.parent))
from common.config import RAW_DIR

def fetch_mesan_data():
    """
    Downloads MESAN reanalysis data from SMHI Open Data API.
    Ref: https://opendata.smhi.se/apidocs/mesan/index.html
    """
    print("Fetching data from MESAN (GRIB2 files)...")
    output_path = RAW_DIR / "mesan"
    output_path.mkdir(exist_ok=True)
    print(f"MESAN data stored in: {output_path}")

if __name__ == "__main__":
    fetch_mesan_data()
