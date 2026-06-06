# Timetable Planner — Design Plan

Feature: let a student pick courses/sections for a term and see them on a weekly
grid, with live conflict detection and seat awareness. Built on the scraped seat
data (`Server/data/eng-timetable-{year}-{sem}.json`).

## 1. Data we have

Per term file (`eng-timetable-2568-1.json`, `eng-timetable-2568-2.json`):
```jsonc
{
  "meta": { "year": "2568", "semester": "1", ... },
  "count": 1468,
  "sections": [
    {
      "prefix": "EE", "group": "engineering",
      "course": "EE211", "course_name": "Electric Circuit Theory",
      "section": "235A",
      "seat_total": "80", "seat_taken": "67", "seat_left": "13",
      "status": "On",          // On | Freeze | Close
      "type": "LECT",          // LECT | LAB | PRAC | RWS | R/W/C
      "day": "Mon", "time": "8:40-11:00", "room": "RA8506"
    }
  ]
}
```
Each row is **one meeting**. A registrable **section** = all rows sharing
`(course, section)` — a section can meet on several days / have LECT+LAB rows.

Not in the data: **credits** (seat3 detail omits them). Plan: build a
`course_code → credits` map from `Server/curriculum_database.json` (offline, no
extra requests) and attach. Service courses (GE/EN/MA/PH) also have credits in
that file; anything missing shows `-`.

## 2. Derived model (frontend `lib/timetable.ts`)

```ts
type Meeting = { day: Day; start: number; end: number; room: string; type: string }; // start/end = minutes from 00:00
type Section = { course: string; courseName: string; section: string; group: 'engineering'|'service';
                 status: 'On'|'Freeze'|'Close'; seatLeft: number; seatTotal: number;
                 credits: number|null; meetings: Meeting[] };
type Course  = { code: string; name: string; prefix: string; group; credits: number|null; sections: Section[] };
```
Build: group rows by course → by section; parse `time` → minutes.

### Conflict rule
Two chosen sections conflict if any meeting pair shares a `day` and overlaps:
`aStart < bEnd && bStart < aEnd`.

## 3. API (FastAPI, same `/api/v1` origin)

- `GET /api/v1/timetable/terms` → `[{year, semester, label, count}]`
- `GET /api/v1/timetable?year=2568&semester=1` → the term's `sections` (+ credits joined)

Implementation: load the term JSON files + a credits map at startup; return as-is.
~30 lines. (Alternative: serve the JSON as a static asset and skip the API — but
the API keeps the credits-join server-side and matches the existing pattern.)

## 4. UI / routes

App gets a second route + a top-level switch in the brand bar:
- `/`           → degree-plan map (existing)
- `/timetable`  → planner (new, `Web/app/timetable/page.tsx`)

### Planner layout
```
┌───────────────────────────────────────────────────────────────┐
│ TopBar:  ◆ OneDegree   [ แผนที่หลักสูตร | จัดตารางเรียน ]   term ▾ │
├──────────────┬────────────────────────────────────────────────┤
│ COURSE PICKER│  WEEKLY GRID  (Mon–Sat × 8:00–21:00)            │
│ search box   │   ┌────┬────┬────┬────┬────┬────┐               │
│ filter: group│ 8 │EE211 LECT│    │CS441│   │   │  ← colored    │
│  / prefix    │ 9 │ (purple) │    │     │   │   │    blocks per │
│              │10 │          │    │     │   │   │    course     │
│ ▸ EE211 ···  │11 │          │ …  │     │   │   │               │
│   235A 13/80 │   conflicts flash red (metro impact cue)        │
│   235B  0/27 │                                                 │
│ ▸ CS441 ···  ├────────────────────────────────────────────────┤
│              │ SUMMARY: 5 courses · 17 credits · 0 conflicts   │
└──────────────┴────────────────────────────────────────────────┘
```
- **Picker:** term switch (2568/1, 2568/2); search by code/name; filter by group
  (engineering/service) or prefix. Each course expands to its sections showing
  day/time/room + a seat badge (`13/80`); `Freeze`/`Close` greyed + non-add.
- **Add/remove:** click a section to add; it renders on the grid colored by
  course. Click a block (or section) to remove. Hover a section → ghost preview
  on the grid.
- **Conflicts:** overlapping blocks turn red + listed in the summary; you swap
  sections to resolve (same vibe as the degree-map withdraw cascade).
- **Seats:** show left/total; full sections warn.
- **Persistence:** save chosen sections per term in `localStorage`.

### Style / motion
Reuse `globals.css` tokens — BU purple/orange duotone, rounded cards, springy
add/remove, grid lines echoing the metro timeline. Course blocks = "trains".

### Mobile
Grid scrolls horizontally (sticky time column); picker collapses to a sheet;
or a day-by-day accordion under ~640px.

## 5. Components
```
Web/app/timetable/
  page.tsx                 // state: term, chosen[], data fetch
  components/
    TermSwitch.tsx
    CoursePicker.tsx       // search + filter + course list
    SectionRow.tsx         // day/time/room + seat badge + add/remove
    WeekGrid.tsx           // grid + blocks + conflict highlight
    SummaryBar.tsx         // courses / credits / conflicts
Web/lib/timetable.ts       // types, time parse, grouping, conflict, credits join
```
Plus a small mode switch in `TopBar.tsx` (links `/` ↔ `/timetable`).

## 6. Build order
1. API routes + credits map (Server).
2. Route + nav switch + data fetch (Web).
3. `lib/timetable.ts` (group + conflict).
4. CoursePicker + SectionRow.
5. WeekGrid + conflict highlight + SummaryBar.
6. Metro styling + mobile responsive + localStorage persist.

## 7. Open questions
1. Credits via curriculum-DB join — OK? (recommended)
2. Show Closed/Frozen sections greyed, or hide them? (recommend show, greyed)
3. Picker scope: all 14 prefixes searchable, or pre-filter to one department? (recommend searchable, with group/prefix filter)
4. Persist the built timetable in localStorage? (recommend yes)
5. Export later (PNG/print/share link)? (later phase)
6. Free electives from other faculties (other prefixes) — add now or later? (later; needs more scraping)
```
