-- Gold layer: the evidence detail behind each account

with assets as (
    select * from {{ ref('stg_assets') }}
),

entities as (
    select entity_key, priority_tier from {{ ref('int_scored_entities') }}
),

final as (
    select
        a.entity_key,
        e.priority_tier,
        a.ip,
        a.port,
        a.product,
        a.country,
        a.org,
        a.domain,
        a.provider_role,
        a.attribution_reason,
        a.raw_score,
        a.adjusted_score,
        a.findings,
        a.tags,
        a.loaded_at
    from assets a
    inner join entities e on a.entity_key = e.entity_key
)

select * from final
order by adjusted_score desc
