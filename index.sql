SELECT 'map' AS component;

select
    'html' as component,
    '<style>h1 {color: red;}</style> <h1>HTML snippet that is safe because it is hardcoded.</h1>' as html;

select
    'html' as component,
    '<style>p {color: black;}</style> <p>Lorem ipsum dolor sit amet</p>' as html;

select
    'html' as component,
    '<style>p {color: black;}</style> 
        <body>
            <h1>Header</h1>
            <p>Lorem ipsum dolor sit amet</p>
            <p>Lorem ipsum dolor sit amet</p>
        </body>' as html;