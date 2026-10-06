"""Technology extraction: turns the raw scan fields of a record into a list of technologies, with rules only."""

import json
import re
from collections import defaultdict
from pathlib import Path

RULES_PATH = Path(__file__).with_name("tech_rules.json")

# the signal lists a technology can have in tech_rules.json, and the source name stored with each hit
SIGNALS = {
    "components": "component",
    "cpe": "cpe",
    "products": "product",
    "server_headers": "server_header",
    "cloud_providers": "cloud",
    "cloud_services": "cloud",
    "hostname_suffixes": "hostname",
    "os_names": "os",
    "tags": "tag",
}

_SERVER_TOKEN = re.compile(r"^\s*([A-Za-z0-9_.+\-]+)(?:/([A-Za-z0-9_.+\-]+))?")


def _norm(value: str) -> str:
    return (value or "").strip().lower()


class Rules:
    """The rules file turned into lookup tables. origins picks the sections to use: seed, discovered."""

    def __init__(self, data: dict, origins=("seed", "discovered")):
        self.categories = data["categories"]
        self.ignore = {kind: {_norm(v) for v in values} for kind, values in data.get("ignore", {}).items()}
        self.technologies = {}
        self.origin_of = {}
        self.index = {signal: defaultdict(list) for signal in SIGNALS}
        for origin in ("seed", "discovered"):
            if origin not in origins:
                continue
            for name, spec in data.get(origin, {}).items():
                if name not in self.technologies:  # the first definition wins the category and vendor
                    self.technologies[name] = {"category": spec["category"], "vendor": spec.get("vendor")}
                    self.origin_of[name] = origin
                for signal in SIGNALS:
                    for value in spec.get(signal, []):
                        if name not in self.index[signal][_norm(value)]:
                            self.index[signal][_norm(value)].append(name)
        self._suffixes = list(self.index["hostname_suffixes"])
        self._os_prefixes = sorted(self.index["os_names"], key=len, reverse=True)

    def catalog(self) -> list[dict]:
        """One row per technology: the small dimension table that evidence rows point to."""
        return [{"technology": name, "category": info["category"], "vendor": info["vendor"], "origin": self.origin_of[name]}
                for name, info in sorted(self.technologies.items())]

    def hit(self, name: str, source: str, signal: str, version: str | None = None) -> dict:
        return {"technology": name, "version": version, "source": source, "signal": signal}


_cache: dict = {}


def load_rules(origins=("seed", "discovered"), path: Path = RULES_PATH) -> Rules:
    key = (tuple(origins), str(path))
    if key not in _cache:
        _cache[key] = Rules(json.loads(Path(path).read_text(encoding="utf-8")), origins)
    return _cache[key]


def _clean_version(value) -> str | None:
    value = (value or "").strip() if isinstance(value, str) else ""
    return None if value in ("", "*", "-") else value


def _cpe_parts(cpe23: str) -> tuple[str, str | None] | None:
    """'cpe:2.3:a:f5:nginx:1.22.1:...' -> ('f5:nginx', '1.22.1')"""
    parts = cpe23.split(":")
    if len(parts) < 5:
        return None
    return f"{parts[3]}:{parts[4]}".lower(), _clean_version(parts[5] if len(parts) > 5 else None)


def _server_token(header: str) -> tuple[str, str | None] | None:
    m = _SERVER_TOKEN.match(header or "")
    return (m.group(1).lower(), _clean_version(m.group(2))) if m else None


def raw_signals(rec: dict) -> list[tuple[str, str, str, str | None]]:
    """Every technology-looking string in a record: (signal kind, normalized value, original text, version)."""
    out = []
    http = rec.get("http") if isinstance(rec.get("http"), dict) else {}
    components = http.get("components") if isinstance(http.get("components"), dict) else {}
    for name in components:
        out.append(("components", _norm(name), name, None))
    for cpe23 in rec.get("cpe23") or []:
        parsed = _cpe_parts(cpe23)
        if parsed:
            out.append(("cpe", parsed[0], cpe23, parsed[1]))
    if rec.get("product"):
        out.append(("products", _norm(rec["product"]), rec["product"], _clean_version(rec.get("version"))))
    token = _server_token(http.get("server") or "")
    if token:
        out.append(("server_headers", token[0], http.get("server"), token[1]))
    cloud = rec.get("cloud") if isinstance(rec.get("cloud"), dict) else {}
    if cloud.get("provider"):
        out.append(("cloud_providers", _norm(cloud["provider"]), cloud["provider"], None))
        if cloud.get("service"):
            out.append(("cloud_services", _norm(f"{cloud['provider']}:{cloud['service']}"), f"{cloud['provider']}:{cloud['service']}", None))
    if rec.get("os"):
        out.append(("os_names", _norm(rec["os"]), rec["os"], None))
    for tag in rec.get("tags") or []:
        out.append(("tags", _norm(tag), tag, None))
    return out


def _hostnames(rec: dict) -> list[str]:
    names = (rec.get("hostnames") or []) + (rec.get("domains") or [])
    return sorted({_norm(h).rstrip(".") for h in names if h})


def extract(rec: dict, rules: Rules | None = None) -> list[dict]:
    """Technology hits for one record. Each hit says what was found and which string revealed it."""
    rules = rules or load_rules()
    hits = {}

    def add(name, source, signal, version=None):
        key = (name, source, version)
        hits.setdefault(key, rules.hit(name, source, signal, version))

    for kind, value, original, version in raw_signals(rec):
        if value in rules.ignore.get(kind, ()):
            continue
        if kind == "os_names":
            for prefix in rules._os_prefixes:
                if value.startswith(prefix):
                    for name in rules.index["os_names"][prefix]:
                        add(name, "os", original)
                    break
            continue
        for name in rules.index[kind].get(value, []):
            add(name, SIGNALS[kind], original, version)

    for host in _hostnames(rec):
        for suffix in rules._suffixes:
            if host == suffix or host.endswith("." + suffix):
                for name in rules.index["hostname_suffixes"][suffix]:
                    add(name, "hostname", host)
    return list(hits.values())


def unmapped(rec: dict, rules: Rules | None = None) -> list[tuple[str, str, str]]:
    """Strings of the kinds the rules cover that no rule recognised: (kind, value, original text)."""
    rules = rules or load_rules()
    out = []
    for kind, value, original, _ in raw_signals(rec):
        if kind in ("cloud_providers", "cloud_services", "tags", "os_names"):
            continue
        if value in rules.ignore.get(kind, ()) or rules.index[kind].get(value):
            continue
        out.append((kind, value, original))
    return out


def save_rules(data: dict, path: Path = RULES_PATH):
    """Writes the rules file with one technology per line, so changes stay easy to review in git."""
    lines = ["{", f'  "schema_version": {data.get("schema_version", 1)},',
             f'  "note": {json.dumps(data.get("note", ""), ensure_ascii=False)},',
             f'  "categories": {json.dumps(data["categories"], ensure_ascii=False)},',
             f'  "ignore": {json.dumps(data.get("ignore", {}), ensure_ascii=False)},']
    for section, trailing in (("seed", ","), ("discovered", "")):
        entries = list(data.get(section, {}).items())
        if not entries:
            lines.append(f'  "{section}": {{}}{trailing}')
            continue
        lines.append(f'  "{section}": {{')
        for i, (name, spec) in enumerate(entries):
            comma = "," if i < len(entries) - 1 else ""
            lines.append(f"    {json.dumps(name, ensure_ascii=False)}: {json.dumps(spec, ensure_ascii=False)}{comma}")
        lines.append(f"  }}{trailing}")
    lines.append("}")
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")
