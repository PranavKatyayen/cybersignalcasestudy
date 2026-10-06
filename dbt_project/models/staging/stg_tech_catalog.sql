-- Staging layer for the technology catalog: one row per technology

select
    trim(technology) as technology,
    trim(category)   as category,
    nullif(trim(vendor), '') as vendor,
    origin
from {{ source('raw', 'tech_catalog') }}
where technology is not null
