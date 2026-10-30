{#- Volume check: an empty or exploding table fails before anyone reads it. -#}
{% test row_count_between(model, min_rows, max_rows) %}
select n
from (select count(*) as n from {{ model }})
where n < {{ min_rows }} or n > {{ max_rows }}
{% endtest %}
