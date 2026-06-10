"""
main.py — Cold Outreach Pipeline Orchestrator
==============================================
One input. Three stages. Zero manual steps.

USAGE:
  python main.py stripe.com
  python main.py stripe.com --limit 5 --dry-run

PIPELINE:
  Stage 1 (Apollo)  : seed domain -> lookalike company domains
  Stage 2 (Prospeo) : domains -> decision-makers + verified emails
  Stage 3 (Brevo)   : contacts -> personalised outreach sent

SAFETY CHECKPOINT:
  Before emails fire, the pipeline prints a full summary and asks
  for confirmation. Pass --no-confirm to skip (e.g. in CI).
"""

import sys
import argparse
from stage1_apollo import find_lookalike_companies
from stage2_prospeo import find_decision_makers
from stage3_brevo import send_emails


def print_banner():
    print("""
+======================================================+
|        Cold Outreach Pipeline - jayantworks.xyz      |
| Stage 1: Apollo -> Stage 2: Prospeo -> Stage 3: Brevo |
+======================================================+
""")


def print_summary(seed_domain: str, domains: list, contacts: list):
    """Safety checkpoint — show a full summary before emails fire."""
    print("\n" + "=" * 54)
    print("  SAFETY CHECKPOINT - Review before sending")
    print("=" * 54)
    print(f"  Seed domain    : {seed_domain}")
    print(f"  Companies found: {len(domains)}")
    print(f"  Contacts found : {len(contacts)}")
    print("-" * 54)

    for i, contact in enumerate(contacts, 1):
        print(f"  {i}. {contact['name']} - {contact['title']}")
        print(f"     {contact['email']} | {contact['company']}")

    print("=" * 54)


def run_pipeline(seed_domain: str, limit: int = 10, dry_run: bool = False, no_confirm: bool = False):
    """
    Full end-to-end pipeline.

    Args:
        seed_domain : the company domain to find lookalikes for
        limit       : max lookalike companies to find (default 10)
        dry_run     : if True, skips sending emails (just shows contacts)
        no_confirm  : if True, skips the safety checkpoint prompt
    """
    print_banner()
    print(f"Starting pipeline for seed domain: {seed_domain}\n")

    # ── Stage 1: Find lookalike companies ──────────────────
    domains = find_lookalike_companies(seed_domain, limit=limit)

    if not domains:
        print("\n[Pipeline] Stage 1 returned no domains. Exiting.")
        sys.exit(1)

    # ── Stage 2: Find decision-makers + emails ──────────────
    contacts = find_decision_makers(domains, limit_per_domain=3)

    if not contacts:
        print("\n[Pipeline] Stage 2 returned no contacts. Exiting.")
        sys.exit(1)

    # ── Safety Checkpoint ───────────────────────────────────
    print_summary(seed_domain, domains, contacts)

    if dry_run:
        print("\n[Pipeline] DRY RUN - emails not sent. Exiting.")
        return

    if not no_confirm:
        answer = input("\n  Proceed and send all emails? [y/N]: ").strip().lower()
        if answer != "y":
            print("\n[Pipeline] Aborted by user. No emails sent.")
            sys.exit(0)

    # ── Stage 3: Send personalised emails ──────────────────
    results = send_emails(contacts)

    # ── Final summary ───────────────────────────────────────
    print("\n" + "=" * 54)
    print("  PIPELINE COMPLETE")
    print("=" * 54)
    sent = sum(1 for r in results if r["status"] == "sent")
    failed = sum(1 for r in results if r["status"] != "sent")
    print(f"  + Sent    : {sent}")
    print(f"  x Failed  : {failed}")
    print("=" * 54)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Cold outreach pipeline — one domain in, emails out."
    )
    parser.add_argument(
        "domain",
        help="Seed company domain e.g. stripe.com",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=10,
        help="Max lookalike companies to find (default: 10)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Run all stages but skip sending emails",
    )
    parser.add_argument(
        "--no-confirm",
        action="store_true",
        help="Skip the safety checkpoint prompt",
    )

    args = parser.parse_args()

    run_pipeline(
        seed_domain=args.domain,
        limit=args.limit,
        dry_run=args.dry_run,
        no_confirm=args.no_confirm,
    )
