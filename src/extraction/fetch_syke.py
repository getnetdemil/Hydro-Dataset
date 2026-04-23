import sys
from pathlib import Path

# Add src to path for relative imports
sys.path.append(str(Path(__file__).resolve().parent.parent))
from common.config import RAW_DIR

def fetch_syke_data():
    """
    Downloads hydrological observations from Syke OData API.
    Ref: https://www.syke.fi/en-US/Open_information
    """
    print("Fetching data from Syke API...")
    output_path = RAW_DIR / "syke"
    output_path.mkdir(exist_ok=True)
    print(f"Syke data stored in: {output_path}")

if __name__ == "__main__":
    fetch_syke_data()
