"""Attribution layer: decides whether a scanned asset can be attributed to a real business."""

import re

from app.backend.skills.org_classification import classify_org

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
    "leaseweb.com", "pebblehost.com", "nazwa.pl", "ovh.ca", "ovh.com", "he.net",
]

RESIDENTIAL_ISP_SUFFIXES = [
    "fibertel.com.ar", "cablelink.at",
]

# Org-classification confidence below this is treated the same as "no attribution"
MIN_ORG_CLASSIFICATION_CONFIDENCE_FOR_MEDIUM = 0.60

# Names that clearly describe a hosting business. Used to spot a provider's own website.
HOSTING_NAME = re.compile(
    r"(hosting|\w*host\b|data ?cent(?:er|re)|colocation|\bcolo\b|\bvps\b|dedicated server|\bservers?\b|\bcloud\b)", re.I)
# Carriers and ISPs. Only used when an organization is the whole evidence (no domain at all).
CARRIER_NAME = re.compile(
    r"(telecom|telekom|telefon|comunicaciones|communications|broadband|internet service|\bisp\b|\w*transit\b|"
    r"backbone|\bcarrier\b|\bcable\b|\bfib(?:er|re)\b|\bnetwork for\b)", re.I)

_IP_LIKE_PATTERN = re.compile(r"^(\d{1,3}\.){3,4}\d{0,3}\.?$")
_TLD = re.compile(r"^([a-z]{2,24}|xn--[a-z0-9-]{2,40})$")


def _looks_like_ip(domain: str) -> bool:
    """Some 'domains' entries in this dataset are actually reverse-DNS IP strings."""
    return bool(_IP_LIKE_PATTERN.match(domain))


def _is_valid_domain(domain: str) -> bool:
    """Rejects fragments such as 'adsl.', 'home.' or 'localhost.' that appear as 'domains'."""
    d = (domain or "").strip().lower().rstrip(".")
    if d == "localhost" or "." not in d:
        return False
    labels = d.split(".")
    return all(labels) and bool(_TLD.match(labels[-1]))


def _is_generated_hostname(host: str, ip: str) -> bool:
    """ISP and hosting providers name machines after the IP (e.g. 70-37-215-251.nntc.net)."""
    octets = [int(x) for x in (ip or "").split(".") if x.isdigit()]
    if len(octets) != 4:
        return False
    nums = [int(x) for x in re.findall(r"\d+", host)]
    if any(nums[i:i + 4] in (octets, octets[::-1]) for i in range(len(nums) - 3)):
        return True
    # some providers only embed two octets (customer-TOLU-PUBLIC-CGN-32-12.megared.net.mx)
    pairs = {(octets[0], octets[1]), (octets[1], octets[0]), (octets[2], octets[3]), (octets[3], octets[2])}
    return any((nums[i], nums[i + 1]) in pairs and max(nums[i], nums[i + 1]) >= 10 for i in range(len(nums) - 1))


def _alnum(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (text or "").lower())


def _domain_matches_org(domain: str, org: str) -> bool:
    """True when the domain's name appears in the organization name (the provider hosts itself)."""
    if not domain or not org:
        return False
    root = _alnum(domain.split(".")[0])
    return len(root) >= 3 and root in _alnum(org)


def _is_providers_own_domain(domain: str, org: str, isp: str) -> bool:
    """A domain named after a hosting business that operates the IP space is the provider's own site."""
    for name in (org, isp):
        if _domain_matches_org(domain, name) and HOSTING_NAME.search(name or ""):
            return True
    return False


def _get_attributable_domain(domains, hostnames=None, ip=None, org=None, isp=None):
    """Return the first domain that is a real business site, not infrastructure or a provider-generated name."""
    excluded = INFRA_DOMAIN_SUFFIXES + RESIDENTIAL_ISP_SUFFIXES
    for raw in (domains or []):
        d = raw.strip().lower().rstrip(".")
        if _looks_like_ip(raw) or not _is_valid_domain(d):
            continue
        if any(d.endswith(suf) or d == suf for suf in excluded):
            continue
        under = [h for h in (hostnames or []) if h == d or h.endswith("." + d)]
        if under and all(_is_generated_hostname(h, ip) for h in under):
            continue  # only seen as the provider's own machine name, not a customer's site
        if _is_providers_own_domain(d, org, isp):
            continue
        return d
    return None


def _on_cloud_range(rec: dict) -> bool:
    """On a cloud IP range the org field names the range holder, not the tenant."""
    cloud = rec.get("cloud")
    return isinstance(cloud, dict) and bool(cloud.get("provider"))


def is_infra_org_name(org: str) -> bool:
    """True when an organization name alone says it sells hosting or connectivity."""
    return bool(HOSTING_NAME.search(org or "") or CARRIER_NAME.search(org or ""))


def _hosting_role(rec: dict, domain: str, org: str, mock) -> tuple[str, str]:
    """Works out how the account is hosted, using the scan itself before the caches."""
    isp = rec.get("isp") or ""
    if _domain_matches_org(domain, org) or _domain_matches_org(domain, isp):
        return "self_hosted_or_direct", f"Business domain '{domain}' observed, operating its own named infrastructure ({org})"
    cloud = rec.get("cloud") if isinstance(rec.get("cloud"), dict) else {}
    provider = cloud.get("provider")
    if provider:
        return "customer_hosted", f"Business domain '{domain}' observed, hosted on {provider} cloud"
    if is_infra_org_name(org) or is_infra_org_name(isp):
        return "customer_hosted", f"Business domain '{domain}' observed, hosted on {org or isp} infrastructure"
    result = classify_org(org, mock=mock, allow_llm=False) if org else {"classification": "infra"}
    if result["classification"] == "infra":
        return "customer_hosted", f"Business domain '{domain}' observed, hosted on {org or 'third-party'} infrastructure"
    if result["classification"] == "unknown":
        return "unknown_hosting", f"Business domain '{domain}' observed; hosting provider ({org}) not classified"
    return "self_hosted_or_direct", f"Business domain '{domain}' observed, operating its own named infrastructure ({org})"


def determine_attribution(rec: dict, mock: bool = None) -> dict | None:
    """Returns None if the record cannot be attributed to a real business at all."""
    tags = rec.get("tags") or []
    if "honeypot" in tags:
        return None  # decoy system, not a real business at all

    org = rec.get("org") or ""
    domain = _get_attributable_domain(rec.get("domains"), rec.get("hostnames"), rec.get("ip_str"), org, rec.get("isp"))

    if domain:
        role, reason = _hosting_role(rec, domain, org, mock)
        return {
            "entity_key": domain,
            "attribution_confidence": "HIGH",
            "provider_role": role,
            "attribution_reason": reason,
            "org": org,
            "domain": domain,
        }

    # No usable domain
    if not org or is_infra_org_name(org) or _on_cloud_range(rec):
        return None  # nothing to attribute to, or hosting or carrier by name, or a cloud range holder

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


def attribute_without_llm(rec: dict) -> str | None:
    """Account key for a record using rules and caches only (used by technology extraction)."""
    if "honeypot" in (rec.get("tags") or []):
        return None
    org = rec.get("org") or ""
    domain = _get_attributable_domain(rec.get("domains"), rec.get("hostnames"), rec.get("ip_str"), org, rec.get("isp"))
    if domain:
        return domain
    if not org or is_infra_org_name(org) or _on_cloud_range(rec):
        return None
    result = classify_org(org, allow_llm=False)
    if result["classification"] == "end_business" and result["confidence"] >= MIN_ORG_CLASSIFICATION_CONFIDENCE_FOR_MEDIUM:
        return org
    return None
