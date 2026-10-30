-- One row per pseudonymised player, with what the warehouse holds on her.
with days as (
    select player_id, any_value(team) as team, min(calendar_date) as first_day, max(calendar_date) as last_day,
           count(*) as n_days
    from {{ ref('int_player_days') }}
    group by player_id
),
sessions as (select player_id, count(*) as n_rpe_sessions from {{ ref('int_training_sessions__deduplicated') }} group by 1),
gps as (select player_id, count(*) as n_gps_sessions from {{ ref('stg_objective__gps_sessions') }} group by 1),
wellness as (select player_id, count(distinct calendar_date) as n_wellness_days from {{ ref('stg_soccermon__wellness') }} group by 1),
hr as (select player_id, max(hr_max_bpm) as hr_max_estimated_bpm from {{ ref('int_gps_sessions__heart_rate') }} group by 1),
injuries as (select player_id, count(*) as n_injury_episodes from {{ ref('int_injury_episodes') }} group by 1)

select
    d.player_id,
    d.team,
    d.first_day,
    d.last_day,
    d.n_days::integer                                   as n_days,
    coalesce(s.n_rpe_sessions, 0)::integer              as n_rpe_sessions,
    coalesce(g.n_gps_sessions, 0)::integer              as n_gps_sessions,
    coalesce(w.n_wellness_days, 0)::integer             as n_wellness_days,
    round(coalesce(w.n_wellness_days, 0) / d.n_days, 3) as wellness_coverage,
    h.hr_max_estimated_bpm,
    coalesce(i.n_injury_episodes, 0)::integer           as n_injury_episodes,
    s.player_id is not null                             as has_subjective_data,
    g.player_id is not null                             as has_objective_data
from days d
left join sessions s using (player_id)
left join gps g using (player_id)
left join wellness w using (player_id)
left join hr h using (player_id)
left join injuries i using (player_id)
