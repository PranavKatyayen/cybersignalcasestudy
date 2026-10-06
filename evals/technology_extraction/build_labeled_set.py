#!/usr/bin/env python3
"""Builds evals/technology_extraction/labeled_set.jsonl from the raw scan.

Each example is a real scan record plus the technologies a person reading the banner, headers and
hostnames would name. The labels were written by reading the raw banner text, not the structured
fields the rules use, but they use the rules' technology names so they can be compared. They are a
first pass that the owner should re-check. Only whitelisted banner header lines are kept, because
raw banners can carry cookie and session values.

Usage:
python evals/technology_extraction/build_labeled_set.py --input sample.jsonl
"""

import argparse
import json
import re
from pathlib import Path

OUT = Path(__file__).with_name("labeled_set.jsonl")
KEEP_HEADERS = re.compile(r"^(server|x-powered-by|x-aspnet-version|via|x-generator):", re.I)

# record line number in sample.jsonl -> technologies a person would name (technology, version or None)
LABELS = {
    25863: [("Nginx", None)],
    29011: [("Cloudflare", None)],
    18254: [("Cloudflare", None)],
    12408: [],
    113: [("VPN endpoint", None)],
    6943: [("Apache HTTP Server", None)],
    4270: [("AWS", None), ("Amazon EC2", None), ("Kestrel", None), ("ASP.NET", None)],
    21995: [("VPN endpoint", None)],
    14422: [("Linode", None), ("OpenResty", None), ("Nginx", None)],
    19977: [("AWS", None), ("Amazon EC2", None), ("Windows", None), ("Windows Server", None), ("Microsoft IIS", "10.0"), ("ASP.NET", None)],
    15401: [("Nginx", None), ("PHP", "7.4.33")],
    5363: [("Cloudflare", None)],
    11748: [("Nginx", "1.22.1")],
    23053: [("Cloudflare", None), ("PHP", "7.4.33"), ("WordPress", None)],
    27220: [("AWS", None), ("Amazon CloudFront", None), ("Apache HTTP Server", None)],
    28658: [("AWS", None), ("AWS Global Accelerator", None)],
    11061: [("Akamai", None)],
    12601: [],
    26096: [("AWS", None), ("AWS Global Accelerator", None), ("OpenResty", None), ("Nginx", None)],
    25621: [("lighttpd", "1.4.54")],
    21213: [("Cloudflare", None)],
    4083: [("AWS", None), ("Amazon EC2", None)],
    20751: [("Cloudflare", None)],
    19252: [],
    23231: [("AWS", None), ("Amazon EC2", None), ("Windows", None), ("Windows Server", None), ("Microsoft IIS", "10.0"), ("ASP.NET", None)],
    20877: [("AWS", None), ("AWS Global Accelerator", None), ("Sprinklr", None)],
    20720: [("Cloudflare", None)],
    11892: [("Microsoft Azure", None), ("OpenResty", "1.15.8.1"), ("Nginx", None)],
    27470: [],
    5271: [("Stormshield Network Security", None), ("jQuery", None), ("Bootstrap", None)],
    19599: [("Apache HTTP Server", None), ("jQuery", None), ("BootstrapCDN", None), ("Bootstrap", "3.3.6"), ("jQuery CDN", None)],
    5143: [("AWS", None), ("Amazon EC2", None), ("Windows", None), ("Windows Server", None), ("Microsoft IIS", "10.0"), ("ASP.NET", "4.0.30319")],
    18670: [("Postfix", None)],
    12712: [("cPanel & WHM", None)],
    1802: [("OpenSSH", "9.2p1"), ("Debian", None), ("Linux", None)],
    12774: [("Google Cloud", None), ("Apache HTTP Server", "2.4.41"), ("Ubuntu", None), ("jQuery", None), ("Google Maps", None),
            ("FancyBox", None), ("Bootstrap", None), ("Stripe", None)],
    28160: [("MikroTik", None)],
    23856: [("Pantheon", None), ("Varnish", None), ("PHP", None), ("Fastly", None), ("Nginx", None), ("MariaDB", None)],
}

FIELDS = ["ip_str", "port", "hostnames", "domains", "os", "cloud", "tags", "product", "version", "cpe23"]


def trimmed(rec: dict) -> dict:
    out = {k: rec[k] for k in FIELDS if rec.get(k) not in (None, [], {})}
    http = rec.get("http") if isinstance(rec.get("http"), dict) else {}
    keep = {k: http[k] for k in ("server", "components") if http.get(k)}
    if keep:
        out["http"] = keep
    lines = [ln.strip() for ln in (rec.get("data") or "").splitlines() if KEEP_HEADERS.match(ln.strip())]
    if lines:
        out["data"] = "\n".join(line[:160] for line in lines)
    return out


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    args = parser.parse_args()
    wanted, found = set(LABELS), {}
    with open(args.input, encoding="utf-8") as f:
        for i, line in enumerate(f):
            if i in wanted:
                found[i] = json.loads(line)
    with open(OUT, "w", encoding="utf-8") as out:
        for i in sorted(found):
            expected = [{"technology": t, "version": v} for t, v in LABELS[i]]
            out.write(json.dumps({"id": i, "expected": expected, "record": trimmed(found[i])}, ensure_ascii=False) + "\n")
    print(f"Wrote {len(found)} labelled records to {OUT}")


if __name__ == "__main__":
    main()
