"""Deterministic exposure-risk scoring, now wired to the real attribution layer."""

import json
from collections import defaultdict

from app.backend.pipeline.attribution import determine_attribution

RISKY_PORTS = {
    23: "Telnet (unencrypted remote access)",
    3389: "RDP (Windows Remote Desktop)",
    5900: "VNC (remote desktop)",
    6379: "Redis (often no auth by default)",
    27017: "MongoDB (often no auth by default)",
    3306: "MySQL exposed to internet",
    5432: "PostgreSQL exposed to internet",
    445: "SMB (Windows file sharing)",
    21: "FTP (unencrypted file transfer)",
    161: "SNMP (often default community strings)",
    502: "Modbus (industrial control system)",
    102: "S7 (Siemens industrial control)",
    1433: "MSSQL exposed to internet",
    5984: "CouchDB (often no auth by default)",
    9200: "Elasticsearch (often no auth by default)",
    2375: "Docker API (unauthenticated = full host takeover risk)",
}

IOT_CAMERA_PRODUCTS = ["hikvision", "dahua", "ip camera"]

SEVERITY_WEIGHTS = {
    "compromised_or_c2": 100,
    "vulns_present": 40,
    "risky_port": 25,
    "eol_product": 20,
    "self_signed": 10,
    "iot_camera": 15,
    "open_dir": 10,
}

# Attribution confidence also scales the final score
CONFIDENCE_MULTIPLIER = {
    "HIGH": 1.0,
    "MEDIUM": 0.7,
}


def score_signals(rec: dict) -> tuple[int, list[str]]:
    """Pure technical scoring -- no attribution logic here."""
    tags = rec.get("tags") or []
    findings = []
    score = 0

    if "compromised" in tags or "c2" in tags:
        score += SEVERITY_WEIGHTS["compromised_or_c2"]
        findings.append("Host shows signs of compromise or active C2 activity")

    vulns = rec.get("vulns")
    if vulns and len(vulns) > 0:
        score += SEVERITY_WEIGHTS["vulns_present"]
        cve_list = list(vulns.keys()) if isinstance(vulns, dict) else vulns
        findings.append(f"Known CVE(s) present: {', '.join(cve_list[:3])}")

    port = rec.get("port")
    if port in RISKY_PORTS:
        score += SEVERITY_WEIGHTS["risky_port"]
        findings.append(f"Risky service exposed on port {port}: {RISKY_PORTS[port]}")

    if "eol-product" in tags:
        score += SEVERITY_WEIGHTS["eol_product"]
        product = rec.get("product") or "software"
        version = rec.get("version") or ""
        findings.append(f"End-of-life software detected: {product} {version}".strip())

    if "self-signed" in tags:
        score += SEVERITY_WEIGHTS["self_signed"]
        findings.append("Self-signed TLS certificate (broken cert hygiene)")

    product_lower = (rec.get("product") or "").lower()
    if any(cam in product_lower for cam in IOT_CAMERA_PRODUCTS):
        score += SEVERITY_WEIGHTS["iot_camera"]
        findings.append(f"IoT/camera device exposed: {rec.get('product')}")

    if "open-dir" in tags:
        score += SEVERITY_WEIGHTS["open_dir"]
        findings.append("Open directory listing (information disclosure)")

    return score, findings


def score_record(rec: dict, mock: bool = None) -> dict | None:
    """Combines attribution + technical scoring for one raw record."""
    # Score first (pure rules, free)
    raw_score, findings = score_signals(rec)
    if raw_score == 0:
        return None  # nothing security-relevant to report

    attribution = determine_attribution(rec, mock=mock)
    if attribution is None:
        return None

    adjusted_score = round(raw_score * CONFIDENCE_MULTIPLIER[attribution["attribution_confidence"]])

    return {
        **attribution,
        "ip": rec.get("ip_str"),
        "port": rec.get("port"),
        "product": rec.get("product"),
        "country": (rec.get("location") or {}).get("country_name"),
        "raw_score": raw_score,
        "adjusted_score": adjusted_score,
        "findings": findings,
        "tags": rec.get("tags") or [],
    }


def aggregate_entities(scored_records: list[dict]) -> list[dict]:
    """Roll up individual scored records into one entity."""
    entities = defaultdict(lambda: {
        "score": 0,
        "asset_count": 0,
        "findings": [],
        "orgs": set(),
        "countries": set(),
        "sample_ips": set(),
        "confidences_seen": set(),
        "provider_roles_seen": set(),
        "attribution_reasons": set(),
    })

    for r in scored_records:
        key = r["entity_key"]
        e = entities[key]
        e["score"] += r["adjusted_score"]
        e["asset_count"] += 1
        e["findings"].extend(r["findings"])
        e["orgs"].add(r["org"])
        e["confidences_seen"].add(r["attribution_confidence"])
        e["provider_roles_seen"].add(r["provider_role"])
        e["attribution_reasons"].add(r["attribution_reason"])
        if r["country"]:
            e["countries"].add(r["country"])
        if r["ip"]:
            e["sample_ips"].add(r["ip"])

    out = []
    for key, e in entities.items():
        # entity-level confidence = the highest confidence seen across its assets
        entity_confidence = "HIGH" if "HIGH" in e["confidences_seen"] else "MEDIUM"
        out.append({
            "entity_key": key,
            "attribution_confidence": entity_confidence,
            "provider_roles": list(e["provider_roles_seen"]),
            "attribution_reasons": list(e["attribution_reasons"])[:2],
            "total_score": e["score"],
            "asset_count": e["asset_count"],
            "orgs": list(e["orgs"]),
            "countries": list(e["countries"]),
            "sample_ips": list(e["sample_ips"])[:5],
            "top_findings": list(dict.fromkeys(e["findings"]))[:8],
        })
    return sorted(out, key=lambda x: -x["total_score"])


if __name__ == "__main__":
    scored = []
    with open("/mnt/user-data/uploads/sample.jsonl") as f:
        for i, line in enumerate(f):
            rec = json.loads(line)
            s = score_record(rec)  # mock=None -> auto-mock since no API key present
            if s:
                scored.append(s)
            if (i + 1) % 10000 == 0:
                print(f"...processed {i+1} records, {len(scored)} scored so far")

    print(f"\nRecords with meaningful signal + attribution: {len(scored)} / 30000")

    entities = aggregate_entities(scored)
    print(f"Distinct attributable entities: {len(entities)}")

    high_conf = [e for e in entities if e["attribution_confidence"] == "HIGH"]
    med_conf = [e for e in entities if e["attribution_confidence"] == "MEDIUM"]
    print(f"  HIGH confidence: {len(high_conf)}")
    print(f"  MEDIUM confidence: {len(med_conf)}")

    print("\n=== TOP 15 HIGHEST-PRIORITY PROSPECTS ===")
    for e in entities[:15]:
        print(f"\n[{e['total_score']} pts | {e['attribution_confidence']} confidence] {e['entity_key']}")
        print(f"  provider_role: {e['provider_roles']} | assets: {e['asset_count']} | countries: {e['countries']}")
        print(f"  attribution: {e['attribution_reasons'][0]}")
        for f in e["top_findings"][:4]:
            print(f"    - {f}")
