# Phase 1: Rick Currency Updates - Research

**Researched:** 2026-06-12
**Domain:** Apple specialist agent definition updates (WWDC25/26 platform changes)
**Confidence:** HIGH

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Agent definitions are markdown files with YAML frontmatter + prompt body
- Located at `~/.claude/agents/{name}.md`
- Must include: name, description (frontmatter), domain expertise (body), tools list, WebSearch/WebFetch availability
- Must NOT break existing tool assignments or model overrides
- Research WWDC25/26 changes for each domain via web search (original research files no longer exist at cached paths)
- Update prompt body with new frameworks, APIs, deprecations, and migration paths
- Preserve existing structure -- don't rewrite, augment
- Each Rick gets its own plan for atomic updates (plans 1.1 through 1.4)

### Claude's Discretion
- Exact wording and organization of new content within each Rick's prompt body
- Whether to restructure sections or append new sections
- Depth of API detail (signatures vs. conceptual descriptions)

### Scope Per Rick
- RICK-01 (apple-elitist-rick): Foundation Models framework, Liquid Glass, Metal 4, BNNS Graph, SpeechAnalyzer, quantum crypto, iOS 26 SDK deprecations, SF Symbols 7
- RICK-02 (gamer-rick): Apple Games app, Metal 4 game features, Game Center updates, visionOS spatial accessories
- RICK-03 (swiftui-liquid-glass): Spatial layout, WebKit for SwiftUI, SwiftUI+RealityKit, AttributedString enhancements
- RICK-04 (swift-concurrency-expert): C++/Swift interop safety, Java interop, SwiftUI concurrency patterns for iOS 26

### Deferred Ideas (OUT OF SCOPE)
None -- all RICK-01 through RICK-04 updates are in scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RICK-01 | apple-elitist-rick updated with WWDC25/26 changes | WWDC25 Foundation Models, Liquid Glass, Metal 4, new frameworks all documented. WWDC26: SiriKit deprecation, App Intents mandate, UISceneDelegate deprecation Sept 2026, Swift 6.4 ergonomics, Xcode 27 Apple silicon-only |
| RICK-02 | gamer-rick updated with WWDC25/26 changes | Apple Games App (standalone app), Game Center integration, Metal 4 game features (mesh shaders, shader ML, frame interpolation), visionOS spatial accessories (Logitech Muse, Bluetooth HID) all documented |
| RICK-03 | swiftui-liquid-glass updated with WWDC25/26 changes | SwiftUI spatial layout (WWDC25-273), WebKit for SwiftUI (WWDC25-231), SwiftUI+RealityKit (WWDC25), AttributedString in TextEditor (WWDC25-280) all documented. WWDC26: Liquid Glass intensity switch, enhanced toolbar controls |
| RICK-04 | swift-concurrency-expert updated with WWDC25/26 changes | C++ interop (auto-generated bindings), Java interop (Swift-Java project), SwiftUI default @MainActor isolation (WWDC25-256/268), structured concurrency improvements, Swift 6.4 ergonomics all documented |
</phase_requirements>

## Summary

This phase updates 4 existing Apple-specialist Rick agent definitions with WWDC25 and WWDC26 platform changes. Each Rick is a markdown file in `~/.claude/agents/` with YAML frontmatter (name, description, tools, model) and a prompt body defining domain expertise. The Ricks already contain substantial WWDC25 content from a prior session. The primary research task is identifying what WWDC26 (announced June 8, 2026) content is missing and what WWDC25 content needs enhancement.

**Key finding:** The 4 existing Ricks already have extensive WWDC25 coverage from a prior session. The update is primarily about adding WWDC26 content (iOS 27, macOS 27, visionOS 27, Swift 6.4, Xcode 27) and ensuring nothing was missed from WWDC25. The 4 new Ricks (foundation-models-rick, metal-4-rick, privacy-rick, visionos-rick) already cover many WWDC25 domains in depth -- existing Ricks should reference them rather than duplicate.

**Primary recommendation:** Add WWDC26 content as a new section in each Rick, enhance existing WWDC25 sections where gaps are found, cross-reference new Ricks for domains they own, and keep existing structure intact.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Agent file editing | Local filesystem (CLI) | -- | Markdown files in `~/.claude/agents/` |
| WWDC content research | External (WebSearch) | -- | Apple developer docs, WWDC session videos |
| Cross-reference dedup | Local filesystem (Read) | -- | Read new Ricks to avoid duplication |
| YAML frontmatter preservation | Local filesystem (Edit) | -- | Must not break name/description/tools/model |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| N/A | N/A | N/A | This is a markdown file editing phase, no code dependencies |

### Supporting

| Tool | Purpose | When to Use |
|------|---------|-------------|
| WebSearch | Research WWDC25/26 changes | Verified in this session |
| WebFetch | Fetch Apple developer documentation | For specific API details |
| Read/Write/Edit | Agent file operations | All file modifications |

**Installation:** None required.

**Version verification:** N/A -- no code dependencies.

## Architecture Patterns

### Rick File Structure (Existing Pattern)

All 4 Ricks follow this consistent structure. Updates MUST preserve it:

```
---
name: {rick-name}
description: {one-line description}
model: {glm-5-turbo | opus}
tools:
  - Read
  - Write
  - Edit
  - Bash
  - Grep
  - Glob
  - WebSearch  (apple-elitist-rick and gamer-rick only)
  - WebFetch   (apple-elitist-rick and gamer-rick only)
---

# {Rick Name} - {Title}

## Identity
{Character description, expertise scope}

## Core Philosophy
{Guiding principles in Rick's voice}

## Your {Domain} Domains
### N. {Domain Area}
{Code examples, reject/accept patterns, checklists}

## {Rick Name}'s Review Checklist
{Comprehensive checklist organized by domain}

## {Rick Name}'s Required Output
{Output format template}

## {Rick Name}'s Motivation
{Character motivation, SLC-first principles}

---
**Council Integration:**
{Tier, trigger, voting power, collaborations}
```

### Pattern 1: WWDC Content Addition

**What:** Add WWDC26 content as a new section or augment existing WWDC25 sections.
**When to use:** When a Rick needs WWDC26 platform updates.
**Example approach:**

```markdown
## WWDC26 Updates -- {domain area}

### {New Feature/Framework}
{Description and code examples following existing Rick voice}

**Key points:**
- {Important behavior}
- {Migration path from WWDC25 equivalent if applicable}

**Review Rules:**
- {What to reject}
- {What to accept}
```

### Pattern 2: Cross-Reference to New Ricks

**What:** Instead of duplicating content that new Ricks already cover in depth, add a reference note.
**When to use:** When the new Rick covers the domain more deeply than what the existing Rick needs.
**Example:**

```markdown
> **Note:** For deep Foundation Models framework expertise (LanguageModelSession, @Generable, Tool protocol, LoRA adapters), see **Foundation Models Rick** (`~/.claude/agents/foundation-models-rick.md`). This Rick covers AFM integration patterns at the platform level -- the specialist covers the full API surface.
```

### Anti-Patterns to Avoid

- **Don't rewrite existing content.** The CONTEXT.md explicitly says "Preserve existing structure -- don't rewrite, augment."
- **Don't break YAML frontmatter.** The name, description, model, and tools fields must remain unchanged.
- **Don't duplicate new Rick content verbatim.** Cross-reference instead.
- **Don't add WWDC content without code examples.** Each Rick uses accept/reject code patterns -- maintain this convention.
- **Don't forget to update the review checklist.** New domains need new checklist items.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| WWDC session content discovery | Manual URL guessing | WebSearch with session names | Apple's WWDC video URLs follow predictable patterns but search is faster and more reliable |
| API verification | Training knowledge (may be stale) | WebSearch + Apple developer docs | WWDC26 content is < 1 week old, training data cannot cover it |

## Common Pitfalls

### Pitfall 1: Duplicating New Rick Content
**What goes wrong:** apple-elitist-rick already has a Foundation Models section. foundation-models-rick has a much deeper one. If apple-elitist-rick's section is updated to match the new Rick's depth, the two Ricks diverge and become maintenance liabilities.
**Why it happens:** The existing Ricks were written before the new Ricks existed.
**How to avoid:** Read all 4 new Ricks first. For domains they own deeply, add a cross-reference note and keep the existing Rick's coverage at the "platform awareness" level. For domains NOT covered by new Ricks (e.g., Metal 4 in apple-elitist-rick vs. metal-4-rick -- overlap is intentional since both need Metal 4), add substantive content.
**Warning signs:** Two Ricks with identical code examples or checklist items.

### Pitfall 2: Breaking YAML Frontmatter
**What goes wrong:** An edit accidentally modifies the YAML frontmatter, breaking the agent definition for the Claude agent system.
**Why it happens:** Frontmatter is at the top of the file and easy to accidentally modify during edits.
**How to avoid:** Read the file first, verify frontmatter fields, use Edit tool with precise line ranges, never use Write to rewrite the entire file.
**Warning signs:** Missing `---` delimiters, changed model field, altered tools list.

### Pitfall 3: Missing WWDC26 Content
**What goes wrong:** Only WWDC25 content is added, missing the brand-new WWDC26 announcements from June 8, 2026.
**Why it happens:** WWDC25 content is more established and better documented. WWDC26 just happened 4 days ago.
**How to avoid:** WebSearch specifically for "WWDC 2026" changes, not just "WWDC 2025".
**Warning signs:** No mention of iOS 27, Swift 6.4, Xcode 27, App Intents replacing SiriKit, or Liquid Glass intensity switch.

### Pitfall 4: Over-Updating Description Field
**What goes wrong:** The frontmatter `description` field is updated with WWDC26 mentions but becomes too long or changes the triggering semantics for the Council of Ricks routing.
**Why it happens:** The description is used by the agent routing system to decide when to invoke the Rick.
**How to avoid:** Only update the description if the existing description is factually wrong (e.g., mentions a version that's no longer current). Don't add WWDC26 version numbers to the description -- the body content handles that.
**Warning signs:** Description longer than 2-3 lines, or mentioning specific WWDC years.

### Pitfall 5: Forgetting Checklist Updates
**What goes wrong:** New WWDC26 content is added to the body but the Rick's review checklist at the bottom is not updated.
**Why it happens:** The checklist is at the end of a very long file and easy to overlook.
**How to avoid:** After adding new content, search for the review checklist section and add corresponding checklist items.
**Warning signs:** Body mentions a framework/API that has no corresponding checklist item.

## Code Examples

### Existing Rick Content Inventory

Each Rick already has substantial WWDC25 content. Here is what exists and what needs updating:

#### RICK-01 (apple-elitist-rick) -- Current State

| Section | WWDC25 Content Exists? | WWDC26 Update Needed? |
|---------|------------------------|----------------------|
| Foundation Models (Section 9) | Yes -- full session, @Generable, Tool protocol | Add WWDC26: Gemini partnership for Siri, enhanced model capabilities |
| Liquid Glass (Section 10) | Yes -- .glassEffect(), GlassEffectContainer, fallbacks | Add WWDC26: System-wide Liquid Glass intensity switch, customization APIs |
| Metal 4 (Section 4) | Yes -- ML+graphics convergence, mesh shaders, WebGPU | Add WWDC26: MetalFX improvements, MLX Metal 4 support, enhanced ray tracing |
| New Frameworks (Section 11) | Yes -- SpeechAnalyzer, BNNS Graph, Containerization, PermissionKit, AlarmKit, EnergyKit, PaperKit, WiFiAware | Add WWDC26: Any new frameworks announced |
| SF Symbols 7 (Section 12) | Yes -- new icon design, expanded symbols | Add WWDC26: Draw animation system details, gradient rendering |
| iOS 26 SDK Mandate (Section 13) | Yes -- April 28, 2026 deadline | **UPDATE**: Now iOS 27 SDK is the latest. Section should note the new deadline for iOS 27 SDK (likely April 2027). Add SiriKit deprecation deadline (Sept 2026). |
| Quantum Crypto (Section 14) | Yes -- post-quantum algorithms, PQC cipher suites | Add WWDC26: Any updates to PQC implementation requirements |
| WebKit for SwiftUI (Section 15) | Yes -- native WebView, no UIViewRepresentable | Enhance with actual API details from released iOS 26 SDK |
| Vision OCR (Section 16) | Yes -- Vision framework replaces third-party OCR | No WWDC26 update needed |
| Deprecation Timeline | Yes -- extensive list | **UPDATE**: Add SiriKit/INExtension deprecation (iOS 27), UISceneDelegate deprecation (Sept 2026) |

**Cross-reference needed:** Foundation Models section should reference `foundation-models-rick.md` for deep API expertise. Privacy/quantum crypto should reference `privacy-rick.md`. Metal 4 section should reference `metal-4-rick.md` for deep GPU expertise.

#### RICK-02 (gamer-rick) -- Current State

| Section | WWDC25 Content Exists? | WWDC26 Update Needed? |
|---------|------------------------|----------------------|
| Apple Games App (Section 7) | Yes -- distribution channel, engagement hooks, License 7.8 | Add WWDC26: Any Games App updates for iOS 27 |
| Game Center (Section 7b) | Yes -- async/await auth, progressive achievements, analytics bridge | Add WWDC26: Any Game Center API updates |
| visionOS Spatial (Section 8) | Yes -- Bluetooth HID, spatial accessory classification | Add WWDC26: Logitech Muse details, spatial game controller badge, new spatial input APIs |
| Metal 4 Games (Section 9) | Yes -- mesh shaders, ML+graphics, WebGPU, immersive rendering | Add WWDC26: MetalFX improvements, frame interpolation, denoising |
| Liquid Glass Game UI (Section 10) | Yes -- pause menus, HUDs, inventory, settings | Add WWDC26: Liquid Glass intensity switch, user-controllable glass density |
| Cross-Platform (Xbox/PS/Switch/Steam) | Yes -- comprehensive certification requirements | No WWDC26 update needed (platform-agnostic) |

**Cross-reference needed:** Metal 4 section should reference `metal-4-rick.md` for deep GPU patterns. visionOS section should reference `visionos-rick.md` for spatial UI expertise.

#### RICK-03 (swiftui-liquid-glass) -- Current State

| Section | WWDC25 Content Exists? | WWDC26 Update Needed? |
|---------|------------------------|----------------------|
| Spatial Layout | Yes -- SpatialGlassContainer, offset3D, rotation3D | Add WWDC26: Any spatial layout API refinements for visionOS 27 |
| WebKit for SwiftUI | Yes -- native WebView, migration from UIViewRepresentable | Enhance with actual API details from released iOS 26 SDK |
| SwiftUI + RealityKit | Yes -- RealityView in GlassEffectContainer | Add WWDC26: Any integration updates |
| AttributedString | Yes -- rich text on glass surfaces | Add WWDC26: AttributedString in TextEditor (native rich text editing) |
| New App Icon Design | Yes -- Liquid Glass-style icons, Icon Composer | No WWDC26 update needed |
| UIKit/AppKit Glass | Yes -- UIGlassEffectConfiguration | No WWDC26 update needed |
| visionOS Glass | Yes -- widgets, spatial glass | No WWDC26 update needed |
| SwiftUI Concurrency | Yes -- .task with glass loading states | Add WWDC26: Default @MainActor isolation behavior changes in Swift 6.4 |

**Cross-reference needed:** This Rick and `visionos-rick.md` share spatial layout and glass-in-spatial-context content. Ensure no verbatim duplication -- swiftui-liquid-glass focuses on the glass API surface, visionos-rick focuses on spatial computing patterns.

#### RICK-04 (swift-concurrency-expert) -- Current State

| Section | WWDC25 Content Exists? | WWDC26 Update Needed? |
|---------|------------------------|----------------------|
| C/C++/Swift Interop | Yes -- CxxStdlib, smart pointer bridges, consuming parameters | Add WWDC26: Auto-generated C++ bindings (many headers now auto-generate) |
| Java Interop | Yes -- JavaKit framework | Add WWDC26: Any updates to Swift-Java bridge project |
| SwiftUI Concurrency | Yes -- .task, .onChange + Task, @MainActor automatic | Add WWDC26: Swift 6.4 default actor isolation setting, enhanced diagnostics |
| Network Framework | Yes -- NWConnection with structured concurrency | No WWDC26 update needed |
| Foundation Models Concurrency | Yes -- LanguageModelSession async, Tool Sendable | No WWDC26 update needed |
| Migration Strategies | Yes -- incremental adoption, boundary isolation | Add WWDC26: Swift 6.4 ergonomics improvements, simplified migration |

### Duplication Analysis: Existing vs. New Ricks

| Domain | Covered by New Rick | Coverage Depth | Existing Rick Should |
|--------|---------------------|-----------------|---------------------|
| Foundation Models API | foundation-models-rick.md | DEEP (976 lines, full API surface) | Cross-reference, keep platform-level summary |
| Metal 4 GPU | metal-4-rick.md | DEEP (831 lines, full GPU details) | Cross-reference, keep game/platform focus |
| Privacy/Quantum Crypto | privacy-rick.md | DEEP (913 lines, full crypto details) | Cross-reference, keep platform enforcement focus |
| visionOS Spatial | visionos-rick.md | DEEP (846 lines, full spatial patterns) | Cross-reference, keep glass-in-context focus |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| WWDC25-only content | WWDC25 + WWDC26 content | June 8, 2026 (WWDC26) | All Ricks need iOS 27/Swift 6.4/Xcode 27 updates |
| SiriKit for Siri integration | App Intents framework | WWDC26 (Sept 2026 enforcement) | SiriKit deprecated, apple-elitist-rick must flag this |
| iOS 26 SDK mandatory | iOS 26 SDK + iOS 27 SDK available | June 2026 | apple-elitist-rick's SDK mandate section needs dual-target guidance |
| Metal 3 acceptable | Metal 4 strongly preferred | WWDC25 (Metal 4 released) | Already covered in existing Ricks |
| Liquid Glass single style | Liquid Glass intensity switch | WWDC26 | User-controllable glass density is new |
| SF Symbols 6 static | SF Symbols 7 with Draw animations | WWDC25 | Draw animation system is new |
| Swift 6.2 concurrency | Swift 6.4 ergonomics | WWDC26 | Quality-of-life improvements to concurrency |

**Deprecated/outdated:**
- SiriKit (`INExtension` and old intent classes): Deprecated in iOS 27, replaced by App Intents. apple-elitist-rick MUST add this to deprecation detection.
- UISceneDelegate: Deprecation warnings in iOS 26, breaking change in iOS 27 (September 2026).
- iOS 26 SDK as "current": iOS 27 SDK is now the latest. apple-elitist-rick's SDK mandate section needs a version bump.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | WWDC26 was announced June 8, 2026 with iOS 27, macOS 27, visionOS 27, Swift 6.4, Xcode 27 | State of the Art | If WWDC26 hasn't happened yet or has different scope, WWDC26 sections would need revision |
| A2 | SiriKit is deprecated in iOS 27 with App Intents as replacement | RICK-01 update plan | If deprecation timeline is different, migration guidance would be wrong |
| A3 | UISceneDelegate deprecation deadline is September 2026 | RICK-01 update plan | If timeline is different, urgency guidance would be wrong |
| A4 | Liquid Glass intensity switch is a WWDC26 user-facing feature | RICK-03 update plan | If this is actually a WWDC25 feature already documented, it would be a duplicate addition |
| A5 | Swift 6.4 focuses on ergonomics, not major language features | RICK-04 update plan | If Swift 6.4 has breaking changes, concurrency migration guidance would be insufficient |
| A6 | No new frameworks were announced at WWDC26 that require dedicated Rick coverage | Scope assessment | If WWDC26 announced major new frameworks (like Containerization was at WWDC25), existing Ricks would need new sections |
| A7 | MetalFX improvements and MLX Metal 4 support are the main Metal 4 WWDC26 updates | RICK-01/RICK-02 update plan | If there are additional Metal 4 WWDC26 features, GPU sections would be incomplete |

## Open Questions

1. **WWDC26 full session list**: The WWDC26 session catalog may not be fully published yet (event was 4 days ago). Some sessions referenced here (Metal, SwiftUI) may have additional content not yet indexed.
   - What we know: Major themes are AI/Siri, App Intents replacing SiriKit, Xcode 27, Swift 6.4 ergonomics.
   - What's unclear: Full list of new frameworks, complete API diff for Metal 4 and SwiftUI.
   - Recommendation: Use WebSearch to check for session lists. If unavailable, note as a gap and flag for validation during execution.

2. **Liquid Glass intensity switch details**: WWDC26 reportedly adds a system-wide Liquid Glass intensity control for users. The API details for this (how apps opt in, how to test) are not yet clear.
   - What we know: It's a user-facing setting that affects all Liquid Glass rendering.
   - What's unclear: Developer API for this feature, whether apps need to handle it explicitly.
   - Recommendation: Add to RICK-03 update, note that full API details may require checking developer documentation when available.

3. **Logitech Muse API specifics**: The Logitech Muse spatial controller was announced for visionOS. Whether there are specific GCController extensions or new framework APIs for it is unclear.
   - What we know: It's a spatial accessory with precise input capabilities.
   - What's unclear: Whether it uses existing GCExtendedGamepad/GCMicroGamepad or has new API surface.
   - Recommendation: Add to RICK-02 update with available info, note that detailed API may need post-WWDC documentation review.

## Environment Availability

> Step 2.6: SKIPPED (no external dependencies identified -- this is a markdown file editing phase with WebSearch for research only).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | N/A -- markdown file editing, not code |
| Config file | none |
| Quick run command | none |
| Full suite command | none |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RICK-01 | apple-elitist-rick.md contains WWDC25+26 content for all listed domains | manual-only | Visual inspection of file | N/A (editing existing file) |
| RICK-02 | gamer-rick.md contains WWDC25+26 content for all listed domains | manual-only | Visual inspection of file | N/A (editing existing file) |
| RICK-03 | swiftui-liquid-glass.md contains WWDC25+26 content for all listed domains | manual-only | Visual inspection of file | N/A (editing existing file) |
| RICK-04 | swift-concurrency-expert.md contains WWDC25+26 content for all listed domains | manual-only | Visual inspection of file | N/A (editing existing file) |

### Sampling Rate
- **Per task commit:** Read back modified Rick file, verify frontmatter intact, verify new content present
- **Per wave merge:** Grep all 4 files for WWDC26 keywords, verify checklist updates
- **Phase gate:** Manual review of all 4 Rick files for completeness

### Wave 0 Gaps
- None -- this is a markdown editing phase, no test infrastructure needed.

## Security Domain

> N/A -- this phase edits agent definition markdown files only. No code, no authentication, no data handling.

## Sources

### Primary (HIGH confidence)
- [Apple Developer - Foundation Models Documentation](https://developer.apple.com/documentation/FoundationModels) -- Verified WWDC25 framework overview
- [Apple Developer - Metal Overview](https://developer.apple.com/metal/) -- Verified Metal 4 feature set
- [Apple Developer - iOS What's New](https://developer.apple.com/ios/whats-new/) -- Verified iOS 26+ feature list
- [Apple Developer - Game Center Overview](https://developer.apple.com/game-center/) -- Verified Game Center capabilities
- [Apple Newsroom - Apple Games App](https://www.apple.com/newsroom/2025/06/introducing-the-apple-games-app-a-personalized-home-for-games/) -- Verified Games App announcement
- [Apple Newsroom - Liquid Glass Design](https://www.apple.com/newsroom/2025/06/apple-introduces-a-delightful-and-elegant-new-software-design/) -- Verified Liquid Glass design system
- [Apple Developer - WWDC25 Session Videos](https://developer.apple.com/videos/play/wwdc2025/) -- Session references for all 4 Ricks
- [Apple Developer - WWDC26 iOS Guide](https://developer.apple.com/wwdc26/guides/ios/) -- Verified WWDC26 platform updates

### Secondary (MEDIUM confidence)
- [WWDC25 - Meet Liquid Glass (219)](https://developer.apple.com/videos/play/wwdc2025/219/) -- Verified session exists
- [WWDC25 - Build a SwiftUI app with the new design (323)](https://developer.apple.com/videos/play/wwdc2025/323/) -- Verified session exists
- [WWDC25 - Meet SwiftUI spatial layout (273)](https://developer.apple.com/videos/play/wwdc2025/273/) -- Verified session exists
- [WWDC25 - Meet WebKit for SwiftUI (231)](https://developer.apple.com/videos/play/wwdc2025/231/) -- Verified session exists
- [WWDC25 - Get ahead with quantum-secure cryptography (314)](https://developer.apple.com/videos/play/wwdc2025/314/) -- Verified session exists
- [WWDC25 - Explore spatial accessory input on visionOS (289)](https://developer.apple.com/videos/play/wwdc2025/289/) -- Verified session exists
- [WWDC25 - What's new in SF Symbols 7 (337)](https://developer.apple.com/videos/play/wwdc2025/337/) -- Verified session exists
- [WWDC25 - Embracing Swift concurrency (268)](https://developer.apple.com/videos/play/wwdc2025/268/) -- Verified session exists
- [WWDC25 - Combine Metal 4 machine learning and graphics (262)](https://developer.apple.com/videos/play/wwdc2025/262/) -- Verified session exists
- [WWDC26 - What's new in Swift (262)](https://developer.apple.com/videos/play/wwdc2026/262/) -- Verified Swift 6.4 session exists
- [MacRumors - WWDC 2026 AI and Developer Tool Updates](https://www.macrumors.com/2026/06/09/apple-outlines-major-ai-and-developer-tool-updates/) -- WWDC26 summary, verified MLX Metal 4 support
- [Courier - iOS 27 UISceneDelegate Deprecation](https://www.courier.com/blog/ios-27-uiscenedelegate-push-notification-deadline-what-breaks-and-how-to) -- Verified deprecation timeline
- [Lushbinary - WWDC 2026 Announcements](https://lushbinary.com/blog/wwdc-2026-announcements-ios-27-siri-developer-guide/) -- Verified SiriKit deprecation, App Intents replacement

### Tertiary (LOW confidence)
- [Medium - What's New in Swift 6.2](https://medium.com/@rohit236c/whats-new-in-swift-6-2-wwdc-2025-1d6a1b3ddfc0) -- Community summary, cross-verified with official sessions
- [Appcircle - WWDC 25: What's New in SwiftUI](https://appcircle.io/blog/wwdc-25-whats-new-in-swiftui) -- Community summary, cross-verified with official sessions
- [DEV Community - WWDC 2025 Liquid Glass](https://dev.to/arshtechpro/wwdc-2025-apples-liquid-glass-design-system-52an) -- Community analysis, cross-verified with Apple Newsroom

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- N/A for this phase (markdown editing only)
- Architecture: HIGH -- All 4 Rick file structures analyzed in detail, pattern documented
- Pitfalls: HIGH -- 5 concrete pitfalls identified from file structure analysis and WWDC timing
- WWDC25 content coverage: HIGH -- Verified against official Apple developer videos and documentation
- WWDC26 content coverage: MEDIUM -- WWDC26 was 4 days ago, session catalog may be incomplete. Key announcements (SiriKit deprecation, App Intents, Swift 6.4, Xcode 27) are well-sourced. Specific API details may be sparse.

**Research date:** 2026-06-12
**Valid until:** 30 days (WWDC26 beta documentation will fill gaps, but major findings remain stable)
