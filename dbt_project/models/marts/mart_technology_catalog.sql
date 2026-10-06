-- Gold layer: one row per technology, with how many accounts use it (and how many of them are ranked)

select
    t.technology,
    t.category,
    t.vendor,
    count(distinct t.entity_key)                                                       as account_count,
    count(distinct case when p.entity_key is not null then t.entity_key end)           as ranked_account_count,
    sum(t.asset_count)                                                                 as asset_count
from {{ ref('mart_account_technologies') }} t
left join {{ ref('mart_prospect_accounts') }} p on t.entity_key = p.entity_key
group by t.technology, t.category, t.vendor
