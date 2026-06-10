# Cold Outreach Pipeline

A fully automated tool that takes one company name as input and sends personalised cold emails to decision-makers at similar companies — no manual work required.

```
python main.py stripe.com
```

---

## What This Project Does

Most people doing cold outreach spend hours manually searching for companies, finding the right person to contact, tracking down their email, and then writing and sending individual emails. This tool automates all of that in one command.

You give it one company — for example, Stripe — and it automatically:

1. Finds 5 to 10 similar companies in the same space
2. Identifies the CEO, CTO, VP, Director-level people at each of those companies
3. Gets their verified work email addresses
4. Sends each of them a personalised cold email — addressed to them by name, mentioning their company and their role

The entire process runs in under 2 minutes and requires zero manual steps after you hit enter.

---

## How It Works (The Three Stages)

```
You enter:   stripe.com
                |
                v
         +--------------+
         |   Stage 1    |   Apollo.io
         |   Find       |   Looks up companies similar to Stripe
         |   companies  |   Returns a list of domains
         +--------------+
                |
          list of domains
                |
                v
         +--------------+
         |   Stage 2    |   Prospeo
         |   Find       |   For each company, finds C-suite / VP people
         |   people     |   and gets their verified work email
         +--------------+
                |
          list of contacts (name, title, email)
                |
                v
       +------------------+
       |  SAFETY CHECK    |   Shows you the full list before anything sends
       |  (you confirm)   |   Type y to proceed, anything else to cancel
       +------------------+
                |
                v
         +--------------+
         |   Stage 3    |   Brevo
         |   Send       |   Sends a personalised email to each person
         |   emails     |   from jayant@jayantworks.xyz
         +--------------+
```

### Stage 1 — Apollo.io

Apollo is a B2B data platform with a database of millions of companies. The pipeline first enriches the seed company (e.g. Stripe) to understand its industry and company size, then searches Apollo for other companies with matching attributes. It returns a list of similar company domains.

### Stage 2 — Prospeo

Prospeo is an email finding and enrichment tool. For each domain from Stage 1, the pipeline searches for C-suite and VP level people (CEO, CTO, Director, Head of, Founder, Vice President) and then fetches their verified work email. Only people with confirmed emails make it through.

### Stage 3 — Brevo

Brevo is a transactional email platform. Each contact gets a personalised email — their first name in the greeting, their company mentioned in the body, their job title referenced naturally. The emails go out from your verified domain `jayantworks.xyz`.

---

## Setup

### 1. Install dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure API keys
The `.env` file holds all credentials:
```
APOLLO_API_KEY=your_key
PROSPEO_API_KEY=your_key
BREVO_API_KEY=your_key
SENDER_EMAIL=jayant@jayantworks.xyz
SENDER_NAME=Jayant Raj
```

### 3. Verify your sending domain in Brevo
- Go to app.brevo.com -> Settings -> Senders & IPs -> Domains
- Add `jayantworks.xyz` and follow the DNS verification steps
- Without this, Stage 3 will not deliver emails

---

## How to Run

### Safe dry run — see everything, send nothing
```bash
python main.py stripe.com --limit 5 --dry-run
```

### Live run — review contacts, then confirm to send
```bash
python main.py stripe.com --limit 5
```
The safety checkpoint shows every contact before anything is sent. Type `y` to confirm.

### Auto-confirm (skip the prompt)
```bash
python main.py stripe.com --limit 5 --no-confirm
```

---

## Project Structure

```
outreach-pipeline/
├── main.py            # Orchestrator — run this
├── stage1_apollo.py   # Stage 1: find lookalike companies via Apollo
├── stage2_prospeo.py  # Stage 2: find decision-makers + emails via Prospeo
├── stage3_brevo.py    # Stage 3: send personalised emails via Brevo
├── .env               # API keys (never commit this file)
├── requirements.txt   # Python dependencies
└── README.md
```

---

## Customising the Email

Open `stage3_brevo.py` and edit the `compose_email()` function. The subject line and email body are fully yours to change — the pipeline just fires whatever you put there.

---

## Free Plan Limits

| Tool    | Free Limit                         |
|---------|------------------------------------|
| Apollo  | 75 credits/month                   |
| Prospeo | 50 searches/day, 50 enrichments/day |
| Brevo   | 300 emails/day                     |
