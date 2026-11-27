---
name: enhancer-prompt
description: "Multi-shot prompt enhancer for Seedance 2.0 — use to tighten a finished clip prompt with deterministic locks: entity locking, screen geography, frame-one readiness, atomic shot timing, FOV and camera speed, prop states, eye-lines, physics, lighting invariance, timestamped audio, and a credibility lint pass."
---

# Multi-Shot Animation Prompt Engineering Skills (`SKILLS.md`)

This document defines a 12-skill modular architecture for multi-shot AI video prompt generation. It is engineered specifically to optimize **token efficiency** (eliminating cross-clip text bloat) and **generation credibility** (preventing directional flips, timing collisions, prop hallucinations, and chained-frame drift).

---

## Architecture Overview: Token Economy & Credibility Principles

1. **Deduplicated Scene Inheritance (Token Optimization):**  
   * Static metadata (`STYLE`, `OUTPUT SETTINGS`, `LIGHTING`, `COLOR GRADE`, and full character voice/wardrobe profiles) must be defined **once** at the Scene/Manifest level and inherited by child clips via compact reference IDs, rather than repeated verbatim in every clip prompt.  
2. **Single-Beat Shot Atomicity (Credibility Optimization):**  
   * Never pack dense multi-turn dialogue exchanges into a single uncut shot. Decompose rapid exchanges into 2.0s–5.0s single-beat shots with exact second-offset timestamps.  
3. **Deterministic Locks Over Qualitative Prose:**  
   * Replace vague descriptors (*"gentle drift"*, *"warm sunlight"*, *"small cart"*) with explicit numeric parameters (`no drift mid-segment`, `4200K high frame-right`, `fits across two cupped hands, 3 wheels attached, 1 wheel loose in dust`).  
4. **Chained-Frame Error Isolation:**  
   * When chaining `clip[n]` from `clip[n-1]`'s final frame, pair the chained frame with canonical asset/environment reference IDs so minor artifacts in `clip[n-1]` do not compound across a sequence.

---

## Skill Index

1. **Skill 01: Reference & Entity Locking** (`ref_entity_lock`)  
2. **Skill 02: Token-Deduplicated Scene Inheritance** (`token_dedup_inheritance`)  
3. **Skill 03: Screen Geography & 180° Line Blocking** (`screen_geography`)  
4. **Skill 04: Frame-One Readiness & Error-Isolated Chaining** (`frame_continuity`)  
5. **Skill 05: Atomic Shot Segmentation & Cut Grammar** (`shot_pacing_cuts`)  
6. **Skill 06: Optical FOV, Speed & Anti-Drift Camera Grammar** (`optics_camera`)  
7. **Skill 07: Prop State, Occlusion & Relative Scale Machine** (`prop_state_machine`)  
8. **Skill 08: Motivated Acting & Eye-Line Choreography** (`acting_eyelines`)  
9. **Skill 09: Physical Mass, Contact & Micro-Motion** (`physics_motion`)  
10. **Skill 10: Lighting Invariance & Material Color Grade** (`lighting_color`)  
11. **Skill 11: Timestamped Dialogue, Foley & Score Layering** (`audio_sync`)  
12. **Skill 12: Automated Credibility & Token Linter** (`credibility_linter`)

---

## Skill 01: Reference & Entity Locking (`ref_entity_lock`)

* **Goal:** Bind every environment, character, prop, and keyframe ID to invariant physical, scale, costume, and vocal attributes.  
* **Deterministic Rules:**  
  * Assign every active entity a unique ID with an explicit match lock (`100% matches the reference`).  
  * Lock exact character age/proportions, layered wardrobe, footwear, and vocal timbre/cadence in the Scene Registry.  
  * Enforce strict entity uniqueness per shot: `Every named character appears exactly once; no duplicate or twin characters.`  
  * Separate background crowd/animal extras from active foreground characters so they never merge, morph, or duplicate.  
* **Credibility Check:** Fail if an unreferenced character appears mid-scene or if character age/wardrobe differs across clips in the same sequence.

---

## Skill 02: Token-Deduplicated Scene Inheritance (`token_dedup_inheritance`)

* **Goal:** Maximize context-window efficiency without losing visual or vocal consistency across multi-clip sequences.  
* **Deterministic Rules:**  
  * Store invariant blocks (`style_block`, `output_settings`, `lighting_master`, `color_grade`, `character_profiles`, `negative_avoid_list`) once in the parent **Scene Manifest**.  
  * Inside individual clip payloads, reference entities by compact ID \+ current beat state (e.g., `char_miri [guarded, clutching closed bundle]`) instead of re-pasting full paragraph biographies in every clip.  
  * Keep per-clip prompt text focused on shot-specific blocking, timestamps, camera optics, dialogue, and state deltas.  
* **Token Check:** Flag and strip duplicate verbatim paragraphs (\>30 tokens) repeated across sibling clips when compiling batch payloads.

---

## Skill 03: Screen Geography & 180° Line Blocking (`screen_geography`)

* **Goal:** Eliminate left-to-right spatial flips, lighting-axis contradictions, and background layout drift across cuts.  
* **Deterministic Rules:**  
  * Define a fixed scene spatial matrix (`frame-left`, `frame-centre`, `frame-right`, `foreground`, `midground`, `background`).  
  * Lock the camera to **one side of the line of action** across all shots (including OTS and reverse OTS pairs) so Character A stays `frame-left` and Character B stays `frame-right`.  
  * Ensure character travel vectors, doorway/prop placements, and sun-shadow angles align across adjacent clips—never flip sun direction from frame-left to frame-right within the same scene.  
  * For unoccupied environment master plates, structure framing into `FOREGROUND`, `MIDGROUND`, and `BACKGROUND` zones (`25°–30°` slight top-down angle) and enforce `No people`.  
* **Credibility Check:** Fail if `screen_left` / `screen_right` assignments or shadow directions contradict the parent Scene Location Map.

---

## Skill 04: Frame-One Readiness & Error-Isolated Chaining (`frame_continuity`)

* **Goal:** Eliminate empty establishing frames, delayed character reveals, and compounding visual drift across chained clips.  
* **Deterministic Rules:**  
  * Open `0.0s` (`FIRST FRAME / BLOCKING`) immediately on active characters, props, and ongoing micro-motion (`Everyone is already moving in the first frame`).  
  * Never open character narrative clips with blank frames or delayed entrances unless explicitly scripted as an unoccupied environment plate.  
  * When chaining `clip[n]` from `clip[n-1]`'s last frame, pass **both** the last-frame reference and the canonical character/environment reference IDs to anchor identity and prevent generational drift.  
  * For continuous non-cut transitions (e.g., crane rise through a sun-flare bloom into a close reveal), lock both `START FRAME` (`0.0s`) and `END FRAME` (`end_sec`) and hold steady for `0.2s–1.4s`.  
* **Credibility Check:** Fail if `0.0s` lacks any required active subject or if a chained clip omits canonical design anchors.

---

## Skill 05: Atomic Shot Segmentation & Cut Grammar (`shot_pacing_cuts`)

* **Goal:** Prevent crowded multi-line shots, rushed lip-sync, and skipped actions by decomposing beats into atomic timed shots.  
* **Deterministic Rules:**  
  * **De-crowding Rule:** Limit shots to **1–2 dialogue turns** within **2.0s–5.0s**. Extend to **5.0s–8.0s** only for continuous physical choreography (kneeling, prop handoff, timed exit).  
  * Separate shots exclusively with explicit cut markers: `HARD CUT`, `REVERSE CUT`, or `INSERT CUT`.  
  * Enforce the global constraint: `Cuts happen only at the stated points, and the camera does not cut on its own.`  
  * End every sequence with a **0.5s–1.4s** tail hold (`no new dialogue or new action`).  
  * **Special Sequence Archetypes:**  
    * *Imagination / Vignette Insert:* Top-down isolated vignette (`30%` edge darkening) with exact second timestamps for visual state changes (e.g., items disappearing one by one).  
    * *Animated Title Card:* Two-shot frontal setup (`0.0s–3.0s` surface/scroll unfurls blank; `3.0s–8.0s` exact locked title text, flourishes, and corner illustrations animate on timestamps, followed by a static hold).  
* **Credibility Check:** Fail if a single shot contains $\geq 3$ rapid back-and-forth dialogue lines without a cut or if shot timestamps overlap/gap.

---

## Skill 06: Optical FOV, Speed & Anti-Drift Camera Grammar (`optics_camera`)

* **Goal:** Enforce deterministic lens perspective, camera height, and motion rates while eliminating unintended camera wandering.  
* **Deterministic Rules:**  
  * Assign an exact diagonal `FOV` per shot from the canonical prime set:  
    * `84° FOV`: Extreme wide / crane establishing (deep focus, rectilinear straight lines).  
    * `63° FOV`: Wide / multi-character comic tableau / dynamic lane framing.  
    * `47° FOV`: Standard normal (dialogue medium shots, OTS pairs, profile two-shots, frontal title cards).  
    * `29° FOV`: Short telephoto (shallow-focus close-ups, OTS reactions, hand/vignette inserts).  
    * `18° FOV`: Tight close-up (very shallow focus for intense emotion or gasps).  
    * `12° FOV`: Macro insert or compressed long-telephoto POV.  
  * Specify camera height (`rooftop crane`, `adult standing eye height`, `child eye level 1.0–1.1 m`, `kneeling shared eye level`, `animal height 0.3–0.4 m`, `top-down`).  
  * Quantify camera motion in `km/h` (`0.3–0.5 km/h` slow push-in, `2.0 km/h` pan/crane/boom, `3.0–9.0 km/h` tracking) and append `with no drift mid-segment` to every shot.  
  * Timestamp optical focus pulls (`rack focus` at exact seconds) and brief handheld POV sway (`~2 cm` bob at `4 km/h`).  
* **Credibility Check:** Fail if any shot lacks an explicit `FOV`, camera height, or `no drift mid-segment` lock.

---

## Skill 07: Prop State, Occlusion & Relative Scale Machine (`prop_state_machine`)

* **Goal:** Prevent props from resizing, self-repairing, multiplying, or exposing concealed items prematurely.  
* **Deterministic Rules:**  
  * Track explicit prop state enums on every shot:  
    * *Containers:* `closed_knotted`, `open_exact_count_N`, `covered_opaque_linen_only`.  
    * *Broken/Mechanical Props:* `handheld_scale_3_wheels_1_loose_in_dust` (explicitly forbid self-repair or full-size vehicle scaling).  
    * *Scrolls/Title Cards:* `rolled_shut`, `unfurled_blank`, `revealed_complete_exact_text`.  
  * Anchor prop dimensions to character anatomy (`fits across two cupped hands, width equal to character's shoulders, wheels smaller than palm`).  
  * Enforce strict occlusion: during `closed` or `covered` states, explicitly lock that concealed items remain **100% hidden from view**.  
* **Credibility Check:** Fail if concealed items are described as visible in a `closed`/`covered` shot or if title-card wording varies from the locked script string.

---

## Skill 08: Motivated Acting & Eye-Line Choreography (`acting_eyelines`)

* **Goal:** Generate sincere, readable character acting without fourth-wall breaks or exaggerated cartoon mugging.  
* **Deterministic Rules:**  
  * Define an explicit **eye-line sequence** per beat (e.g., eyes check target object $\rightarrow$ listener's face $\rightarrow$ escape path $\rightarrow$ back to object).  
  * Precede spoken lines with **0.2s–1.4s** of physical anticipation (thumb rubbing cloth, breath catch, swallow, head tilt, shoulder slump, or blink burst).  
  * Ground comedic moments in **deadpan stillness** (`both hold perfectly still from 19.0s to 20.4s`) rather than winking at the camera.  
  * Specify living eyes with directional sun catch-lights and staggered group reactions (`never moving in perfect sync`).  
* **Credibility Check:** Fail if acting descriptions rely on abstract adjectives (`acts sad`) instead of observable physical cues and eye-lines.

---

## Skill 09: Physical Mass, Contact & Micro-Motion (`physics_motion`)

* **Goal:** Ground stylized 3D characters and props in realistic weight, surface contact, and environmental micro-motion.  
* **Deterministic Rules:**  
  * Specify ground contact mechanics: heel-to-toe weight transfer, soft contact shadows on packed earth, and small dust puffs that lift and **settle within 1 second**.  
  * Define material physics: woven basket mass and bob, folded linen shape retention, fabric compression under fingers, paper flex/ripple on unrolling, and ink drying from wet gloss to matte.  
  * Include continuous secondary motion: hair bounce, shawl fringe sway, ear/tail follow-through, chewing animals, flickering oven embers, rising steam, and drifting straw/flour motes.  
* **Credibility Check:** Fail if prop transfers or character locomotion omit contact, weight, or settling behavior.

---

## Skill 10: Lighting Invariance & Material Color Grade (`lighting_color`)

* **Goal:** Lock key light direction, color temperature, atmospheric haze, and material palette across all shots in a scene.  
* **Deterministic Rules:**  
  * Maintain identical key-light direction (`warm morning sun from high frame-right`), Kelvin temperature (`4200K`), warm clay/limestone bounce fill, and practical ember glows across every real-world shot in a scene.  
  * Specify atmospheric haze density (`15%` standard morning haze; `25%` in compressed `12° FOV` long-telephoto POV; `10%` $\rightarrow$ `30%` $\rightarrow$ `20%` during golden-hour flare transitions).  
  * Permit Kelvin shifts (`4800K` $\rightarrow$ `3200K`) only during explicit time-of-day transitions or isolated dream vignettes (`dreamy golden top-light with 30% vignette`).  
  * Define color grading through tactile materials (ochre earth, pale tan clay, creamy limestone, cool indigo/slate fabric accents, golden amber highlights) with soft contrast and gentle highlight roll-off.  
* **Credibility Check:** Fail if key-light angle or Kelvin value shifts unmotivated between consecutive shots.

---

## Skill 11: Timestamped Dialogue, Foley & Score Layering (`audio_sync`)

* **Goal:** Synchronize dialogue, foley, and score cues to exact second marks for clean audio-visual alignment.  
* **Deterministic Rules:**  
  * Format every spoken line with an exact second offset and delivery tag: `2.7s — SPEAKER (delivery): "Exact scripted words."`  
  * Enforce word-for-word, in-order dialogue fidelity with synced lip movement on the named speaker only.  
  * Structure audio into three explicit layers:  
    1. *Ambient Bed:* Continuous environmental sound with exact `%` dips during intimate beats (`softens to 50%` or `dips to near silence`).  
    2. *Timestamped Foley/SFX:* Specific action sounds tied to visual timestamps (`footsteps`, `paw pats`, `wooden wheel clack`, `wicker thud`, `quill ink strokes`).  
    3. *Score Cues:* Explicit musical swells, plucks, or chimes at exact seconds—or an explicit `no background music` lock when silent underscore is required.  
* **Credibility Check:** Fail if dialogue lines lack second offsets or if unscripted dialogue/narration is introduced.

---

## Skill 12: Automated Credibility & Token Linter (`credibility_linter`)

* **Goal:** Validate every compiled JSON prompt against token budgets and cross-shot consistency rules before video generation.  
* **Deterministic Rules:**  
  * **Token Audit:** Verify that static scene-level blocks are inherited rather than duplicated across clips, keeping per-clip payloads concise and high-signal.  
  * **Cross-Shot Audit:** Verify monotonic timestamps, valid cut markers (`HARD CUT`, `REVERSE CUT`, `INSERT CUT`), consistent `FOV`/height/anti-drift locks, invariant `screen_left`/`screen_right` geography, matching `4200K` sun axis, and valid prop occlusion states.  
  * **Guardrail Injection:** Ensure every compiled prompt includes both `POSITIVE LOCKS` and `NEGATIVE / AVOID` constraints (forbidding autonomous cuts, mid-segment drift, duplicate characters, anachronisms, 2D/live-action style drift, and unscripted text/subtitles/logos/watermarks).
---

