-- Custom (singular) dbt test: the technology work must not change the ranked list
-- (every ranked account stays in mart_prospect_accounts, one row each)

select entity_key, count(*) as row_count
from {{ ref('mart_prospect_accounts') }}
group by entity_key
having count(*) != 1
