-- One row per reported training session.
-- The source is a single JSON document {player: [sessions]}: it is exploded
-- here and nowhere else. Exact repeats (same player, day, RPE and duration)
-- are kept but flagged: the provider's own daily load counts them, the
-- warehouse lets each consumer decide (see int_training_sessions__deduplicated).
with document as (
    select content::json as doc from {{ source('soccermon', 'training_sessions') }}
),

players as (
    select unnest(json_keys(doc)) as player_id, doc from document
),

sessions as (
    select
        player_id,
        unnest(from_json(
            json_extract(doc, '$."' || player_id || '"'),
            '[{"srpe": "DOUBLE", "rpe": "DOUBLE", "duration": "DOUBLE", "date": "VARCHAR"}]'
        )) as s
    from players
),

typed as (
    select
        player_id,
        split_part(player_id, '-', 1)                as team,
        strptime(s.date, '%d.%m.%Y')::date           as session_date,
        s.rpe::integer                               as rpe,
        s.duration::integer                          as duration_min,
        s.srpe                                       as srpe_au
    from sessions
)

select
    md5(concat_ws('|', player_id, session_date, rpe, duration_min,
        row_number() over (partition by player_id, session_date, rpe, duration_min order by srpe_au))) as session_id,
    *,
    row_number() over (partition by player_id, session_date, rpe, duration_min order by srpe_au) > 1
        as is_exact_repeat
from typed
