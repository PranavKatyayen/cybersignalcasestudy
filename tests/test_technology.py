"""Unit tests for technology extraction and its discovery helpers. No model or database calls are made."""

from app.backend.pipeline import attribution
from app.backend.pipeline.technology import Rules, extract, load_rules, raw_signals, unmapped
from app.backend.skills.technology_discovery import validate_decisions

RULES = Rules({
    "categories": ["Web server & proxy", "Cloud & hosting", "Operating system", "Exposed service type", "Security"],
    "ignore": {"components": ["HSTS"]},
    "seed": {
        "Nginx": {"category": "Web server & proxy", "vendor": "F5", "components": ["Nginx"], "cpe": ["f5:nginx"],
                  "products": ["nginx"], "server_headers": ["nginx"]},
        "AWS": {"category": "Cloud & hosting", "vendor": "Amazon", "cloud_providers": ["Amazon"],
                "hostname_suffixes": ["amazonaws.com"]},
        "Amazon EC2": {"category": "Cloud & hosting", "vendor": "Amazon", "cloud_services": ["Amazon:EC2"]},
        "Windows Server": {"category": "Operating system", "vendor": "Microsoft", "os_names": ["Windows Server"]},
        "Windows": {"category": "Operating system", "vendor": "Microsoft", "os_names": ["Windows"]},
        "AI service": {"category": "Exposed service type", "vendor": None, "tags": ["ai"]},
    },
    "discovered": {
        "Okta": {"category": "Security", "vendor": "Okta", "components": ["Okta"]},
    },
})


def names(hits):
    return {h["technology"] for h in hits}


def test_server_header_gives_name_and_version():
    hits = extract({"http": {"server": "nginx/1.22.1"}}, RULES)
    assert [(h["technology"], h["version"], h["source"]) for h in hits] == [("Nginx", "1.22.1", "server_header")]


def test_cpe_version_is_read_and_wildcard_is_not():
    with_version = extract({"cpe23": ["cpe:2.3:a:f5:nginx:1.18.0:*:*:*"]}, RULES)
    without = extract({"cpe23": ["cpe:2.3:a:f5:nginx:*:*:*:*"]}, RULES)
    assert with_version[0]["version"] == "1.18.0" and without[0]["version"] is None


def test_amazonaws_hostname_means_aws_but_not_a_lookalike():
    assert "AWS" in names(extract({"hostnames": ["ec2-1-2-3-4.compute-1.amazonaws.com"]}, RULES))
    assert extract({"hostnames": ["notamazonaws.com"]}, RULES) == []


def test_cloud_provider_and_service_are_both_found():
    hits = extract({"cloud": {"provider": "Amazon", "service": "EC2"}}, RULES)
    assert names(hits) == {"AWS", "Amazon EC2"}


def test_ignored_component_is_dropped_and_not_reported_as_unmapped():
    rec = {"http": {"components": {"HSTS": {}}}}
    assert extract(rec, RULES) == [] and unmapped(rec, RULES) == []


def test_longest_os_prefix_wins():
    server = extract({"os": "Windows Server 2022 (build 10.0.20348)"}, RULES)
    desktop = extract({"os": "Windows (build 10.0.17763)"}, RULES)
    assert names(server) == {"Windows Server"} and names(desktop) == {"Windows"}


def test_scan_tags_become_exposed_service_types():
    assert names(extract({"tags": ["ai", "cloud", "cdn"]}, RULES)) == {"AI service"}


def test_same_technology_from_two_sources_is_two_pieces_of_evidence():
    hits = extract({"product": "nginx", "http": {"server": "nginx", "components": {"Nginx": {}}}}, RULES)
    assert sorted(h["source"] for h in hits) == ["component", "product", "server_header"]


def test_unknown_strings_are_reported_not_invented():
    rec = {"http": {"server": "mystery/1.0", "components": {"Frobnicator": {}}}, "product": "Zorp"}
    assert extract(rec, RULES) == []
    assert {(kind, value) for kind, value, _ in unmapped(rec, RULES)} == {
        ("server_headers", "mystery"), ("components", "frobnicator"), ("products", "zorp")}


def test_empty_and_odd_records_do_not_crash():
    assert extract({}, RULES) == []
    assert extract({"http": None, "cloud": "x", "cpe23": ["bad"], "tags": None}, RULES) == []
    assert raw_signals({"http": {"components": None}}) == []


def test_discovered_rules_only_apply_when_asked_for():
    rec = {"http": {"components": {"Okta": {}}}}
    seed_only = Rules({"categories": RULES.categories, "seed": {}, "discovered": {"Okta": {"category": "Security", "components": ["Okta"]}}}, ("seed",))
    assert extract(rec, seed_only) == []
    assert names(extract(rec, RULES)) == {"Okta"}


def test_catalog_has_one_row_per_technology_with_its_origin():
    catalog = {row["technology"]: row for row in RULES.catalog()}
    assert catalog["Nginx"]["origin"] == "seed" and catalog["Okta"]["origin"] == "discovered"
    assert len(catalog) == len(RULES.technologies)


def test_real_rules_file_is_consistent():
    rules = load_rules()
    assert len(rules.technologies) > 100
    for name, info in rules.technologies.items():
        assert info["category"] in rules.categories, name
    assert "Cloudflare" in rules.technologies and "AWS" in rules.technologies


# ---- discovery helpers

CATEGORIES = ["Security", "Other"]
BATCH = [{"id": 0}, {"id": 1}, {"id": 2}]


def test_valid_decision_is_kept():
    out = validate_decisions([{"id": 0, "technology": " OpenSSL ", "category": "Security", "vendor": "OpenSSL", "keep": True}], BATCH, CATEGORIES)
    assert out[0] == {"technology": "OpenSSL", "category": "Security", "vendor": "OpenSSL", "keep": True}


def test_bad_category_or_missing_name_turns_keep_off():
    out = validate_decisions([
        {"id": 0, "technology": "X", "category": "Made up", "keep": True},
        {"id": 1, "technology": None, "category": "Security", "keep": True},
    ], BATCH, CATEGORIES)
    assert out[0]["keep"] is False and out[1]["keep"] is False and out[0]["technology"] is None


def test_answers_for_ids_we_did_not_ask_about_are_dropped():
    assert validate_decisions([{"id": 99, "technology": "X", "category": "Security", "keep": True}], BATCH, CATEGORIES) == {}
    assert validate_decisions("not a list", BATCH, CATEGORIES) == {}


# ---- attribution rules added with the technology work

def test_junk_domains_are_rejected():
    for junk in ("adsl.", "home.", "localhost.", "04.", "reverse-dns.", "pcextreme."):
        assert not attribution._is_valid_domain(junk), junk
    assert attribution._is_valid_domain("duolingo.com") and attribution._is_valid_domain("example.co.uk.")


def test_second_domain_is_used_when_the_first_is_junk():
    assert attribution._get_attributable_domain(["home.", "arsops.com"], ["snap.home", "home.arsops.com"], "192.241.242.88") == "arsops.com"


def test_partial_ip_in_hostname_is_a_generated_name():
    assert attribution._is_generated_hostname("customer-TOLU-PUBLIC-CGN-32-12.megared.net.mx", "189.196.32.12")
    assert not attribution._is_generated_hostname("shop-1-2.example.com", "10.0.1.2")  # both numbers are single digits


def test_a_hosting_providers_own_domain_is_not_a_prospect():
    rec = {"domains": ["leaseweb.com"], "hostnames": ["hosted-by.leaseweb.com"], "ip_str": "89.149.200.164", "org": "LeaseWeb Netherlands B.V."}
    assert attribution.attribute_without_llm(rec) is None
    assert attribution._is_providers_own_domain("pebblehost.com", "PebbleHost", "Daniel Jackson")


def test_org_name_only_record_on_a_cloud_range_is_not_attributed():
    rec = {"org": "Oracle Svenska AB", "cloud": {"provider": "Oracle Cloud Infrastructure"}, "ip_str": "1.2.3.4"}
    assert attribution.attribute_without_llm(rec) is None


def test_carrier_and_hosting_names_are_infrastructure():
    for name in ("TerraTransit AG", "Network for hosting services", "PebbleHost", "Shaw Communications Inc."):
        assert attribution.is_infra_org_name(name), name
    assert not attribution.is_infra_org_name("Mitsubishi Electric Information Network Corporation")
