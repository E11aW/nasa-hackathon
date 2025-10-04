select
    'map' as component,
    5     as zoom,
    8     as max_zoom,
    800   as height,
    40   as latitude,
    -110    as longitude,
    'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png' as tile_source,
    ''    as attribution;
select
    'rectangle' as icon,
    20      as size;
