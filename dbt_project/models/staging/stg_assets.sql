-- Staging layer for individual scored assets

with source as (
    select * from {{ source('raw', 'scored_assets') }}
),

cleaned as (
    select
        trim(entity_key)                       as entity_key,
        upper(trim(attribution_confidence))    as attribution_confidence,
        provider_role,
        attribution_reason,
        org,
        domain,
        ip,
        port::number                            as port,
        product,
        country,
        raw_score::number                       as raw_score,
        adjusted_score::number                   as adjusted_score,
        findings,
        tags,
        loaded_at
    from source
    where entity_key is not null
)

select * from cleaned
