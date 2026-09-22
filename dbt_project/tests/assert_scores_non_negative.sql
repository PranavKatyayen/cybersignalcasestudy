-- Custom (singular) dbt test

select entity_key, total_score
from {{ ref('stg_entities') }}
where total_score <= 0
