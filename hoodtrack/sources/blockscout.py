"""Blockscout REST API v2 adapter for Robinhood Chain.

Blockscout uses keyset pagination: a list response carries `next_page_params`,
and you pass those keys straight back as query params to get the next page.
When the field is absent or null, the result set is exhausted.
"""

from __future__ import annotations

import logging

from ..http import JsonClient

log = logging.getLogger(__name__)


class Blockscout:
    def __init__(self, base_url, client: JsonClient, max_pages=200):
        self.base = base_url.rstrip("/")
        self.client = client
        self.max_pages = max_pages

    def _paged(self, path, params=None, max_pages=None):
        """Yield every item across all pages of a Blockscout v2 list endpoint."""
        url = f"{self.base}{path}"
        page_params = dict(params or {})
        limit = max_pages if max_pages is not None else self.max_pages
        seen_cursors = set()
        for page in range(limit):
            payload = self.client.get(url, page_params)
            if not payload:
                return
            items = payload.get("items") or []
            for item in items:
                yield item
            nxt = payload.get("next_page_params")
            if not nxt:
                return
            # Guard against a server that keeps handing back the same cursor.
            cursor = tuple(sorted((str(k), str(v)) for k, v in nxt.items()))
            if cursor in seen_cursors:
                log.warning("repeated pagination cursor on %s; stopping", path)
                return
            seen_cursors.add(cursor)
            page_params = dict(params or {})
            page_params.update(nxt)
        log.warning("hit max_pages=%d on %s; results truncated", limit, path)

    # --- address-scoped -------------------------------------------------
    def address_transactions(self, address, max_pages=None):
        return self._paged(f"/api/v2/addresses/{address}/transactions",
                           max_pages=max_pages)

    def address_token_transfers(self, address, max_pages=None):
        return self._paged(f"/api/v2/addresses/{address}/token-transfers",
                           max_pages=max_pages)

    def address_internal_transactions(self, address, max_pages=None):
        return self._paged(f"/api/v2/addresses/{address}/internal-transactions",
                           max_pages=max_pages)

    def address_info(self, address):
        return self.client.get(f"{self.base}/api/v2/addresses/{address}")

    # --- token-scoped ---------------------------------------------------
    def token_transfers(self, token, max_pages=None):
        return self._paged(f"/api/v2/tokens/{token}/transfers",
                           max_pages=max_pages)

    def token_info(self, token):
        return self.client.get(f"{self.base}/api/v2/tokens/{token}")

    # --- transaction-scoped ---------------------------------------------
    def transaction_token_transfers(self, tx_hash, max_pages=None):
        return self._paged(f"/api/v2/transactions/{tx_hash}/token-transfers",
                           max_pages=max_pages)
