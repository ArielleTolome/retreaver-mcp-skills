# Changelog

All notable changes to `retreaver-mcp-skills` are documented in this file.

## [v1.0.0] - 2026-10-13

### Added
- **9 Production Operator Skills (100% of 51/51 Retreaver MCP Tools)**:
  - `retreaver-operator`: Master orchestrator & unified CLI (`retreaver_cli.py`) supporting `whoami`, `audit`, `buyer`, `publisher`, `webhook`, `rtb-diag`, and `stats`.
  - `retreaver-buyer-ops`: Call Buyer (`Target`) creation, priority/weight balancing, 5-tier cap management (`concurrency`, `hourly`, `daily`, `monthly`, `hard`), hard-cap resets, multi-block business hours, and target cloning (`buyer_ops.py`).
  - `retreaver-publisher-ops`: Publisher (`Affiliate`) onboarding, campaign-bound RTB & Data Writing Postback Key provisioning, and conversion group payouts (`publisher_ops.py`).
  - `retreaver-campaign-routing-ops`: Campaign lifecycle management, nested priority/weight routing ladders (`menu_options_attributes`), Waiting Room retries/timers, Handler Groups (`target_groups`), and polymorphic IVR Prompts (`campaign_routing_ops.py`).
  - `retreaver-numbers-pools-ops`: Tracking DID inventory (`numbers`), Dynamic Number Pools (`number_pools`), DNI concurrency/lease sizing, SIP URI routing (`sip:...`), and granular number-level caps (`numbers_pools_ops.py`).
  - `retreaver-caller-lists-suppression`: Campaign and Buyer Caller Lists (`suppressed*` blocklists & `accepted*` allowlists), single number add/remove, live suppression checks, and asynchronous bulk CSV uploads (`caller_lists_ops.py`).
  - `retreaver-webhook-ops`: `PassthroughTimer`, `HTTPTimer`, `PingTimer`, and `PostbackTimer` management, 100+ Webhook Configurator templates (CallGrid, TrackDrive, Anura, Leadspedia, 33MileRadius), output tag mapping, and live test-firing (`webhook_ops.py`).
  - `retreaver-tags-bidding-ops`: Tag Wizard catalog registration (`Text`, `Numeric`, `Date`, `Boolean`), replacement token discovery, Payout Bid Modification (PBM) SHA-256 CSV rule tables, and manual call revenue/payout crediting (`tags_bidding_ops.py`).
  - `retreaver-diagnostics-reporting`: ClickHouse RTB reservation log inspector (`no-target`, `expired`, `claimed`, `ping_shield_*`), call detail flow analysis, multi-dimensional drill-down rollups, and S3 CSV exports (`diag_reporting.py`).
- **10 Slash Command Prompt Shortcuts (`/retreaver:*`)**:
  - `/retreaver:status`, `/retreaver:rtb-diag`, `/retreaver:stats`, `/retreaver:setup-buyer`, `/retreaver:setup-publisher`, `/retreaver:setup-webhook`, `/retreaver:routing`, `/retreaver:suppress`, `/retreaver:pbm`, and `/retreaver:audit`.
- **Portable Auto-Refreshing OAuth Client (`lib/retreaver_client.py`)**:
  - Automatic OAuth 2.0 PKCE token refresh against `https://retreaver.com/oauth/token` with resource binding for `https://ai.retreaver.com/mcp`.
- **Automated Multi-Harness Installer (`install.sh`)**:
  - Installs all 9 skills and 10 slash commands across OMP, Claude Code, Cursor, OpenAI Codex, xAI Grok, and Nous Hermes.
