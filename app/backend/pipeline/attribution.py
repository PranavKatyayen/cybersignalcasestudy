"""Attribution layer: decides whether a scanned asset can be attributed to a real business."""

from app.backend.skills.org_classification import classify_org

import re

INFRA_DOMAIN_SUFFIXES = [
    "googleusercontent.com", "amazonaws.com", "cloudapp.azure.com",
    "azure.com", "akamaitechnologies.com", "akamaiedge.net",
    "fastly.net", "cloudflare.com", "cloudflare.net", "incapdns.net",
    "digitalocean.com", "linodeusercontent.com", "vultrusercontent.com",
    "hetzner.com", "your-server.de", "ovh.net", "scaleway.com",
    "flyio.net", "oraclecloud.com", "aliyuncs.com", "alibaba-inc.com",
    "hinet.net", "btcentralplus.com", "awsglobalaccelerator.com",
    "pbiaas.com", "contaboserver.net", "sakura.ne.jp", "ptrcloud.net",
    "hwclouds-dns.com", "t-ipconnect.de", "digitaloceanspaces.com",
    "gmocloud.com", "fastvps-server.com", "dattaweb.com", "vps-default-host.net", "linode.com",
    "webhostbox.net", "netsolhost.com", "unifiedlayer.com", "secureserver.net",
]

RESIDENTIAL_ISP_SUFFIXES = [
    "fibertel.com.ar", "cablelink.at",
]

# Org-classification confidence below this is treated the same as "no attribution"
MIN_ORG_CLASSIFICATION_CONFIDENCE_FOR_MEDIUM = 0.60


_IP_LIKE_PATTERN = re.compile(r"^(\d{1,3}\.){3,4}\d{0,3}\.?$")


def _looks_like_ip(domain: str) -> bool:
    """Some 'domains' entries in this dataset are actually reverse-DNS IP strings."""
    return bool(_IP_LIKE_PATTERN.match(domain))


def _is_generated_hostname(host: str, ip: str) -> bool:
    """ISP and hosting providers name machines after their IP (e.g. 70-37-215-251.nntc.net)."""
    octets = [int(x) for x in (ip or "").split(".") if x.isdigit()]
    if len(octets) != 4:
        return False
    nums = [int(x) for x in re.findall(r"\d+", host)]
    return any(nums[i:i + 4] in (octets, octets[::-1]) for i in range(len(nums) - 3))


def _get_attributable_domain(domains, hostnames=None, ip=None):
    """Return the first domain that is not infrastructure, a bare IP string or a provider-generated name."""
    excluded = INFRA_DOMAIN_SUFFIXES + RESIDENTIAL_ISP_SUFFIXES
    for d in (domains or []):
        if _looks_like_ip(d):
            continue
        if any(d.endswith(suf) or d == suf for suf in excluded):
            continue
        under = [h for h in (hostnames or []) if h == d or h.endswith("." + d)]
        if under and all(_is_generated_hostname(h, ip) for h in under):
            continue  # only seen as the provider's own machine name, not a customer's site
        return d
    return None


def _domain_matches_org(domain: str, org: str) -> bool:
    """Crude but effective: check whether the domain's root name appears in the org string."""
    if not domain or not org:
        return False
    root = domain.split(".")[0].lower()
    return len(root) >= 4 and root in org.lower().replace(" ", "").replace(",", "")


def determine_attribution(rec: dict, mock: bool = None) -> dict | None:
    """Returns None if the record cannot be attributed to a real business at all."""
    tags = rec.get("tags") or []
    if "honeypot" in tags:
        return None  # decoy system, not a real business at all

    org = rec.get("org") or ""
    domains = rec.get("domains") or []
    attributable_domain = _get_attributable_domain(domains, rec.get("hostnames"), rec.get("ip_str"))

    if attributable_domain:
        # We have direct evidence: a real, non-infra domain pointed at this asset
        org_result = classify_org(org, mock=mock, allow_llm=False) if org else {"classification": "infra", "confidence": 1.0}
        if _domain_matches_org(attributable_domain, org):
            # The infra provider's own domain matching its own org name
            provider_role = "self_hosted_or_direct"
            reason = f"Business domain '{attributable_domain}' observed, operating its own named infrastructure ({org})"
        elif org_result["classification"] == "unknown":
            provider_role = "unknown_hosting"
            reason = f"Business domain '{attributable_domain}' observed; hosting provider ({org}) not classified"
        elif org_result["classification"] == "infra":
            provider_role = "customer_hosted"
            reason = f"Business domain '{attributable_domain}' observed, hosted on {org or 'third-party'} infrastructure"
        else:
            provider_role = "self_hosted_or_direct"
            reason = f"Business domain '{attributable_domain}' observed, operating its own named infrastructure ({org})"
        return {
            "entity_key": attributable_domain,
            "attribution_confidence": "HIGH",
            "provider_role": provider_role,
            "attribution_reason": reason,
            "org": org,
            "domain": attributable_domain,
        }

    # No usable domain
    if not org:
        return None  # nothing to attribute to at all

    org_result = classify_org(org, mock=mock)
    if org_result["classification"] == "end_business" and org_result["confidence"] >= MIN_ORG_CLASSIFICATION_CONFIDENCE_FOR_MEDIUM:
        return {
            "entity_key": org,
            "attribution_confidence": "MEDIUM",
            "provider_role": "unknown_hosting",
            "attribution_reason": f"No business domain observed; attributed by organization name only (classifier confidence {org_result['confidence']:.2f})",
            "org": org,
            "domain": None,
        }

    # Either classified as infra, or end_business with confidence below our threshold
    return None
