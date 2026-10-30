{# Layer schemas are named after the layer (staging, marts...), not prefixed
   with the target schema: the warehouse reads like the architecture diagram. #}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {{ custom_schema_name if custom_schema_name is not none else target.schema }}
{%- endmacro %}
