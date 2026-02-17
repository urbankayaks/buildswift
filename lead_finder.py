#!/usr/bin/env python3
"""
BuildSwift Lead Finder
Finds local businesses with bad/no websites for outreach.
Usage: python lead_finder.py "plumbers in Chicago" --count 20
Output: CSV + JSON files in leads/ directory
"""

import json, csv, os, sys, re, time, argparse
from datetime import datetime
from pathlib import Path

LEADS_DIR = Path(__file__).parent / "leads"
LEADS_DIR.mkdir(exist_ok=True)

def extract_emails_from_text(text):
    """Extract email addresses from text."""
    pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    return list(set(re.findall(pattern, text)))

def extract_domain(url):
    """Extract domain from URL."""
    if not url:
        return ""
    url = url.replace("https://", "").replace("http://", "").split("/")[0]
    return url

def score_website_quality(url, title="", snippet=""):
    """Score a business's web presence (lower = worse = better lead)."""
    score = 50  # neutral
    issues = []

    if not url or url == "":
        score = 0
        issues.append("No website found")
        return score, issues

    domain = extract_domain(url)

    # Red flags for bad sites
    if any(x in domain for x in ['wix.com', 'weebly.com', 'godaddy.com', 'squarespace.com']):
        score -= 15
        issues.append("Using basic website builder")
    if any(x in domain for x in ['facebook.com', 'yelp.com', 'yellowpages.com']):
        score -= 25
        issues.append("No real website — using social/directory page")
    if 'wordpress.com' in domain:  # .com = free hosted
        score -= 10
        issues.append("Free WordPress.com site")

    # Snippet analysis
    snippet_lower = (snippet or "").lower()
    if any(x in snippet_lower for x in ['under construction', 'coming soon', 'parked']):
        score -= 30
        issues.append("Site under construction or parked")
    if any(x in snippet_lower for x in ['flash', 'silverlight']):
        score -= 25
        issues.append("Uses outdated technology")

    if not issues:
        issues.append("Has a website — may need review")

    return max(0, min(100, score)), issues


def format_lead_row(lead):
    """Format a lead for display."""
    score_bar = "🔴" if lead['score'] < 20 else "🟡" if lead['score'] < 40 else "🟢"
    return f"{score_bar} {lead['business']} | {lead['url'] or 'NO SITE'} | Score: {lead['score']}/100 | {', '.join(lead['issues'])}"


def save_leads(leads, query):
    """Save leads to CSV and JSON."""
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r'[^a-z0-9]+', '_', query.lower()).strip('_')

    csv_path = LEADS_DIR / f"{slug}_{ts}.csv"
    json_path = LEADS_DIR / f"{slug}_{ts}.json"

    # CSV
    with open(csv_path, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['business', 'url', 'domain', 'email', 'location', 'industry', 'score', 'issues', 'snippet'])
        writer.writeheader()
        for lead in leads:
            row = {**lead, 'issues': '; '.join(lead['issues']), 'email': '; '.join(lead.get('emails', []))}
            writer.writerow(row)

    # JSON
    with open(json_path, 'w') as f:
        json.dump({'query': query, 'timestamp': ts, 'count': len(leads), 'leads': leads}, f, indent=2)

    return csv_path, json_path


def print_leads_table(leads):
    """Print leads in a readable format."""
    print("\n" + "="*80)
    print(f"  Found {len(leads)} leads — sorted by opportunity (worst site = best lead)")
    print("="*80)

    for i, lead in enumerate(leads, 1):
        score = lead['score']
        icon = "🔴" if score < 20 else "🟡" if score < 40 else "🟢"
        print(f"\n{i}. {icon} {lead['business']}")
        print(f"   URL: {lead['url'] or 'NO WEBSITE'}")
        if lead.get('emails'):
            print(f"   Email: {', '.join(lead['emails'])}")
        if lead.get('location'):
            print(f"   Location: {lead['location']}")
        print(f"   Score: {score}/100 — {', '.join(lead['issues'])}")
        if lead.get('snippet'):
            print(f"   Snippet: {lead['snippet'][:120]}...")

    print("\n" + "="*80)
    hot = [l for l in leads if l['score'] < 25]
    warm = [l for l in leads if 25 <= l['score'] < 45]
    print(f"  🔴 Hot leads (score <25): {len(hot)}")
    print(f"  🟡 Warm leads (score 25-44): {len(warm)}")
    print(f"  🟢 Others: {len(leads) - len(hot) - len(warm)}")
    print("="*80)


# Main entry — designed to be called by agents via exec
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find local business leads with bad websites")
    parser.add_argument("query", help='Search query, e.g. "plumbers in Chicago"')
    parser.add_argument("--count", type=int, default=10, help="Number of results to find")
    parser.add_argument("--output", choices=["table", "json", "csv"], default="table")
    args = parser.parse_args()

    print(f"\n🔍 Searching: {args.query}")
    print("   (Use with OpenClaw web_search tool for best results)")
    print(f"   Run: Reese or Silas should call web_search('{args.query} website') and pipe results through this scorer.\n")

    # This script provides the scoring/formatting framework.
    # Actual search should be done via web_search tool, then results fed in.
    # For standalone use, it reads from stdin (JSON array of {title, url, snippet}).

    if not sys.stdin.isatty():
        data = json.load(sys.stdin)
        leads = []
        for item in data:
            score, issues = score_website_quality(item.get('url', ''), item.get('title', ''), item.get('snippet', ''))
            leads.append({
                'business': item.get('title', 'Unknown'),
                'url': item.get('url', ''),
                'domain': extract_domain(item.get('url', '')),
                'emails': extract_emails_from_text(item.get('snippet', '') + ' ' + item.get('title', '')),
                'location': item.get('location', ''),
                'industry': '',
                'score': score,
                'issues': issues,
                'snippet': item.get('snippet', '')
            })

        leads.sort(key=lambda x: x['score'])
        print_leads_table(leads)
        csv_path, json_path = save_leads(leads, args.query)
        print(f"\n📁 Saved: {csv_path}")
        print(f"📁 Saved: {json_path}")
    else:
        print("💡 Tip: Pipe search results as JSON to score them:")
        print(f'   echo \'[{{"title":"Biz","url":"http://example.com","snippet":"old site"}}]\' | python {__file__} "{args.query}"')
        print(f"\n   Or have Reese/Silas use web_search + this tool together.")
