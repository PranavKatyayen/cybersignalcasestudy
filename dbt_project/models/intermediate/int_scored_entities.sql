-- Intermediate layer: this is where business logic lives

with entities as (
    select * from {{ ref('stg_entities') }}
),

tiered as (
    select
        *,
        case
            when total_score >= 100 then 'CRITICAL'
            when total_score >= 40  then 'HIGH'
            when total_score >= 20  then 'MEDIUM'
            else 'LOW'
        end as priority_tier,
        row_number() over (order by total_score desc, entity_key) as priority_rank
    from entities
)

select * from tiered
