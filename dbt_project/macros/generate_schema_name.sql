{#
    dbt's default generate_schema_name macro CONCATENATES a model's custom
    +schema config onto the profile's target schema (e.g. target schema
    'staging' + model config 'analytics' -> 'staging_analytics'), rather than
    replacing it. That silently produced a schema that doesn't match the
    ANALYTICS schema actually created by scripts/snowflake_setup.sql, and the
    Next.js app queries `mart_prospect_accounts` unqualified (relying on its
    session schema), so it failed with "Object does not exist".

    This is the standard override every real dbt project using multiple
    schemas ends up needing: use the custom schema name literally when one is
    given, otherwise fall back to the profile's default target schema.
#}

{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- set default_schema = target.schema -%}
    {%- if custom_schema_name is none -%}
        {{ default_schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
