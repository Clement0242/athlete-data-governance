-- Data-quality mart: share of days each source reported, per player and
-- month. What a staff looks at before trusting any indicator.
select
    player_id,
    team,
    date_trunc('month', calendar_date)::date        as month,
    count(*)::integer                               as n_days,
    round(avg(has_rpe::integer), 3)                 as rpe_coverage,
    round(avg(has_gps::integer), 3)                 as gps_coverage,
    round(avg(has_wellness::integer), 3)            as wellness_coverage
from {{ ref('fct_player_day') }}
group by all
