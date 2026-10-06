-- Gold layer: one row per account and technology, with how many assets showed it and how it was seen

select
    entity_key,
    technology,
    category,
    vendor,
    count(distinct asset_id)                       as asset_count,
    array_compact(array_agg(distinct version))     as versions,
    array_agg(distinct source)                     as sources,
    count(*)                                       as evidence_count
from {{ ref('mart_tech_evidence') }}
group by entity_key, technology, category, vendor
