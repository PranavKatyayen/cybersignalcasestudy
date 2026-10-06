-- Custom (singular) dbt test: an account must have at most one row per technology

select entity_key, technology, count(*) as row_count
from {{ ref('mart_account_technologies') }}
group by entity_key, technology
having count(*) > 1
