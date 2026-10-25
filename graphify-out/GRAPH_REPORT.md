# Graph Report - ERP  (2026-10-25)

## Corpus Check
- 113 files · ~104,292 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 110 file(s) not represented in the graph (top: .po 62, .xml 34, .csv 4)

## Summary
- 1186 nodes · 1904 edges · 71 communities (19 shown, 52 thin omitted)
- Extraction: 91% EXTRACTED · 8% INFERRED · 0% AMBIGUOUS · INFERRED: 157 edges (avg confidence: 0.86)
- Token cost: 240,858 input · 0 output

## Community Hubs (Navigation)
- Dynamic Report Handler Base
- Integration Test Fixtures
- SaaS Infrastructure & Docker
- Dynamic Report Orchestrator
- Report Execution Cache
- Sectioned Report Layouts
- SSRF Net Guard
- SQL Builder Unit Tests
- XLSX Report Writer
- IC Mirror Tests
- Report Wizard Model
- Golden IFRS Test Base
- IC Invoice Mirroring
- SQL Primitive & Currency Join
- SQL Builder Integration Tests
- IC Elimination Golden Tests
- Sealed Move Guard
- IC Order Mixin
- SO/PO Mirror Tests
- JS Dashboards (OWL)
- Install Hooks & Groups
- SQL Builder Grouping
- IC Docs & Screenshots
- Report Wizard Tests
- IC Elimination Batch
- Audit & Cron Mixins
- Saved Report Views
- Inter-Company Branding
- Discount Manager Models
- Orchestrator Constraint Tests
- Fold State Tests
- Currency Conversion Tests
- Report Wizard Module
- GL Reversal & Post-Once
- Move Seal Tests
- IC Module Wiring
- Account Cache Invalidation
- Orchestrator Cache Tests
- Dashboard Controllers
- Monthly Disbursement
- Report Fold State
- Base Engine Branding
- Workflow Guard Mixin
- Discount Program Lifecycle
- Discount Compute Wizard
- Container Entrypoint
- Orchestrator Test Doubles
- IC Unrealised Profit Lines
- SO/PO Mirroring Branding
- Partner Compat Shim
- IC Elimination Batch Lines
- Discount Journal Entries
- Company Move Version Counter
- IC Company Config
- IC Elimination Mismatch
- wait-for-it Script

## God Nodes (most connected - your core abstractions)
1. `MoveLineQuery` - 71 edges
2. `SQL` - 55 edges
3. `TestMoveLineQueryShape` - 47 edges
4. `assert_safe_url()` - 29 edges
5. `TestIntercompanyMirror` - 26 edges
6. `EhAccountDynamicReportHandler` - 25 edges
7. `TestNetGuard` - 25 edges
8. `EhIcEliminationBatch` - 25 edges
9. `EhAccountDynamicReportSectionedHandler` - 24 edges
10. `XlsxReportWriter` - 23 edges

## Surprising Connections (you probably didn't know these)
- `Per-Company Move-Version Result Cache (eh_move_version)` --semantically_similar_to--> `Redis 7 Session Store & ORM Cache`  [INFERRED] [semantically similar]
  custom_addons/eh_account_base/static/description/index.html → ARCHITECTURE.md
- `Traefik Docker provider (network erp_frontend)` --conceptually_related_to--> `erp_network (single bridge network)`  [AMBIGUOUS]
  config/traefik/traefik.yml → docker-compose.yml
- `build_complex_query()` --calls--> `MoveLineQuery`  [INFERRED]
  custom_addons/eh_account_base/tests/test_perf_sql_builder.py → custom_addons/eh_account_base/tools/sql_builder.py
- `run()` --calls--> `MoveLineQuery`  [INFERRED]
  custom_addons/eh_account_base/tests/test_perf_sql_builder.py → custom_addons/eh_account_base/tools/sql_builder.py
- `Enterprise Odoo 17 SaaS Platform Architecture` --references--> `odoo-chain middleware chain`  [INFERRED]
  ARCHITECTURE.md → config/traefik/dynamic.yml

## Import Cycles
- None detected.

## Hyperedges (group relationships)
- **Request path: Traefik -> odoo-web -> PgBouncer -> PostgreSQL (+Redis sessions)** — architecture_traefik, architecture_odoo_web, architecture_pgbouncer, architecture_postgresql, architecture_redis [EXTRACTED 1.00]
- **Odoo route middleware chain** — config_traefik_dynamic_odoo_chain, config_traefik_dynamic_security_headers, config_traefik_dynamic_rate_limit, config_traefik_dynamic_compress, config_traefik_dynamic_buffering [EXTRACTED 1.00]
- **Inter-company mirror cycle (orders to invoices) driven by Represented Company + config** — custom_addons_eh_account_intercompany_static_description_index_invoice_mirroring, custom_addons_eh_account_intercompany_so_po_static_description_index_sale_order_mirror, custom_addons_eh_account_intercompany_so_po_static_description_index_purchase_order_mirror, custom_addons_eh_account_intercompany_static_description_index_represented_company, custom_addons_eh_account_intercompany_static_description_index_intercompany_config [INFERRED 0.85]
- **EH Account Base App Store Branding Assets** — custom_addons_eh_account_base_static_description_banner_animated_banner, custom_addons_eh_account_base_static_description_banner_static_banner, custom_addons_eh_account_base_static_description_icon_eab_icon, custom_addons_eh_account_base_static_description_icon_2x_eab_icon_hires, custom_addons_eh_account_base_static_description_icon_ledger_lines_icon [INFERRED 0.85]
- **Inter-Company Rules advertised feature set** — custom_addons_eh_account_intercompany_static_description_banner_auto_sale_to_purchase_mirror, custom_addons_eh_account_intercompany_static_description_banner_duplicate_proof_linkage, custom_addons_eh_account_intercompany_static_description_banner_inter_company_review_queue, custom_addons_eh_account_intercompany_static_description_banner_amount_mismatch_detection, custom_addons_eh_account_intercompany_static_description_banner_tax_by_rate_analytic_safe [EXTRACTED 1.00]
- **ERP Heritage intercompany branding assets** — custom_addons_eh_account_intercompany_static_description_banner_animated_feature_banner, custom_addons_eh_account_intercompany_static_description_banner_static_banner, custom_addons_eh_account_intercompany_static_description_icon_ic_monogram_icon, custom_addons_eh_account_intercompany_static_description_icon_2x_ic_monogram_icon_hires, custom_addons_eh_account_intercompany_static_description_icon_mirrored_documents_icon, custom_addons_eh_account_intercompany_static_description_banner_erp_heritage_brand [INFERRED 0.85]
- **Inter-Company SO/PO Module Branding Assets** — custom_addons_eh_account_intercompany_so_po_static_description_banner_gif, custom_addons_eh_account_intercompany_so_po_static_description_banner, custom_addons_eh_account_intercompany_so_po_static_description_icon, custom_addons_eh_account_intercompany_so_po_static_description_icon_2x [INFERRED 0.85]

## Communities (71 total, 52 thin omitted)

### Community 1 - "Integration Test Fixtures"
Cohesion: 0.07
Nodes (9): EhAccountIntegrationTestCase, TestAccountMoveReportRender, TestCacheInvalidationHook, TestSqlBuilderPerfBaseline, build_complex_query(), run(), run(), TestSqlBuilderPerfHeavy (+1 more)

### Community 2 - "SaaS Infrastructure & Docker"
Cohesion: 0.07
Nodes (45): Backup & Recovery (pg_dump per tenant, filestore tar), Monitoring Stack (Prometheus, Grafana, Loki, Uptime Kuma), Frontend/Backend Network Isolation, odoo-web (UI Workers), odoo-worker (Cron/Reports), PgBouncer Transaction-Mode Pool, PostgreSQL 15 (One DB per Tenant), Redis 7 Session Store & ORM Cache (+37 more)

### Community 3 - "Dynamic Report Orchestrator"
Cohesion: 0.06
Nodes (4): EhAccountDynamicReport, TestPayloadCodec, compress_payload(), decompress_payload()

### Community 4 - "Report Execution Cache"
Cohesion: 0.06
Nodes (3): EhAccountReportExecution, TestOptionsCanonicalisation, TestReportExecutionLifecycle

### Community 6 - "SSRF Net Guard"
Cohesion: 0.08
Nodes (7): _addrinfo(), TestNetGuard, _addr_forbidden(), assert_safe_url(), _parse_literal_ip(), _proxy_in_effect(), UnsafeUrlError

### Community 10 - "Report Wizard Model"
Cohesion: 0.07
Nodes (3): EhAccountReportWizard, TestWorkflowGuard, EhMonthlyDisbursement

### Community 11 - "Golden IFRS Test Base"
Cohesion: 0.08
Nodes (4): EhGoldenTestCase, full_product(), pairwise_cases(), TestPropertyIcElimination

### Community 17 - "Sealed Move Guard"
Cohesion: 0.14
Nodes (3): AccountMove, AccountMoveLine, AccountPartialReconcile

### Community 18 - "IC Order Mixin"
Cohesion: 0.10
Nodes (3): EhIcOrderMixin, PurchaseOrder, SaleOrder

### Community 21 - "Install Hooks & Groups"
Cohesion: 0.12
Nodes (4): _ensure_partner(), post_init_hook(), grouped_sum(), read_group_compat()

### Community 23 - "IC Docs & Screenshots"
Cohesion: 0.17
Nodes (18): intercompany_order_mixin (destination company resolver), No Back-Mirroring Guard (eh_ic_origin_*_id), purchase.order button_confirm -> _eh_ic_create_mirror_so, sale.order action_confirm -> _eh_ic_create_mirror_po, Inter-Company SO/PO Mirroring (eh_account_intercompany_so_po), test_so_po_mirror integration tests, Screenshot: Auto-Mirror on Post, Screenshot: Per-Company Mirror Configuration (+10 more)

### Community 29 - "Inter-Company Branding"
Cohesion: 0.31
Nodes (11): Inter-Company Rules Animated Banner (GIF), Auto Sale-to-Purchase Mirror, ERP Heritage Brand, Inter-Company Review Queue, Inter-Company Rules, LGPL-3 License, Multi Entity Accounting, Inter-Company Rules Static Banner (PNG) (+3 more)

### Community 30 - "Discount Manager Models"
Cohesion: 0.19
Nodes (4): EhDiscountType, EhDiscountVendorLine, EhDiscountComputeVendorWizard, EhDiscountPurgeWizard

### Community 31 - "Orchestrator Constraint Tests"
Cohesion: 0.19
Nodes (3): EhAccountUnitTestCase, TestOrchestratorConstraints, TestOrchestratorErrorPath

### Community 41 - "Account Cache Invalidation"
Cohesion: 0.18
Nodes (3): AccountAccount, EhAccountReportAnnotation, ResConfigSettings

### Community 47 - "Base Engine Branding"
Cohesion: 0.27
Nodes (8): Accounting Suite Base Engine, EH Account Base Animated Banner (GIF), ERP Heritage (brand), Odoo 19 Community Edition (LGPL-3, v19.0.1.5.0), EH Account Base Store Banner (PNG), EAB Module Icon 512px (@2x), EAB Module Icon 256px, Ledger Lines SVG Icon

### Community 51 - "Container Entrypoint"
Cohesion: 0.53
Nodes (8): fix_permissions(), log_error(), log_info(), log_warn(), main(), entrypoint.sh script, wait_for_db(), wait_for_redis()

### Community 54 - "SO/PO Mirroring Branding"
Cohesion: 0.36
Nodes (7): Inter-Company SO/PO Mirroring Banner, ERP Heritage Accounting Suite, Inter-Company SO/PO Mirroring Animated Banner, Bidirectional Order Mirroring, Inter-Company SO/PO Mirroring, SO Module Icon, SO Module Icon (2x)

### Community 63 - "wait-for-it Script"
Cohesion: 0.80
Nodes (4): echoerr(), wait-for-it.sh script, usage(), wait_for()

## Ambiguous Edges - Review These
- `Traefik v3.1 Reverse Proxy` → `Docker Compose Stack (Nginx Edition)`  [AMBIGUOUS]
  ARCHITECTURE.md · relation: conceptually_related_to
- `PgBouncer Transaction-Mode Pool` → `odoo-worker service`  [AMBIGUOUS]
  docker-compose.yml · relation: conceptually_related_to
- `Frontend/Backend Network Isolation` → `erp_network (single bridge network)`  [AMBIGUOUS]
  ARCHITECTURE.md · relation: conceptually_related_to
- `erp_network (single bridge network)` → `Traefik Docker provider (network erp_frontend)`  [AMBIGUOUS]
  config/traefik/traefik.yml · relation: conceptually_related_to
- `Tax Mapping by Rate and Direction` → `Screenshot: Tax-Preserving Mirror Builder`  [AMBIGUOUS]
  custom_addons/eh_account_intercompany/static/description/_screenshots_block.html · relation: conceptually_related_to

## Knowledge Gaps
- **17 isolated node(s):** `Scaling Strategy (horizontal web, vertical workers, DB)`, `Monitoring Stack (Prometheus, Grafana, Loki, Uptime Kuma)`, `postgres-data volume`, `redis-data volume`, `compress middleware (gzip)` (+12 more)
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 425 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **52 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `MoveLineQuery` connect `SQL Builder Integration Tests` to `Dynamic Report Handler Base`, `Integration Test Fixtures`, `Currency Conversion Tests`, `SQL Builder Execution`, `SQL Analytic Filters`, `Sectioned Report Layouts`, `SQL Builder Unit Tests`, `SQL Primitive & Currency Join`, `Install Hooks & Groups`, `SQL Builder Grouping`, `SQL Builder Aggregates`?**
  _High betweenness centrality (0.171) - this node is a cross-community bridge._
- **Are the 29 inferred relationships involving `MoveLineQuery` (e.g. with `EhAccountDynamicReportHandler` and `._expand_build_page_query()`) actually correct?**
  _`MoveLineQuery` has 29 INFERRED edges - model-reasoned connections that need verification._
- **What connects `Scaling Strategy (horizontal web, vertical workers, DB)`, `Monitoring Stack (Prometheus, Grafana, Loki, Uptime Kuma)`, `postgres-data volume` to the rest of the system?**
  _17 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `Dynamic Report Handler Base` be split into smaller, more focused modules?**
  _Cohesion score 0.05593220338983051 - nodes in this community are weakly interconnected._
- **Why does `EhAccountUnitTestCase` connect `Orchestrator Constraint Tests` to `Currency Conversion Tests`, `Report Wizard Module`, `Dynamic Report Orchestrator`, `Report Execution Cache`, `Orchestrator & XLSX Modules`, `SQL Builder Unit Tests`, `XLSX Report Writer`, `Report Handler Modules`, `Orchestrator Cache Tests`, `Shared Test Suite Wiring`, `Orchestrator Test Doubles`, `Report Wizard Tests`?**
  _High betweenness centrality (0.156) - this node is a cross-community bridge._

### Low-confidence Hints
_AMBIGUOUS edges — the extractor was unsure. Verify before acting on these._

- **What is the exact relationship between `Traefik v3.1 Reverse Proxy` and `Docker Compose Stack (Nginx Edition)`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._
- **What is the exact relationship between `PgBouncer Transaction-Mode Pool` and `odoo-worker service`?**
  _Edge tagged AMBIGUOUS (relation: conceptually_related_to) - confidence is low._