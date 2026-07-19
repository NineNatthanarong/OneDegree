# VIDEO.md — OneDegree Launch Film

> A motion brief for generating the OneDegree hero video with Claude Design.
> Goal: in 60 fast, fun seconds, stop a thumb mid-scroll and make a stranger *need* to open it.

---

## 0. North Star

**One line the whole film must earn:**

> "เห็นทั้งเส้นทางการเรียน จากปี 1 สู่วันรับปริญญา — ในหน้าเดียว."
> *(See your entire degree, from year one to graduation day — on one screen.)*

If a viewer finishes the cut and gets that in their gut, the video worked. Everything below serves that single feeling.

**Two tools, one continuous move.** OneDegree is two surfaces and the film should never feel like it cut between two apps. It's one camera move: pull back to see the **whole degree** (the 4-year metro map), then zoom *into a single station* and watch it bloom open into the **weekly timetable** for that term. Big picture → this week → back out to graduation. The zoom is the seam, and it must be invisible.

**The hook (first 3 seconds, non-negotiable):** open on chaos — a student drowning in browser tabs — then *snap* into a single, breathing metro map. Problem → relief. That contrast is the whole pitch.

---

## 1. The Feeling

OneDegree is a Thai university degree planner drawn as a **subway map**. Each semester is a station. Each course is a stop. Prerequisite chains are the rail lines. Graduation is the terminus.

There is also a second view: the **Timetable Planner** (`/timetable`) — a weekly Mon–Sat grid where you actually build *next term's* schedule. Pick a degree plan and it auto-fills the whole term; drag a course onto the week and it shows you every conflict-free slot in green; clashes light up red. If the map is the *whole journey*, the timetable is *this week's train*. The film shows both as one zoom.

The emotional target, in order:
1. **Overwhelm** (0–3s) — the problem everyone recognizes.
2. **Awe** (3–13s) — the map draws itself like a transit system coming alive.
3. **Delight** (13–25s) — you *touch* it; it responds with spring and pulse.
4. **Power** (25–32s) — pull one course and watch the ripple. You understand consequences instantly.
5. **Magic** (32–50s) — zoom into one station; it opens into a weekly timetable that *fills itself* from your degree plan, and slots snap into place conflict-free.
6. **Belonging** (50–60s) — pull back; the line reaches รับปริญญา (graduation). It feels like *your* journey.

Energy = Gen-Z, fast, fun, beat-driven. Palette = formal, institutional, trustworthy. **The motion parties; the color stays sober.** That split is the magic — punchy enough to stop a thumb mid-scroll, clean enough that a dean would trust it. Never a toy, never boring.

---

## 2. Visual DNA

Pull these straight from the live product (`Web/app/globals.css`) so the film and the app are indistinguishable.

### Color (Bangkok University official CI — duotone)
| Token | Hex | Role in film |
|---|---|---|
| `--bu` purple | `#3F194B` | The spine / main rail. Brand. Structure. |
| `--accent` orange | `#E56436` | Energy. The light that travels the rail. CTAs. |
| `--blue` purple-mid | `#7B5387` | Prerequisite network lines |
| `--red` | `#E03131` | Impact / "this breaks if you pull it" |
| `--gold` amber | `#F9A526` | Ordering warning |
| `--paper` | `#F8F8F8` | Background. Clean, off-white, map-paper |
| `--paper-3` | `#FFFFFF` | Station / card surfaces |
| `--ink` | `#1D1E20` | Text |

**Rule:** purple = the skeleton, orange = the heartbeat. Two colors do the heavy lifting. Resist rainbow. The discipline is the brand.

### Type
- **Thai display / titles:** **Kanit** (400–700). Bold, modern, the look of the launch banner.
- **UI text:** IBM Plex Sans Thai.
- **Mono accents** (course codes, numbers ticking): JetBrains Mono.
- Thai typography law: line-height ≥ 1.4, **never** letter-space Thai, control wraps with hard breaks.

### Motion tokens (use these exact curves — they ARE the product's feel)
| Curve | Value | Use |
|---|---|---|
| Spring | `cubic-bezier(.34, 1.56, .64, 1)` | every press, pop, card entrance (overshoot = alive) |
| Punch | `cubic-bezier(.5, 1.85, .4, 1)` | the loud stuff — title slams, zoom-bounces, beat hits (big overshoot, snappy) |
| Ease | `cubic-bezier(.2, .7, .2, 1)` | draws, fades, camera moves |
| Snap-out | `cubic-bezier(.7, 0, .84, 0)` | whip-pans / exits — fast accelerate, gone in 3–5 frames |

**Anticipation rule (the fun lives here):** before any big launch, pull back the *opposite* way for ~80ms first (squash down before a pop, drift left before a whip-right). Then squash-stretch on the move and overshoot on the land. Wind-up → snap → settle. That micro-recoil is what reads as "fun" instead of "smooth".

### Signature animations (timings lifted from the real CSS — match them)
- **Spine pulse** — orange light travels the purple rail, `4.5s` loop. *This is the heartbeat of the whole film.*
- **Station breathe** — semester rings expand/contract, `3.4s` ease-in-out.
- **Ink draw** — prerequisite arcs draw on like pen on paper, `1100ms` ease.
- **Arc march** — dashed concurrent lines crawl, `0.9s` linear loop.
- **Arc throb** — affected arcs pulse when something changes, `1.6s`.
- **Chip pop** — course cards spring in, `260ms` spring.
- **Map fade** — whole map reveals, `520ms` ease.
- **Stop strike** — a withdrawn course gets struck through, `360ms`.

**Timetable view animations (for the second act):**
- **Block pop** — a course lands on the week grid, `220ms` spring.
- **Drop-hint pulse** — green "you can put it here" slots breathe, `1.4s` ease-in-out. *(green = the only non-brand color, and only here — it means "safe slot".)*
- **Toast in** — purple confirmation toast slides up, `220ms` spring.
- **Sheet in** — mobile section-chooser slides up as a bottom sheet, `240ms` spring.

**Course colors (timetable only):** blocks are tinted by a per-course HSL hash so each subject is distinguishable. This is the *one* place multi-color is allowed — keep them **muted/pastel**, low saturation, so the grid reads calm, not a rainbow. The purple spine and orange energy still own the rest of the film.

---

## 3. Soundtrack & Rhythm

- **Genre:** fast, fun, kinetic — UK garage / jersey-club bounce / hyperpop-lite. **BPM ~145–150.** Skippy hi-hats, fat sub bass, a hook you bob your head to. Energetic, not chill.
- **Everything cuts on the beat.** Hard cuts, zoom-punches, and type slams land on the kick/snare — never between beats. If a move doesn't sit on the grid, nudge it until it does. The whole film should feel *quantized*.
- **Sound design = the star.** Map the audio to the motion:
  - *Glitchy stutter + sub drop* on the tab-chaos → map snap (the beat DROPS here — this is the "turn it up" moment).
  - *Plucky arp machine-gunning up* as stations light the rail (fast, one note per stop, climbing).
  - *Tactile click + spring boing + tiny vinyl scratch* on every card pop and drag.
  - *Riser → beat-cut-to-silence → impact* before the "pull a course" ripple.
  - *Deep zoom-whoosh + tape-stop + filter sweep* on the station→week-grid dive.
  - *Rapid-fire arp burst* as the timetable auto-fills (a note per block, like a combo counter), then a *crisp snap* when a dragged course locks into a green slot.
- **Contrast is the trick.** Stack speed for ~50s, then a *full beat-cut to silence* (0.5s) right before graduation — then the bass blooms back. The pause hits 10× harder after all that energy.
- The kick rides the **spine pulse** — sync the traveling orange light to the beat the whole way through.

---

## ⚡ Motion Energy Pack — the Gen-Z layer

This is the difference between "nice product video" and "wait, run that back." Layer it on top of every beat. Color stays formal; **the motion does the partying.**

### Pacing law
- **Hook in 1 second**, not three. The beat drops by 0:02.
- **Fast stretches = 0.6–1.2s per shot/move.** Stack them. Momentum > clarity in the build.
- **Then HOLD.** After ~5 quick hits, freeze one hero frame for a full beat. Fast-fast-fast → *stop*. The contrast is the whole vibe — constant speed is just noise.
- Nothing fades slowly in the energy stretches. Things **arrive** — snap, slam, pop.

### Signature moves (reuse these everywhere)
- **Zoom-bounce** — punch-in that overshoots ~8% then settles (`Punch` curve). On every reveal.
- **Whip-pan / whip-cut** — 3–5 frame motion-blurred swipe between beats. Direction-match across the cut.
- **Match-cut on circles** — the station ring ↔ a clock face ↔ the "O" in OneDegree ↔ the auto-fill button. Round things morph into each other.
- **Smear / echo trails** — fast-moving chips leave 2–3 ghost frames. Reads as speed.
- **Squash & stretch** — anything that lands deforms on impact then snaps round. Exaggerate it.
- **Beat-shake** — a 2px whole-frame kick-shake on big hits. Subtle, rhythmic, addictive.
- **Speed ramp** — ramp INTO a move at 2×, hold the peak, whip out. Especially the dive (Beat 7).

### Kinetic type (Gen-Z captions)
- Words **slam in** one at a time on the beat: scale 1.25 → 1 with `Punch`, tiny ±2° rotate jitter, hard stop.
- **Numbers roll/tick** in JetBrains Mono — credits count up fast (`0 → 19 หน่วยกิต`), ปี 1→4 rolls like an odometer.
- Highlight key words by snapping them to **orange** mid-sentence (one word, one beat).
- **Thai stays whole-word** — animate per word, *never* per glyph (sara/tone marks break). Latin/numbers can go per-character.
- Keep captions big, bottom-third, safe for muted autoplay.

### Per-beat energy move
| Beat | The fast/fun hit |
|---|---|
| 1 Problem | Tabs jitter on the hi-hats, speed-ramp faster and faster → glitch-stutter freeze |
| 2 Snap | Whole frame vacuums to one orange dot **on the drop**, 4-frame freeze, title SLAMS in with squash |
| 3 Build | Stations "deal in" like cards machine-gunning up the rail, smear trails, `ปี 1→4` odometer rolls |
| 4 Heartbeat | Orange pulse rips a **fast full lap** before settling to tempo; 2px beat-shake per kick; punch-in on "ก่อนหลัง" |
| 5 Drag | Chip yoinks up with anticipation recoil + motion smear; drop = squash-splat + a ring shockwave |
| 6 Ripple | Beat-cut to 2 black frames → red SLAMS down the chain as a rapid combo; screen-shake on impact |
| 7 Dive | Tape-stop + 2× speed-ramp through the zoom; **match-cut** station ring → grid |
| 8 Auto-fill | Blocks rapid-fire like a **combo counter**; credits tick up fast beside the grid; arp machine-guns |
| 9 Drag-snap | Green slots strobe-pulse quick; snap = hard click + 1-frame white flash; clash = red shake |
| 10 Terminus | Whip-zoom OUT, then **SLAM to silence + hold** (the breath); 🎓 pops with big overshoot |
| 11 CTA | Logo bounces in on `Punch`; URL types out fast in mono; last frame loops back to Beat 1 |

### Replay bait
- **Seamless loop:** Beat 11's final frame == Beat 1's first frame, so it auto-replays clean (TikTok/Reels keep looping = more watch time).
- Optional **0.4s "rewind" micro-recap** before the CTA — blink-fast montage of the 5 hero hits. Gives the "run it back" instinct something to chew.
- Hide one tiny easter-egg frame (a 🎓 on a random station) for the rewatchers.

---

## 4. Storyboard — 60s cut

Eleven beats. Timecodes are targets. Every beat names SHOT · MOTION · TEXT · SFX. Beats 1–6 = the **map** (your whole degree). Beat 7 is the **dive**. Beats 8–9 = the **timetable** (next term). Beats 10–11 = payoff + CTA.

### Beat 1 — The Problem · `0:00–0:02`
- **SHOT:** Tight on a screen littered with 6+ overlapping browser tabs (course site, free-elective site, registrar, PDF curriculum). Cursor frantic. Slight desaturation.
- **MOTION:** Tabs jitter, a PDF scrolls too fast, cursor darts. Mild chaos, handheld micro-shake.
- **TEXT:** none yet — let the mess speak. (Optional tiny Thai: "เทอมหน้าลงอะไรดี?")
- **SFX:** anxious UI clatter, rising tension.

### Beat 2 — The Snap · `0:02–0:06`
- **SHOT:** Everything collapses to a single point of orange light, then explodes outward into the clean paper canvas.
- **MOTION:** All tabs vacuum into one dot (`ease`), 0.4s hold on black/white, then `map-fade` 520ms reveal.
- **TEXT:** wordmark **OneDegree** fades in, Kanit, purple.
- **SFX:** big whoosh + sub drop → silence → first synth pluck.

### Beat 3 — The Map Builds Itself · `0:06–0:13`
- **SHOT:** Hero wide of the metro map. The purple spine draws top-to-bottom; stations (semesters) pop into place one by one up the line; course chips spring onto each station.
- **MOTION:** `ink-draw` the spine, then `chip-pop` (260ms spring) cascades — stagger ~80ms per chip so it ripples. Stations `station-breathe` once they land.
- **TEXT:** ปี 1 → ปี 2 → ปี 3 → ปี 4 labels light up the rail as it climbs.
- **SFX:** arpeggiated plucks climbing in pitch with the stations.

### Beat 4 — The Heartbeat · `0:13–0:19`
- **SHOT:** Slow push-in on the spine. The **orange pulse travels the rail** (`spine-pulse` 4.5s). Prerequisite arcs `ink-draw` between courses across lines.
- **MOTION:** camera dolly along the line (parallax depth between rail / chips / background grid). Arcs draw and connect like circuitry.
- **TEXT:** "เส้นวิชาก่อนหลัง" / *prerequisites, drawn for you*.
- **SFX:** the kick locks to the traveling light. Heartbeat established.

### Beat 5 — You Touch It · `0:19–0:25`
- **SHOT:** A real cursor/finger **drags a course chip** to a new semester. It lifts with a spring, drops, the map re-settles.
- **MOTION:** drag = scale-up + shadow lift (`spring`); on drop, neighbors nudge and re-flow. A drop-target station glows orange.
- **TEXT:** "ลากจัดเทอมเองได้" / *drag to re-plan your terms*.
- **SFX:** pick-up boing, satisfying drop click, soft re-flow shimmer.

### Beat 6 — The Ripple (the money shot) · `0:25–0:32`
- **SHOT:** Cursor pulls/withdraws one early course. A **chain reaction of red** fires downstream — every course that depended on it throbs red, arcs `arc-throb`, struck through with `stop-strike`.
- **MOTION:** 0.5s music dip → the red propagates outward along the arcs like a current, `affected-pulse` 1.6s. Consequence made visible.
- **TEXT:** "ถอนวิชาเดียว เห็นเลยว่ากระทบตัวไหนบ้าง" / *pull one course — see exactly what breaks*.
- **SFX:** reverse swell → sharp impact → ominous low pulse on the red throb.

### Beat 7 — Heal & Dive (the seam) · `0:32–0:37`
- **SHOT:** The cursor drags the pulled course back into place; the red drains out of the chain and the line goes calm again. Then the camera **dives straight into the upcoming semester station** — its ring expands to fill the frame.
- **MOTION:** red → neutral fade (`arc-throb` settles), then one continuous push-in zoom; the station ring blooms past camera and dissolves into a blank weekly grid. No cut — a single move.
- **TEXT:** "แผนนิ่งแล้ว ทีนี้จัดเทอมหน้า" / *plan's solid — now build next term*.
- **SFX:** red dissipates, deep zoom-whoosh + filter sweep. This is the seam between the two tools — make it seamless.

### Beat 8 — It Fills Itself · `0:37–0:45`
- **SHOT:** A blank weekly grid, **Mon–Sat, 8:00–21:00**. A degree-plan picker cascades open — ปี → คณะ → สาขา → ชั้นปี → ภาคเรียน — then a button: **เติมตารางอัตโนมัติ**. The whole term's courses populate the grid.
- **MOTION:** dropdowns cascade with `chip-pop`; on the button press, course-colored blocks `tt-block pop` (220ms spring) cascade across the week, staggered ~50ms, pastel HSL-hashed colors. The week fills like a board lighting up.
- **TEXT:** "เลือกแผนการเรียน เติมทั้งเทอมให้อัตโนมัติ" / *pick your plan — the whole term fills itself*.
- **SFX:** rapid arpeggio burst, one note per block landing. Satisfying density.

### Beat 9 — Drag · Snap · No-Clash · `0:45–0:51`
- **SHOT:** The user drags a course from the sidebar onto the grid. **Green pulsing slots** appear in every conflict-free time — drop on green and it locks. Then a deliberate clashing drop flashes a **red outline** and the conflict summary (courses · credits · conflicts) ticks.
- **MOTION:** `tt-hint-pulse` green footprints breathe (1.4s); drag lifts with spring; clean **snap** on the green drop; red conflict outline + a purple `toast-in`. On phone, the section chooser `sheet-in` from the bottom.
- **TEXT:** "ลากวาง — ช่องเขียวคือไม่ชนกัน" / *drag — green means no clash*.
- **SFX:** drag boing → clean snap on green → soft warning tick on red.

### Beat 10 — Pull Back to the Terminus · `0:51–0:57`
- **SHOT:** Camera **zooms back out** of the full week grid, the station ring re-forms around it, and we're on the metro map again — gliding up the line to the final station: **รับปริญญา** with a mortarboard 🎓 interchange marker. The orange line arrives and blooms.
- **MOTION:** reverse of the Beat 7 dive (closes the loop), near-silence 0.5s, then terminus `badge-pop` + warm light bloom. Confetti restrained — a few orange/purple particles, not a party.
- **TEXT:** "ปลายทาง: วันรับปริญญา" / *destination: graduation day*.
- **SFX:** zoom-out whoosh → silence → bright resolving chord. The exhale.

### Beat 11 — CTA · `0:57–1:00`
- **SHOT:** Pull back to the full map breathing calmly, wordmark + URL. A tiny split-frame hint of both views (map + week grid) under the logo.
- **MOTION:** spine-pulse continues softly under the lockup. Logo settles with one spring.
- **TEXT:** **OneDegree** · `onedegree.wiki` · "แผนที่หลักสูตร & จัดตารางเรียน ม.กรุงเทพ".
- **SFX:** final pluck, tail reverb.

---

## 5. Hero Moments (must be flawless)

If budget/time forces cuts, these carry the film:
1. **The Snap** (Beat 2) — chaos → calm. The reason-to-care.
2. **The Heartbeat** (Beat 4) — orange light on the purple rail. The signature visual.
3. **The Ripple** (Beat 6) — red consequence chain. The "whoa, I need this" moment.
4. **The Dive** (Beat 7) — station opens into the week grid. The seam that proves it's one product, not two.
5. **It Fills Itself** (Beat 8) — the whole term auto-populates. The "wait, it does *that*?" moment.

Render these at the highest fidelity; everything else can be simpler. If you can only ship 15 seconds, ship #1, #3, and #5 — problem, consequence, magic.

---

## 6. Generation Prompts (paste-ready)

### A. Master style prompt (prepend to every shot)
```
Motion-graphics product film for "OneDegree", a Thai university degree planner
designed as a subway/metro map. Clean off-white paper background (#F8F8F8).
Duotone palette: deep Bangkok University purple #3F194B (rails, structure) and
warm orange #E56436 (energy, the light traveling the line). Prerequisite lines
in muted purple #7B5387. Flat, precise, premium transit-map aesthetic — think
Apple Maps meets Tokyo Metro diagram. Smooth springy motion with gentle overshoot.
No clutter, lots of negative space, soft shadows. Thai display type in Kanit.
24fps cinematic, shallow depth between layers, subtle parallax.
```

### B. Shot prompts (append each to the master)
- **Snap:** `Six chaotic overlapping browser tabs vacuum-collapse into a single orange point of light, then explode outward into a clean blank map canvas. Fast whoosh, then stillness.`
- **Build:** `A vertical purple metro line draws itself from top to bottom. Circular station markers pop into place one by one climbing the line, each with a small spring overshoot. Small rounded course-chip cards cascade in beside each station, staggered like a ripple.`
- **Heartbeat:** `Slow camera push along a vertical purple metro rail while a glowing orange pulse of light travels smoothly up the line. Thin arcs draw between stops like circuitry connecting. Layered parallax depth.`
- **Drag:** `A cursor lifts a small course card off the metro map — it scales up with a soft shadow, springs, and drops onto a glowing orange target station. Neighboring cards gently nudge and re-flow into place.`
- **Ripple:** `One early station on a metro map is pulled out; a chain reaction of red light propagates downstream along the connecting arcs, each dependent stop throbbing red and getting struck through. Tense, then resolves.`
- **Dive:** `Continuous push-in zoom into a single circular metro station marker; the ring expands past the camera and dissolves into a clean blank weekly calendar grid (days across the top, hours down the side). One seamless move, no cut.`
- **Auto-fill:** `An empty weekly timetable grid, Monday to Saturday. Rounded course blocks in soft muted pastel colors pop into their time slots one after another in a quick cascade, filling the whole week, each with a small spring overshoot. Calm, satisfying, organized.`
- **Schedule-drag:** `A cursor drags a small course card over a weekly grid; several empty time slots glow and pulse soft green to show valid drop spots; the card snaps cleanly into one. A different slot flashes a thin red outline to signal a time clash.`
- **Terminus:** `Camera glides up a metro line to a final station marked with a graduation cap. The orange line arrives, the station blooms with warm light, a few restrained purple and orange particles drift up.`

### C. Motion-design pass (if compositing in After Effects / Claude-driven SVG)
Match the real CSS so the film == the app:
```
spine pulse: orange gradient sweep along purple stroke, 4.5s linear loop
station breathe: scale 1.0↔1.06, 3.4s ease-in-out
ink draw: stroke-dashoffset → 0 over 1100ms, ease cubic-bezier(.2,.7,.2,1)
chip pop: scale 0.9→1 + fade, 260ms spring cubic-bezier(.34,1.56,.64,1)
map fade: opacity 0→1, 520ms ease
arc throb (affected): opacity/width pulse, 1.6s ease-in-out
stop strike: line-through wipe, 360ms ease
— timetable —
block pop: scale 0.94→1 + fade, 220ms spring (stagger ~50ms across the grid)
drop-hint pulse: opacity .75↔1, 1.4s ease-in-out (green slots)
toast in: translateY(12px)→0 + fade, 220ms spring
sheet in (mobile): translateY(40px)→0 + fade, 240ms spring
```

---

## 7. Format & Delivery

| Cut | Aspect | Length | Where |
|---|---|---|---|
| Hero | 16:9 | 60s | site header, YouTube, GitHub README embed |
| Vertical | 9:16 | 24s (Beats 2, 6, 8, 9, 10) | TikTok / Reels / Stories |
| Square | 1:1 | 15s (Beats 2, 8, 9) | LINE / IG feed |
| Loop | 16:9 | 6s silent (Beat 8 auto-fill) | OG / social preview, autoplay-muted |

- Captions burned in (Thai primary, English secondary) — most views are muted.
- Export the 6s loop first frame = the full breathing map (great as a static thumbnail too).
- Keep the existing OG banner (`Web/public/banner.png`) as the end-card style reference.

---

## 8. Brand Guardrails

**Do**
- **Hit fast, then breathe** — stack quick punches, then HOLD one hero frame. Contrast, not constant speed.
- Cut/zoom/slam **on the beat** — quantize everything to the kick.
- Exaggerate squash-stretch and overshoot — wind-up → snap → settle.
- Keep purple structural, orange energetic (motion goes wild, color stays disciplined).
- Show *real* interactions (drag, withdraw, ripple, auto-fill, green-slot drop) — authenticity sells it.
- Make the station→grid zoom **one unbroken move** — never hard-cut between map and timetable.

**Don't**
- No rainbow gradients, no neon, no glassmorphism noise. The *only* multi-color is the timetable's muted pastel course blocks — keep them low-saturation.
- No fake 3D city flythroughs — it's a *diagram*, keep it flat and confident.
- Don't letter-space or per-glyph-animate Thai. Don't crowd the frame.
- Don't run speed flat the whole way — no held frames = exhausting, not fun. The pauses make the speed land.
- Don't oversell graduation with heavy confetti — restraint is the brand.
- Don't show the timetable as a *separate* app — it's the same map, zoomed into one term.
- **Keep it safe:** beat-shake ≤2px, flashes ≤1 frame, no strobing >3Hz — and the reduced-motion cut (§9) kills all of it.

---

## 9. Accessibility Cut

The product honors `prefers-reduced-motion`. Ship a **calm cut** too: same shots, motion replaced by soft cross-fades, no pulsing/throbbing, captions only. Same story, zero vestibular load.

---

### The one thing to remember
The product turns *anxiety* (which courses? what breaks? am I on track? what do I even register for next term?) into something you can read in one glance — the **whole degree** as a map, and **next term** as a timetable that fills itself. The film's job is to make that transformation **felt**: chaos in, clarity out, one camera move from your first year to graduation day. Make people see their own path in it. That's what makes them love it.
