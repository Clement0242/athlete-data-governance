-- The analysis table: one row per player and calendar day, every source
-- aligned. A null means "not reported", never zero; `has_*` columns say
-- which sources reported that day.
with srpe as (
    select player_id, session_date as calendar_date, sum(srpe_au) as srpe_au, count(*) as n_rpe_sessions
    from {{ ref('int_training_sessions__deduplicated') }}
    group by all
),
gps as (
    select player_id, session_date as calendar_date,
           sum(distance_m) as distance_m, sum(distance_hsr_m) as distance_hsr_m,
           sum(distance_sprint_m) as distance_sprint_m, sum(n_accelerations) as n_accelerations,
           sum(n_decelerations) as n_decelerations, sum(accelerometer_load_au) as accelerometer_load_au,
           sum(edwards_trimp_au) as edwards_trimp_au, avg(hr_at_2_ms_bpm) as hr_at_2_ms_bpm
    from {{ ref('fct_gps_session') }}
    where gps_quality_flag = 'ok'
    group by all
),
wellness as (
    pivot {{ ref('stg_soccermon__wellness') }}
    on item in ('readiness', 'fatigue', 'soreness', 'stress', 'mood', 'sleep_quality', 'sleep_duration')
    using any_value(value)
    group by player_id, calendar_date
),
injury as (
    select d.player_id, d.calendar_date,
           bool_or(d.calendar_date = e.onset_date) as is_injury_onset,
           true                                    as is_injured
    from {{ ref('int_player_days') }} d
    join {{ ref('fct_injury_episode') }} e
      on e.player_id = d.player_id and d.calendar_date between e.onset_date and e.last_report_date
    group by all
),
illness as (
    select distinct player_id, report_date as calendar_date, true as is_ill
    from {{ ref('stg_soccermon__illness_reports') }}
)

select
    d.player_id,
    d.team,
    d.calendar_date,
    s.srpe_au,
    coalesce(s.n_rpe_sessions, 0)::integer        as n_rpe_sessions,
    g.distance_m,
    g.distance_hsr_m,
    g.distance_sprint_m,
    g.n_accelerations::integer                    as n_accelerations,
    g.n_decelerations::integer                    as n_decelerations,
    g.accelerometer_load_au,
    g.edwards_trimp_au,
    g.hr_at_2_ms_bpm,
    w.readiness, w.fatigue, w.soreness, w.stress, w.mood, w.sleep_quality, w.sleep_duration,
    coalesce(i.is_injury_onset, false)            as is_injury_onset,
    coalesce(i.is_injured, false)                 as is_injured,
    coalesce(il.is_ill, false)                    as is_ill,
    s.player_id is not null                       as has_rpe,
    g.player_id is not null                       as has_gps,
    w.player_id is not null                       as has_wellness
from {{ ref('int_player_days') }} d
left join srpe s using (player_id, calendar_date)
left join gps g using (player_id, calendar_date)
left join wellness w using (player_id, calendar_date)
left join injury i using (player_id, calendar_date)
left join illness il using (player_id, calendar_date)
