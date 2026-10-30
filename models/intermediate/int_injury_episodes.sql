-- From daily reports to injury episodes. PmSys asks injured players to
-- report every day, so one injury appears on many consecutive days. Reports
-- of the same body location are chained into one episode while the gap
-- between two reports stays within var('injury_episode_gap_days').
with reports as (
    select distinct player_id, team, report_date, body_location, severity
    from {{ ref('stg_soccermon__injury_reports') }}
),

flagged as (
    select
        *,
        case
            when lag(report_date) over w is null then 1
            when report_date - lag(report_date) over w > {{ var('injury_episode_gap_days') }} then 1
            else 0
        end as is_new_episode
    from reports
    window w as (partition by player_id, body_location order by report_date)
),

numbered as (
    select *, sum(is_new_episode) over (partition by player_id, body_location order by report_date) as episode_no
    from flagged
)

select
    md5(concat_ws('|', player_id, body_location, min(report_date))) as injury_episode_id,
    player_id,
    any_value(team)                                   as team,
    body_location,
    min(report_date)                                  as onset_date,
    max(report_date)                                  as last_report_date,
    max(report_date) - min(report_date) + 1           as span_days,
    count(*)                                          as n_reports,
    case when bool_or(severity = 'major') then 'major' else 'minor' end as worst_severity
from numbered
group by player_id, body_location, episode_no
