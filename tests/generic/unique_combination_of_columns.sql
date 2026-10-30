{#- The grain of a table: this combination of columns identifies a row. -#}
{% test unique_combination_of_columns(model, combination) %}
select {{ combination | join(', ') }}, count(*) as n_rows
from {{ model }}
group by {{ combination | join(', ') }}
having count(*) > 1
{% endtest %}
