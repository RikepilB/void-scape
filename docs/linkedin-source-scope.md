# LinkedIn source scope

Reviewed 2026-09-10 for issue55. Local observation/note helpers do not access the
LinkedIn service. Their synthetic tests do not authorize or validate a live
saved-post scraping or unsave loop.

LinkedIn's [prohibited-software guidance](https://www.linkedin.com/help/linkedin/answer/a1341387/prohibited-software-and-extensions)
and [automated-activity guidance](https://www.linkedin.com/help/linkedin/answer/a1340567/automated-activity-on-linkedin?lang=en)
prohibit unapproved third-party scraping and activity automation. Its
[User Agreement](https://www.linkedin.com/legal/user-agreement), section8.2,
sets the corresponding restrictions and refers to separately granted permission.

Consequently, a signed-in browser and the account owner's task approval are not
evidence that a particular acquisition method is permitted by the platform.
Before implementing or testing a live saved-post loop, document the applicable
approved API/integration or specific permission and its exact operations. Do not
assume a general LinkedIn API grant includes saved-post enumeration or unsaving.
No such permitted live route has been established in this work.

The local workflow can process synthetic observations and selected content the
user is entitled to supply. Do not automatically fetch links, export unrelated
account data, extract credentials or use a different browser/transport to route
around an unavailable or prohibited source path. Content-owner rights and any
external disclosure permission remain separate from possession of a local file.

The full live acceptance items in issue55 remain open; local-only completion is
not a substitute for them. The future skill must label its supported modes and
stop before unsupported acquisition/account actions. It may report verified local
notes and prepare a human review list, but it must not claim items were unsaved.
