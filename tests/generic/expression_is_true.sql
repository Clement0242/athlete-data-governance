{#- A business rule written as a boolean SQL expression, checked on every row. -#}
{% test expression_is_true(model, expression, where=none) %}
select *
from {{ model }}
where not ({{ expression }})
{% if where %}  and {{ where }}{% endif %}
{% endtest %}
