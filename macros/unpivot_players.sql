{#
  SoccerMon delivers most daily metrics in "wide" format: one row per calendar
  day, one column per player (and a first column holding the date, whose name
  changes from file to file). This macro turns such a file into the tidy
  (date, player, value) shape every downstream model expects.
  Empty cells are dropped by UNPIVOT: an absent report stays absent.
#}
{% macro unpivot_players(relation, value_name) %}
select
    strptime(raw_date, '%d.%m.%Y')::date      as calendar_date,
    player_id,
    split_part(player_id, '-', 1)             as team,
    try_cast(raw_value as double)             as {{ value_name }}
from (
    unpivot (
        select columns(lambda c: c not like 'Team%') as raw_date, columns('^Team')
        from {{ relation }}
    )
    on columns('^Team')
    into name player_id value raw_value
)
where nullif(trim(raw_value), '') is not null
{% endmacro %}
