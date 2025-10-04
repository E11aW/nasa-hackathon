SELECT 'map' AS component;

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