select
    'map'   as component,
    5       as zoom,
    8       as max_zoom,
    800     as height,
    40      as latitude,
    -110    as longitude,
    'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png' as tile_source,
    ''      as attribution;
select
    'rectangle' as icon,
    20      as size;

select
    'html' as component,
    '<header><link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap" rel="stylesheet"></header>' as html;

select
    'html' as component,
    '<style>
            h1 {
                font-family: "Inter", sans-serif;
            }

            p {
                color: black;
            }
        </style> 

        <body>
            <h1>Header</h1>
            <p>Lorem ipsum dolor sit amet</p>
            <p>Lorem ipsum dolor sit amet</p>
        </body>' as html;