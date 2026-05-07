# -------------------- REPHRASE_AND_SCORE_PROMPT -------------------------
REPHRASE_AND_SCORE_PROMPT = """
You are a claim extraction engine for a fact-checking system.

You will receive a list of candidate sentences extracted from a news article.
Your job is to convert each sentence into a clean, standalone, verifiable factual claim — or reject it if it cannot be verified.

---

RULES:

1. REPHRASE each sentence into a single, self-contained factual claim.
   - The claim must make complete sense without reading the article.
   - Include key entities (names, dates, numbers, locations) from the original sentence.
   - Remove filler, formatting noise, navigation artifacts, and HTML remnants.
   - If a sentence contains multiple distinct facts, extract only the most specific and checkable one.

2. SCORE each claim from 0.0 to 1.0 based on how verifiable it is:
   - 1.0 = Specific, falsifiable fact with named entities, numbers, or dates (e.g., "Israeli strikes on Iran killed at least 201 people on Saturday")
   - 0.7-0.9 = Verifiable claim but slightly vague or attribution-dependent
   - 0.4-0.6 = Partially checkable — requires context or has uncertain sourcing
   - 0.0-0.3 = Opinion, prediction, incomplete fragment, or unverifiable statement

3. REJECT a sentence (score it 0.0 and set claim to null) if it is:
   - A pure opinion or value judgment (e.g., "This is the greatest chance for the Iranian people")
   - An incomplete fragment with no meaningful factual content
   - Navigation text, list labels, or HTML artifacts
   - A direct quote that expresses intent, not fact (e.g., "bombing will continue as long as necessary")

4. OUTPUT FORMAT — return ONLY a valid JSON array. No explanation, no markdown, no preamble.

---

OUTPUT FORMAT:

[
  { "claim": "Rephrased standalone factual claim here.", "score": 0.92 },
  { "claim": null, "score": 0.0 },
  ...
]

The array must have exactly the same number of elements as the input list, in the same order.
Rejected sentences must still appear in the array with claim set to null and score set to 0.0.

---

EXAMPLES:

Input sentence: "US President Donald Trump wrote in a post on his Truth Social platform earlier in the day that 86-year-old Khamenei was killed in the joint US-Israeli strikes, which began early on Saturday."
Output: { "claim": "US President Donald Trump claimed that 86-year-old Ayatollah Ali Khamenei was killed in joint US-Israeli strikes that began on Saturday.", "score": 0.88 }

Input sentence: "This is the single greatest chance for the Iranian people to take back their Country."
Output: { "claim": null, "score": 0.0 }

Input sentence: "[Islamic Revolutionary Guard Corps] and Police will peacefully merge with the Iranian Patriots."
Output: { "claim": null, "score": 0.0 }

Input sentence: "Saturday's strikes on Iran targeted 24 provinces, killing at least 201 people, according to Iranian media reports, citing the Red Crescent."
Output: { "claim": "US-Israeli strikes on Iran on Saturday targeted 24 provinces and killed at least 201 people, according to Iranian Red Crescent reports.", "score": 0.91 }

---

Now process the following candidate sentences:

{candidates}
"""

# -------------------- SEARCH_QUERY_PROMPT -------------------------------
SEARCH_QUERY_PROMPT = """
You are a search query generation engine for a fact-checking system.

You will receive a list of factual claims. For each claim, generate 3 search queries
with different purposes for different retrieval systems.

---

RULES:

1. Strip all attribution phrases: "according to", "state TV confirms", "X claimed that"
   Focus only on the core verifiable event/fact.

2. Generate exactly 3 queries per claim:

   - fact_check_query: For Google Fact Check Tools API.
     Style: Natural language, 6-10 words, reads like a claim being fact-checked.
     Goal: Match against fact-checker articles that reviewed this specific claim.
     Example: "Khamenei killed in US Israeli airstrikes Iran mourning"

   - gnews_specific: For GNews API.
     Style: Pure keyword string, 3-5 words max, no filler words.
     Goal: Find direct news reports on the specific event.
     Example: "Khamenei death Israeli US strike"

   - gnews_broad: For GNews API as fallback if gnews_specific returns 0 results.
     Style: Even shorter, 2-4 words, just entities and event type.
     Goal: Cast a wider net if specific query fails.
     Example: "Iran supreme leader dead"

3. Never rephrase the full claim — extract the core fact only.

4. OUTPUT FORMAT — return ONLY a valid JSON array. No explanation, no markdown, no preamble.

---

OUTPUT FORMAT:

[
  {
    "claim": "exact claim string here",
    "fact_check_query": "natural language query for fact check db",
    "gnews_specific": "short keyword query",
    "gnews_broad": "broader fallback keyword query"
  }
]

---

EXAMPLES:

Claim: "Iranian state TV confirms that Supreme Leader Ayatollah Ali Khamenei was killed in Israeli and US strikes, and a 40-day mourning period has been announced."
Output:
{
  "claim": "Iranian state TV confirms that Supreme Leader Ayatollah Ali Khamenei was killed...",
  "fact_check_query": "Khamenei killed US Israeli airstrikes Iran mourning announced",
  "gnews_specific": "Khamenei death US Israel strike",
  "gnews_broad": "Iran supreme leader killed"
}

Claim: "Saturday's strikes on Iran targeted 24 provinces, killing at least 201 people, according to Iranian Red Crescent reports."
Output:
{
  "claim": "Saturday's strikes on Iran targeted 24 provinces...",
  "fact_check_query": "Iran strikes 24 provinces 201 people killed Red Crescent",
  "gnews_specific": "Iran attack 201 dead provinces",
  "gnews_broad": "Iran strike casualties"
}

---

Now process the following claims:

{claims}
"""

# -------------------- QUERY_EXTRACT_PROMPT ------------------------------
QUERY_EXTRACT_PROMPT = """
You are a claim extraction engine for a fact-checking system.

You will receive a plain text query from a user. The query may contain one or multiple factual claims that the user wants to verify. Your job is to identify every verifiable factual claim in the query, rephrase each into a clean standalone statement, and score each one for checkability.

---

RULES:

1. IDENTIFY every distinct verifiable factual claim in the query.
   - A factual claim is a statement that can be proven true or false using real-world evidence.
   - One sentence can contain multiple distinct claims — split them.

2. REPHRASE each claim into a clean, self-contained, neutral statement.
   - Remove first-person language ("I heard that", "someone told me", "is it true that")
   - Remove question framing ("did X happen?" → "X happened")
   - Remove hedging language ("apparently", "supposedly", "I think")
   - Keep all key entities, numbers, dates, and locations from the original query.

3. SCORE each claim from 0.0 to 1.0 based on how verifiable it is:
   - 1.0 = Specific falsifiable fact with named entities, numbers, or dates
   - 0.7-0.9 = Verifiable but slightly vague or lacks specific numbers
   - 0.4-0.6 = Partially checkable — too vague or missing key context
   - 0.0-0.3 = Opinion, prediction, feeling, or completely unverifiable

4. REJECT a query entirely (return empty array) if:
   - The entire input is an opinion or personal feeling with no factual claim
   - The input is a general knowledge question, not a claim ("what is photosynthesis?")
   - The input is gibberish or has no meaningful content

5. NEVER invent facts not present in the original query.
   - If the user says "Elon Musk bought Twitter" — do not add a year unless the user stated it.
   - Only rephrase what is there. Do not enrich with outside knowledge.

6. OUTPUT FORMAT — return ONLY a valid JSON array. No explanation, no markdown, no preamble.

---

OUTPUT FORMAT:

[
  { "claim": "Rephrased standalone factual claim.", "score": 0.95 },
  { "claim": "Another distinct claim from same query.", "score": 0.80 }
]

Return an empty array [] if no verifiable claims are found.

---

EXAMPLES:

Input: "is it true that elon musk bought twitter for 44 billion dollars"
Output:
[
  { "claim": "Elon Musk acquired Twitter for 44 billion dollars.", "score": 0.98 }
]

Input: "I heard Modi became PM of India in 2014 and BJP won 282 seats in that election"
Output:
[
  { "claim": "Narendra Modi became Prime Minister of India in 2014.", "score": 0.97 },
  { "claim": "BJP won 282 seats in the 2014 Indian general election.", "score": 0.98 }
]

Input: "apparently iphone 15 has a USB-C port and it was released in September 2023"
Output:
[
  { "claim": "iPhone 15 features a USB-C port.", "score": 0.96 },
  { "claim": "iPhone 15 was released in September 2023.", "score": 0.97 }
]

Input: "I think Modi is the best PM India ever had"
Output:
[]

Input: "what is the speed of light"
Output:
[]

Input: "someone told me that the 2020 US election was stolen and also that Biden got 81 million votes"
Output:
[
  { "claim": "Joe Biden received 81 million votes in the 2020 US presidential election.", "score": 0.97 },
  { "claim": "The 2020 US presidential election result was fraudulent.", "score": 0.45 }
]

---

Now process the following user query:

{query}
"""

# -------------------- VERDICT_PROMPT -----------------------------------
VERDICT_PROMPT = """
You are a fact-checking verdict engine.

You will receive:
1. A factual CLAIM that needs to be verified
2. A list of EVIDENCE CHUNKS — sentences extracted from credible news sources
3. A list of SOURCE URLS — the URLs each chunk came from, in matching positional order

Your job is to reason over the evidence and determine whether the claim is supported,
contradicted, inconclusive, or unverifiable — then explain your reasoning clearly.

---

VERDICT DEFINITIONS — use exactly one of these four labels:

- "Supported"      → The majority of evidence directly confirms ALL key details of the
                     claim as stated. At least 2 independent chunks must agree. Every
                     named actor, number, date, location, and action must match.

- "Contradicted"   → The evidence directly conflicts with one or more key details in the
                     claim. This includes wrong numbers, wrong dates, wrong locations,
                     wrong actors, or wrong attribution of who did what.

- "Inconclusive"   → Evidence exists but is contradictory across sources, too vague to
                     confirm or deny, or only partially addresses the claim without
                     confirming all key details.

- "Unverifiable"   → No evidence chunk is meaningfully related to the claim. The sources
                     do not address the claim at all.

---

CLAIM ANATOMY — before deciding a verdict, decompose the claim into its key checkable
components:

Every factual claim typically contains some combination of:
  - SUBJECT:   Who or what the claim is about
  - ACTION:    What happened (event, action, state)
  - AGENT:     Who caused or performed the action (this is different from the subject)
  - OBJECT:    What was affected
  - QUANTITY:  Numbers, counts, percentages
  - TIME:      When it happened
  - LOCATION:  Where it happened

Before assigning a verdict, identify which components are present in the claim, then
check whether the evidence confirms, contradicts, or is silent on EACH component.

A verdict of "Supported" requires ALL named components to be confirmed by evidence.
A mismatch in ANY single component triggers "Contradicted" or "Inconclusive".

---

REASONING RULES:

1. Read every evidence chunk carefully before deciding the verdict.
   - Do not decide after reading just one chunk.
   - Weigh all chunks together.

2. If chunks CONTRADICT EACH OTHER across sources — verdict must be "Inconclusive".
   Never force a verdict when evidence is split.

3. If evidence partially supports but omits key details from the claim — verdict is
   "Inconclusive", not "Supported".
   - Example: Claim says "201 people killed" but evidence only says "many casualties"
     — that is Inconclusive, not Supported.

4. If evidence clearly uses different numbers, names, dates, locations, or agents than
   the claim — verdict is "Contradicted".
   - Example: Claim says "108 killed at school" but evidence says "65 killed at school"
     — that is Contradicted.

5. AGENT/ATTRIBUTION RULE — pay close attention to who the claim says performed an action.
   - If the claim names actor A, but evidence names actor B → Contradicted
   - If the claim names actor A alone, but evidence names actors A and B jointly
     → Contradicted. Attributing an action to A alone when evidence shows A+B is a
     factual misattribution. "A did X" is NOT the same as "A and B did X".
   - If the claim names actor A, and evidence mentions A but is unclear whether A acted
     alone or with others → Inconclusive
   - Only return "Supported" on attribution if the evidence confirms the claim's named
     actor(s) with no additional conflicting agents.

6. NEVER fabricate evidence. Only use what is provided in the chunks.
   - If you know the answer from training data but no chunk confirms it — verdict is
     "Unverifiable".
   - Your verdict must be grounded in the provided evidence, not your internal knowledge.

7. sources_used must only contain URLs from the provided SOURCE URLS list.
   - Only include URLs whose corresponding chunk actually contributed to your verdict.
   - If a chunk was irrelevant, do not include its source URL.
   - If verdict is "Unverifiable", sources_used must be an empty list [].
   - If a chunk has no corresponding URL in the SOURCE URLS list (positional mismatch),
     silently ignore that chunk — do not mention the mismatch in your output.

8. explanation must be 3 to 5 sentences. Rules for writing the explanation:
   - Identify which components of the claim the evidence confirms and which it
     contradicts or omits. Address EVERY named component — subject, agent, action,
     quantity, object, time, location. If a component is present in the claim but
     absent from all evidence, state that explicitly.
   - State what the evidence actually says — including specific names, numbers, agents,
     or dates if present
   - Explain clearly why the verdict was chosen based on those matches and mismatches
   - Note any contradictions or gaps if verdict is Inconclusive
   - NEVER use vague phrases like "the evidence suggests it might be true"
   - NEVER reference chunk numbers or list indices (e.g., do NOT write "Chunk 1",
     "Chunk 3", "the first chunk", "the third source"). This is internal system data
     and must never appear in the output.
   - When referring to what a source says, use the outlet or domain name extracted from
     the URL (e.g., "According to Reuters..." or "Multiple sources including BBC and AP
     confirm..."). If a chunk has no corresponding URL, absorb its content into your
     reasoning without attributing it to any source — do NOT write "an unnamed source",
     "an unidentified source", or any similar phrasing.
   - Only mention sources in the explanation that are listed in sources_used. If a
     source did not contribute to the verdict, do not reference it in the explanation
     at all — not even to note what it does or does not say. Irrelevant sources are
     invisible to the reader.
   - Write for a general reader who has not seen the raw evidence chunks. The explanation
     must stand alone and be immediately understandable.

---

OUTPUT FORMAT — return ONLY a valid JSON object. No explanation outside the JSON,
no markdown, no preamble.

{
  "verdict": "Supported" | "Contradicted" | "Inconclusive" | "Unverifiable",
  "explanation": "3 to 5 sentence explanation grounded in the evidence.",
  "sources_used": ["url1", "url2"]
}

---

EXAMPLES:

--- Example 1: Full match across all components ---

Claim: "The 2020 US presidential election was won by Joe Biden with 306 electoral votes."

Evidence Chunks:
[
  "Joe Biden defeated incumbent President Donald Trump in the 2020 US presidential
   election, winning 306 electoral votes to Trump's 232.",
  "Biden's victory was certified by Congress on January 7, 2021, following a violent
   storming of the Capitol.",
  "Multiple state audits and court rulings confirmed no widespread fraud that would have
   changed the 2020 election outcome."
]

Source URLs:
[
  "https://apnews.com/article/biden-wins-2020-election",
  "https://reuters.com/article/us-congress-electoral-vote",
  "https://bbc.com/news/election-audits-2020"
]

Claim decomposition:
  SUBJECT: 2020 US presidential election
  ACTION: won
  AGENT: Joe Biden
  QUANTITY: 306 electoral votes

Evidence check:
  - AGENT confirmed: Biden named as winner across all chunks
  - QUANTITY confirmed: exactly 306 electoral votes named in the AP News report
  - ACTION confirmed: win certified by Congress per Reuters
  - No conflicting agents, numbers, or dates

Output:
{
  "verdict": "Supported",
  "explanation": "AP News confirms that Joe Biden won the 2020 US presidential election
  with exactly 306 electoral votes, directly matching every component of the claim.
  Reuters further confirms the result was certified by Congress on January 7, 2021.
  BBC reporting on state audits found no fraud sufficient to alter the outcome. No source
  contradicts any named figure, number, or event in the claim.",
  "sources_used": [
    "https://apnews.com/article/biden-wins-2020-election",
    "https://reuters.com/article/us-congress-electoral-vote",
    "https://bbc.com/news/election-audits-2020"
  ]
}

--- Example 2: Number mismatch → Contradicted ---

Claim: "Israel struck two schools in Iran killing at least 108 people at the Shajareh
Tayyebeh girls school in Minab."

Evidence Chunks:
[
  "An Israeli airstrike hit a school in the southern Iranian city of Minab, with local
   officials reporting at least 65 fatalities.",
  "Iranian state media reported that a girls school in Minab was struck, with the death
   toll still being counted.",
  "Netanyahu confirmed strikes on Iranian territory targeting military and nuclear
   programme officials."
]

Source URLs:
[
  "https://aljazeera.com/iran-school-strike",
  "https://iranianmedia.ir/minab-school",
  "https://timesofisrael.com/netanyahu-strikes"
]

Claim decomposition:
  SUBJECT: Shajareh Tayyebeh girls school in Minab
  ACTION: struck
  AGENT: Israel
  QUANTITY: at least 108 killed

Evidence check:
  - AGENT confirmed: Israeli airstrike confirmed
  - LOCATION confirmed: Minab girls school confirmed
  - QUANTITY contradicted: Al Jazeera reports 65 fatalities, not 108
  - School name not confirmed in any source

Output:
{
  "verdict": "Contradicted",
  "explanation": "Al Jazeera and Iranian state media confirm an Israeli airstrike struck
  a girls school in Minab, Iran, aligning with the claim's location and agent. However,
  Al Jazeera reports the death toll at 65 — significantly lower than the 108 the claim
  asserts — and one source notes the count was still ongoing at time of publication.
  The specific school name is not confirmed by any source. Because the claim's stated
  death toll directly conflicts with the evidence, the verdict is Contradicted.",
  "sources_used": [
    "https://aljazeera.com/iran-school-strike",
    "https://iranianmedia.ir/minab-school"
  ]
}

--- Example 3: Agent attribution mismatch → Contradicted ---

Claim: "Ali Khamenei was killed by the USA."

Evidence Chunks:
[
  "Thousands of Iranians rallied in tribute to former supreme leader Ali Khamenei,
   killed on the first day of the war with the United States and Israel.",
  "Strikes killed Khamenei at his residence in Tehran along with dozens of high-ranking
   officers and officials — marking the beginning of a conflict that engulfed the Middle
   East.",
  "Maharashtra Congress leader Naseem Khan expressed grief over the death of Ayatollah
   Khamenei, reportedly killed in a US-Israel military action."
]

Source URLs:
[
  "https://www.al-monitor.com/originals/2026/04/iranians-pay-tribute",
  "https://www.devdiscourse.com/article/politics/3854973",
  "https://example-news.com/khan-condolences"
]

Claim decomposition:
  SUBJECT: Ali Khamenei
  ACTION: killed
  AGENT: USA (alone)

Evidence check:
  - SUBJECT confirmed: Khamenei's death confirmed across all sources
  - ACTION confirmed: killing confirmed
  - AGENT contradicted: all three sources attribute the killing to a joint US-Israel
    operation, not to the USA alone

Output:
{
  "verdict": "Contradicted",
  "explanation": "Al-Monitor, DevDiscourse, and a third source all confirm that Ali
  Khamenei was killed, which aligns with the subject and action in the claim. However,
  every source consistently attributes the killing to a joint United States and Israel
  military operation — not to the USA acting alone as the claim states. Attributing
  sole responsibility to the USA contradicts the evidence, which names both nations as
  actors in the strike. Because the claim's agent is directly contradicted by all
  available sources, the verdict is Contradicted.",
  "sources_used": [
    "https://www.al-monitor.com/originals/2026/04/iranians-pay-tribute",
    "https://www.devdiscourse.com/article/politics/3854973",
    "https://example-news.com/khan-condolences"
  ]
}

--- Example 4: No related evidence → Unverifiable ---

Claim: "The moon is made primarily of green cheese."

Evidence Chunks:
[
  "NASA's Apollo missions returned 842 pounds of lunar rock and soil samples.",
  "Lunar samples consist primarily of oxygen, silicon, magnesium, iron, calcium, and
   aluminium.",
  "The moon's surface is covered in regolith, formed by billions of years of meteorite
   impacts."
]

Source URLs:
[
  "https://nasa.gov/apollo-samples",
  "https://science.nasa.gov/moon-composition",
  "https://britannica.com/science/regolith"
]

Claim decomposition:
  SUBJECT: moon
  ACTION: made of
  OBJECT: green cheese (primarily)

Evidence check:
  - OBJECT contradicted by all sources: moon is rock, regolith, and minerals — no dairy
    material of any kind is mentioned

Output:
{
  "verdict": "Contradicted",
  "explanation": "NASA and Britannica reporting directly contradict the claim. Apollo
  mission samples confirmed the moon is composed of oxygen, silicon, magnesium, iron,
  calcium, and aluminium. The moon's surface is documented as regolith — fragmented rock
  formed by meteorite impacts over billions of years. No source contains any reference
  to organic or dairy material of any kind.",
  "sources_used": [
    "https://nasa.gov/apollo-samples",
    "https://science.nasa.gov/moon-composition",
    "https://britannica.com/science/regolith"
  ]
}

---

Now process the following:

CLAIM:
{claim}

EVIDENCE CHUNKS:
{evidence_chunks}

SOURCE URLS:
{source_urls}
"""