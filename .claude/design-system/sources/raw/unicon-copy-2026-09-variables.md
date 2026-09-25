# DESIGN.md -- Paragon Design System - Unicon Copy

<!-- extraction-meta
source: Figma file "Paragon Design System - Unicon Copy"
scope: 13 page(s)
date: 2026-09-24
nodes-scanned: 49266
generator: figma-cli extract
-->

## 1. Variables

Real Figma variable collections — the authoritative tokens (names, modes, values). These come straight from the file, unlike the sampled palette above. `figma-cli import` can recreate them as variables.

### Collection: Primitives  ·  104 variables  ·  modes: Mode 1

| Variable | Type | Mode 1 |
|---|---|---|
| white | COLOR | `#ffffff` |
| black | COLOR | `#000000` |
| accent/a | COLOR | `#00bbf9` |
| accent/b | COLOR | `#ffee88` |
| gray/100 | COLOR | `#ebebeb` |
| gray/200 | COLOR | `#cccccc` |
| gray/300 | COLOR | `#adadad` |
| gray/400 | COLOR | `#8f8f8f` |
| gray/500 | COLOR | → var:gray/base |
| gray/600 | COLOR | `#5c5c5c` |
| gray/700 | COLOR | `#454545` |
| gray/800 | COLOR | `#333333` |
| gray/900 | COLOR | `#212529` |
| primary/100 | COLOR | `#f0f3f5` |
| gray/base | COLOR | `#707070` |
| primary/200 | COLOR | `#c2cbd5` |
| primary/300 | COLOR | `#8598aa` |
| primary/400 | COLOR | `#476480` |
| primary/500 | COLOR | → var:primary/base |
| primary/600 | COLOR | `#092b4d` |
| primary/700 | COLOR | `#082644` |
| primary/800 | COLOR | `#082440` |
| primary/900 | COLOR | `#07223c` |
| primary/base | COLOR | `#0a3055` |
| brand/100 | COLOR | `#f9f0f5` |
| brand/200 | COLOR | `#e7bfd4` |
| brand/300 | COLOR | `#ce80aa` |
| brand/400 | COLOR | `#b6407f` |
| brand/500 | COLOR | → var:brand/base |
| brand/600 | COLOR | `#8d004c` |
| brand/700 | COLOR | `#7e0043` |
| brand/800 | COLOR | `#76003f` |
| brand/900 | COLOR | `#6e003b` |
| secondary/100 | COLOR | `#f4f4f4` |
| secondary/200 | COLOR | `#d1d1d1` |
| secondary/300 | COLOR | `#a2a2a2` |
| secondary/400 | COLOR | `#747474` |
| secondary/500 | COLOR | → var:secondary/base |
| secondary/600 | COLOR | `#3e3e3e` |
| secondary/700 | COLOR | `#373737` |
| secondary/800 | COLOR | `#343434` |
| secondary/900 | COLOR | `#303030` |
| success/100 | COLOR | `#f1f8f5` |
| success/200 | COLOR | `#c5e0d4` |
| success/300 | COLOR | `#8bc1a9` |
| success/400 | COLOR | `#51a17e` |
| success/500 | COLOR | → var:success/base |
| success/600 | COLOR | `#15754b` |
| success/700 | COLOR | `#126842` |
| success/800 | COLOR | `#11623e` |
| success/900 | COLOR | `#105b3a` |
| info/100 | COLOR | `#f0f6fa` |
| info/200 | COLOR | `#bfdbea` |
| info/300 | COLOR | `#80b6d5` |
| info/400 | COLOR | `#4092bf` |
| info/500 | COLOR | → var:info/base |
| info/600 | COLOR | `#006299` |
| info/700 | COLOR | `#005788` |
| brand/base | COLOR | `#9d0054` |
| info/800 | COLOR | `#005280` |
| info/900 | COLOR | `#004c77` |
| danger/100 | COLOR | `#fbf2f3` |
| danger/200 | COLOR | `#f0cbce` |
| secondary/base | COLOR | `#454545` |
| danger/300 | COLOR | `#e1969d` |
| danger/400 | COLOR | `#d2626b` |
| danger/500 | COLOR | → var:danger/base |
| danger/600 | COLOR | `#b02934` |
| danger/700 | COLOR | `#9c242e` |
| success/base | COLOR | `#178253` |
| danger/800 | COLOR | `#92222c` |
| danger/900 | COLOR | `#892029` |
| warning/100 | COLOR | `#fffdf0` |
| warning/200 | COLOR | `#fff6bf` |
| warning/300 | COLOR | `#ffec80` |
| info/base | COLOR | `#006daa` |
| warning/400 | COLOR | `#ffe340` |
| warning/500 | COLOR | → var:warning/base |
| warning/600 | COLOR | `#e6c300` |
| danger/base | COLOR | `#c32d3a` |
| warning/700 | COLOR | `#ccae00` |
| warning/800 | COLOR | `#bfa300` |
| warning/900 | COLOR | `#b39800` |
| light/100 | COLOR | `#fdfdfd` |
| warning/base | COLOR | `#ffd900` |
| light/200 | COLOR | `#f8f7f6` |
| light/300 | COLOR | `#f0eeed` |
| light/400 | COLOR | `#e9e6e4` |
| light/500 | COLOR | → var:light/base |
| light/600 | COLOR | `#cbc7c5` |
| light/700 | COLOR | `#b4b1af` |
| light/800 | COLOR | `#a9a6a4` |
| light/900 | COLOR | `#9e9b99` |
| dark/100 | COLOR | `#f2f3f3` |
| dark/200 | COLOR | `#c9cfcb` |
| dark/300 | COLOR | `#939f97` |
| dark/400 | COLOR | `#5d6f63` |
| dark/500 | COLOR | → var:dark/base |
| dark/600 | COLOR | `#23392a` |
| dark/700 | COLOR | `#1f3226` |
| dark/800 | COLOR | `#1d2f23` |
| dark/900 | COLOR | `#1b2c21` |
| light/base | COLOR | `#e1dddb` |
| dark/base | COLOR | `#273f2f` |

### Collection: Semantic  ·  60 variables  ·  modes: Mode 1

| Variable | Type | Mode 1 |
|---|---|---|
| theme/bg/primary | COLOR | → var:primary/100 |
| theme/border/primary | COLOR | → var:primary/200 |
| theme/hover/primary | COLOR | → var:primary/700 |
| theme/active/primary | COLOR | → var:primary/900 |
| theme/bg/brand | COLOR | → var:brand/100 |
| theme/border/brand | COLOR | → var:brand/200 |
| theme/hover/brand | COLOR | → var:brand/700 |
| theme/active/brand | COLOR | → var:brand/900 |
| theme/bg/secondary | COLOR | → var:secondary/100 |
| theme/border/secondary | COLOR | → var:secondary/200 |
| theme/hover/secondary | COLOR | → var:secondary/700 |
| theme/active/secondary | COLOR | → var:secondary/900 |
| theme/bg/success | COLOR | → var:success/100 |
| theme/border/success | COLOR | → var:success/200 |
| theme/hover/success | COLOR | → var:success/700 |
| theme/active/success | COLOR | → var:success/900 |
| theme/bg/info | COLOR | → var:info/100 |
| theme/border/info | COLOR | → var:info/200 |
| theme/hover/info | COLOR | → var:info/700 |
| theme/active/info | COLOR | → var:info/900 |
| theme/bg/danger | COLOR | → var:danger/100 |
| theme/border/danger | COLOR | → var:danger/200 |
| theme/hover/danger | COLOR | → var:danger/700 |
| theme/active/danger | COLOR | → var:danger/900 |
| theme/bg/warning | COLOR | → var:warning/100 |
| theme/border/warning | COLOR | → var:warning/200 |
| theme/hover/warning | COLOR | → var:warning/700 |
| theme/active/warning | COLOR | → var:warning/900 |
| theme/bg/light | COLOR | → var:light/100 |
| theme/border/light | COLOR | → var:light/200 |
| theme/hover/light | COLOR | → var:light/700 |
| theme/active/light | COLOR | → var:light/900 |
| theme/bg/dark | COLOR | → var:dark/100 |
| theme/border/dark | COLOR | → var:dark/200 |
| theme/hover/dark | COLOR | → var:dark/700 |
| theme/active/dark | COLOR | → var:dark/900 |
| theme/bg/gray | COLOR | → var:gray/100 |
| theme/border/gray | COLOR | → var:gray/200 |
| theme/hover/gray | COLOR | → var:gray/700 |
| theme/active/gray | COLOR | → var:gray/900 |
| border | COLOR | → var:gray/200 |
| theme/bg/base | COLOR | → var:white |
| active | COLOR | → var:white |
| text/primary | COLOR | → var:gray/700 |
| text/secondary | COLOR | → var:gray/base |
| text/disabled | COLOR | → var:gray/300 |
| text/on-dark | COLOR | → var:white |
| text/on-light | COLOR | → var:black |
| theme/default/primary | COLOR | → var:primary/base |
| theme/default/brand | COLOR | → var:brand/base |
| theme/default/secondary | COLOR | → var:secondary/base |
| theme/default/success | COLOR | → var:success/base |
| theme/default/info | COLOR | → var:info/base |
| theme/default/danger | COLOR | → var:danger/base |
| theme/default/warning | COLOR | → var:warning/base |
| theme/default/light | COLOR | → var:light/base |
| theme/default/dark | COLOR | → var:dark/base |
| theme/default/gray | COLOR | → var:gray/base |
| text/50-black | COLOR | `#00000080` |
| text/50-white | COLOR | `#ffffff80` |

### Collection: Spacing  ·  13 variables  ·  modes: Mode 1

| Variable | Type | Mode 1 |
|---|---|---|
| spacer/0 | FLOAT | 0 |
| spacer/1 | FLOAT | 4 |
| spacer/1-5 | FLOAT | 6 |
| spacer/2 | FLOAT | 8 |
| spacer/2-5 | FLOAT | 12 |
| spacer/3 | FLOAT | 16 |
| spacer/3-5 | FLOAT | 20 |
| spacer/4 | FLOAT | 24 |
| spacer/4-5 | FLOAT | 32 |
| spacer/5 | FLOAT | 48 |
| spacer/5-5 | FLOAT | 64 |
| spacer/6 | FLOAT | 80 |
| grid/gutter-width | FLOAT | 24 |

### Collection: Typography  ·  26 variables  ·  modes: Mode 1

| Variable | Type | Mode 1 |
|---|---|---|
| font-size/base | FLOAT | 18 |
| font-size/lg | FLOAT | 22.5 |
| font-size/sm | FLOAT | 15.75 |
| font-size/xs | FLOAT | 13.5 |
| font-size/micro | FLOAT | 11 |
| font-size/h1 | FLOAT | 40 |
| font-size/h1-mobile | FLOAT | 36 |
| font-size/h2 | FLOAT | 32 |
| font-size/h3 | FLOAT | 22 |
| font-size/h4 | FLOAT | 18 |
| font-size/h5 | FLOAT | 14 |
| font-size/h6 | FLOAT | 12 |
| font-size/display-1 | FLOAT | 60 |
| font-size/display-2 | FLOAT | 78 |
| font-size/display-3 | FLOAT | 90 |
| font-size/display-4 | FLOAT | 120 |
| line-height/base | FLOAT | 28 |
| line-height/lg | FLOAT | 34 |
| line-height/sm | FLOAT | 24 |
| line-height/micro | FLOAT | 15 |
| font-weight/light | FLOAT | 300 |
| font-weight/normal | FLOAT | 400 |
| font-weight/semi-bold | FLOAT | 500 |
| font-weight/bold | FLOAT | 700 |
| font-weight/lighter | FLOAT | 200 |
| font-weight/bolder | FLOAT | 800 |

### Collection: Sizing  ·  22 variables  ·  modes: Mode 1

| Variable | Type | Mode 1 |
|---|---|---|
| border/width | FLOAT | 1 |
| border-radius/base | FLOAT | 6 |
| border-radius/lg | FLOAT | 6.800000190734863 |
| border-radius/sm | FLOAT | 4 |
| border-radius/pill | FLOAT | 800 |
| icon/xs | FLOAT | 16 |
| icon/sm | FLOAT | 20 |
| icon/md | FLOAT | 24 |
| icon/lg | FLOAT | 28 |
| avatar/xs | FLOAT | 24 |
| avatar/sm | FLOAT | 36 |
| avatar/base | FLOAT | 48 |
| avatar/lg | FLOAT | 64 |
| avatar/xl | FLOAT | 96 |
| container/xs | FLOAT | 464 |
| container/sm | FLOAT | 708 |
| container/md | FLOAT | 952 |
| container/lg | FLOAT | 1192 |
| container/xl | FLOAT | 1440 |
| avatar/xxl | FLOAT | 184 |
| avatar/huge | FLOAT | 300 |
| icon/inline | FLOAT | 12.800000190734863 |

### Collection: Paragon Categories  ·  7 variables  ·  modes: Components

| Variable | Type | Components |
|---|---|---|
| Actions | STRING | "Button, ButtonGroup, IconButton, IconButton.Toggle, Hyperlink, MailtoLink, StatefulButton, ActionRow" |
| Form Controls | STRING | "Form, Form.Control, Form.Group, Form.Label, Form.Control.Feedback, Input, Input.Inline, InputGroup, Autosuggest, Checkbox, Radio, Switch, SearchField, SelectMenu, SelectableBox, Multiselect, Dropzone, ColorPicker" |
| Indicators & Badges | STRING | "Badge, Bubble, Avatar, AvatarButton, Chip, ChipCarousel, Spinner, ProgressBar, Skeleton, Annotation, Icon, Image, Figure" |
| Feedback & Messaging | STRING | "Alert, Toast, Tooltip, Popover, ProductTour, Overlay" |
| Cards and Content | STRING | "Card, DataTable, Collapsible, ContentBlockEmpty, ContentBlockError, Truncate" |
| Navigation | STRING | "NavBar, Nav, Breadcrumbs, Pagination, Tabs, MenuItem, Menu, Dropdown, Stepper" |
| Layouts & Surfaces | STRING | "Modal, Sheet, Carousel, PageBanner, Container, Layout, Stack, Scrollable, Sticky, TransitionReplace" |
