-- Staging layer for technology evidence: light cleaning and an asset key, no business logic

with source as (
    select * from {{ source('raw', 'tech_evidence') }}
)

select
    trim(entity_key)               as entity_key,
    trim(technology)               as technology,
    nullif(trim(version), '')      as version,
    source,
    signal,
    ip,
    port::number                   as port,
    country,
    ip || ':' || port::string      as asset_id,
    loaded_at
from source
where entity_key is not null
  and technology is not null
