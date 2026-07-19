# OneDegree Design Direction

## Product Vision

OneDegree is an interactive academic navigation system for university students.

The product helps students:

* understand their curriculum path
* explore course relationships
* plan semesters
* build their timetable

The experience should feel:

* Creative
* Fast
* Interactive
* Modern
* Student-friendly

while maintaining a small amount of university professionalism.

The product should NOT feel like:

* AI assistant software
* enterprise dashboard
* generic SaaS application

The feeling should be closer to:

* Bangkok transit map
* Spotify exploration
* Apple smoothness
* modern education technology

---

# Core Design Concept

## "Academic Metro Journey"

The curriculum is a journey.

Mapping:

* Semester = Station
* Course = Stop
* Prerequisite = Route
* Course dependency = Connection
* Timetable = Journey schedule

The interface should make students feel:

"I can see where I am going."

---

# Design Personality

Target audience:

* Gen Z university students

Design ratio:

```
Creative interaction    60%
Motion experience       25%
University formality    15%
```

University professionalism comes from:

* clear hierarchy
* accurate information
* clean typography
* trustworthy interaction

NOT from:

* boring corporate styling

---

# Visual Language

## Overall Style

Use:

* strong shapes
* clear routes
* playful movement
* meaningful animation
* visual exploration

Avoid:

* excessive rounded SaaS cards
* glassmorphism
* AI-style gradients
* floating assistant UI
* unnecessary decoration

---

# Color System

Maintain the existing brand colors.

## Primary Purple

Purpose:

* university identity
* curriculum structure
* navigation
* selected states

```
Primary Purple
#3F194B
```

Additional:

```
Deep Purple
#291033

Interactive Purple
#6D3FA0
```

---

## Orange

Purpose:

* action
* current location
* important moments
* active progress

Existing:

```
Orange
#E56436
```

Additional:

```
Bright Orange
#FF7A3D
```

Do NOT use orange as the main structure.

Purple creates the world.
Orange represents student action.

---

## Background

Use warm clean surfaces:

```
Canvas
#FAF7FC

Surface
#FFFFFF
```

The feeling should be:

* premium
* soft
* paper-like

---

# Typography

Maintain:

Primary UI:

```
IBM Plex Sans Thai
```

Technical information:

```
JetBrains Mono
```

Use mono only for:

* course codes
* credits
* technical metadata

Do not make the whole interface feel technical.

---

# Curriculum Map Redesign

## Main Experience

The curriculum map should be the wow moment.

Opening animation:

1. Purple route draws across the screen
2. Semester stations appear
3. Course stops appear
4. Connections animate

Example:

```
●────────●────────●────────●

Year 1    Year 2    Year 3
```

---

# Semester Station

Semester should feel like a transit station.

Structure:

```
        ●

+----------------+
| Semester 3     |
|                |
| 6 Courses      |
| 18 Credits     |
|                |
| View Route →   |
+----------------+
```

Use:

* large station marker
* clear semester identity
* expandable content

---

# Course Node

Courses should feel like stops.

Example:

```
● CS201

Data Structure

3 Credits

Unlocks:
- AI
- Backend
- Software Design
```

Students should understand:

* what this course is
* why it matters
* what it connects to

---

# Interaction

## Hover

Do not only highlight.

Reveal information.

Example:

Before:

```
CS302 Database
```

After:

```
CS302 Database

✨ Unlocks:
Backend Engineering

Prerequisite:
CS201
```

---

## Focus Mode

When selecting a course:

* highlight related routes
* fade unrelated courses
* show upstream/downstream path

The map should feel intelligent.

---

# Motion Design

Motion should create delight.

Never add animation only for decoration.

---

## Micro Interaction

Duration:

100-200ms

Use for:

* button feedback
* hover
* selection
* chips

---

## Interface Movement

Duration:

300-600ms

Use for:

* opening semester
* expanding course
* changing views

---

## Journey Animation

Duration:

1-2 seconds

Use for:

* first curriculum reveal
* route drawing
* semester transition

---

# Timetable Planner

The timetable is a workspace.

Layout:

Desktop:

```
+----------------+-------------------+
| Course Picker  | Timetable Grid    |
|                |                   |
|                |                   |
+----------------+-------------------+
```

---

# Course Selection

When selecting a course:

Do not simply change color.

The course should:

* move
* connect
* snap into timetable

Interaction feeling:

"Placing my semester."

---

# Timetable Blocks

Use:

* course color
* rounded corners
* clear text hierarchy

Show:

```
CS201

09:00 - 12:00

Room A301
```

---

# Empty States

Avoid generic empty screens.

Example:

```
Your journey starts here

Choose your degree
and discover your route.

[Start Planning]
```

Animation:

* route appears
* stations appear

---

# Navigation

No user login.

Do not use:

* avatar
* profile
* personal dashboard

Use:

```
OneDegree

Computer Science
2026 Curriculum

[Map]
[Planner]
```

---

# Important UX Principles

## Fast

Students should understand the screen within seconds.

Avoid:

* hidden actions
* complicated menus
* too many dialogs

---

## Interesting

Every major action should have feedback.

Examples:

* selecting course
* opening semester
* completing timetable
* changing degree

---

## Clear

The student should always know:

* where they are
* what they selected
* what happens next

---

# Implementation Rules

Preserve existing semantic meanings:

Purple:

* structure
* navigation
* curriculum

Orange:

* action
* progress
* current focus

Red:

* conflicts/errors

Amber:

* warnings

Do not introduce random colors.

---

# Final Product Feeling

When a student opens OneDegree, the reaction should be:

"Cool, I can actually see my degree."

Not:

"This is another university system."

The product should feel like:

A living academic map.
A navigation tool for graduation.
A modern student experience.
