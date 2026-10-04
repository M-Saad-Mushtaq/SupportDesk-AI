# Five showcase screenshots

[Portfolio overview](../../README.md) | [Recording and preparation guide](demo-script.md)

Use the fictional Michael Chang scenario (`CUS-1041`, `ORD-9104`). The original
ticket is `TKT-1041`; the optional isolated preparation in the recording guide
creates `TKT-SHOWCASE-1041` without deleting anything. Complete that guide before
capturing screens. These are shot specifications, not screenshots already taken.

Keep the application's demo banner and provider/mock label visible. Capture the
app viewport, not private terminals, environment files, browser storage, API keys,
or unrelated tabs. Use only fictional policies and replies. Existing ignored
verification images are test artifacts; review them before considering reuse.

| Screenshot | What it demonstrates | How to prepare |
| --- | --- | --- |
| 1. Customer policy conversation | Customer perspective, fictional identity, public reply, and honest provider labeling | Open customer chat, select Michael's recording ticket, and send `What is your returns policy?` after explicitly uploading the fixture. Wait for an actual completed reply. Keep `Demo store` and `Mock simulation` visible if mock is used. Do not add a citation badge that the customer UI does not implement. |
| 2. Staff Inbox with evidence | The same policy exchange with a saved source title, location, and quoted excerpt | Use **Staff view** on that ticket. Expand **View sources** on the newly generated policy reply, not a seeded AI sample. At 1366 px leave the details drawer closed to keep the conversation readable. |
| 3. Knowledge Base search and preview | Real file ingestion, Ready status, extracted text, and keyword evidence | Upload the fictional `shipping-returns.md` in the recording workspace, select it for preview, then use **Document search** with `returns`. Show the returned section/excerpt. Expand Advanced only if useful; caption this SQLite FTS5 search, not semantic search or AI confidence. |
| 4. Actual order-tool run | Inspectable tool execution against the customer's stored sample order | Send `What is the stored status of my order ORD-9104?`. In Agent Activity select the new run for the recording ticket and expand **View tool input and result** for `get_order_details`. Include its sample-data qualification. Keep seeded-history examples collapsed. Use only reported usage, if any. |
| 5. Human handover in two views | Staff control and the public reply received by the customer | After `Please connect me with a person.`, take over and send a fictional public reply. Arrange the customer chat and staff Inbox side by side, each wide enough to read, or capture a clearly captioned two-panel composition. Show **Support specialist** in customer chat and **AI paused** in staff view. An optional fictional internal note can appear on the staff side only; the image alone is not proof of API filtering. |

Use a desktop window around 1366x768 or wider; keep text legible rather than
shrinking every panel into one shot. For a mobile crop of screenshot 1, use a
390x844 viewport and check the composer fits. Hide unrelated personal browser
chrome and notifications without hiding demo disclosures. Do not fabricate
success screens, tool payloads, elapsed times, or a Gemini label for mock output.

Rehearsal and screenshot capture remain manual next steps. Earlier browser checks
are documented in the [development reference](../development.md#customer-demo-verification);
no new desktop/mobile visual check was run during this documentation task.
