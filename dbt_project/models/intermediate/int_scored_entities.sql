-- Intermediate layer: this is where business logic lives
-- Tiers: CRITICAL 100+, HIGH 40-99, MEDIUM 20-39, LOW below 20.
-- An account matched by organization name only (MEDIUM confidence) is capped at HIGH:
-- a CRITICAL call needs a verified business domain. Rank is tier first, then score.

with entities as (
    select * from {{ ref('stg_entities') }}
),

tiered as (
    select
        *,
        case
            when total_score >= 100 and attribution_confidence = 'HIGH' then 'CRITICAL'
            when total_score >= 40 then 'HIGH'
            when total_score >= 20 then 'MEDIUM'
            else 'LOW'
        end as priority_tier
    from entities
),

ranked as (
    select
        *,
        row_number() over (
            order by
                case priority_tier when 'CRITICAL' then 1 when 'HIGH' then 2 when 'MEDIUM' then 3 else 4 end,
                total_score desc,
                entity_key
        ) as priority_rank
    from tiered
)

select * from ranked
