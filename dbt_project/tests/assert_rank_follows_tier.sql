-- Custom (singular) dbt test: a lower-priority tier must never be ranked above a higher one

with ordered as (
    select
        entity_key,
        priority_rank,
        case priority_tier when 'CRITICAL' then 1 when 'HIGH' then 2 when 'MEDIUM' then 3 else 4 end as tier_order,
        lag(case priority_tier when 'CRITICAL' then 1 when 'HIGH' then 2 when 'MEDIUM' then 3 else 4 end)
            over (order by priority_rank) as previous_tier_order
    from {{ ref('int_scored_entities') }}
)

select entity_key, priority_rank
from ordered
where previous_tier_order is not null
  and tier_order < previous_tier_order
