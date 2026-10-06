-- Gold layer: every piece of technology evidence with its category, for the account page

select
    e.entity_key,
    e.technology,
    c.category,
    c.vendor,
    e.version,
    e.source,
    e.signal,
    e.ip,
    e.port,
    e.country,
    e.asset_id
from {{ ref('stg_tech_evidence') }} e
inner join {{ ref('stg_tech_catalog') }} c on e.technology = c.technology
