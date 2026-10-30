-- One row per (report, body location): a report naming two locations
-- becomes two rows. Severity is the provider's minor / major.
with reports as (
    select
        player_name                                   as player_id,
        split_part(player_name, '-', 1)               as team,
        strptime("timestamp", '%d.%m.%Y')::date       as report_date,
        "type"::json                                  as locations
    from {{ source('soccermon', 'injury_reports') }}
),

exploded as (
    select player_id, team, report_date, unnest(json_keys(locations)) as body_location, locations
    from reports
)

select
    player_id,
    team,
    report_date,
    body_location,
    json_extract_string(locations, '$.' || body_location) as severity
from exploded
