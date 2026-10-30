-- Two different recordings filed under the same name in the archive. Both
-- are quarantined (gps_quality_flag = duplicate_file_name).
{{ config(severity = 'warn') }}
select source_file, count(*) as n_recordings
from {{ ref('stg_objective__gps_sessions') }}
group by source_file
having count(*) > 1
