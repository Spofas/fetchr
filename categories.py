"""Collect CoinGecko categories used to exclude assets from the homepage."""
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app import MARKETS_URL

CATEGORIES = ('stablecoins', 'liquid-staking-tokens', 'liquid-staked-apt', 'liquid-staked-btc',
              'liquid-staked-eth', 'liquid-staked-hype', 'liquid-staked-sol', 'liquid-staked-sui')


def fetch_categories(key, url=MARKETS_URL):
    ids = set()
    for category in CATEGORIES:
        for page in range(1, 51):
            query = urlencode({'vs_currency': 'usd', 'category': category, 'order': 'market_cap_desc',
                               'per_page': 250, 'page': page, 'sparkline': 'false'})
            request = Request(url + '?' + query, headers={'x-cg-demo-api-key': key, 'User-Agent': 'fetchr/1.0'})
            with urlopen(request, timeout=30) as response:
                data = json.load(response)
            if not isinstance(data, list) or any(not isinstance(x, dict) or not x.get('id') for x in data):
                raise ValueError(f'Invalid category response: {category}')
            ids.update(x['id'] for x in data)
            if len(data) < 250:
                break
        else:
            raise ValueError(f'Category too large: {category}')
    return {'excluded_ids': sorted(ids), 'updated_at': datetime.now(timezone.utc).isoformat()}


if __name__ == '__main__':
    key = os.getenv('COINGECKO_API_KEY')
    if not key:
        raise SystemExit('COINGECKO_API_KEY must be configured')
    path = Path('data/categories.json')
    if not path.exists():
        result = fetch_categories(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result), encoding='utf-8')
        print(f"Collected {len(result['excluded_ids'])} category IDs")
