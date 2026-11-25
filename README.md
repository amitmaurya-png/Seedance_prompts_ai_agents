# Seedance prompts AI agent

Turns a skit or screenplay PDF into ready-to-run Seedance 2.0 video requests. A LangGraph pipeline reads the script, writes acting profiles and image prompts for the characters and locations, splits every scene into short clips, writes a director-grade prompt for each clip, and builds a curl command per clip.

The LLM is OpenAI (`gpt-5.5` by default). Each LLM step follows the instructions in one or more skill files under [skills/](skills/).

## Run it

```bash
python3.12 -m venv .venv && source .venv/bin/activate
pip install -U -r requirements.txt
echo "OPENAI_API_KEY=sk-..." > .env       # optional: OPENAI_MODEL=...
python main.py                           # uses data/TSL.pdf
python main.py path/to/skit.pdf
```

For a cheap first run, set `MAX_SCENES = 1` in [agent/config.py](agent/config.py).

## The pipeline

```
load_skit → extract_breakdown → profile_characters → asset_prompts → plan_clips → direct_prompts → build_curl
```

| Node | Kind | Skills | Writes |
|---|---|---|---|
| `load_skit` | code | – | the scenes, split at INT./EXT. headings |
| `extract_breakdown` | LLM, 1 call per scene | – | `data/breakdown.json`: every scene as shots of action + dialogue, word for word |
| `profile_characters` | LLM, 1 call | acting-system, stylized-3d-film-director | `data/characters.json`: each character's acting profile and locked voice |
| `asset_prompts` | LLM, 1 call | lira-image-prompts, stylized-3d-film-director | `data/asset_prompts.json`: image prompts for character sheets and location plates |
| `plan_clips` | LLM, 1 call per scene | stylized-3d-film-director | clips of 4–15 s and 1–4 shots (checkpoint: `data/clip_plans.json`) |
| `direct_prompts` | LLM, 1 call per scene (up to 8 clips) | cinedance-director, acting-system, stylized-3d-film-director | `data/prompt.json`: each clip's final prompt (checkpoint: `data/clip_prompts.json`) |
| `build_curl` | code | follows seedance-curl | `curl/curl_commands.json`: one Seedance API request per clip |

Each LLM reply is checked in code: dialogue and actions copied word for word, clip lengths, reference tags, the locked style line. Problems that code can fix are fixed in code; the rest are sent back to the LLM once (`RETRIES`). Anything still wrong is printed as a warning at the end; the run doesn't stop.

## Reruns don't pay twice

Every LLM step saves its output and reuses it on the next run when its input hasn't changed:

- `breakdown.json`, `characters.json` and `asset_prompts.json` are reused whole when they cover this run's scenes and characters.
- `clip_plans.json` and `clip_prompts.json` are written after every LLM call and reused scene by scene and clip by clip, so a crashed run resumes where it stopped.

To redo a step, delete its file. Earlier versions of every output are kept in `data/backups/`.

## From prompts to video

1. Generate the images from `data/asset_prompts.json`, host them, and add each URL under its NAME in `skills/seedance-curl/references/image_urls`. Voice samples go in `audio_urls`.
2. Run `main.py` again (only `build_curl` has new work), then check `missing` for the clip in `curl/curl_commands.json`.
3. `export ARK_API_KEY=...` and run the clip's `curl`. When the task finishes, add its `last_frame_url` to `skills/seedance-curl/references/last_frames`, so the next clip can continue from it.

## Code map

```
main.py                  entry point: runs the graph, prints a summary
agent/
  config.py              paths, skills per node, run settings, project style and constraints
  graph.py               wires the nodes in order
  state.py               the state passed between nodes, and the Scene/Shot/Clip/Profile names
  prompts.py             every instruction sent to the LLM
  llm.py                 OpenAI wrapper; loads the node's skills into its system prompt
  skills.py              reads skills/<name>/SKILL.md and its references/
  retry.py               ask, check the reply, ask again with the problems listed
  errors.py              friendly messages for OpenAI errors (no credits, bad key ...)
  nodes/                 one file per node, in run order
  helpers/               plain code used by the nodes (no LLM calls)
skills/                  the skill files the LLM steps follow
data/                    the input PDF and every output above
```

## Settings worth knowing ([agent/config.py](agent/config.py))

| Setting | What it does |
|---|---|
| `MAX_SCENES` | Process only the first N scenes (None = all) |
| `RETRIES` | How often a reply that fails its checks is sent back to the LLM |
| `DIRECTOR_CLIPS_PER_CALL` | Clips per director call; lower it if replies get cut off |
| `*_SKILLS` | Which skills each LLM node loads |
| `STYLE_LINE`, `BASE_CONSTRAINTS` | The film's locked style and the rules every clip carries |
| `SEEDANCE` | Seedance model, ratio, resolution and other API settings |

Keys stay out of the repo: `OPENAI_API_KEY` lives in `.env` (git-ignored), and the curl commands read `$ARK_API_KEY` from your shell.
