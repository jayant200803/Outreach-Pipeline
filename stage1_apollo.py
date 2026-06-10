"""
Stage 1 — Find Lookalike Companies via Apollo.io
-------------------------------------------------
INPUT  : seed domain (e.g. "stripe.com")
OUTPUT : list of similar company domains

Apollo APIs used:
  POST https://api.apollo.io/api/v1/organizations/enrich
       → pull seed company's industry tags + employee count
  POST https://api.apollo.io/api/v1/organizations/search
       → find companies that share those attributes (free-plan compatible)
  Docs: https://apolloio.github.io/apollo-api-docs/
"""

import os
import requests
from dotenv import load_dotenv

load_dotenv()

APOLLO_API_KEY = os.getenv("APOLLO_API_KEY")
BASE_URL = "https://api.apollo.io/api/v1"

# Apollo's fixed employee-count brackets (lo, hi inclusive, API label)
_EMPLOYEE_BRACKETS = [
    (1,     10,    "1,10"),
    (11,    20,    "11,20"),
    (21,    50,    "21,50"),
    (51,    200,   "51,200"),
    (201,   500,   "201,500"),
    (501,   1000,  "501,1000"),
    (1001,  2000,  "1001,2000"),
    (2001,  5000,  "2001,5000"),
    (5001,  10000, "5001,10000"),
    (10001, None,  "10001,20000"),
]


def _employee_range(count: int | None) -> list[str]:
    """
    Given a head-count, return the matching Apollo size bracket plus the
    adjacent ones so the search captures slightly smaller and larger peers.
    """
    if not count:
        return []
    for i, (lo, hi, _) in enumerate(_EMPLOYEE_BRACKETS):
        if lo <= count and (hi is None or count <= hi):
            start = max(0, i - 1)
            end   = min(len(_EMPLOYEE_BRACKETS) - 1, i + 1)
            return [_EMPLOYEE_BRACKETS[j][2] for j in range(start, end + 1)]
    return []


_HEADERS = {
    "Content-Type": "application/json",
    "Cache-Control": "no-cache",
    "X-Api-Key": APOLLO_API_KEY,
}


def _enrich_seed(domain: str) -> dict:
    """
    Fetch organisation details for the seed domain via Apollo's enrich endpoint.
    Returns an empty dict on any failure so callers degrade gracefully.
    """
    try:
        response = requests.post(
            f"{BASE_URL}/organizations/enrich",
            headers=_HEADERS,
            json={"domain": domain},
            timeout=30,
        )
        response.raise_for_status()
        return response.json().get("organization", {})
    except Exception as e:
        print(f"[Stage 1] Could not enrich seed domain ({domain}): {e}")
        return {}


def find_lookalike_companies(seed_domain: str, limit: int = 10) -> list[str]:
    """
    Given a seed domain, returns a list of similar company domains.

    Strategy:
      1. Enrich the seed domain to get its industry keyword tags and size.
      2. Search Apollo for companies that share those attributes.
         (Using q_organization_domains alone would only return the seed
          company itself — it is a domain-equality filter, not a similarity
          signal.)

    Args:
        seed_domain : company you already know — e.g. "stripe.com"
        limit       : how many lookalike domains to return (default 10)

    Returns:
        list of domain strings e.g. ["braintree.com", "adyen.com", ...]
    """
    print(f"\n[Stage 1] Finding lookalike companies for: {seed_domain}")

    # ── Step 1: enrich the seed company ────────────────────────
    org            = _enrich_seed(seed_domain)
    keyword_tags   = (org.get("keyword_tags") or [])[:8]   # cap at 8 tags
    employee_ranges = _employee_range(org.get("estimated_num_employees"))

    if not keyword_tags and not employee_ranges:
        print("[Stage 1] Seed company attributes unavailable — "
              "running a broad search.")

    # ── Step 2: search for lookalikes by shared attributes ─────
    payload: dict = {
        "page":     1,
        "per_page": limit + 5,   # fetch a few extra; seed is filtered below
    }
    if keyword_tags:
        payload["q_organization_keyword_tags"] = keyword_tags
    if employee_ranges:
        payload["q_organization_num_employees_ranges"] = employee_ranges

    try:
        response = requests.post(
            f"{BASE_URL}/organizations/search",
            headers=_HEADERS,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        accounts = data.get("accounts", []) or data.get("organizations", [])
        domains: list[str] = []

        for account in accounts:
            domain = account.get("domain") or account.get("primary_domain")
            if domain and domain != seed_domain and domain not in domains:
                domains.append(domain)
            if len(domains) >= limit:
                break

        print(f"[Stage 1] Found {len(domains)} lookalike companies: {domains}")
        return domains

    except requests.exceptions.HTTPError as e:
        print(f"[Stage 1] HTTP Error: {e.response.status_code} — {e.response.text}")
        return []
    except Exception as e:
        print(f"[Stage 1] Unexpected error: {e}")
        return []


if __name__ == "__main__":
    results = find_lookalike_companies("stripe.com", limit=5)
    print("\nResult:", results)
