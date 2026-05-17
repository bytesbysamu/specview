# mom next weekend

## Overview
Two-day Zürich itinerary (2026-05-17/18) with mom. Weather-contingent A/B plan, one locked dinner reservation. Sequence: preferences (T1) → weather check (T2) + itinerary (T3) parallel → dinner booking (T4) → buffer activities (T5).

## Pre-flight
- Confirm dates: Sat 05-17 / Sun 05-18
- Create `projects/mom-next-weekend-1778326913888/deliverables/`
- Bookmark MeteoSwiss/SRF Meteo for Friday-evening weather gate
- Identify mom's Telegram for sharing
- Verify ZSG short-cruise schedules, Kunsthaus/Landesmuseum Sat/Sun hours
- Confirm Zeughauskeller + one lighter restaurant accept online reservations for Saturday
- Prepare printable two-column Sat/Sun template

---

## Task 1: Confirm preferences [0.25 day]
Resolve five unknowns: mobility level, indoor/outdoor lean, food preferences, first-time-in-Zürich status, budget tier.

**Files**: Create `deliverables/preferences.md`; modify `epic.md` mark complete.

**Steps**: Message mom re: walking comfort, outdoor vs museums, dietary restrictions/restaurant style, prior Zürich visits, budget. Record answers, derive constraints (max walking/day, default path, dinner style). Share one-sentence summary for confirmation.

**Verify**: All five dimensions explicit, max walking as number, dinner style recorded, mom acknowledged.

---

## Task 2: Check weather [0.1 day]
Friday evening gate → binary outdoor Path A or indoor Path B.

**Files**: Create `deliverables/weather-gate.md`; modify `deliverables/itinerary.md` mark active path.

**Steps**: Friday 05-16 after 18:00: MeteoSwiss Zürich Sat/Sun temp, precip, wind. Rule: precip <30% and temp >14°C both days → Path A, else → Path B. Record forecast + decision. Notify mom via Telegram with clothing note.

**Verify**: Forecast data with source/timestamp, clear A/B decision, itinerary reflects path, mom notified.

---

## Task 3: Draft itinerary [0.5 day]
Single-page two-column itinerary with time blocks, travel times, walking totals. Both paths fully drafted.

**Files**: Create `deliverables/itinerary.md`, `deliverables/travel-times.md`.

**Steps**:
- **Path A (outdoor)**: Sat AM Uetliberg ridge walk, PM Old Town + lake pier, evening dinner. Sun AM ZSG cruise, PM Lindenhof + Niederdorf.
- **Path B (indoor)**: Sat AM Landesmuseum, PM Kunsthaus, evening dinner. Sun AM Lindt Home of Chocolate (Kilchberg), PM café crawl Niederdorf.
- Each slot: departure, transport, travel time, walking distance. Totals within preference cap.

**Verify**: No placeholder slots, all blocks have start/end/location/travel, walking totals within cap, renders single-page.

---

## Task 4: Book Saturday dinner [0.25 day]
Lock inventory-constrained item ASAP after preferences confirmed.

**Files**: Create `deliverables/dinner-booking.md`; modify itinerary Saturday evening slot.

**Steps**: Traditional → Zeughauskeller/Kronenhalle; lighter → Hiltl/Marktküche. Party of 2, 18:30–20:00. If unavailable, try backup; if both full, phone. Record confirmation, cancellation terms. Update itinerary.

**Verify**: Booking details + confirmation number, cancellation deadline, itinerary matches, backup noted.

---

## Task 5: Buffer activities [0.25 day]
2–4 ranked unscheduled activities for filling gaps or spontaneous detours.

**Files**: Create `deliverables/buffer-pool.md`; modify itinerary footer.

**Steps**: Candidates: Lindt (if not Path B), Grossmünster tower, ZSG loop (if not Path A), Zürich West/Viadukt market. Each: location, duration, cost, walking distance, replaceable slot. Rank by preference fit. Add itinerary footer with top 3 + trigger conditions.

**Verify**: ≥3 options with duration/cost/distance, clear triggers, itinerary footer consistent, none exceeds walking cap when added.