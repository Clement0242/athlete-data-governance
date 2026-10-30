-- GNSS files whose player column is empty: the player was recovered from the
-- file name. Listed so the provider can be told, and so nobody is surprised.
{{ config(severity = 'warn') }}
select source_file, session_date
from {{ ref('stg_objective__gps_sessions') }}
where player_recovered_from_file_name
