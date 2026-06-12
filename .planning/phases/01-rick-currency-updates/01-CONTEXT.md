# Phase 1: Rick Currency Updates - Context

**Gathered:** 2026-06-12
**Status:** Ready for planning
**Source:** Auto-generated from ROADMAP.md scope

<domain>
## Phase Boundary

Update 4 existing Apple-specialist Rick agent definitions with WWDC25/26 platform changes. Each Rick is a markdown file in `~/.claude/agents/` with frontmatter (name, description, model) and a prompt body defining domain expertise, tools, and knowledge areas.

This phase covers ONLY existing Rick updates (RICK-01 through RICK-04). New Ricks (RICK-05 through RICK-08) were already created in a prior session — they exist at `~/.claude/agents/`.

</domain>

<decisions>
## Implementation Decisions

### Rick File Format
- Agent definitions are markdown files with YAML frontmatter + prompt body
- Located at `~/.claude/agents/{name}.md`
- Must include: name, description (frontmatter), domain expertise (body), tools list, WebSearch/WebFetch availability
- Must NOT break existing tool assignments or model overrides

### Update Strategy
- Research WWDC25/26 changes for each domain via web search (original research files no longer exist at cached paths)
- Update prompt body with new frameworks, APIs, deprecations, and migration paths
- Preserve existing structure — don't rewrite, augment
- Each Rick gets its own plan for atomic updates

### Scope Per Rick

**RICK-01 (apple-elitist-rick):** Foundation Models framework, Liquid Glass, Metal 4, BNNS Graph, SpeechAnalyzer, quantum crypto, iOS 26 SDK deprecations, SF Symbols 7

**RICK-02 (gamer-rick):** Apple Games app, Metal 4 game features, Game Center updates, visionOS spatial accessories

**RICK-03 (swiftui-liquid-glass):** Spatial layout, WebKit for SwiftUI, SwiftUI+RealityKit, AttributedString enhancements

**RICK-04 (swift-concurrency-expert):** C++/Swift interop safety, Java interop, SwiftUI concurrency patterns for iOS 26

### Claude's Discretion
- Exact wording and organization of new content within each Rick's prompt body
- Whether to restructure sections or append new sections
- Depth of API detail (signatures vs. conceptual descriptions)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Rick Agent Definitions (files to modify)
- `~/.claude/agents/apple-elitist-rick.md` — Apple platform generalist
- `~/.claude/agents/gamer-rick.md` — Apple Gaming / GameController specialist
- `~/.claude/agents/swiftui-liquid-glass.md` — SwiftUI Liquid Glass API specialist
- `~/.claude/agents/swift-concurrency-expert.md` — Swift Concurrency specialist

### Project Files
- `.planning/REQUIREMENTS.md` — RICK-01 through RICK-04 requirement text
- `.planning/ROADMAP.md` — Phase 1 scope and plan descriptions

### Pre-existing New Ricks (reference only — NOT modified in this phase)
- `~/.claude/agents/foundation-models-rick.md` — Shows current format/content for AFM domain
- `~/.claude/agents/metal-4-rick.md` — Shows current format/content for Metal 4 domain
- `~/.claude/agents/privacy-rick.md` — Shows current format/content for Privacy domain
- `~/.claude/agents/visionos-rick.md` — Shows current format/content for visionOS domain

</canonical_refs>

<specifics>
## Specific Ideas

- Each Rick update should be a separate plan (1.1 through 1.4) for atomic commits
- Web search for WWDC25/26 session content is required since cached research is stale
- Cross-reference new Ricks (Phase 2) to avoid duplication — they already cover some WWDC25/26 content

</specifics>

<deferred>
## Deferred Ideas

None — all RICK-01 through RICK-04 updates are in scope.

</deferred>

---

*Phase: 01-rick-currency-updates*
*Context gathered: 2026-06-12 via auto-generation from roadmap*
