"""Optional second opinion from Claude on the top-ranked jobs (needs ANTHROPIC_API_KEY or `ant auth login`)."""
from typing import List

import anthropic
from pydantic import BaseModel, Field

SYSTEM = """You are a technical recruiter assessing how well one candidate fits one job ad.
Judge realistically: the candidate is a final-year B.Sc. Software Engineering student (LUT, Finland) on exchange at TUM Munich,
looking for working-student, internship, trainee or junior roles. Weigh hard requirements (years of experience,
mandatory languages, degree level, specific must-have tech) more than nice-to-haves. Answer in English."""


class Verdict(BaseModel):
    fit_score: int = Field(description="0-100 realistic chance-weighted fit")
    hard_blockers: List[str] = Field(description="Requirements the candidate clearly does not meet")
    strongest_selling_points: List[str] = Field(description="CV items to emphasise in the application, max 4")
    gaps_to_address: List[str] = Field(description="Skills or experience to address in the cover letter, max 4")
    summary: str = Field(description="One or two sentences")


def assess(client, model, cv_text, job):
    msg = client.messages.parse(
        model=model,
        max_tokens=16000,
        system=SYSTEM,
        output_config={"effort": "low"},
        extra_headers={"anthropic-beta": "server-side-fallback-2026-07-01"},
        extra_body={"fallbacks": "default"},
        messages=[{"role": "user", "content": (
            f"<cv>\n{cv_text}\n</cv>\n\n<job>\nTitle: {job['title']}\nCompany: {job['company']}\n"
            f"Location: {job['location']}\n\n{(job.get('description') or '')[:12000]}\n</job>")}],
        output_format=Verdict,
    )
    if msg.stop_reason == "refusal" or msg.parsed_output is None:
        return None
    return msg.parsed_output.model_dump()


def enrich(jobs, profile, cfg, store):
    llm_cfg = cfg["llm"]
    client = anthropic.Anthropic()
    todo = [j for j in jobs[: llm_cfg["top_n"]] if not j.get("llm") and j.get("description")]
    print(f"Asking Claude ({llm_cfg['model']}) about {len(todo)} jobs...")
    for i, job in enumerate(todo, 1):
        try:
            job["llm"] = assess(client, llm_cfg["model"], profile.text, job)
        except (anthropic.AuthenticationError, TypeError) as e:
            if isinstance(e, TypeError) and "authentication" not in str(e):
                raise
            print("  ! No valid Anthropic credentials. Set ANTHROPIC_API_KEY. Skipping LLM step.")
            return
        except anthropic.RateLimitError:
            print("  ! Rate limited. Stopping the LLM step for this run.")
            return
        except anthropic.APIStatusError as e:
            print(f"  ! API error {e.status_code} on '{job['title']}', skipping")
            continue
        except anthropic.APIConnectionError:
            print("  ! Connection error, skipping")
            continue
        if job["llm"]:
            store.set_llm(job)
            print(f"  [{i}/{len(todo)}] {job['llm']['fit_score']:>3}  {job['title']} @ {job['company']}")
