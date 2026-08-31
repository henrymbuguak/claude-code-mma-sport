# Design

## Visual identity

Dark theme by default, bold/high-contrast, fitting a combat-sports product.

**Colors**
| Purpose | Hex |
|---|---|
| Background | `#0B0B0D` |
| Surface/card | `#18181B` |
| Primary accent (actions, links, highlights) | `#E31C3D` |
| Secondary accent (badges, "live" indicators — use sparingly) | `#F2B705` |
| Text primary | `#F5F5F5` |
| Text secondary | `#A1A1AA` |
| Success / upcoming | `#22C55E` |
| Live / warning | `#EF4444` |

**Typography**
- Headings (event names, fighter names): bold condensed sans — e.g.
  **Oswald** or **Bebas Neue** — for a broadcast/poster feel.
- Body (schedules, descriptions, everything read at length): a clean,
  highly-legible sans — e.g. **Inter**.
- Numerals (records, dates, countdowns): use tabular figures so they align.

This is a starting direction, not final brand guidelines — revisit once
real UI is being built.

## Responsive design

**Mobile-first**: design and build for small screens first, then scale up
to tablet/desktop. Fits how most sports fans check schedules (on the go,
on a phone).

## Accessibility

Target **WCAG 2.1 AA**. In particular:
- Color contrast must meet AA ratios (4.5:1 normal text, 3:1 large
  text/UI components) — check any accent color combos above against their
  background before using them for text.
- Full keyboard navigation and visible focus states.
- Semantic HTML and proper heading structure over div soup.
- Alt text for fighter photos/images; don't convey info by color alone
  (e.g. "live" status needs a text/icon indicator, not just red).
- Screen reader support for dynamic content (e.g. live score/status
  updates).

## Reference documents

None yet. Add links/paths here as they're created (brand guide,
wireframes, competitor sites used as style references).
