-- Injury episodes (see int_injury_episodes for the rule). Grain: one episode.
select
    e.injury_episode_id,
    e.player_id,
    e.team,
    e.body_location,
    b.body_region,
    b.side,
    e.onset_date,
    e.last_report_date,
    e.span_days::integer  as span_days,
    e.n_reports::integer  as n_reports,
    e.worst_severity
from {{ ref('int_injury_episodes') }} e
left join {{ ref('body_locations') }} b using (body_location)
