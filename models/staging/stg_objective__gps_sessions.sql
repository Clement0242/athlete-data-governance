-- One row per player and recording day (STATSports APEX), as extracted.
-- The heart-rate histogram is kept as a list: seconds spent at each bpm
-- from 40 to 230, so that HR zones can be recomputed with any HRmax.
-- The player is read inside the file; when that column is empty (a few files
-- of 2021) it is recovered from the file name, and the case is counted by
-- assert_gps_player_from_file_name.
with s as (
    select *, regexp_extract(file, '(Team[AB]-[0-9a-f-]{36})', 1) as player_from_file_name
    from {{ source('objective', 'gps_sessions') }}
)

select
    md5(concat_ws('|', file, start_s, distance))             as recording_id,
    coalesce(player, player_from_file_name)                 as player_id,
    split_part(coalesce(player, player_from_file_name), '-', 1) as team,
    player is null                                          as player_recovered_from_file_name,
    "date"::date                        as session_date,
    file                                as source_file,
    start_s,
    duration_min,
    distance                            as distance_m,
    dist_0_2                            as distance_0_2_m,
    dist_2_43                           as distance_2_43_m,
    dist_hsr                            as distance_hsr_m,
    dist_sprint                         as distance_sprint_m,
    speed_max                           as speed_max_ms,
    n_acc                               as n_accelerations,
    n_dec                               as n_decelerations,
    acc_load                            as accelerometer_load_au,
    hr_coverage,
    hr_mean                             as hr_mean_bpm,
    hr_peak                             as hr_peak_bpm,
    hr_hist                             as hr_seconds_by_bpm
from s
