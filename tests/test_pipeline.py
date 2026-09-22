"""Unit tests for the scoring and attribution rules. No AI or database calls are made."""

from app.backend.pipeline import attribution, scoring


def rec(**over):
    base = {"ip_str": "203.0.113.7", "port": 443, "org": "Acme Ltd", "domains": ["acme.com"], "hostnames": ["www.acme.com"],
            "tags": [], "product": "nginx", "location": {"country_name": "Germany"}}
    base.update(over)
    return base


def fake_classifier(classification, confidence=0.9):
    return lambda org, **kwargs: {"classification": classification, "confidence": confidence}


# ---- scoring rules ----

def test_no_findings_scores_zero():
    assert scoring.score_signals(rec()) == (0, [])


def test_cve_scores_forty():
    score, findings = scoring.score_signals(rec(vulns={"CVE-2023-44487": {}}))
    assert score == 40 and "CVE-2023-44487" in findings[0]


def test_points_add_up():
    r = rec(port=3389, tags=["eol-product", "self-signed"], vulns={"CVE-2020-1": {}})
    score, _ = scoring.score_signals(r)
    assert score == 40 + 25 + 20 + 10


def test_compromise_is_worth_100():
    assert scoring.score_signals(rec(tags=["compromised"]))[0] == 100


def test_medium_confidence_counts_seventy_percent(monkeypatch):
    monkeypatch.setattr(attribution, "classify_org", fake_classifier("end_business"))
    r = rec(domains=[], hostnames=[], vulns={"CVE-2020-1": {}})
    scored = scoring.score_record(r)
    assert scored["attribution_confidence"] == "MEDIUM" and scored["adjusted_score"] == 28


# ---- attribution rules ----

def test_honeypot_is_never_attributed():
    assert attribution.determine_attribution(rec(tags=["honeypot"])) is None


def test_business_domain_gives_high_confidence(monkeypatch):
    monkeypatch.setattr(attribution, "classify_org", fake_classifier("infra"))
    result = attribution.determine_attribution(rec())
    assert result["entity_key"] == "acme.com" and result["attribution_confidence"] == "HIGH"


def test_generated_hostname_is_detected():
    assert attribution._is_generated_hostname("syn-096-010-102-154.biz.spectrum.com", "96.10.102.154")
    assert attribution._is_generated_hostname("235.233.71.198.host.secureserver.net", "198.71.233.235")
    assert not attribution._is_generated_hostname("www.ourminds.in", "112.133.202.45")


def test_isp_own_domain_is_not_a_prospect(monkeypatch):
    monkeypatch.setattr(attribution, "classify_org", fake_classifier("infra"))
    r = rec(ip_str="96.10.102.154", org="Charter Communications", domains=["spectrum.com"],
            hostnames=["syn-096-010-102-154.biz.spectrum.com"])
    assert attribution.determine_attribution(r) is None


def test_customer_domain_on_provider_machine_is_kept():
    domain = attribution._get_attributable_domain(
        ["secureserver.net", "biomedix.com"],
        ["235.233.71.198.host.secureserver.net", "store.biomedix.com"],
        "198.71.233.235",
    )
    assert domain == "biomedix.com"


def test_no_domain_uses_org_classification(monkeypatch):
    r = rec(domains=[], hostnames=[])
    monkeypatch.setattr(attribution, "classify_org", fake_classifier("infra"))
    assert attribution.determine_attribution(r) is None
    monkeypatch.setattr(attribution, "classify_org", fake_classifier("end_business", 0.5))
    assert attribution.determine_attribution(r) is None  # below the 0.60 threshold
    monkeypatch.setattr(attribution, "classify_org", fake_classifier("end_business", 0.8))
    assert attribution.determine_attribution(r)["attribution_confidence"] == "MEDIUM"


def test_infrastructure_domains_are_ignored():
    assert attribution._get_attributable_domain(["ec2-1-2-3-4.compute-1.amazonaws.com"]) is None
    assert attribution._looks_like_ip("5.9.10.76.")


# ---- roll-up ----

def test_entities_are_sorted_by_score():
    rows = [
        {"entity_key": "a.com", "adjusted_score": 40, "attribution_confidence": "HIGH", "provider_role": "x",
         "attribution_reason": "r", "org": "A", "country": "US", "ip": "1.1.1.1", "findings": ["f1"]},
        {"entity_key": "b.com", "adjusted_score": 100, "attribution_confidence": "MEDIUM", "provider_role": "x",
         "attribution_reason": "r", "org": "B", "country": "DE", "ip": "2.2.2.2", "findings": ["f2"]},
        {"entity_key": "b.com", "adjusted_score": 40, "attribution_confidence": "MEDIUM", "provider_role": "x",
         "attribution_reason": "r", "org": "B", "country": "DE", "ip": "2.2.2.3", "findings": ["f2"]},
    ]
    out = scoring.aggregate_entities(rows)
    assert [e["entity_key"] for e in out] == ["b.com", "a.com"]
    assert out[0]["total_score"] == 140 and out[0]["asset_count"] == 2
