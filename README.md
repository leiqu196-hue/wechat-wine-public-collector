# Public wholesale report probe

This standalone diagnostic reads one publisher's publicly accessible daily wine quotation.
It contains no POS source code, merchant data, credentials, account profiles or SSH keys.
It writes the bounded public article result to workflow logs so the full table can be checked. It uploads no Actions artifacts and creates no cache, keeping the probe within free standard-runner execution. It never logs in, solves a CAPTCHA, changes a price cache, or connects to a production service.

The GitHub Actions workflow is manual or scheduled, bounded to 6 minutes, and uses a standard Ubuntu runner. It is intended for a **new public repository**, where standard hosted runner use is free under GitHub's current billing policy. The current POS repository is private and must remain private. The workflow is a diagnostic and stores a current public report in data/latest.json for independent validation by the consuming server.

The diagnostic status `publisher_today_verified_completeness_unverified` only proves publisher and publication date; row-count thresholds do not prove completeness. A successful diagnostic is only the first gate. Enabling daily collection and production ingestion requires complete per-row validation and a reviewed handoff, plus real server and public API verification. This probe does not establish long-term daily availability.

Scheduled attempts use China time 09:50, 10:15, 10:40 and 11:20. GitHub may delay scheduled jobs. A failed collection does not replace the last successful public report; consumers must reject stale dates. The runtime token is supplied by GitHub only to the final public-data commit step, never stored in this repository. The collector reports completeness as unverified; the consuming server must compare every parsed row to the original tables before publishing prices.

## Additional original publisher

The scheduled workflow also reads 茅粉鲁智深 from its publisher-owned quotation album (biz Mzg4MzMyMTExMQ==, album 4475132542408294400). Each publisher runs independently and saves to a separate fixed public file; an unavailable publisher cannot replace or suppress another publisher. The server validates every table, including the first daily-price table and the later reference-price tables; retail columns are never used as reference prices. Historical sample inspection is not a current-date publication.
