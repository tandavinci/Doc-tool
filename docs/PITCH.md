# Documentation AI Tool — Project Pitch

## The Problem

Information developers at Infor spend significant time on repetitive, tool-fragmented workflows:

| Pain Point | Impact |
|-----------|--------|
| Checking content against 90+ writing standards | 30-60 min per document, manual, error-prone |
| Converting between formats (Word → DITA XML) | 15-30 min per topic, tedious markup work |
| Getting AI feedback on documentation | Requires cloud tools, data privacy concerns |
| Assessing documentation impact from Jira changes | Hours of manual cross-referencing |
| Context-switching between 5+ separate tools | Lost productivity, inconsistent workflows |

**Current state:** Writers use separate tools for editing (Word/Oxygen), standards checking (manual review), DITA conversion (manual XML), AI assistance (cloud-based ChatGPT with data exposure), and impact analysis (spreadsheets + Jira browsing).

---

## The Solution

A single offline desktop application that consolidates all documentation workflows:

```
 ┌────────────────────────────────────────────────────────┐
 │           Documentation AI Tool                         │
 │                                                         │
 │  Write → Analyze → Review → Convert → Publish          │
 │                                                         │
 │  All in one window. All offline. All compliant.         │
 └────────────────────────────────────────────────────────┘
```

---

## Value Proposition

### For Writers
- **90% faster compliance checking** — instant feedback instead of waiting for peer review
- **Zero context-switching** — write, review, convert, and get AI help in one window
- **AI assistant that knows Infor standards** — trained on the exact rules, not generic advice
- **Offline operation** — works on planes, in secure environments, without VPN

### For the Organization
- **$0 recurring cost** — no cloud AI subscriptions (runs on local hardware)
- **Zero data exposure** — all processing happens locally, no content leaves the machine
- **Consistent quality** — same rules enforced automatically across all writers
- **Faster time-to-publish** — fewer review cycles needed when content is pre-checked
- **Scalable** — distribute as a standalone .exe, no IT infrastructure needed

### ROI Estimate

| Metric | Before | After | Savings |
|--------|--------|-------|---------|
| Standards review time per doc | 45 min | 5 min | 89% reduction |
| DITA conversion per topic | 20 min | 30 sec | 97% reduction |
| AI assistance (annual subscription) | $240/user/year | $0 | 100% eliminated |
| Review cycle iterations | 3-4 rounds | 1-2 rounds | 50% reduction |
| Documentation impact analysis | 2-3 hours | 5 min | 95% reduction |

For a team of 20 writers: **~$100K+ annual productivity gain** (conservative estimate based on time savings alone).

---

## Key Features (7 Tabs)

| # | Feature | What It Does |
|---|---------|-------------|
| 1 | **DOC to DITA** | Converts pasted/uploaded content into valid DITA XML (Concept or Task) |
| 2 | **Content Analysis** | Scans text against 90+ Infor rules with inline Grammarly-style fixes |
| 3 | **Initial Draft** | Lightweight Word-like editor with comments, replies, and formatting |
| 4 | **MarkItDown** | Converts any file (PDF, Word, PPT, Excel, HTML) to Markdown |
| 5 | **Quick Review** | Compliance score (0-100) + automatic standards-compliant rewrite |
| 6 | **Doc Impact** | Identifies which documentation needs updating from Jira changes |
| 7 | **AI Assistant** | Chat with local AI trained on all Infor ID writing standards |

---

## Technical Differentiators

| Aspect | Our Tool | Cloud AI (ChatGPT/Copilot) |
|--------|----------|---------------------------|
| Data privacy | 100% local | Data sent to external servers |
| Internet required | No (after setup) | Yes, always |
| Infor standards knowledge | Hardcoded + trained | Generic, must be prompted |
| Recurring cost | $0 | $20-240/user/year |
| Response consistency | Deterministic rules | Varies per request |
| Deployment | Single .exe | Browser + account management |
| Customization | Full control (open source) | Limited by vendor |

---

## Competitive Landscape

| Tool | Standards Checking | DITA Conversion | AI Chat | Offline | Cost |
|------|-------------------|----------------|---------|---------|------|
| **Our Tool** | ✅ 90+ rules | ✅ | ✅ Local | ✅ | Free |
| Acrolinx | ✅ (cloud) | ❌ | ❌ | ❌ | $$$$$ |
| Grammarly | Partial | ❌ | ❌ | ❌ | $$$ |
| ChatGPT | Prompted only | Prompted only | ✅ Cloud | ❌ | $$ |
| Oxygen XML | Limited | ✅ | ❌ | ✅ | $$$$ |
| MS Word + Copilot | Basic | ❌ | ✅ Cloud | ❌ | $$$ |

---

## Implementation Status

| Phase | Status | Delivered |
|-------|--------|-----------|
| Core Analysis Engine | ✅ Complete | 90+ rules, inline fixes, undo/redo |
| Document Editor | ✅ Complete | WYSIWYG, comments, file I/O |
| DITA Conversion | ✅ Complete | Concept + Task generation |
| File Conversion (MarkItDown) | ✅ Complete | 20+ format support |
| Quick Review + Rewrite | ✅ Complete | 8-category scoring + auto-rewrite |
| AI Assistant | ✅ Complete | 22 capabilities, local Ollama |
| Doc Impact Assessment | ✅ Complete | Jira-based impact analysis |
| Offline Packaging | ✅ Complete | Single .exe with bundled AI |
| RAG (documentation search) | 🔮 Next | Vector-indexed doc search |
| Streaming AI | 🔮 Next | Token-by-token response display |

---

## Deployment Plan

### Phase 1: Pilot (Current)
- 2-3 writers using the tool daily
- Collect feedback, measure time savings
- Iterate on rules and AI accuracy

### Phase 2: Team Rollout
- Build standalone installer (build-all.bat)
- Distribute to full ID team (20+ writers)
- Add team-specific terminology/rules

### Phase 3: Enterprise
- Central documentation index (RAG)
- GPU-accelerated AI (8B model for quality)
- Integration with existing CMS workflows
- Custom model fine-tuning on Infor docs

---

## Requirements

| Resource | Specification |
|----------|--------------|
| Hardware | Any Windows 10/11 PC, 8GB RAM, ~4GB disk |
| Software | None needed on target (self-contained installer) |
| Network | None after initial setup |
| GPU | Optional (CPU works fine, GPU = 3x faster AI) |
| IT Support | Zero — no servers, no accounts, no maintenance |

---

## Risk Mitigation

| Risk | Mitigation |
|------|-----------|
| AI accuracy | Rules engine catches 90% deterministically; AI is supplementary |
| Model quality (3B) | Upgradeable to 8B/70B as hardware allows |
| Offline-only limitation | By design — privacy and reliability advantage |
| Single platform (Windows) | Electron supports Mac/Linux; cross-platform build possible |
| Maintenance burden | No external dependencies; self-contained; rules are config-driven |

---

## Ask

1. **Pilot approval** — 30-day pilot with 3 writers measuring time savings
2. **GPU hardware** (optional) — One NVIDIA GPU (16GB VRAM) for faster AI responses
3. **Feedback loop** — Weekly 15-min sync to iterate on rules and features

---

## Contact

Built by the Infor Information Development innovation team.
Repository: https://github.com/tandavinci/Doc-tool/tree/DOC2DITA
