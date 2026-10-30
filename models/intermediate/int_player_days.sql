-- The calendar spine: one row per player and day, from the first to the
-- last day the player appears in *any* source. Facts are joined onto it, so
-- a day without data is an explicit row with nulls, not a missing row.
with appearances as (
    select player_id, team, session_date as d from {{ ref('stg_soccermon__training_sessions') }}
    union all
    select player_id, team, calendar_date from {{ ref('stg_soccermon__wellness') }}
    union all
    select player_id, team, report_date from {{ ref('stg_soccermon__injury_reports') }}
    union all
    select player_id, team, session_date from {{ ref('stg_objective__gps_sessions') }}
),

bounds as (
    select player_id, any_value(team) as team, min(d) as first_day, max(d) as last_day
    from appearances
    group by player_id
)

select
    player_id,
    team,
    unnest(generate_series(first_day, last_day, interval 1 day))::date as calendar_date
from bounds
