---
name: stylized-3d-film-director
description: Directs a stylised 3D animated short film made with AI image and video models (Higgsfield, Seedance, Kling, Veo, Seedream, GPT Image, Nano Banana and similar), from idea to final cut. Use it whenever someone pitches a story or a character for a stylised 3D or animated AI film, asks for character sheets, location plates, a shot list, video prompts, a previz plan, a review of drafts, or a finishing plan. Its first duty is to research every character on the web (articles, guides, interviews, Reddit and X/Twitter posts, first-person accounts) and turn that research into a written acting profile before any prompt is written.
---

# Stylised 3D Film Director

A playbook for making a stylised 3D animated film with generative models, distilled from a finished contest short (a wordless 120-second myth about a blind slave and a woman whose gaze turns men to stone). It works with Claude, GPT or any assistant that can browse the web, and with any image or video model that takes reference images.

The core belief: **models copy what you show them and improvise what you leave out.** Everything below exists to show them the right things and leave them nothing important to guess.

---

## 0. The first duty: research every character before you prompt it

When the user describes a story or a character, do not start writing prompts. **Go to the web first.** Video models act out clichés unless you give them real behaviour, and real behaviour comes from people who live it.

### 0.1 What to research

For every character with a defining condition, role or circumstance (blind, deaf, elderly, a child, a soldier with PTSD, a nurse at the end of a shift, a thief, a grieving mother, a dancer, a prisoner, someone drunk, someone injured, someone in love for the first time), find out:

| Area | Questions to answer |
|---|---|
| Body | Posture, gait, weight, balance, where tension sits, how they sit, stand and rest |
| Hands | What the hands do first, how they hold and touch, nervous habits, how fine work looks |
| Senses and attention | What they notice first, which sense leads, where their eyes go (or don't), how they listen |
| Reactions | What a sudden sound, a touch or a threat does to them, beat by beat |
| Daily habits | Routines and small repeated gestures; tools and how they handle them |
| Social behaviour | Distance to others, how they greet, avoid or trust, how they ask for help |
| Under pressure | How they break: what changes in breath, hands, voice and eyes |
| What outsiders get wrong | The clichés and film tropes that people in this group find false or offensive |

### 0.2 Where to look (use several, prefer first-person voices)

- **First-person accounts:** Reddit communities and "ask me anything" threads by people who live it, posts on X/Twitter and Threads, personal blogs, YouTube videos where people describe their own experience.
- **Guides written for actors, writers and animators** on portraying that condition or role.
- **Organisations and professionals:** advocacy groups, charities, clinicians, trainers, instructors (for example orientation-and-mobility instructors for blindness).
- **Articles and interviews** in reputable outlets; documentaries.
- **Forum threads where people correct portrayals** ("what movies get wrong about…"). They are gold for avoiding clichés.

Search in the user's language and in English. Read at least 5 to 10 sources, and more for a main character.

### 0.3 What to deliver: the acting profile

Write a short research note listing the sources you used, then distil it into:

1. **The master profile:** one paragraph in present tense describing how this person moves, touches, listens, looks and breaks under pressure. Behaviour only, no adjectives about feelings.
2. **CAPS RULES:** 6 to 15 numbered, physical, testable rules (e.g. "HAND FIRST, HEAD AFTER").
3. **Forbidden readings:** the wrong performances the model will default to, named explicitly (e.g. "he never looks at the thing he hears").
4. **Per-shot adaptation notes:** how the profile changes in a close-up, an insert of the hands, a wide shot and a walk.

Show the profile to the user before prompting. Adapt it to every shot; never paste it unchanged; never drop a rule because a shot makes it awkward (transfer it instead: a pacer who must sit still keeps the energy in his fingers).

Be respectful: build from what people say about themselves, avoid stereotypes, and summarise sources in your own words rather than copying private posts.

### 0.4 Worked example: a man blind from birth

The first video takes showed him *looking* at a statue and then getting scared, which is a sighted reaction. After research, the rules that fixed him were:

1. HAND FIRST, HEAD AFTER: the hand finds a thing; a beat later the head turns so the **ear** points at it, never the eyes.
2. SOUND = STILLNESS, THEN THE EAR: at a sound he freezes, hands stop in mid-air, eyes do not widen or turn, face stays tipped down, then one ear leans toward the sound, which turns his face slightly *away* from it.
3. EYES: open, soft, drifting, normal blinks; they never aim at, follow or lock onto anything.
4. ONE HAND READS, ONE HAND HOLDS; never stiff "zombie" arms; free-walking hands stay low and loose; toes test the ground before weight follows.
5. TOUCH HAS FOUR PARTS: contact, stop, palm settles, fingertips travel; a feared thing gets one brief hand that jerks back.
6. FINE WORK IS WRITTEN FINGER BY FINGER ("thumbnail and two fingers pick at the knot, slip once, pick again"), never "he unties it".
7. On close-ups the object he senses is kept **outside the frame**, so "looking at it" cannot be rendered.
8. After he regains sight, old habits linger: the hand still reaches out before he trusts his eyes.

A story detail grew out of the research too: a blind man builds his world from sound, so he calls the woman he loves with **two claps**, his own voice.

---

## 1. Story: make it readable without words

- **One main character**, present in the first and last frames.
- Answer three questions on paper before any image exists: *who wants what, who is where, how does it end.*
- **Stage the relationships in space.** Distance between characters is the story; plan how it changes from act to act.
- **Plant and pay off with objects and marks** (a rope, a bell, a mark on a cheek). Every prop must be on the asset sheet and in every prompt where it appears.
- **Use myth and symbol on purpose.** Find the older stories your idea echoes (here: Medusa, the Sirens, yin and yang) and borrow their logic, not their images.
- **Show time without words:** seasons, growing piles of gifts, a costume that changes, an animal that returns with young.

## 2. Look: lock one style and never paraphrase it

- Pick a benchmark film or project and study **its prompts and its process**, not just its frames.
- Write one **style block for characters** and one for **environments**, and paste them word for word into every prompt. Rewording drifts the style.
- For stylised 3D, describe the material behaviour, not a studio name: "smooth rounded volumetric forms, matte materials, soft cel shading, large expressive eyes with a clear catchlight, fabric with real thickness, thin loose pencil strokes over the forms that never close into a contour. Not photoreal, not a flat 2D painting, not anime."
- Choose one **lighting formula** for the whole film (e.g. low warm late sun, long soft shadows) and repeat it.
- Never use another artist's images or a real person's likeness as a reference. Describe a look in words.

## 3. Assets: sheets, states and plates

**Character sheets** (three panels on a flat light-grey background, even soft light, no scenery):
- LEFT: full body from the front, **cut at the chin** (no head).
- CENTRE: full body from behind, head attached.
- RIGHT: one **large dead-on face** from the crown to the collarbones.
The face appears once, big, so the model has one place to take it from.

**Every state is its own asset:** clean, wounded, wet, freed, healed, eyes shut, turned to stone. Mixed states in one image make the model mix them in video.

**Location plates:** build depth into every plate (a dark foreground frame, a clear midground, a misty distance). Make a separate plate per season or time of day, a top-down plan for layout, and both sides of any space you will shoot shot-reverse-shot.

**Test key assets in motion** with a short cheap draft before you build scenes on them.

**References are your own generations only,** and each one is **cropped to its single job.** A whole frame is drawn whole, people and all.

## 4. Previz: a position map, not a performance

Use 3D blocking (Blender or similar) only when positions between several figures must be exact, the camera follows someone, or a shot keeps failing. Keep it bare: simple colour-coded figures on a floor plan. Video models copy everything in a previz (water ripples, stiff poses, timing), so give it nothing you do not want copied.

## 5. Writing the video prompt

**Structure** (in this order):
1. A one-line **English summary** of the shot for the human (keep it even if the body is in another language).
2. **References with roles:** "@image1 = the man, face and costume only", "@video1 = positions only".
3. **Layout / map:** where everything is in camera-relative terms (frame left / frame right), one landmark per character.
4. **First frame:** who is already in place when the shot opens.
5. **Shots:** at most **4 shots per generation**, at most **2 actions per shot**, each with seconds, camera, lens feel and the action as **behaviour**.
6. **Acting:** the profile adapted to this shot, plus its **forbidden readings**.
7. **Physics:** weight, contact, water, cloth, gravity; serious stories get grounded motion with no cartoon squash and stretch.
8. **Light:** the locked formula.
9. **Sound:** exactly one "no background music" line, real sounds in angle brackets `<waves on sand>`, and no voices if the film is wordless.
10. **Positive locks:** counts and constants written as what IS in the frame ("exactly four stone men; his hand stays living skin").

**Rules that save the most credits:**
- Describe **what to show**, not what to avoid. Negations are unreliable.
- **Write the physics of a symbol, never the symbol's name.** "A single dark-red drop blooms in the eye's water like ink in clear water", not "blood heals his eye". A red fingertip read as nail polish; "veins" appeared when we wrote "spreads".
- **Long beats, few actions.** Fifteen beats in fifteen seconds looks sped up.
- **Emotion = behaviour:** "stillness, a breath that catches, brows drawing together, lips parting, a swallow".
- **Reflections and mirrors** must follow physics: say which side is lit, what the surface reflects and from where.
- **Animals:** state their size against a person and how they are held or tied.
- **Continuity:** every new generation opens where the last one ended, carrying marks, props and wounds.
- Some models hold long action timing better with the prompt body in Chinese; test it if English prompts keep failing.

## 6. Drafts, review and the rules log

- Generate **cheap drafts** (low resolution) first. Price every batch, tell the user the cost, and wait for an explicit yes before spending. Never retry automatically.
- Cut every draft into a **running rough cut** and watch it against its neighbours.
- Review honestly: never approve a draft with a visible fault (a morph, a missing mark, an extra person, a sighted reaction from a blind character, music in the audio).
- Turn every note into a **numbered rule** in a log and apply it to every later prompt.
- If a shot fails twice for the same reason, **simplify the shot** (split it, remove an action, change the angle) instead of adding words.

## 7. Finishing

- **Finalise** approved drafts at full resolution (a re-render, which may differ slightly) or **upscale** the exact take (Topaz-style keeps the take; check that faces and animals hold).
- **Video-to-video:** to continue an action seamlessly, extend clip A forward and cut clip B straight after it; note the timecode.
- **Sound:** strip generated music, build ambience beds first, then effects, then score; one shared ambience glues shots made separately.
- **Title:** generate the exact lettering as an end frame with an image model that renders text well, then animate toward that end frame. Match the title's motion to the film's tone: a love story wants slow, organic motion, not slams.
- **Package:** folders by stage, iterations kept, a brief that tells the story and shows the prompts.

## 8. Quick failure → fix table

| Symptom | Fix |
|---|---|
| Blind or impaired character acts sighted | Research profile + "the object stays out of frame" + "eyes do not widen or turn" in the beat |
| Old frame's people reappear | The reference was a whole frame: crop it to its one job |
| Previz poses or ripples copied | Strip the previz to a bare position map |
| Motion looks sped up | Fewer actions, longer beats, max 4 shots per gen |
| Music leaks into the clip | One "no background music" line plus named diegetic sounds |
| Symbol misread (polish, veins, glow) | Describe the physical event, size and material instead of the symbol |
| Wrong scale animal or prop | State the size against a person and how it is held |
| Faces drift between shots | One-face sheet, states as separate assets, the same descriptor every time |
| Title looks like an action trailer | Ask for slow, continuous, weightless motion; ban impacts, flashes and shakes |
