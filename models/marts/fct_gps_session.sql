-- Objective session metrics, external (GNSS, accelerometer) and internal
-- (heart rate). Grain: one player and recording day. Every recording is
-- here with its quality flags; heart-rate indicators exist only when the
-- heart rate passed validation. Analyses filter on gps_quality_flag = 'ok'.
select
    g.recording_id,
    g.player_id,
    g.team,
    g.session_date,
    g.gps_quality_flag,
    g.hr_quality_flag,
    g.duration_min,
    g.distance_m,
    g.distance_0_2_m,
    g.distance_2_43_m,
    g.distance_hsr_m,
    g.distance_sprint_m,
    g.speed_max_ms,
    g.n_accelerations::integer   as n_accelerations,
    g.n_decelerations::integer   as n_decelerations,
    g.accelerometer_load_au,
    g.hr_coverage,
    case when g.hr_quality_flag = 'ok' then g.hr_mean_bpm end as hr_mean_bpm,
    case when g.hr_quality_flag = 'ok' then g.hr_peak_bpm end as hr_peak_bpm,
    h.edwards_trimp_au,
    h.minutes_above_90pct_hrmax,
    h.hr_at_2_ms_bpm,
    case when g.distance_m > 500 and h.edwards_trimp_au is not null
         then h.edwards_trimp_au / (g.distance_m / 1000) end as trimp_per_km,
    g.source_file
from {{ ref('int_gps_sessions__validated') }} g
left join {{ ref('int_gps_sessions__heart_rate') }} h
       on h.player_id = g.player_id and h.session_date = g.session_date and g.gps_quality_flag = 'ok'
