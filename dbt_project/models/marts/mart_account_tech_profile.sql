-- Gold layer: one row per account that has technology evidence.
-- Accounts that are not in the ranked list have no exposure findings in this scan: is_ranked is false.

with technologies as (
    select * from {{ ref('mart_account_technologies') }}
),

by_category as (
    select
        entity_key,
        category,
        array_agg(technology) within group (order by asset_count desc, technology) as techs
    from technologies
    group by entity_key, category
),

categories as (
    select
        entity_key,
        count(*)                                  as category_count,
        object_agg(category, to_variant(techs))   as tech_by_category
    from by_category
    group by entity_key
),

per_account as (
    select
        entity_key,
        count(*)                                                                    as tech_count,
        array_agg(technology) within group (order by asset_count desc, technology)  as technologies
    from technologies
    group by entity_key
),

assets as (
    select
        entity_key,
        count(distinct asset_id)                      as asset_count,
        array_compact(array_agg(distinct country))    as countries
    from {{ ref('mart_tech_evidence') }}
    group by entity_key
)

select
    a.entity_key,
    a.tech_count,
    c.category_count,
    a.technologies,
    c.tech_by_category,
    s.asset_count,
    s.countries,
    p.entity_key is not null as is_ranked,
    p.priority_tier,
    p.priority_rank,
    p.total_score
from per_account a
inner join categories c on a.entity_key = c.entity_key
inner join assets s on a.entity_key = s.entity_key
left join {{ ref('mart_prospect_accounts') }} p on a.entity_key = p.entity_key
