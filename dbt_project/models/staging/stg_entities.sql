-- Staging layer: light cleaning/typing only, no business logic here

with source as (
    select * from {{ source('raw', 'scored_entities') }}
),

cleaned as (
    select
        trim(entity_key)                       as entity_key,
        upper(trim(attribution_confidence))    as attribution_confidence,
        provider_roles,
        attribution_reasons,
        total_score::number                    as total_score,
        asset_count::number                    as asset_count,
        orgs,
        countries,
        sample_ips,
        top_findings,
        array_size(top_findings)                as finding_count,
        loaded_at
    from source
    where entity_key is not null
)

select * from cleaned
