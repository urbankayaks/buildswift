#!/usr/bin/env python3
"""
BuildSwift Lead Finder
Analyzes a website URL and generates a lead report + email draft.
Usage: python3 lead_finder.py https://example.com
       python3 lead_finder.py --batch urls.txt
"""

import sys
import json
import re
import argparse
from datetime import datetime
from pathlib import Path

LEADS_DIR = Path(__file__).parent / "leads"
LEADS_DIR.mkdir(exist_ok=True)


def analyze_website(url):
    """Analyze a website for quality issues and extract contact info."""
    import requests

    if not url.startswith('http'):
        url = 'https://' + url

    score = 0
    issues = []
    try:
        resp = requests.get(url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        }, allow_redirects=True)
        html = resp.text
        html_lower = html.lower()

        # Mobile
        if '<meta name="viewport"' not in html_lower:
            score += 3; issues.append("❌ Not mobile responsive")

        # HTTPS
        if resp.url.startswith('http://'):
            score += 2; issues.append("❌ No HTTPS (insecure)")

        # Ancient patterns
        if '<table' in html_lower and html_lower.count('<table') > 3:
            score += 3; issues.append("❌ Table-based layout (very outdated)")
        if '<marquee' in html_lower:
            score += 4; issues.append("❌ Uses <marquee> (ancient)")
        if '<frame' in html_lower or '<frameset' in html_lower:
            score += 5; issues.append("❌ Uses frames")
        if 'flash' in html_lower and ('.swf' in html_lower or 'swfobject' in html_lower):
            score += 5; issues.append("❌ Uses Flash")
        if 'comic sans' in html_lower or 'papyrus' in html_lower:
            score += 3; issues.append("❌ Comic Sans / Papyrus font")

        # Old copyright
        for m in re.finditer(r'(?:©|copyright)\s*(\d{4})', html_lower):
            yr = int(m.group(1))
            if yr < 2022:
                score += 2; issues.append(f"❌ Copyright year: {yr}")
                break

        # Speed (page size as proxy)
        if len(html) > 500_000:
            score += 1; issues.append("⚠️ Very heavy page (slow load)")

        # Under construction
        if 'under construction' in html_lower or 'coming soon' in html_lower:
            score += 2; issues.append("❌ Under construction / coming soon")

        # Builder detection
        for builder, name in [('wix.com', 'Wix'), ('squarespace', 'Squarespace'), ('weebly', 'Weebly')]:
            if builder in html_lower:
                issues.append(f"ℹ️ Built on {name}")

        # WordPress detection
        if 'wp-content' in html_lower:
            issues.append("ℹ️ WordPress site")
            # Check for default theme
            if 'flavor' not in html_lower and ('twentytwenty' in html_lower or 'flavor' in html_lower):
                score += 1; issues.append("⚠️ Default WordPress theme")

        # Extract contacts
        emails = list(set(re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', html)))
        phones = list(set(re.findall(r'\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', html)))

        # Title
        title_m = re.search(r'<title[^>]*>(.*?)</title>', html, re.I | re.DOTALL)
        title = title_m.group(1).strip()[:120] if title_m else url

        # Meta description
        desc_m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\'](.*?)["\']', html, re.I)
        description = desc_m.group(1).strip()[:200] if desc_m else ""

        return {
            "url": resp.url,
            "title": title,
            "description": description,
            "score": min(score, 10),
            "issues": issues,
            "emails": emails[:5],
            "phones": phones[:5],
            "status": resp.status_code,
            "mobile_friendly": '<meta name="viewport"' in html_lower,
            "https": resp.url.startswith('https'),
            "page_size_kb": round(len(html) / 1024),
        }

    except Exception as e:
        return {
            "url": url,
            "title": "Error",
            "description": "",
            "score": 2,
            "issues": [f"❌ Site unreachable: {str(e)[:80]}"],
            "emails": [],
            "phones": [],
            "status": 0,
            "mobile_friendly": False,
            "https": False,
            "page_size_kb": 0,
        }


def generate_email_draft(lead):
    """Generate a cold outreach email draft based on the lead analysis."""
    biz = lead['title'].split('|')[0].split('-')[0].split('—')[0].strip()
    if len(biz) > 40 or biz == lead['url']:
        biz = "your business"

    pain_points = [i for i in lead['issues'] if i.startswith('❌')]
    
    if not pain_points:
        hook = "I noticed your website could use a refresh"
    elif len(pain_points) == 1:
        hook = f"I noticed {pain_points[0].replace('❌ ', '').lower()} on your website"
    else:
        hook = f"I found {len(pain_points)} issues with your current website that are likely costing you customers"

    email = f"""Subject: Quick question about {biz}'s website

Hi,

{hook}. I specialize in rebuilding websites for local businesses — fast, affordable, and designed to actually bring in customers.

Here's what I found:
"""
    for issue in pain_points[:3]:
        email += f"  • {issue.replace('❌ ', '')}\n"

    if not lead['mobile_friendly']:
        email += "\nOver 60% of your potential customers are searching on their phones. If your site doesn't work on mobile, you're invisible to them.\n"

    email += f"""
We can have a modern, mobile-friendly website live for {biz} within 48 hours — starting at $0 down, $20/month (everything included).

Take a look at what we do: https://buildswift.co

Would you be open to a free site analysis? No obligation — just a quick report on what's working and what's not.

Best,
Cole Ashford
BuildSwift
CAshford@buildswift.co
"""
    return email.strip()


def format_report(lead):
    """Format a single lead into a readable report."""
    stars = '🔥' * min(lead['score'], 5)
    lines = [
        f"{'='*60}",
        f"LEAD REPORT: {lead['title']}",
        f"{'='*60}",
        f"URL:      {lead['url']}",
        f"Score:    {stars} ({lead['score']}/10)",
        f"Mobile:   {'✅ Yes' if lead['mobile_friendly'] else '❌ NO'}",
        f"HTTPS:    {'✅ Yes' if lead['https'] else '❌ NO'}",
        f"Size:     {lead['page_size_kb']} KB",
    ]
    if lead['emails']:
        lines.append(f"Emails:   {', '.join(lead['emails'])}")
    if lead['phones']:
        lines.append(f"Phones:   {', '.join(lead['phones'])}")
    if lead['issues']:
        lines.append(f"\nIssues found:")
        for issue in lead['issues']:
            lines.append(f"  {issue}")
    
    lines.append(f"\n--- EMAIL DRAFT ---\n")
    lines.append(generate_email_draft(lead))
    lines.append("")
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='BuildSwift Lead Analyzer')
    parser.add_argument('url', nargs='?', help='Website URL to analyze')
    parser.add_argument('--batch', '-b', help='File with URLs (one per line)')
    parser.add_argument('--json', action='store_true', help='JSON output')
    
    args = parser.parse_args()
    
    urls = []
    if args.batch:
        urls = [l.strip() for l in Path(args.batch).read_text().splitlines() if l.strip()]
    elif args.url:
        urls = [args.url]
    else:
        parser.print_help()
        return

    results = []
    for url in urls:
        print(f"Analyzing {url}...", file=sys.stderr)
        lead = analyze_website(url)
        lead['email_draft'] = generate_email_draft(lead)
        results.append(lead)

    if args.json:
        print(json.dumps(results, indent=2))
    else:
        for lead in results:
            print(format_report(lead))

    # Auto-save
    ts = datetime.now().strftime('%Y%m%d-%H%M')
    out = LEADS_DIR / f"analysis-{ts}.json"
    out.write_text(json.dumps(results, indent=2))
    print(f"\n📁 Saved: {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
