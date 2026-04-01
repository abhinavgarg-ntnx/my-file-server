"""SVG icon constants used in HTML rendering."""

SVG_HOME = (
    '<svg width="14" height="14" fill="none" stroke="currentColor"'
    ' stroke-width="2" viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M2.25 12l8.954-8.955c.44-.439 1.152-.439 1.591 0L21.75'
    " 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4"
    ".875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1"
    ".125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8."
    '25 21h8.25"/></svg>'
)

SVG_VIEW = (
    '<svg fill="none" stroke="currentColor" stroke-width="2"'
    ' viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M2.036 12.322a1.012 1.012 0 010-.639C3.423 7.51 7.36'
    " 4.5 12 4.5c4.638 0 8.573 3.007 9.963 7.178.07.207.07"
    ".431 0 .639C20.577 16.49 16.64 19.5 12 19.5c-4.638 0-8"
    '.573-3.007-9.963-7.178z"/>'
    '<path stroke-linecap="round" stroke-linejoin="round"'
    ' d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/></svg>'
)

SVG_DOWNLOAD = (
    '<svg fill="none" stroke="currentColor" stroke-width="2"'
    ' viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25'
    " 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5"
    ' 4.5V3"/></svg>'
)

_DEL_D = (
    "M14.74 9l-.346 9m-4.788 0L9.26 9m9.968-3.21c.342.052"
    ".682.107 1.022.166m-1.022-.165L18.16 19.673a2.25 2.25"
    " 0 01-2.244 2.077H8.084a2.25 2.25 0 01-2.244-2.077L4"
    ".772 5.79m14.456 0a48.108 48.108 0 00-3.478-.397m-12"
    " .562c.34-.059.68-.114 1.022-.165m0 0a48.11 48.11 0 01"
    "3.478-.397m7.5 0v-.916c0-1.18-.91-2.164-2.09-2.201a51"
    ".964 51.964 0 00-3.32 0c-1.18.037-2.09 1.022-2.09 2.2"
    "01v.916m7.5 0a48.667 48.667 0 00-7.5 0"
)
SVG_DELETE = (
    '<svg fill="none" stroke="currentColor" stroke-width="2"'
    ' viewBox="0 0 24 24">'
    f'<path stroke-linecap="round" stroke-linejoin="round" d="{_DEL_D}"/></svg>'
)

SVG_BACK = (
    '<svg fill="none" stroke="currentColor" stroke-width="2"'
    ' viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round"'
    ' d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18"/></svg>'
)

_EDIT_D = (
    "M16.862 4.487l1.687-1.688a1.875 1.875 0 1 1 2.652 2.652"
    "L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685"
    "a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931z"
    "M19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21"
    "H5.25A2.25 2.25 0 0 1 3 18.75V8.25"
    "A2.25 2.25 0 0 1 5.25 6H10"
)
SVG_EDIT = (
    '<svg fill="none" stroke="currentColor" stroke-width="2"'
    ' viewBox="0 0 24 24">'
    f'<path stroke-linecap="round" stroke-linejoin="round" d="{_EDIT_D}"/></svg>'
)

SVG_UPLOAD_CLOUD_SM = (
    '<svg width="16" height="16" fill="none" stroke="currentColor"'
    ' stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round"'
    ' stroke-linejoin="round" d="M3 16.5v2.25'
    "A2.25 2.25 0 0 0 5.25 21h13.5"
    "A2.25 2.25 0 0 0 21 18.75V16.5"
    "m-13.5-9L12 3m0 0l4.5 4.5"
    'M12 3v13.5"/></svg>'
)

SVG_UPLOAD_CLOUD = (
    '<svg width="48" height="48" fill="none" stroke="currentColor"'
    ' stroke-width="1.5" viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round"'
    ' d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3'
    "M6.75 19.5a4.5 4.5 0 0 1-1.41-8.775"
    " 5.25 5.25 0 0 1 10.338-2.32"
    " 3.75 3.75 0 0 1 3.572 5.345"
    ' 4.5 4.5 0 0 1-2.76 5.75"/></svg>'
)

SVG_COPY = (
    '<svg width="14" height="14" fill="none"'
    ' stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round"'
    ' d="M8.25 7.5V6.108c0-1.135.845-2.098 1.976-2.192'
    ".373-.03.748-.057 1.123-.08M15.75 18H18a2.25 2.25 0"
    " 0 0 2.25-2.25V6.108c0-1.135-.845-2.098-1.976-2.192"
    "a48.424 48.424 0 0 0-1.123-.08M15.75 18.75v-1.875a3.375"
    " 3.375 0 0 0-3.375-3.375h-1.5a1.125 1.125 0 0 1-1.125"
    "-1.125v-1.5A3.375 3.375 0 0 0 6.375 7.5H5.25m11.9-3.664"
    "A2.251 2.251 0 0 0 15 2.25h-1.5a2.251 2.251 0 0 0-2.15"
    " 1.586m5.8 0c.065.21.1.433.1.664v.75h-6V4.5c0-.231.035"
    "-.454.1-.664M6.75 7.5H4.875c-.621 0-1.125.504-1.125"
    " 1.125v12c0 .621.504 1.125 1.125 1.125h9.75c.621 0"
    ' 1.125-.504 1.125-1.125V16.5a9 9 0 0 0-9-9z"/></svg>'
)

SVG_UPLOAD_BTN = (
    '<svg fill="none" stroke="currentColor" stroke-width="2"'
    ' viewBox="0 0 24 24"><path stroke-linecap="round"'
    ' stroke-linejoin="round" d="M3 16.5v2.25'
    "A2.25 2.25 0 0 0 5.25 21h13.5"
    "A2.25 2.25 0 0 0 21 18.75V16.5"
    "m-13.5-9L12 3m0 0l4.5 4.5"
    'M12 3v13.5"/></svg>'
)

SVG_RENAME = (
    '<svg fill="none" stroke="currentColor" stroke-width="2"'
    ' viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round"'
    ' d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652'
    " 2.652L6.832 19.82a4.5 4.5 0 0 1-1.897 1.13l-2.685.8"
    " .8-2.685a4.5 4.5 0 0 1 1.13-1.897L16.863 4.487Z"
    '"/></svg>'
)

SVG_CM_UPLOAD = (
    '<svg width="28" height="28" fill="none"'
    ' stroke="currentColor" stroke-width="1.5"'
    ' viewBox="0 0 24 24"><path stroke-linecap="round"'
    ' stroke-linejoin="round"'
    ' d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5'
    " A2.25 2.25 0 0 0 21 18.75V16.5m-13.5-9L12 3"
    ' m0 0l4.5 4.5M12 3v13.5"/></svg>'
)

SVG_FILERS = (
    '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round" '
    'd="M5 12h14M5 12a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v4'
    "a2 2 0 01-2 2M5 12a2 2 0 00-2 2v4a2 2 0 002 2h14a2 2 0 002-2"
    'v-4a2 2 0 00-2-2m-2-4h.01M17 16h.01"/></svg>'
)

SVG_FOLDER_PLUS = (
    '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round"'
    ' d="M12 10.5v6m3-3H9m4.06-7.19l-2.12-2.12a1.5 1.5 0 00-1.061-.44'
    "H4.5A2.25 2.25 0 002.25 6v12a2.25 2.25 0 002.25 2.25h15A2.25"
    ' 2.25 0 0021.75 18V9a2.25 2.25 0 00-2.25-2.25h-5.379a1.5 1.5 0 01-1.06-.44z"/></svg>'
)

SVG_FILE_PLUS = (
    '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round"'
    ' d="M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125'
    " 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25"
    "m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25"
    "c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504"
    ' 1.125-1.125V11.25a9 9 0 00-9-9z"/></svg>'
)

SVG_HELM = (
    '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round"'
    ' d="M10.5 6a7.5 7.5 0 107.5 7.5h-7.5V6z"/>'
    '<path stroke-linecap="round" stroke-linejoin="round"'
    ' d="M13.5 10.5H21A7.5 7.5 0 0013.5 3v7.5z"/></svg>'
)

SVG_LINK = (
    '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round"'
    ' d="M13.19 8.688a4.5 4.5 0 011.242 7.244l-4.5 4.5a4.5 4.5'
    " 0 01-6.364-6.364l1.757-1.757m13.35-.622l1.757-1.757a4.5"
    ' 4.5 0 00-6.364-6.364l-4.5 4.5a4.5 4.5 0 001.242 7.244"/></svg>'
)

SVG_STAR_OUTLINE = (
    '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round"'
    ' d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563'
    " 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602"
    "a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61"
    "l-4.725-2.885a.562.562 0 00-.586 0L6.982 20.54a.562.562 0"
    " 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602"
    'a.562.562 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z"/></svg>'
)

SVG_STAR_FILLED = (
    '<svg fill="currentColor" stroke="currentColor" stroke-width="1" viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round"'
    ' d="M11.48 3.499a.562.562 0 011.04 0l2.125 5.111a.563.563'
    " 0 00.475.345l5.518.442c.499.04.701.663.321.988l-4.204 3.602"
    "a.563.563 0 00-.182.557l1.285 5.385a.562.562 0 01-.84.61"
    "l-4.725-2.885a.562.562 0 00-.586 0L6.982 20.54a.562.562 0"
    " 01-.84-.61l1.285-5.386a.562.562 0 00-.182-.557l-4.204-3.602"
    'a.562.562 0 01.321-.988l5.518-.442a.563.563 0 00.475-.345L11.48 3.5z"/></svg>'
)

SVG_SEARCH = (
    '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round"'
    ' d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196'
    ' a7.5 7.5 0 0010.607 10.607z"/></svg>'
)

SVG_GITHUB = (
    '<svg fill="currentColor" viewBox="0 0 24 24">'
    '<path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8'
    " 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04"
    "-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633"
    " 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236"
    " 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417"
    "-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465"
    "-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322"
    " 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405"
    " 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12"
    " 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475"
    " 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286"
    " 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0"
    '-6.627-5.373-12-12-12"/></svg>'
)

SVG_MOVE = (
    '<svg fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">'
    '<path stroke-linecap="round" stroke-linejoin="round"'
    ' d="M15.75 17.25v3.375c0 .621-.504 1.125-1.125 1.125h-9.5'
    "A1.125 1.125 0 014 20.625V7.875c0-.621.504-1.125 1.125-1.125"
    "H8.25m8.25 3.75l3.75-3.75m0 0l-3.75-3.75M20.25 6.75H11.25"
    '"/></svg>'
)
