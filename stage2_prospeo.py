"""
Stage 2 - Find Decision-Makers + Emails via Prospeo
-----------------------------------------------------
INPUT  : list of company domains from Stage 1
OUTPUT : list of dicts with name, title, email, linkedin_url, company

Prospeo APIs used (migrated from deprecated /domain-search):
  POST https://api.prospeo.io/search-person
       -> find C-suite/VP people at each domain
  POST https://api.prospeo.io/enrich-person
       -> fetch verified work email for each match
  Docs: https://prospeo.io/api-docs
"""

import os
import time
import requests
from dotenv import load_dotenv

load_dotenv()

PROSPEO_API_KEY = os.getenv("PROSPEO_API_KEY")
BASE_URL = "https://api.prospeo.io"

# Prospeo seniority enum values that map to decision-makers
DECISION_MAKER_SENIORITIES = [
    "C-Suite",
    "Director",
    "Founder/Owner",
    "Head",
    "Vice President",
]

_HEADERS = {
    "Content-Type": "application/json",
    "X-KEY": PROSPEO_API_KEY,
}


def _search_people(domain: str, limit: int) -> list[dict]:
    """
    Find decision-maker profiles at a domain via Prospeo's search-person endpoint.
    Returns raw result dicts (no email — that comes from enrich-person).
    """
    payload = {
        "filters": {
            "company": {
                "websites": {"include": [domain]},
            },
            "person_seniority": {
                "include": DECISION_MAKER_SENIORITIES,
            },
        },
        "page": 1,
    }

    try:
        response = requests.post(
            f"{BASE_URL}/search-person",
            headers=_HEADERS,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("error"):
            print(f"     Search error for {domain}: {data}")
            return []

        return (data.get("results") or [])[:limit]

    except requests.exceptions.HTTPError as e:
        print(f"     HTTP Error searching {domain}: {e.response.status_code} - {e.response.text}")
        return []
    except Exception as e:
        print(f"     Error searching {domain}: {e}")
        return []


def _enrich_person(person_id: str) -> tuple[str, str] | None:
    """
    Fetch a verified work email + job title for a person using their Prospeo person_id.
    Returns (email, title) on success, None if email is unavailable or unverified.
    """
    payload = {
        "only_verified_email": True,
        "data": {
            "person_id": person_id,
        },
    }

    try:
        response = requests.post(
            f"{BASE_URL}/enrich-person",
            headers=_HEADERS,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        if data.get("error"):
            return None

        person = data.get("person", {})
        email_obj = person.get("email", {})

        # email field may be a dict {"email": "...", "status": "VERIFIED"} or a plain string
        if isinstance(email_obj, dict):
            email = email_obj.get("email")
        else:
            email = email_obj

        if not email or "@" not in str(email):
            return None

        title = (person.get("title") or person.get("job_title")
                 or person.get("headline") or "")

        return str(email), str(title)

    except Exception:
        return None


def find_decision_makers(domains: list[str], limit_per_domain: int = 3) -> list[dict]:
    """
    For each domain, finds C-suite/VP contacts with verified emails.

    Two-step approach (Prospeo's current API):
      1. search-person  -> get candidates by domain + seniority filter
      2. enrich-person  -> resolve verified email for each candidate

    Args:
        domains           : list of company domains from Stage 1
        limit_per_domain  : max contacts to return per company (default 3)

    Returns:
        list of contact dicts:
        [
          {
            "name": "Jane Doe",
            "title": "CEO",
            "email": "jane@company.com",
            "linkedin_url": "https://linkedin.com/in/janedoe",
            "company": "company.com"
          },
          ...
        ]
    """
    print(f"\n[Stage 2] Finding decision-makers for {len(domains)} domains...")

    all_contacts = []

    for domain in domains:
        print(f"  -> Searching: {domain}")

        # Fetch more candidates than we need — some may have no verifiable email
        candidates = _search_people(domain, limit=limit_per_domain * 2)

        time.sleep(1)   # stay within Prospeo's free-plan rate limit

        if not candidates:
            print(f"     No results for {domain}")
            continue

        count = 0
        for result in candidates:
            if count >= limit_per_domain:
                break

            person = result.get("person") or {}
            person_id = person.get("person_id") or person.get("id")
            if not person_id:
                continue

            first = person.get("first_name", "")
            last  = person.get("last_name", "")
            name  = f"{first} {last}".strip() or person.get("full_name", "Unknown")
            # search-person returns seniority level; enrich-person returns job title
            title = (person.get("title") or person.get("job_title")
                     or person.get("seniority") or "")
            linkedin = person.get("linkedin_url", "")

            enriched = _enrich_person(person_id)
            if not enriched:
                continue

            email, enriched_title = enriched
            # prefer the richer title from the enrich response
            final_title = enriched_title or title

            all_contacts.append({
                "name": name,
                "title": final_title,
                "email": email,
                "linkedin_url": linkedin,
                "company": domain,
            })
            count += 1

        print(f"     Found {count} decision-makers")

    print(f"[Stage 2] Total contacts found: {len(all_contacts)}")
    return all_contacts


if __name__ == "__main__":
    # Quick test
    test_domains = ["stripe.com"]
    results = find_decision_makers(test_domains, limit_per_domain=2)
    for r in results:
        print(r)
