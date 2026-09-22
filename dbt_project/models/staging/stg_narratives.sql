-- Staging layer for pre-generated risk narratives

with source as (
    select * from {{ source('raw', 'entity_narratives') }}
),

cleaned as (
    select
        trim(entity_key)     as entity_key,
        summary,
        outreach_angle,
        cited_evidence_indices,
        narrative_source,
        provider    as narrative_provider,
        model       as narrative_model,
        prompt_version as narrative_prompt_version,
        loaded_at
    from source
    where entity_key is not null
)

select * from cleaned
