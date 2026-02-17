#!/usr/bin/env python3
"""
BuildSwift Auto-Build Pipeline
Generates complete websites using Anthropic Claude API.
"""

import os
import json
import requests
import argparse
import subprocess
from pathlib import Path
from datetime import datetime

ANTHROPIC_API = "https://api.anthropic.com/v1/messages"
ANTHROPIC_KEY = os.environ.get("ANTHROPIC_API_KEY")
if not ANTHROPIC_KEY:
    raise ValueError("ANTHROPIC_API_KEY environment variable not set")
OUTPUT_DIR = Path(__file__).parent.parent / "builds"
TEMPLATES_DIR = Path(__file__).parent / "templates"


def call_anthropic(prompt, max_tokens=4000):
    """Call Anthropic Claude API and return the response text."""
    resp = requests.post(ANTHROPIC_API, headers={
        "x-api-key": ANTHROPIC_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }, json={
        "model": "claude-opus-4-1",
        "max_tokens": max_tokens,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "system": "You are an expert web developer. Output ONLY code. No explanations, no markdown fences, no commentary. Just the raw HTML/CSS/JS. Ensure the HTML is complete, self-contained, and production-ready."
    }, timeout=120)
    
    data = resp.json()
    if resp.status_code != 200:
        raise Exception(f"Anthropic error: {data.get('error', {}).get('message', 'Unknown error')}")
    
    content = data["content"][0]["text"]
    usage = data.get("usage", {})
    # Anthropic pricing: $15 per 1M input tokens, $75 per 1M output tokens
    cost_input = usage.get("input_tokens", 0) * 15 / 1_000_000
    cost_output = usage.get("output_tokens", 0) * 75 / 1_000_000
    total_cost = cost_input + cost_output
    
    print(f"  Tokens: {usage.get('input_tokens', 0)} in / {usage.get('output_tokens', 0)} out | Cost: ${total_cost:.4f}")
    return content, total_cost


def clean_code(text):
    """Strip markdown fences if the model wraps code in them."""
    lines = text.strip().split('\n')
    if lines[0].startswith('```'):
        lines = lines[1:]
    if lines[-1].startswith('```'):
        lines = lines[:-1]
    return '\n'.join(lines)


def build_site(config):
    """
    Build a complete website from a config dict.
    
    config = {
        "business_name": "Joe's Pizza",
        "industry": "restaurant",
        "tagline": "Best pizza in Chicago since 1985",
        "phone": "773-555-1234",
        "address": "123 Main St, Chicago, IL 60601",
        "email": "joe@joespizza.com",
        "website": "joespizza.com",
        "colors": {"primary": "#D4380D", "dark": "#1a1a1a"},  # optional
        "services": ["Dine-in", "Takeout", "Catering", "Delivery"],
        "hours": "Mon-Sat 11am-10pm, Sun 12pm-9pm",
        "description": "Family-owned pizzeria...",
        "pages": ["home", "menu", "about", "contact"]  # optional, default single page
    }
    """
    biz = config["business_name"]
    industry = config.get("industry", "local business")
    slug = biz.lower().replace("'", "").replace(" ", "-").replace(".", "")
    build_dir = OUTPUT_DIR / slug
    build_dir.mkdir(parents=True, exist_ok=True)
    
    total_cost = 0.0
    print(f"\n{'='*60}")
    print(f"  BuildSwift — Generating site for: {biz}")
    print(f"  Industry: {industry}")
    print(f"{'='*60}\n")
    
    # Load industry template prompt if available
    template_path = TEMPLATES_DIR / f"{industry.lower().replace(' ', '-')}.txt"
    industry_hints = ""
    if template_path.exists():
        industry_hints = template_path.read_text()
    
    # --- STEP 1: Generate the main HTML page ---
    print("[1/3] Generating HTML...")
    
    colors = config.get("colors", {})
    primary = colors.get("primary", "#FF6B00")
    dark = colors.get("dark", "#0A0A0A")
    
    services_list = "\n".join(f"- {s}" for s in config.get("services", []))
    
    html_prompt = f"""Build a complete, single-file HTML website for this business:

Business: {biz}
Industry: {industry}
Tagline: {config.get('tagline', '')}
Phone: {config.get('phone', '')}
Address: {config.get('address', '')}
Email: {config.get('email', '')}
Hours: {config.get('hours', '')}
Description: {config.get('description', '')}
Services/Offerings:
{services_list}

Design requirements:
- Single HTML file with embedded CSS (no external files)
- Dark modern theme: background {dark}, primary accent {primary}
- Google Fonts: Inter (weights 400,500,600,700,800)
- Mobile-first responsive design
- Sections: Hero with CTA, About, Services/Menu, Hours/Location with Google Maps embed placeholder, Contact form, Footer
- Click-to-call button for phone number
- Click-to-email for email
- SEO meta tags (title, description, og tags)
- PageSpeed optimized: no heavy JS frameworks, minimal DOM, lazy load images
- Professional, conversion-focused design
- Footer: "© {datetime.now().year} {biz}. All rights reserved."
{industry_hints}

Output ONLY the complete HTML. No explanations."""

    html_content, cost = call_anthropic(html_prompt, max_tokens=4000)
    total_cost += cost
    html_content = clean_code(html_content)
    
    # Write HTML
    (build_dir / "index.html").write_text(html_content)
    
    # --- STEP 2: Generate sitemap ---
    print("[2/3] Generating sitemap...")
    domain = config.get("website", f"{slug}.com")
    sitemap = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>https://{domain}/</loc>
    <lastmod>{datetime.now().strftime('%Y-%m-%d')}</lastmod>
    <priority>1.0</priority>
  </url>
</urlset>"""
    (build_dir / "sitemap.xml").write_text(sitemap)
    
    # --- STEP 3: Generate robots.txt ---
    print("[3/3] Generating robots.txt...")
    robots = f"""User-agent: *
Allow: /
Sitemap: https://{domain}/sitemap.xml"""
    (build_dir / "robots.txt").write_text(robots)
    
    # --- Write build manifest ---
    manifest = {
        "business": biz,
        "industry": industry,
        "domain": domain,
        "built_at": datetime.now().isoformat(),
        "total_cost_usd": round(total_cost, 4),
        "files": ["index.html", "sitemap.xml", "robots.txt"],
        "status": "ready_for_review"
    }
    (build_dir / "manifest.json").write_text(json.dumps(manifest, indent=2))
    
    print(f"\n{'='*60}")
    print(f"  ✅ Site built: {build_dir}")
    print(f"  💰 Total cost: ${total_cost:.4f}")
    print(f"  📁 Files: index.html, sitemap.xml, robots.txt")
    print(f"{'='*60}\n")
    
    return str(build_dir), total_cost


def preview_site(build_dir):
    """Open site in browser for preview."""
    index = Path(build_dir) / "index.html"
    if index.exists():
        subprocess.run(["open", str(index)])
    else:
        print(f"No index.html found in {build_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="BuildSwift Auto-Builder")
    parser.add_argument("--config", type=str, help="Path to JSON config file")
    parser.add_argument("--preview", action="store_true", help="Open in browser after build")
    parser.add_argument("--demo", action="store_true", help="Run demo build")
    args = parser.parse_args()
    
    if args.demo:
        demo_config = {
            "business_name": "Bella's Italian Kitchen",
            "industry": "restaurant",
            "tagline": "Authentic Italian cuisine in the heart of Chicago",
            "phone": "773-555-8888",
            "address": "456 Oak Street, Chicago, IL 60614",
            "email": "info@bellasitaliankitchen.com",
            "website": "bellasitaliankitchen.com",
            "colors": {"primary": "#C41E3A", "dark": "#0A0A0A"},
            "services": ["Dine-in", "Private Events", "Catering", "Takeout", "Wine Bar"],
            "hours": "Tue-Thu 5pm-10pm, Fri-Sat 5pm-11pm, Sun 4pm-9pm",
            "description": "Family-owned since 1998. Handmade pasta, wood-fired pizza, and an award-winning wine list."
        }
        build_dir, cost = build_site(demo_config)
        if args.preview:
            preview_site(build_dir)
    elif args.config:
        with open(args.config) as f:
            config = json.load(f)
        build_dir, cost = build_site(config)
        if args.preview:
            preview_site(build_dir)
    else:
        parser.print_help()
