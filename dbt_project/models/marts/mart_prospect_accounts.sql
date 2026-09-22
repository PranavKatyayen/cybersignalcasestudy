-- Gold layer: this is what the Next.js app actually queries for the main dashboard

with entities as (
    select * from {{ ref('int_scored_entities') }}
),

narratives as (
    select * from {{ ref('stg_narratives') }}
),

final as (
    select
        e.entity_key,
        e.priority_tier,
        e.priority_rank,
        e.attribution_confidence,
        e.total_score,
        e.finding_count,
        e.asset_count,
        e.provider_roles,
        e.attribution_reasons,
        e.orgs,
        e.countries,
        e.sample_ips,
        e.top_findings,
        -- convenience column: the single top finding as plain text
        e.top_findings[0]::string as headline_finding,
        n.summary as narrative_summary,
        n.outreach_angle as narrative_outreach_angle,
        n.cited_evidence_indices as narrative_cited_evidence_indices,
        n.narrative_source,
        n.narrative_provider,
        n.narrative_model,
        n.narrative_prompt_version,
        e.loaded_at
    from entities e
    left join narratives n on e.entity_key = n.entity_key
)

select * from final
order by priority_rank
