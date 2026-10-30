"""Generate the public static market snapshot."""
import csv
import json
import os
from pathlib import Path

from app import FIELDS, Store, positive_int


def generate(output, store):
    # Do not write public files until the complete fetch has succeeded.
    store.refresh()
    snapshot = store.get()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    with (output / 'assets.json').open('w', encoding='utf-8') as f:
        json.dump(snapshot, f, ensure_ascii=False, allow_nan=False)
    with (output / 'assets.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, lineterminator='\n')
        writer.writeheader()
        for asset in snapshot['assets']:
            writer.writerow({key: ("'" + value if isinstance(value, str) and value.lstrip().startswith(('=', '+', '-', '@')) else value)
                             for key, value in asset.items()})


if __name__ == '__main__':
    key = os.getenv('COINGECKO_API_KEY')
    if not key:
        raise SystemExit('COINGECKO_API_KEY must be configured')
    store = Store(positive_int('FETCHR_ASSET_COUNT', 3000), os.getenv('FETCHR_DATA_DIR', 'data'), key)
    generate(os.getenv('FETCHR_OUTPUT_DIR', 'site'), store)
    print(f"Generated {len(store.get()['assets'])} assets")
