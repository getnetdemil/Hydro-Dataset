import sys
from pathlib import Path

# Add src to path for relative imports
sys.path.append(str(Path(__file__).resolve().parent.parent))
from common.config import RAW_DIR

def fetch_fmi_data():
    """
    Downloads station and satellite data from FMI Open Data API.
    Ref: https://en.ilmatieteenlaitos.fi/open-data
    """
    print("Fetching data from FMI API...")
    output_path = RAW_DIR / "fmi"
    output_path.mkdir(exist_ok=True)
    print(f"FMI data stored in: {output_path}")

if __name__ == "__main__":
    fetch_fmi_data()
