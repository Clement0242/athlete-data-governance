select
    player                          as player_id,
    "date"::date                    as session_date,
    epoch                           as epoch_index,
    speed                           as speed_mean_ms,
    "load"                          as accelerometer_load_au,
    hr                              as hr_mean_bpm
from {{ source('objective', 'gps_epochs') }}
