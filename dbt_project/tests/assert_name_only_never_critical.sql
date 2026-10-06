-- Custom (singular) dbt test: an account matched by organization name only must never be CRITICAL

select entity_key, attribution_confidence, priority_tier
from {{ ref('int_scored_entities') }}
where attribution_confidence = 'MEDIUM'
  and priority_tier = 'CRITICAL'
