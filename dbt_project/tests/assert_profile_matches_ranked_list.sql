-- Custom (singular) dbt test: is_ranked, tier and rank in the technology profile must match the ranked list

select p.entity_key
from {{ ref('mart_account_tech_profile') }} p
left join {{ ref('mart_prospect_accounts') }} m on p.entity_key = m.entity_key
where (p.is_ranked and m.entity_key is null)
   or (not p.is_ranked and m.entity_key is not null)
   or (p.is_ranked and (p.priority_tier != m.priority_tier or p.priority_rank != m.priority_rank))
