-- One row per illness report; symptoms kept as a list (free text, not coded).
select
    player_name                                   as player_id,
    split_part(player_name, '-', 1)               as team,
    strptime("timestamp", '%d.%m.%Y')::date       as report_date,
    from_json(problems, '["VARCHAR"]')            as symptoms
from {{ source('soccermon', 'illness_reports') }}
