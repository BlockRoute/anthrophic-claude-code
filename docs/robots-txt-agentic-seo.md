# robots.txt for Agentic Search Optimization

A reference for structuring `robots.txt` so your site is discoverable by AI
search engines and agentic assistants (ChatGPT, Claude, Perplexity, Google AI,
Copilot) — the emerging discipline sometimes called **GEO** (Generative Engine
Optimization) or **AEO** (Answer Engine Optimization).

The core idea: traditional SEO optimizes for one crawler family (Googlebot).
Agentic search adds *three* new categories of bot, each with different behavior.
If you want your content cited in AI answers, you must explicitly allow the
relevant user-agents — many sites unintentionally block them.

## The three categories of AI bot

Every AI bot falls into one of three buckets. Deciding access means deciding per
bucket, because they do very different things:

| Category | What it does | Blocking it means | Example agents |
|---|---|---|---|
| **Search / index crawlers** | Crawl and index pages so they can be *surfaced and cited* in AI-generated search answers | You won't appear in AI search results | `OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`, `Googlebot`, `Bingbot` |
| **User-triggered fetchers** | Fetch a page live *because a specific user asked* (pasted a link, requested a summary) | Users can't pull your page into their AI session on demand | `ChatGPT-User`, `Claude-User`, `Perplexity-User` |
| **Training crawlers** | Collect content to *train or ground* foundation models | Your content isn't used for model training | `GPTBot`, `ClaudeBot`, `Google-Extended` |

Key insight: **allowing training ≠ allowing search, and vice versa.** They're
separate user-agents. A site that wants maximum AI-search visibility but *not*
model training would allow the first two categories and disallow the third. The
example below allows all three (maximum openness).

## Annotated example

```
# --- Search / index crawlers: get cited in AI answers ---
User-agent: OAI-SearchBot        # OpenAI — ChatGPT Search index
Allow: /

User-agent: Claude-SearchBot     # Anthropic — Claude search index
Allow: /

User-agent: PerplexityBot        # Perplexity — search index
Allow: /

User-agent: Googlebot            # Google Search (+ AI Overviews)
Allow: /

User-agent: Bingbot              # Bing (also powers Copilot)
Allow: /

# --- User-triggered fetchers: live fetch on a user's request ---
User-agent: ChatGPT-User         # OpenAI — user action in ChatGPT
Allow: /

User-agent: Claude-User          # Anthropic — user action in Claude
Allow: /

User-agent: Perplexity-User      # Perplexity — user action
Allow: /

# --- Training crawlers: content used to train/ground models ---
User-agent: GPTBot               # OpenAI training crawler
Allow: /

User-agent: ClaudeBot            # Anthropic training/general crawler
Allow: /

User-agent: Google-Extended      # Google — Gemini/Vertex AI training toggle
Allow: /

# --- Everyone else ---
User-agent: *
Allow: /

Sitemap: https://example.com/sitemap.xml
```

## Structure rules that matter

- **One directive block per user-agent.** Each block is `User-agent: <name>`
  followed by its `Allow:` / `Disallow:` lines. Do **not** leave a blank line
  between `User-agent:` and its own name — `User-agent:` and the bot name must be
  on the same line (a stray newline there breaks the block).
- **`Allow: /` is explicit permission** for the whole site. If you only ever want
  to *permit*, `Allow: /` and a bare `Disallow:` (empty value) are equivalent;
  use `Disallow: /path` to carve out exceptions.
- **Order & specificity:** most crawlers match the *most specific* user-agent
  block that applies to them and ignore the wildcard `*` block once matched. So
  per-bot blocks override the `User-agent: *` catch-all — list the specific bots
  you care about explicitly rather than relying on `*`.
- **`Sitemap:` is global**, not tied to any user-agent block. Put it once
  (conventionally at the bottom) with an absolute URL. It helps every crawler,
  including AI ones, find your full page list.
- **robots.txt lives at the domain root** (`https://site.com/robots.txt`) and is
  a *voluntary* standard — well-behaved bots honor it; it is not access control.
  Use auth/WAF for anything that must actually be private.

## Practical checklist

- [ ] File served at `https://<domain>/robots.txt`, HTTP 200, `text/plain`.
- [ ] Search crawlers (`OAI-SearchBot`, `Claude-SearchBot`, `PerplexityBot`,
      `Googlebot`, `Bingbot`) allowed if you want AI-search visibility.
- [ ] User fetchers (`ChatGPT-User`, `Claude-User`, `Perplexity-User`) allowed if
      you want users to pull your pages into their AI sessions.
- [ ] Training crawlers (`GPTBot`, `ClaudeBot`, `Google-Extended`) set to your
      policy — allow to opt in, `Disallow: /` to opt out.
- [ ] Valid `Sitemap:` line with an absolute URL.
- [ ] No stray blank line between `User-agent:` and the bot name.

## Notes & caveats

- Bot names and their behavior change over time; each vendor publishes the
  current list (OpenAI, Anthropic, Perplexity, Google, Microsoft docs). Re-check
  periodically and add new agents as they appear.
- Allowing a search/index bot maximizes the *chance* of being cited but does not
  guarantee it — the answer engine still ranks and selects sources.
- robots.txt controls *crawling*, not *citation formatting*. Pair it with clean,
  well-structured content, semantic HTML, and a sitemap for best results.
