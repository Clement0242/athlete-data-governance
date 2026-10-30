-- Internal load from heart rate, and its coupling with external load.
-- Only recordings whose heart rate passed validation (hr_quality_flag = 'ok').
--
-- * HRmax per player: highest session peak (99.5th percentile of a session,
--   which ignores isolated spikes) over sessions with a plausible peak
--   (150-225 bpm); at least 3 such sessions, otherwise unknown.
-- * Edwards TRIMP = minutes in each 10 % band of HRmax from 50 % upwards,
--   weighted 1 to 5, computed from the per-bpm histogram: a new HRmax only
--   needs a re-run, not a new extraction.
-- * HR at 2 m/s: regression of 30 s epoch heart rate on epoch speed over the
--   moving epochs (0.8-3.5 m/s, at least 15, R² >= 0.2). The cardiac cost of a
--   standard running speed: lower = fitter, or fresher.
with sessions as (
    select * from {{ ref('int_gps_sessions__validated') }}
    where hr_quality_flag = 'ok' and gps_quality_flag = 'ok'
),

hr_max as (
    select player_id, max(hr_peak_bpm) as hr_max_bpm
    from sessions
    where hr_peak_bpm between 150 and 225
    group by player_id
    having count(*) >= 3
),

histogram as (
    select
        s.player_id,
        s.session_date,
        39 + generate_subscripts(s.hr_seconds_by_bpm, 1) as bpm,
        unnest(s.hr_seconds_by_bpm)                      as seconds
    from sessions s
),

trimp as (
    select
        h.player_id,
        h.session_date,
        sum(h.seconds / 60.0 * case
            when h.bpm >= 0.9 * m.hr_max_bpm then 5
            when h.bpm >= 0.8 * m.hr_max_bpm then 4
            when h.bpm >= 0.7 * m.hr_max_bpm then 3
            when h.bpm >= 0.6 * m.hr_max_bpm then 2
            when h.bpm >= 0.5 * m.hr_max_bpm then 1
            else 0 end)                                                           as edwards_trimp_au,
        sum(case when h.bpm >= 0.9 * m.hr_max_bpm then h.seconds else 0 end) / 60.0 as minutes_above_90pct_hrmax
    from histogram h
    join hr_max m using (player_id)
    group by all
),

hr_speed as (
    select
        e.player_id,
        e.session_date,
        regr_intercept(e.hr_mean_bpm, e.speed_mean_ms) + 2.0 * regr_slope(e.hr_mean_bpm, e.speed_mean_ms) as hr_at_2_ms_bpm,
        regr_r2(e.hr_mean_bpm, e.speed_mean_ms)                                                          as hr_speed_r2,
        count(*)                                                                                         as n_moving_epochs
    from {{ ref('stg_objective__gps_epochs') }} e
    join sessions s using (player_id, session_date)
    where e.speed_mean_ms between 0.8 and 3.5 and e.hr_mean_bpm is not null
    group by all
    having count(*) >= 15
)

select
    s.player_id,
    s.session_date,
    m.hr_max_bpm,
    t.edwards_trimp_au,
    t.minutes_above_90pct_hrmax,
    case when hs.hr_speed_r2 >= 0.2 then hs.hr_at_2_ms_bpm end as hr_at_2_ms_bpm,
    hs.hr_speed_r2,
    hs.n_moving_epochs
from sessions s
left join hr_max m using (player_id)
left join trimp t using (player_id, session_date)
left join hr_speed hs using (player_id, session_date)
