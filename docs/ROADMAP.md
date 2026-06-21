# AXIOM — Product Roadmap

## Vision

Scale AXIOM from a single-topic-per-day pipeline to a production-grade, fully autonomous system that generates 1000+ hours of educational video content per year across MBBS and BTech curricula.

---

## Phases

### Phase 1: Foundation (Delivered ✅)

**Timeline**: Q2 2026

**Scope**:
- Core pipeline (Notion → NotebookLM → TTS → FFmpeg → YouTube)
- Basic dashboard UI
- Notion database schema
- YouTube uploader with OAuth2
- Error handling and retry logic

**Status**: ✅ COMPLETE

**Key Deliverables**:
- 1 topic/day capacity
- 85%+ success rate
- Dashboard for queue management and publishing

---

### Phase 2: Quality & Automation (In Progress)

**Timeline**: Q3 2026

**Scope**:
- Viral SEO optimization (12 title formulas, 29+ keywords)
- AI thumbnail generation (Gemini + headshot compositing)
- Intelligent topic branching (YouTube trend analysis)
- Colab auto-launch (no manual URL pasting)
- Voice quality refinement (CosyVoice 2 tuning)

**Current Status**: 85% complete

**Remaining Work**:
- ✅ SEO title generation — DONE
- ✅ Thumbnail generation — DONE
- ✅ Topic strategy & branching — DONE
- ✅ Colab auto-launch — DONE
- ⏳ Voice quality A/B testing — IN PROGRESS
- ⏳ Audio/video sync refinement — PLANNED

**Key Deliverables**:
- 95%+ success rate
- 9/10 average video quality
- Per-video thumbnail uniqueness

---

### Phase 3: Scale & Autonomy (Planned)

**Timeline**: Q4 2026

**Scope**:
- Batch processing (3+ topics/day)
- Autonomous daily scheduler (node-cron)
- YouTube Analytics integration
- Competitor thumbnail scraping
- Audio/video sync (Whisper + FFmpeg time-stretch)
- Multi-language support (initial: English only)

**Key Deliverables**:
- 3+ topics/day capacity
- 100% autonomous daily runs
- Per-video analytics dashboard
- Voice library (dramatic, calm, energetic tones)
- 1000+ subs/month growth target

**Estimated Effort**: 4-6 weeks

---

### Phase 4: Intelligence & Optimization (Future)

**Timeline**: Q1 2027

**Scope**:
- ML-powered topic prioritization (based on viewer engagement)
- Real-time trend detection (YouTube trending topics)
- Audience sentiment analysis (comments, ratings)
- Dynamic thumbnail A/B testing
- Adaptive voice tone selection (match audience mood)
- Multi-platform publishing (YouTube Shorts, Instagram Reels, TikTok)

**Key Deliverables**:
- 2000+ subs/month growth
- 50%+ improvement in video retention
- Fully data-driven content strategy

---

## Timeline

```
Q2 2026 ████████ Foundation (DONE)
Q3 2026 ██████░░ Quality & Automation (IN PROGRESS)
Q4 2026 ░░░░░░░░ Scale & Autonomy (PLANNED)
Q1 2027 ░░░░░░░░ Intelligence & Optimization (FUTURE)
```

---

## Success Metrics

| Metric | Current | Phase 2 Target | Phase 3 Target | Phase 4 Target |
|---|---|---|---|---|
| Videos/Day | 1 | 1 | 3+ | 5+ |
| Success Rate | 85% | 95%+ | 98%+ | 99%+ |
| Avg Video Quality | 7.5/10 | 9/10 | 9.5/10 | 9.8/10 |
| Avg Watch Time | TBD | +30% | +50% | +75% |
| Subscriber Growth/Month | 0 (launch) | 500+ | 2000+ | 5000+ |
| Content Hours/Year | 20 | 80 | 250+ | 500+ |

---

## Dependency Map

```
┌─────────────────────────┐
│ Phase 1: Foundation ✅  │
│ (Core pipeline)         │
└────────────┬────────────┘
             │
        ┌────▼────────────────────────────────┐
        │ Phase 2: Quality & Automation (WIP)  │
        │ - SEO, thumbnails, branching         │
        │ - Colab auto-launch                  │
        │ - Voice refinement                   │
        └────────────┬─────────────────────────┘
                     │
        ┌────────────▼─────────────────────────────┐
        │ Phase 3: Scale & Autonomy (PLANNED)      │
        │ - Batch processing (3+/day)              │
        │ - Daily autonomous scheduler             │
        │ - YouTube Analytics                      │
        │ - Audio/video sync (Whisper + FFmpeg)    │
        └────────────┬─────────────────────────────┘
                     │
        ┌────────────▼──────────────────────────┐
        │ Phase 4: Intelligence & Optimization  │
        │ - ML-powered topic prioritization     │
        │ - Real-time trends                    │
        │ - Multi-platform publishing           │
        │ - Sentiment analysis                  │
        └───────────────────────────────────────┘
```

---

## Technical Debt & Planned Refactors

| Item | Priority | Phase | Est. Effort |
|---|---|---|---|
| Transcript timestamp alignment (Engine 1/2) | HIGH | 3 | 1 week |
| Batch processing parallelization | HIGH | 3 | 1 week |
| YouTube Analytics API integration | MEDIUM | 3 | 3 days |
| Colab notebook versioning | MEDIUM | 2 | 2 days |
| Voice library management | MEDIUM | 3 | 3 days |
| Error recovery automation | MEDIUM | 2 | 2 days |
| Dashboard performance optimization | LOW | 4 | 1 day |
| Logging & monitoring improvements | LOW | 3 | 2 days |

---

## Open Questions

1. **Audio/Video Sync**: How to handle pacing drift when TTS differs from original? 
   - Answer: Implement Whisper timestamps + FFmpeg time-stretch (Phase 3)

2. **Autonomous Scheduling**: How to handle failures without human oversight?
   - Answer: Build retry queue + email alerts + manual override dashboard

3. **Content Saturation**: How many videos can one channel safely publish before algorithmic suppression?
   - Answer: Start with 1/day, monitor engagement, scale to 3/day if metrics improve

4. **Voice Fatigue**: Can one voice clone sustain 1000+ videos without listener fatigue?
   - Answer: Build voice library (3-5 tone variants) by Phase 3

5. **Notion Scalability**: Can Notion APIs handle millions of rows as we scale?
   - Answer: Monitor API quota usage; consider hybrid Notion + PostgreSQL by Phase 4

---

## Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Colab session limits (max concurrent notebooks) | MEDIUM | HIGH | Implement queue backoff; support multiple Colab accounts |
| YouTube Content ID claims on music | HIGH | HIGH | Switch to royalty-free music library; ensure full SRT licensing |
| NotebookLM generation failures | MEDIUM | HIGH | Add fallback script generation; manual brief storage |
| Notion API rate limits | LOW | MEDIUM | Cache topics locally; implement backoff |
| Voice clone quality degradation | LOW | MEDIUM | Regular voice sampling; listener feedback loop |
| TTS Colab dependency risk | MEDIUM | HIGH | Plan alternative TTS (ElevenLabs API, local Whisper TTS) |

---

## Budget & Resources

| Phase | Estimated Cost | Resource Allocation |
|---|---|---|
| Phase 1 (Foundation) | $500-1000 | 40 hrs (API keys, Colab credits) |
| Phase 2 (Quality) | $200-500 | 25 hrs (continued Colab + Gemini usage) |
| Phase 3 (Scale) | $1000-2000 | 40 hrs (batch Colab, analytics, infra) |
| Phase 4 (Intelligence) | $2000-5000 | 60 hrs (ML models, multi-platform APIs) |

---

## How to Contribute

See [CONTRIBUTING.md](../CONTRIBUTING.md) for developer guidelines.

---

## See Also

- **[SPRINT-LOG.md](SPRINT-LOG.md)** — Current sprint progress
- **[ARCHITECTURE.md](ARCHITECTURE.md)** — System design
- **[README.md](../README.md)** — Getting started
