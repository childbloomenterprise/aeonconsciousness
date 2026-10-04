"""A compact, accessible site renderer driven by the worker's creative choices."""

from __future__ import annotations

from html import escape
from typing import Any


PALETTES = {
    "amber": ("#131016", "#251b25", "#f5e9d9", "#d6ac5b", "#b9aaba"),
    "violet": ("#111124", "#222344", "#f1efff", "#a9a1ff", "#b7b7d1"),
    "cyan": ("#081b22", "#10323b", "#e8fbfc", "#65d8d5", "#abd4d6"),
    "rose": ("#27151d", "#452636", "#fff1f0", "#efa8ad", "#dfc5ca"),
}


def render_site(value: dict[str, Any]) -> str:
    """Render one responsive HTML file; unknown facts stay absent."""

    name = escape(str(value.get("name", "New project"))[:100])
    role = escape(str(value.get("role", "Available for inquiries"))[:130])
    tagline = escape(str(value.get("tagline", "A compelling new presence"))[:180])
    intro = escape(str(value.get("intro", "Explore the work and start a conversation."))[:400])
    audience = escape(str(value.get("audience", "For thoughtful collaborators"))[:130])
    email = str(value.get("contact_email", "")).strip()
    if email and ("@" not in email or any(character in email for character in '<>"\r\n')):
        raise ValueError("contact_email is invalid.")
    palette_name = str(value.get("palette", "amber")).lower()
    if palette_name not in PALETTES:
        raise ValueError("Unknown palette. Choose amber, violet, cyan, or rose.")
    bg, surface, text, accent, muted = PALETTES[palette_name]
    raw_sections = value.get("sections", [])
    if not isinstance(raw_sections, list):
        raise ValueError("sections must be a list.")
    sections = []
    for item in raw_sections[:3]:
        if not isinstance(item, dict):
            continue
        heading = escape(str(item.get("heading", "Explore"))[:100])
        body = escape(str(item.get("body", "Get in touch to learn more."))[:350])
        sections.append(f'<article class="card"><span class="card-mark" aria-hidden="true">✦</span><h3>{heading}</h3><p>{body}</p></article>')
    if not sections:
        sections = [
            '<article class="card"><span class="card-mark" aria-hidden="true">✦</span><h3>Discover</h3><p>Explore the creative direction and possibilities.</p></article>',
            '<article class="card"><span class="card-mark" aria-hidden="true">✦</span><h3>Connect</h3><p>Share your brief and start a conversation.</p></article>',
        ]
    if email:
        safe_email = escape(email, quote=True)
        contact = f'<a class="button primary" href="mailto:{safe_email}">Start an inquiry <span aria-hidden="true">↗</span></a><p class="contact-note">{safe_email}</p>'
    else:
        contact = '<p class="contact-note">Contact details pending verification. Add a confirmed address before publishing.</p>'
    return f'''<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="Explore {name} and make an inquiry.">
  <title>{name} — {role}</title>
  <style>
    :root{{--bg:{bg};--surface:{surface};--ink:{text};--accent:{accent};--muted:{muted}}}
    *{{box-sizing:border-box}}
    html{{scroll-behavior:smooth}}
    body{{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,Segoe UI,sans-serif}}
    a{{color:inherit}}
    a:focus-visible{{outline:3px solid var(--accent);outline-offset:4px}}
    .wrap{{width:min(1120px,calc(100% - 48px));margin:auto}}
    .top{{display:flex;align-items:center;justify-content:space-between;gap:24px;padding:24px 0;border-bottom:1px solid color-mix(in srgb,var(--muted) 25%,transparent)}}
    .brand{{font-family:Georgia,serif;font-weight:700;font-size:1.25rem;letter-spacing:.04em;text-decoration:none}}
    .top nav{{display:flex;gap:26px;align-items:center}}
    .top nav a{{text-decoration:none;font-size:.84rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase}}
    .top nav a:hover{{color:var(--accent)}}
    .hero{{display:grid;grid-template-columns:1.1fr .9fr;align-items:center;gap:42px;min-height:630px;padding:80px 0}}
    .eyebrow{{color:var(--accent);font-size:.78rem;font-weight:800;letter-spacing:.18em;text-transform:uppercase}}
    h1,h2,h3,p{{margin-top:0}}
    h1,h2,h3{{font-family:Georgia,serif;line-height:1.12}}
    h1{{font-size:clamp(3.6rem,7vw,7rem);letter-spacing:-.055em;margin:20px 0 30px;max-width:850px}}
    .hero p{{color:var(--muted);font-size:1.12rem;max-width:540px}}
    .actions{{display:flex;flex-wrap:wrap;gap:14px;margin-top:34px}}
    .button{{display:inline-flex;align-items:center;gap:22px;padding:14px 22px;border:1px solid var(--accent);border-radius:4px;text-decoration:none;font-size:.9rem;font-weight:800}}
    .button.primary{{background:var(--accent);color:var(--bg)}}
    .button:hover{{transform:translateY(-2px)}}
    .art{{height:min(440px,72vw);position:relative;display:grid;place-items:center;isolation:isolate}}
    .art::before{{content:"";position:absolute;width:78%;aspect-ratio:1;border:1px solid var(--accent);border-radius:50%;transform:rotate(-18deg) scaleX(.7);box-shadow:0 0 100px color-mix(in srgb,var(--accent) 25%,transparent)}}
    .art::after{{content:"";position:absolute;width:54%;aspect-ratio:1;border-radius:50%;background:radial-gradient(circle at 30% 25%,var(--accent),var(--surface) 68%);opacity:.8;z-index:-1}}
    .art span{{font:700 clamp(5rem,14vw,11rem)/1 Georgia,serif;color:var(--bg);text-shadow:0 2px 40px var(--accent)}}
    .section{{padding:88px 0;border-top:1px solid color-mix(in srgb,var(--muted) 22%,transparent)}}
    .section-head{{display:flex;justify-content:space-between;align-items:end;gap:30px;margin-bottom:34px}}
    h2{{font-size:clamp(2.3rem,4.5vw,4.5rem);letter-spacing:-.035em;max-width:680px;margin:12px 0 0}}
    .section-head p{{max-width:350px;color:var(--muted);margin:0}}
    .cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,250px),1fr));gap:16px}}
    .card{{background:var(--surface);padding:32px;border:1px solid color-mix(in srgb,var(--muted) 18%,transparent);min-height:245px}}
    .card-mark{{color:var(--accent);font-size:1.8rem}}
    .card h3{{font-size:1.6rem;margin:28px 0 14px}}
    .card p{{color:var(--muted);margin:0}}
    .contact{{display:grid;grid-template-columns:1fr 1fr;gap:40px;align-items:end}}
    .contact-note{{color:var(--muted);overflow-wrap:anywhere}}
    footer{{border-top:1px solid color-mix(in srgb,var(--muted) 22%,transparent);padding:30px 0;color:var(--muted);font-size:.82rem}}
    footer .wrap{{display:flex;justify-content:space-between;gap:20px}}
    @media(max-width:760px){{
      .wrap{{width:min(100% - 32px,560px)}}
      .top{{align-items:flex-start}}
      .top nav{{gap:12px;flex-wrap:wrap;justify-content:flex-end}}
      .top nav a{{font-size:.68rem}}
      .hero{{grid-template-columns:1fr;min-height:auto;padding:68px 0 30px;gap:10px}}
      h1{{font-size:clamp(3rem,13vw,5rem)}}
      .art{{height:260px}}
      .art::before{{width:240px}}
      .art::after{{width:170px}}
      .art span{{font-size:6rem}}
      .section{{padding:64px 0}}
      .section-head,.contact{{display:block}}
      .section-head p{{margin-top:20px}}
      footer .wrap{{display:block}}
      footer .wrap span{{display:block}}
    }}
    @media(prefers-reduced-motion:reduce){{html{{scroll-behavior:auto}}.button:hover{{transform:none}}}}
  </style>
</head>
<body>
  <header class="wrap top"><a class="brand" href="#home">{name}</a><nav aria-label="Main navigation"><a href="#about">About</a><a href="#explore">Explore</a><a href="#contact">Contact</a></nav></header>
  <main id="home">
    <section class="wrap hero" aria-labelledby="hero-title">
      <div><span class="eyebrow">{role}</span><h1 id="hero-title">{tagline}</h1><p>{intro}</p><div class="actions"><a class="button primary" href="#contact">Get in touch <span aria-hidden="true">↗</span></a><a class="button" href="#explore">Explore more</a></div></div>
      <div class="art" aria-hidden="true"><span>✦</span></div>
    </section>
    <section class="section" id="about"><div class="wrap"><span class="eyebrow">A clear introduction</span><div class="section-head"><h2>Meet {name}</h2><p>{audience}</p></div></div></section>
    <section class="section" id="explore"><div class="wrap"><span class="eyebrow">Discover</span><div class="section-head"><h2>Where ideas take shape.</h2><p>Choose a direction, learn more, or start a conversation.</p></div><div class="cards">{''.join(sections)}</div></div></section>
    <section class="section" id="contact"><div class="wrap contact"><div><span class="eyebrow">Next step</span><h2>Let's make something memorable.</h2></div><div>{contact}</div></div></section>
  </main>
  <footer><div class="wrap"><span>{name}</span><span>Built for thoughtful inquiries.</span></div></footer>
</body>
</html>
'''
