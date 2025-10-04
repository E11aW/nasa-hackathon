select 'shell' as component, 
       'custom_theme.css' as css, 
       'custom_theme' as theme,
       'Inter' as font,
       '[NASA International Space Apps Challenge 2025](https://github.com/E11aW/nasa-hackathon)' as footer;

select
    'html' as component,
        '<h1>Sustainable City Planning</h1>' as html;

select 
    'html' as component,
    '<img style="width: auto, height: 200px, margin-right: auto, margin-left: auto, display: block, text-align: center" src=NASA_Hackathon_Logo.png alt="A purple cityscape with trees with the words Sustainable City Planning underneath.">' as html;

/* select 'card' as component,
    'Logo' as title,
    'NASA_Hackathon_Logo' as image,
    'logo-image' as id;

select 'html' as component,
    '<style>
        #logo-image img {
            width: auto;
            height: auto;
            margin-right: auto;
            margin-left: auto;
            display: block;
        }
     </style>' as html; */

SELECT 'map' AS component;

select
    'html' as component,
        '<body>
            <h1>Header</h1>
            <p>Lorem ipsum dolor sit amet</p>
            <p>Lorem ipsum dolor sit amet</p>
        </body>' as html;
