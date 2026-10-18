# Public wholesale report probe

This standalone diagnostic reads one publisher's publicly accessible daily wine quotation.
It contains no POS source code, merchant data, credentials, account profiles or SSH keys.
It writes the bounded public article result to workflow logs so the full table can be checked. It uploads no Actions artifacts and creates no cache, keeping the probe within free standard-runner execution. It never logs in, solves a CAPTCHA, changes a price cache, or connects to a production service.

The proposed GitHub Actions workflow is manual only, bounded to 6 minutes, and uses a standard Ubuntu runner. It is intended for a **new public repository**, where standard hosted runner use is free under GitHub's current billing policy. The current POS repository is private and must remain private. The workflow is a diagnostic and does not yet enable a daily production feed.

The diagnostic status `publisher_today_verified_completeness_unverified` only proves publisher and publication date; row-count thresholds do not prove completeness. A successful diagnostic is only the first gate. Enabling daily collection and production ingestion requires complete per-row validation and a reviewed handoff, plus real server and public API verification. This probe does not establish long-term daily availability.
