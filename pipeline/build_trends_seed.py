"""Build backend/data/trends.json (run: python3 pipeline/build_trends_seed.py backend/data/trends.json) — the seed for the Trends tab (as of 2026-11-11).

Figures only where sourced in research this session (Crunchbase News, Menlo Ventures, State of AI, Fortune/PitchBook,
Seraphim, Fusion Industry Association, Dealroom, TechCrunch). Tracker-linked companies (id) take live valuations from
the database; explicit valuations here are only for newer sourced marks or untracked names.
"""
import json
import sys

ASOF = '2026-11-11'


def co(name, id=None, domain='', stage='', desc='', val=None, vdate='', label='REPORTED', rnd='', inv=None, hq=''):
    d = {'name': name, 'id': id, 'domain': domain, 'stage': stage, 'description': desc, 'hq': hq,
         'last_round': rnd, 'investors': inv or []}
    if val is not None:
        d.update(valuation_usd_bn=val, valuation_date=vdate, valuation_label=label)
    return d


def P(text, sev='medium'):
    return {'text': text, 'severity': sev}


def R(title, url, source, kind, date='', summary=''):
    return {'title': title, 'url': url, 'source': source, 'kind': kind, 'date': date, 'summary': summary}


CB_Q3 = 'https://news.crunchbase.com/venture/q3-2026-global-startup-funding-ai-billion-dollar-rounds-exits-data/'
CB_PHYS = 'https://news.crunchbase.com/venture/physical-ai-funding-startups-robotics-aerospace-h1-2026/'
CB_DEF = 'https://news.crunchbase.com/defense-tech/startup-venture-funding-all-time-record-ai-anduril/'
CB_AV = 'https://news.crunchbase.com/venture/record-funding-autonomous-vehicles-q1-2026/'
CB_CHIP = 'https://news.crunchbase.com/semiconductors-and-5g/chip-startup-funding-2026-cerebras-matx-ayar-labs-ipos-nvda/'
CB_CYBER = 'https://news.crunchbase.com/cybersecurity/solid-startup-venture-funding-growth-h1-2026/'
CB_WK_AUG21 = 'https://news.crunchbase.com/venture/biggest-funding-rounds-defense-tech-ai-infrastructure-castelion/'
CB_WK_JUL31 = 'https://news.crunchbase.com/venture/biggest-funding-rounds-safe-superintelligence-commonwealth-fusion/'
MENLO = 'https://menlovc.com/wp-content/uploads/2026/11/menlo_ventures_enterprise_ai_report-2026-110326.pdf'
SOAI = 'https://www.stateof.ai/'
FORTUNE_Q = 'https://fortune.com/2026/06/29/blackrock-nvidia-temasek-betting-billions-quantum-computing/'
SERAPHIM_Q2 = 'https://seraphim.vc/wp-content/uploads/2026/07/Seraphim-Space-Index-Q2-2026.pdf'
SPACE_Q3 = 'https://www.analyticsinsight.net/news/space-startups-raise-record-usd-208-billion-why-investors-are-betting-on-infrastructure'
FIA = 'https://www.power-eng.com/nuclear/record-4-48bn-funding-boomtime-for-fusion-industry/'
AIF_NOV = 'https://aifunding.me/insights/weekly-roundup-nov-2-6-2026'
ROBO_Q3 = 'https://runtimewire.com/article/robotics-startup-funding-q3-2026-physical-ai'

themes = []

# 1 ─ Frontier models
themes.append({
    'id': 'frontier-models', 'name': 'Frontier models & AI labs', 'category': 'AI', 'order': 1, 'color': '#0f2347',
    'signal': 'hot', 'heat': 95, 'conviction': 'high', 'horizon': 'now', 'deploy_early': 'avoid', 'deploy_growth': 'selective',
    'summary': 'The labs building frontier models (Anthropic, OpenAI, Google DeepMind, xAI) plus well-funded challengers. '
               'Revenue is compounding faster than any software category on record, and labs now capture most enterprise AI spend.',
    'why_now': 'State of AI 2026 puts the combined OpenAI + Anthropic revenue run-rate at about $105bn (from about $30bn at the start of the year). '
               'Menlo Ventures finds Anthropic, OpenAI and Google take 69% of enterprise AI deployment dollars, with Anthropic at 55% of enterprise API spend.',
    'deploy_view': 'Growth only, and only at entry prices that still compound: tenders and primary rounds in the two leaders, accessed directly or via low-fee SPVs. '
                   'Seed-stage "neo-labs" now price at multi-billion valuations (Thinking Machines, SSI, Reflection), so they are not early-stage risk/return. Avoid fee-stacked SPV layers.',
    'funding': [
        {'period': '2026 YTD (to Q3)', 'stage': 'growth', 'capital_usd_bn': 227, 'note': 'OpenAI ($132bn) + Anthropic ($95bn) raised in 2026: about one-third of all global VC',
         'source': 'CB Insights via Fintech News Switzerland', 'url': 'https://fintechnews.ch/aifintech/q3-cb-insight-report-global-vc-funding-surges-driven-by-ai/86530/', 'label': 'REPORTED'},
        {'period': '2026', 'stage': 'all', 'capital_usd_bn': 176.8, 'note': 'US enterprise AI deployment spend (5.4x YoY); labs take 69%', 'metric': 'market',
         'source': 'Menlo Ventures, State of Enterprise AI 2026', 'url': MENLO, 'label': 'ESTIMATE'},
    ],
    'valuation_notes': 'Leaders trade at roughly 10-20x forward run-rate revenue, re-marked every few months. Second-tier labs are priced on team and compute access, not revenue.',
    'risks': [P('Compute capex and power constraints: hyperscaler capex guided to about $733bn in 2026', 'high'),
              P('Open-weight models (incl. Chinese labs) compress API pricing; cost per benchmark point falls about 13x a year', 'high'),
              P('Entry price: most value accrues to holders who got in before 2025; fee layers erode returns', 'medium'),
              P('Regulatory, copyright and safety incidents', 'medium')],
    'catalysts': [P('Agentic products (coding, computer use) lift revenue per customer', 'high'),
                  P('IPO path for the leaders creates liquidity for early holders', 'medium')],
    'kpis': ['Run-rate revenue and gross margin of the leaders', 'Enterprise API share (Menlo)', 'Tender / secondary prices vs last primary',
             'Cost per token and open-weight benchmark gap', 'Compute contracts (GW) signed'],
    'segments': [
        {'name': 'Leading labs', 'companies': [
            co('Anthropic', 'anthropic', 'anthropic.com', desc='Claude models; leads enterprise API spend'),
            co('OpenAI', 'openai', 'openai.com', desc='ChatGPT, GPT models, Codex'),
            co('xAI', 'xai', 'x.ai', desc='Grok; merged into SpaceX'),
            co('Mistral AI', 'mistral', 'mistral.ai', desc='European open-weight and sovereign AI lab'),
            co('Cohere', 'cohere', 'cohere.com', desc='Enterprise models and agents')]},
        {'name': 'Neo-labs (priced as growth from day one)', 'companies': [
            co('Safe Superintelligence', 'ssi', 'ssi.inc', desc='Ilya Sutskever lab; reported $5bn raise Jul 2026', rnd='$5bn (reported), Jul 2026'),
            co('Thinking Machines Lab', 'thinkingmachines', 'thinkingmachines.ai', desc='Mira Murati lab; $5bn raise reported Nov 2026', rnd='$5bn, Nov 2026'),
            co('Reflection AI', 'reflection', 'reflection.ai', desc='Open frontier models / autonomous coding'),
            co('Perplexity', 'perplexity', 'perplexity.ai', desc='AI answer engine and browser')]},
    ],
    'news': [
        {'date': '2026-11-06', 'headline': 'Thinking Machines Lab raises $5.0bn', 'url': AIF_NOV, 'source': 'aifunding.me weekly roundup'},
        {'date': '2026-10-08', 'headline': 'State of AI 2026: OpenAI + Anthropic run-rate about $105bn; Anthropic about $65bn', 'url': SOAI, 'source': 'Air Street Capital'},
        {'date': '2026-07-31', 'headline': 'Safe Superintelligence reported to raise $5bn led by Nvidia', 'url': CB_WK_JUL31, 'source': 'Crunchbase News'},
    ],
    'resources': [
        R('State of AI Report 2026', SOAI, 'Air Street Capital', 'report', '2026-10-08', 'Annual 244-slide review: research, industry, politics, safety, predictions.'),
        R('Menlo Ventures: State of Enterprise AI 2026', MENLO, 'Menlo Ventures', 'report', '2026-11-03', '$176.8bn enterprise AI spend, model share, coding and agents.'),
        R('Enterprise AI spend hit $177bn; only 22% came from software budgets', 'https://www.saastr.com/ai-spend-hit-177-billion-this-year-only-22-of-it-came-out-of-software-budgets/', 'SaaStr', 'article', '2026-11', 'Where AI budgets come from and what it means for SaaS incumbents.'),
    ],
})

# 2 ─ AI infra
themes.append({
    'id': 'ai-infrastructure', 'name': 'AI infrastructure: compute, neoclouds & inference', 'category': 'AI', 'order': 2, 'color': '#1d4e89',
    'signal': 'hot', 'heat': 90, 'conviction': 'high', 'horizon': 'now', 'deploy_early': 'selective', 'deploy_growth': 'selective',
    'summary': 'GPU clouds, data-centre developers, and inference / serving platforms that turn models into production workloads.',
    'why_now': 'Agents multiply model calls: 80% of OpenRouter tokens are now agent traffic (Menlo). Data centres were among five Q3 2026 sectors to clear $10bn of venture funding (Crunchbase).',
    'deploy_view': 'Early: overweight software that lowers inference cost (serving, orchestration, evaluation), not asset-heavy GPU resellers. '
                   'Growth: be selective. Neoclouds are capital-intensive and GPU-backed debt is a real risk; prefer platforms with contracted, investment-grade demand and their own power.',
    'funding': [
        {'period': 'Q3 2026', 'stage': 'all', 'capital_usd_bn': None, 'note': 'Data centres one of five sectors above $10bn in Q3 2026 venture funding', 'source': 'Crunchbase News', 'url': CB_Q3},
        {'period': '2026', 'stage': 'all', 'capital_usd_bn': 733, 'note': 'Big-4 hyperscaler 2026 capex guidance (+79% YoY): demand backdrop, not VC', 'metric': 'market', 'source': 'State of AI 2026', 'url': SOAI, 'label': 'REPORTED'},
    ],
    'valuation_notes': 'Inference platforms re-rated sharply in 2026 (e.g. Baseten to about $13bn); neocloud values track contracted megawatts and backlog.',
    'risks': [P('GPU depreciation and refinancing risk on asset-backed debt', 'high'), P('Hyperscalers and labs vertically integrating inference', 'high'),
              P('Local opposition: about $68bn of data-centre projects blocked or delayed in Q2 2026 (Data Center Watch via State of AI)', 'medium')],
    'catalysts': [P('Agent workloads and reasoning models raise tokens per task', 'high'), P('Custom silicon diversity (beyond Nvidia) lowers serving cost', 'medium')],
    'kpis': ['Contracted MW and backlog', 'Inference price per million tokens', 'Utilisation and gross margin of neoclouds', 'Debt cost of GPU financing'],
    'segments': [
        {'name': 'Neoclouds & AI data centres', 'companies': [
            co('Crusoe', 'crusoe', 'crusoe.ai', desc='Energy-first AI data centres'), co('CoreWeave', 'coreweave', 'coreweave.com', desc='Listed GPU cloud'),
            co('Lambda', 'lambda', 'lambda.ai', desc='GPU cloud for AI developers'), co('Nscale', None, 'nscale.com', 'growth', 'European AI hyperscaler; $3bn+ round in Q3 2026', rnd='>$3bn, Q3 2026')]},
        {'name': 'Inference & serving platforms', 'companies': [
            co('Baseten', 'baseten', 'baseten.co', desc='Model inference platform', val=13.0, vdate='2026-06'),
            co('Fireworks AI', 'fireworks', 'fireworks.ai', desc='Inference cloud for open models'),
            co('Together AI', 'together', 'together.ai', desc='Open-model cloud'),
            co('fal', None, 'fal.ai', 'growth', 'Generative media inference; $1.3bn Series F', rnd='$1.3bn Series F, Nov 2026', inv=['Bessemer', 'NVIDIA', 'T. Rowe Price']),
            co('Modal', 'modal', 'modal.com', desc='Serverless GPU compute')]},
    ],
    'news': [{'date': '2026-11-03', 'headline': 'fal raises $1.3bn Series F (Bessemer, NVIDIA, T. Rowe Price)', 'url': AIF_NOV, 'source': 'aifunding.me'}],
    'resources': [R('Neoclouds: AI\'s $150bn middle layer that owns almost nothing', 'https://measuredai.substack.com/p/neoclouds-ai-middle-layer', 'Measured AI', 'article', '', 'Skeptical take on neocloud economics.')],
})

# 3 ─ AI chips
themes.append({
    'id': 'ai-semiconductors', 'name': 'AI semiconductors & photonics', 'category': 'AI', 'order': 3, 'color': '#2c5f8a',
    'signal': 'accelerating', 'heat': 82, 'conviction': 'medium', 'horizon': '1-3y', 'deploy_early': 'selective', 'deploy_growth': 'selective',
    'summary': 'Inference ASICs, wafer-scale and transformer-specific chips, chiplets and interconnect, and silicon photonics challenging GPU lock-in.',
    'why_now': 'Inference now outweighs training in demand. Cerebras listed in 2026 and Etched re-priced to $21bn, giving the category real exits and marks.',
    'deploy_view': 'Early: photonics and interconnect (bandwidth is the bottleneck), plus power-efficient inference. Growth: only names with hyperscaler or lab design wins; binary technical risk remains.',
    'funding': [{'period': '2026 YTD (to 10 Jun)', 'stage': 'all', 'capital_usd_bn': 10.7, 'note': 'Seed to pre-IPO semiconductor funding, on track to beat 2025', 'source': 'Crunchbase News', 'url': CB_CHIP}],
    'valuation_notes': 'Cerebras listed at a market cap around $50bn, then fell about a third. Etched $21bn (Aug 2026), Groq $3.5bn.',
    'risks': [P('Nvidia roadmap pace and CUDA ecosystem', 'high'), P('Tape-out failures; 3-4 year product cycles', 'high'), P('TSMC capacity allocation', 'medium')],
    'catalysts': [P('Labs diversifying away from a single supplier', 'high'), P('Co-packaged optics adoption', 'medium')],
    'kpis': ['Design wins at labs / hyperscalers', 'Tokens per second per watt vs Nvidia', 'Tape-out and volume ramp dates'],
    'segments': [
        {'name': 'AI accelerators', 'companies': [
            co('Etched', 'etched', 'etched.com', desc='Transformer-specific ASIC', val=21, vdate='2026-08', rnd='$700M led by Jane Street, Aug 2026'),
            co('Cerebras', 'cerebrassystems', 'cerebras.ai', desc='Wafer-scale AI systems; listed 2026'),
            co('Groq', 'groq', 'groq.com', desc='LPU inference chips and cloud'),
            co('MatX', 'matx', 'matx.com', 'growth', 'Chips for frontier-model training', rnd='$500M Series B, Feb 2026'),
            co('d-Matrix', 'dmatrix', 'd-matrix.ai', desc='In-memory compute for inference'),
            co('Tenstorrent', 'tenstorrent', 'tenstorrent.com', desc='RISC-V AI processors')]},
        {'name': 'Photonics & interconnect', 'companies': [
            co('Ayar Labs', 'ayar', 'ayarlabs.com', desc='Optical I/O chiplets', rnd='$500M Series E, Mar 2026'),
            co('Lightmatter', 'lightmatter', 'lightmatter.co', desc='Photonic interconnect'),
            co('Eliyan', None, 'eliyan.com', 'growth', 'Chiplet interconnect', val=1.0, vdate='2026-07', rnd='$145M Series C')]},
    ],
    'resources': [R('Chip startup funding in 2026: Cerebras, MatX, Ayar Labs and the IPO window', CB_CHIP, 'Crunchbase News', 'article', '2026-06-10')],
})

# 4 ─ AI coding
themes.append({
    'id': 'ai-coding', 'name': 'AI coding & software agents', 'category': 'AI', 'order': 4, 'color': '#3a6ea5',
    'signal': 'hot', 'heat': 86, 'conviction': 'high', 'horizon': 'now', 'deploy_early': 'selective', 'deploy_growth': 'watch',
    'summary': 'Coding assistants, autonomous software engineers and app builders: the first AI category with clear, large revenue.',
    'why_now': 'Coding is $34bn of the $77bn enterprise AI application market and 96% AI-native (Menlo). SpaceX agreed to buy Cursor for $60bn in stock (Jun 2026).',
    'deploy_view': 'Growth: watch. Labs\' own agents (Claude Code, Codex) take about 70% of coding spend, which squeezes independents, and valuations already price in leadership. '
                   'Early: selective on adjacent layers such as testing, code review, security of AI-written code, and agent infrastructure.',
    'funding': [{'period': '2026', 'stage': 'all', 'capital_usd_bn': 34.0, 'note': 'Enterprise spend on AI coding (labs\' first-party apps $24bn of it)', 'metric': 'market', 'source': 'Menlo Ventures', 'url': MENLO, 'label': 'ESTIMATE'}],
    'valuation_notes': 'Cursor $29.3bn (late 2025) → $50bn (Jul 2026) → $60bn SpaceX deal. Lovable $13.3bn, Replit $9bn, Cognition $26bn+.',
    'risks': [P('Labs competing directly with their own coding agents', 'high'), P('Low switching costs; model-driven feature parity', 'medium')],
    'catalysts': [P('Non-developer builders: Codex non-developer users grew 137x Aug 2025 to Jun 2026 (State of AI)', 'medium'), P('Strategic M&A by labs and big tech', 'medium')],
    'kpis': ['ARR and net revenue retention of independents', 'Share of coding spend held by labs (Menlo: about 70%)', 'Gross margin after model costs'],
    'segments': [
        {'name': 'IDEs & software-engineer agents', 'companies': [
            co('Cursor (Anysphere)', 'cursor', 'cursor.com', desc='AI IDE; being acquired by SpaceX for $60bn'),
            co('Cognition', 'cognition', 'cognition.ai', desc='Devin agent + Windsurf'), co('poolside', 'poolside', 'poolside.ai', desc='Models for software engineering'),
            co('Trajectory', None, '', 'early', 'AI developer tools; $45M Series A, Nov 2026', rnd='$45M Series A', inv=['Sequoia', 'NVIDIA', 'Bessemer', 'BCV'])]},
        {'name': 'App builders & platforms', 'companies': [
            co('Lovable', 'lovable', 'lovable.dev', desc='Prompt-to-app builder'), co('Replit', 'replit', 'replit.com', desc='Cloud IDE and agent'),
            co('Vercel', 'vercel', 'vercel.com', desc='Frontend cloud, v0'), co('Supabase', 'supabase', 'supabase.com', desc='Postgres backend for AI apps')]},
    ],
    'news': [{'date': '2026-06-16', 'headline': 'SpaceX to acquire Cursor for $60bn in stock days after its IPO', 'url': 'https://techcrunch.com/2026/06/16/spacex-to-acquire-cursor-for-60b-in-stock-days-after-blockbuster-ipo/', 'source': 'TechCrunch'}],
    'resources': [R('SpaceX to acquire Cursor for $60B in stock', 'https://techcrunch.com/2026/06/16/spacex-to-acquire-cursor-for-60b-in-stock-days-after-blockbuster-ipo/', 'TechCrunch', 'news', '2026-06-16')],
})

# 5 ─ Enterprise agents & vertical AI
themes.append({
    'id': 'enterprise-agents', 'name': 'Enterprise agents & vertical AI', 'category': 'AI', 'order': 5, 'color': '#4a7fb5',
    'signal': 'hot', 'heat': 84, 'conviction': 'high', 'horizon': '1-3y', 'deploy_early': 'overweight', 'deploy_growth': 'selective',
    'summary': 'Agents that do work end to end (customer service, legal, finance, sales, back office) and vertical AI that owns a workflow and its data.',
    'why_now': 'Customer success is the fastest-growing AI department (4.3x, Menlo). 55% of incremental AI dollars come from net-new budgets, and ICONIQ finds about 70% of AI builders are vertical. Pricing is moving to outcomes.',
    'deploy_view': 'Early: overweight vertical, "multiplayer" agents with proprietary workflow data and outcome-based pricing (a16z Big Ideas). '
                   'Growth: selective. Incumbents keep 91% of IT and 68% of HR spend (Menlo), so back category leaders with clear net-new budget capture (Sierra, Harvey, Decagon).',
    'funding': [{'period': '2026', 'stage': 'all', 'capital_usd_bn': 77.3, 'note': 'Enterprise AI application market (coding + chatbots = 76%)', 'metric': 'market', 'source': 'Menlo Ventures', 'url': MENLO, 'label': 'ESTIMATE'}],
    'valuation_notes': 'Category leaders at $5-16bn on high-growth ARR. Many seed / A rounds at $50-150M+ post for AI-native teams.',
    'risks': [P('Labs moving up the stack (plugins, agents) compress the application layer', 'high'), P('Incumbent seat conversion: 13 of 22 points of software-budget shift went to incumbents (Menlo)', 'medium')],
    'catalysts': [P('Outcome pricing and labour-budget capture', 'high'), P('Agent reliability gains', 'medium')],
    'kpis': ['ARR per FTE', 'Share of revenue from outcome-based pricing', 'Gross margin after inference', 'Logo retention vs incumbents'],
    'segments': [
        {'name': 'Customer & revenue agents', 'companies': [
            co('Sierra', 'sierra', 'sierra.ai', desc='Customer-experience agents'), co('Decagon', 'decagon', 'decagon.ai', desc='AI customer support'),
            co('Clay', 'clay', 'clay.com', desc='GTM data and agents'), co('Nooks', None, 'nooks.ai', 'growth', 'AI sales assistant; $500M growth round led by General Catalyst', rnd='$500M growth, Nov 2026'),
            co('ElevenLabs', 'elevenlabs', 'elevenlabs.io', desc='Voice AI and voice agents')]},
        {'name': 'Vertical AI: legal, finance, knowledge work', 'companies': [
            co('Harvey', 'harvey', 'harvey.ai', desc='Legal AI'), co('Hebbia', 'hebbia', 'hebbia.com', desc='AI for finance research'),
            co('Glean', 'glean', 'glean.com', desc='Enterprise search and agents'),
            co('Rillet', None, 'rillet.com', 'growth', 'AI-native ERP / accounting', val=1.0, vdate='2026-08', rnd='$100M Series C led by ICONIQ')]},
    ],
    'resources': [R('ICONIQ: 2026 State of AI bi-annual snapshot', 'https://www.iconiq.com/growth/insights/state-of-ai-bi-annual-snapshot', 'ICONIQ', 'report', '2026', 'Builder survey: model usage, pricing (outcome pricing at 18%), margins, vertical focus.'),
                  R('a16z Big Ideas 2026 (part 1)', 'https://a16z.com/newsletter/big-ideas-2026-part-1/', 'Andreessen Horowitz', 'article', '2026', 'Agent-native infrastructure, systems of record losing ground, multiplayer vertical AI.')],
})

# 6 ─ Healthcare AI
themes.append({
    'id': 'healthcare-ai', 'name': 'Healthcare AI & clinical agents', 'category': 'AI', 'order': 6, 'color': '#2f7d6d',
    'signal': 'accelerating', 'heat': 74, 'conviction': 'medium', 'horizon': '1-3y', 'deploy_early': 'overweight', 'deploy_growth': 'selective',
    'summary': 'Ambient scribes, clinical decision support, healthcare agents and consumer preventive health.',
    'why_now': 'Clinician adoption of AI scribes and evidence tools is mainstream, and "healthy MAUs" (preventive monitoring) is an a16z 2026 big idea. Large growth rounds continue (Function $450M, Laza Medical $160M).',
    'deploy_view': 'Early: overweight agents that touch reimbursement (revenue cycle, prior auth) and specialty workflows. Growth: selective; scribes are commoditising.',
    'funding': [],
    'risks': [P('Scribe commoditisation; EHR vendors bundling AI', 'high'), P('Regulatory (FDA, liability) and long hospital sales cycles', 'medium')],
    'catalysts': [P('Payer and provider labour shortages', 'high'), P('CMS reimbursement codes for AI-enabled care', 'medium')],
    'kpis': ['Health-system logo count', 'Revenue per clinician', 'Regulatory clearances'],
    'segments': [{'name': 'Clinical AI', 'companies': [
        co('OpenEvidence', 'openevidence', 'openevidence.com', desc='Clinical evidence assistant for physicians'),
        co('Abridge', 'abridge', 'abridge.com', desc='Ambient clinical documentation'),
        co('Hippocratic AI', 'hippocratic', 'hippocraticai.com', desc='Healthcare agents (non-diagnostic)'),
        co('Ambience Healthcare', 'ambiencehealthcare', 'ambiencehealthcare.com', desc='Ambient AI and coding'),
        co('Laza Medical', None, '', 'early', 'AI healthcare; $160M Series B, Nov 2026', rnd='$160M Series B', inv=['GE HealthCare'])]},
        {'name': 'Consumer & preventive health', 'companies': [co('Function Health', None, 'functionhealth.com', 'growth', 'Lab testing and preventive health', rnd='$450M growth, Jul 2026', inv=['General Catalyst'])]}],
})

# 7 ─ AI bio
themes.append({
    'id': 'ai-drug-discovery', 'name': 'AI drug discovery & TechBio', 'category': 'Bio', 'order': 7, 'color': '#3f8f5f',
    'signal': 'accelerating', 'heat': 66, 'conviction': 'medium', 'horizon': '3-7y', 'deploy_early': 'selective', 'deploy_growth': 'selective',
    'summary': 'Foundation models for biology and chemistry, generative protein and molecule design, and AI-native drug developers.',
    'why_now': 'Mega-rounds signal a shift from promise to deployment: Isomorphic Labs $2.1bn Series B (May 2026), Chai Discovery $400M Series C at $3.8bn.',
    'deploy_view': 'Early: platforms with pharma partnerships that carry milestone economics, and molecules nearing the clinic. Growth: selective; value only crystallises at clinical readouts (7-10 year horizon).',
    'funding': [],
    'valuation_notes': 'Chai Discovery $3.8bn (Series C, 2026). Listed peers (Recursion) remain well below 2021 highs, so public-market comps are weak.',
    'risks': [P('Clinical attrition: AI has not yet proven higher phase-2 success rates', 'high'), P('Long timelines vs fund lives', 'medium')],
    'catalysts': [P('First AI-designed molecules reaching phase 2/3 readouts', 'high'), P('Big-pharma platform deals', 'medium')],
    'kpis': ['Clinical candidates and phase transitions', 'Pharma deal milestones', 'Model benchmarks (structure, binding)'],
    'segments': [{'name': 'AI-first drug discovery', 'companies': [
        co('Isomorphic Labs', 'isomorphic', 'isomorphiclabs.com', 'growth', 'DeepMind spin-out; $2.1bn Series B', rnd='$2.1bn Series B, May 2026'),
        co('Xaira Therapeutics', 'xairatherapeutics', 'xaira.com', 'growth', 'AI drug developer'),
        co('Chai Discovery', 'chaidiscovery', 'chaidiscovery.com', desc='Foundation models for molecular design', val=3.8, vdate='2026', rnd='$400M Series C'),
        co('Recursion', 'recursionpharmaceuticals', 'recursion.com', desc='Listed TechBio'),
        co('Enveda', 'enveda', 'envedabio.com', desc='Nature-derived medicines with AI')]}],
    'resources': [R('Chai Discovery raises $400M at $3.8bn', 'https://thenextweb.com/news/chai-discovery-400m-series-c-ai-drug-discovery', 'The Next Web', 'news', '2026'),
                  R('Isomorphic Labs raises $2.1bn to expand AI-driven drug discovery', 'https://www.biopharminternational.com/view/isomorphic-labs-raises-2-1-billion-to-expand-ai-driven-drug-discovery-platform', 'BioPharm International', 'news', '2026-05-13')],
})

# 8 ─ Physical AI
themes.append({
    'id': 'physical-ai-robotics', 'name': 'Physical AI & robotics', 'category': 'Physical', 'order': 8, 'color': '#b38728',
    'signal': 'accelerating', 'heat': 93, 'conviction': 'high', 'horizon': '3-7y', 'deploy_early': 'overweight', 'deploy_growth': 'selective',
    'summary': 'Robot foundation models ("one brain for all robots"), humanoids, and AI-native industrial, logistics and field robots.',
    'why_now': 'Physical AI took $47.4bn in H1 2026 across 521 deals, almost 4x H2 2025 (Crunchbase). Robotics alone raised $9.9bn in Q3 2026 (+185% YoY). '
               'Robot foundation models are showing generalisation: Physical Intelligence\'s π-0.7 performs tasks it was never trained on.',
    'deploy_view': 'Early: overweight application robots with paying customers (logistics, construction, inspection) and data / simulation infrastructure. '
                   'Growth: selective. Robot-brain leaders (Physical Intelligence, Skild) are worth owning, but humanoid valuations (Figure $39bn) are far ahead of revenue.',
    'funding': [
        {'period': 'H1 2026', 'stage': 'all', 'capital_usd_bn': 47.4, 'deals': 521, 'note': 'Physical AI (robotics, AVs, aerospace, drones, industrial automation, sensors)', 'source': 'Crunchbase News', 'url': CB_PHYS},
        {'period': 'H2 2025', 'stage': 'all', 'capital_usd_bn': 12.0, 'deals': 470, 'source': 'Crunchbase News', 'url': CB_PHYS},
        {'period': 'H1 2025', 'stage': 'all', 'capital_usd_bn': 26.4, 'deals': 436, 'source': 'Crunchbase News', 'url': CB_PHYS},
        {'period': 'Q3 2026', 'stage': 'all', 'capital_usd_bn': 9.9, 'note': 'Robotics only, +185% YoY; China $13.2bn and US $12.1bn YTD', 'source': 'Crunchbase via RuntimeWire', 'url': ROBO_Q3},
    ],
    'valuation_notes': 'Skild AI $14bn (Jan 2026, 9x in 18 months); Physical Intelligence above $11bn (reported Mar 2026, from $5.6bn); Figure $39bn (Sep 2025). Mobileye bought Mentee Robotics for about $900M.',
    'risks': [P('Humanoid hardware cost and reliability are years from consumer scale', 'high'), P('China\'s cost advantage (Unitree and others) and supply chain', 'high'),
              P('Valuations driven by narrative and data scarcity, not revenue', 'medium')],
    'catalysts': [P('Foundation-model generalisation (π-0.7, Skild Brain)', 'high'), P('Labour shortages in logistics, manufacturing and construction', 'high'),
                  P('Nvidia ecosystem (Isaac, GR00T) lowering build cost', 'medium')],
    'kpis': ['Deployed robots and hours in production', 'Cost per robot-hour vs labour', 'Generalisation benchmarks', 'Humanoid unit pricing (1X NEO preorders at $20k)'],
    'segments': [
        {'name': 'Robot foundation models', 'companies': [
            co('Physical Intelligence', 'physicalintelligence', 'physicalintelligence.company', desc='π models: general robot policies', val=11.0, vdate='2026-03', rnd='About $1bn (reported), Mar 2026', inv=['Founders Fund', 'Thrive', 'Lux']),
            co('Skild AI', 'skild', 'skild.ai', desc='Skild Brain: general-purpose robot intelligence', rnd='$1.4bn Series C, Jan 2026', inv=['SoftBank', 'NVentures', 'Bezos Expeditions']),
            co('Generalist AI', 'generalist', 'generalistai.com', desc='Embodied foundation models'),
            co('Field AI', None, 'fieldai.com', 'growth', 'Universal robot brains for field robots', rnd='$405M, Aug 2025')]},
        {'name': 'Humanoids', 'companies': [
            co('Figure AI', 'figure', 'figure.ai', desc='General-purpose humanoid'), co('Agility Robotics', 'agilityrobotics', 'agilityrobotics.com', desc='Digit humanoid for logistics'),
            co('Apptronik', None, 'apptronik.com', 'growth', 'Apollo humanoid; Google DeepMind partner'), co('1X', None, '1x.tech', 'growth', 'NEO home humanoid ($20k preorders)'),
            co('Unitree Robotics', 'unitreerobotics', 'unitree.com', 'growth', 'Chinese quadrupeds and humanoids', hq='Hangzhou'),
            co('Sunday Robotics', 'sunday', '', 'early', 'Home robotics')]},
        {'name': 'Industrial, logistics & field robots', 'companies': [
            co('Gecko Robotics', 'geckorobotics', 'geckorobotics.com', desc='Inspection robots and data'), co('Bedrock Robotics', 'bedrockrobotics', 'bedrockrobotics.com', desc='Autonomous construction equipment'),
            co('Mytra', 'mytra', 'mytra.ai', desc='Warehouse storage robotics'), co('Tutor Intelligence', 'tutorintelligence', 'tutorintelligence.com', desc='Factory and warehouse robots; $75M Nov 2026'),
            co('Dexterity', None, 'dexterity.ai', 'growth', 'AI robots for logistics')]},
    ],
    'news': [{'date': '2026-11-03', 'headline': 'Tutor Intelligence raises $75M', 'url': AIF_NOV, 'source': 'aifunding.me'},
             {'date': '2026-10-27', 'headline': 'Robotics startups raised $9.9bn in Q3 2026, +185% YoY', 'url': ROBO_Q3, 'source': 'RuntimeWire / Crunchbase'},
             {'date': '2026-08-18', 'headline': 'Physical AI startups raised $47.4bn in H1 2026, almost 4x H2 2025', 'url': CB_PHYS, 'source': 'Crunchbase News'}],
    'resources': [R('Physical AI funding: robotics and aerospace, H1 2026', CB_PHYS, 'Crunchbase News', 'report', '2026-08-18', 'The definitive H1 2026 physical-AI funding tally and largest rounds.'),
                  R('Skild AI hits $14bn valuation', 'https://fintool.com/news/skild-ai-14-billion-valuation-robotics', 'Fintool', 'news', '2026-01'),
                  R('Physical Intelligence seeks $1bn at $11bn valuation', 'https://dealroom.co/news/127095-robot-ai-startup-physical-intelligence-seeks-1b-at-11b-valuation/', 'Dealroom (Bloomberg)', 'news', '2026-03-30'),
                  R('Robot unicorns are getting bigger', 'https://robotsandstartups.substack.com/p/robot-unicorns-are-getting-bigger', 'Robots & Startups (Substack)', 'newsletter', '', 'Specialist robotics newsletter worth following.')],
})

# 9 ─ Autonomy
themes.append({
    'id': 'autonomous-mobility', 'name': 'Autonomous vehicles, drones & delivery', 'category': 'Physical', 'order': 9, 'color': '#c79a3a',
    'signal': 'accelerating', 'heat': 80, 'conviction': 'medium', 'horizon': '1-3y', 'deploy_early': 'selective', 'deploy_growth': 'selective',
    'summary': 'Robotaxis, autonomous trucking, embodied-AI driving stacks, simulation, and autonomous aerial delivery.',
    'why_now': 'AV funding hit $21.4bn by mid-April 2026, a record, versus $5.9bn in all of 2025 (Crunchbase). Waymo raised $16bn at $126bn, Wayve $1.2-1.5bn at $8.6bn for a London robotaxi launch, and Zipline $1.5bn (Nov 2026).',
    'deploy_view': 'Growth: Waymo is the category winner but is priced for it. Wayve offers an "AV 2.0" end-to-end option. Early: simulation, validation, teleoperation and fleet software; avoid sub-scale full-stack AV.',
    'funding': [{'period': '2026 YTD (to 15 Apr)', 'stage': 'all', 'capital_usd_bn': 21.4, 'deals': 34, 'note': 'Record; Waymo about three-quarters of it', 'source': 'Crunchbase News', 'url': CB_AV},
                {'period': '2025', 'stage': 'all', 'capital_usd_bn': 5.9, 'deals': 99, 'source': 'Crunchbase News', 'url': CB_AV},
                {'period': '2024', 'stage': 'all', 'capital_usd_bn': 12.1, 'deals': 127, 'source': 'Crunchbase News', 'url': CB_AV}],
    'risks': [P('Safety incidents and regulatory pauses', 'high'), P('Capital intensity of fleets', 'medium'), P('Chinese competition (Momenta, Pony) in global markets', 'medium')],
    'catalysts': [P('Robotaxi city launches (London, US expansion)', 'high'), P('Drone delivery regulation (BVLOS)', 'medium')],
    'kpis': ['Paid driverless rides per week', 'Cities live', 'Cost per mile', 'Disengagement and incident data'],
    'segments': [{'name': 'Robotaxi & driving stacks', 'companies': [
        co('Waymo', 'waymo', 'waymo.com', desc='Robotaxi leader'), co('Wayve', 'wayve', 'wayve.ai', desc='End-to-end embodied AI driving'),
        co('Applied Intuition', 'appliedintuition', 'appliedintuition.com', desc='Simulation and vehicle software'),
        co('Nuro', 'nuro', 'nuro.ai', desc='Autonomy licensing'), co('Waabi', 'waabi', 'waabi.ai', desc='AI-first autonomous trucking')]},
        {'name': 'Drones & delivery', 'companies': [co('Zipline', 'zipline', 'flyzipline.com', desc='Autonomous drone delivery; $1.5bn raise, Nov 2026')]}],
    'news': [{'date': '2026-11-06', 'headline': 'Zipline raises $1.5bn (Paradigm, Fidelity, Uber, Tiger, ARK and others)', 'url': AIF_NOV, 'source': 'aifunding.me'}],
    'resources': [R('Record funding for autonomous vehicles in Q1 2026', CB_AV, 'Crunchbase News', 'report', '2026-04-17'),
                  R('Wayve raises $1.2bn at $8.6bn ahead of London robotaxi launch', 'https://dealroom.co/news/126121-wayve-raises-1-2b-at-8-6b-valuation-ahead-of-london-robotaxi-launch/', 'Dealroom', 'news', '2026-02-25')],
})

# 10 ─ Defense
themes.append({
    'id': 'defense-tech', 'name': 'Defense tech & national security', 'category': 'Physical', 'order': 10, 'color': '#8a1c22',
    'signal': 'hot', 'heat': 91, 'conviction': 'high', 'horizon': '1-3y', 'deploy_early': 'overweight', 'deploy_growth': 'selective',
    'summary': 'Autonomous systems (air, sea, land), munitions and hypersonics, counter-drone, defence software and AI, and the industrial base.',
    'why_now': 'Defense funding passed its full-year record by June 2026 ($14.6bn+ YTD vs $9.6bn in 2025, Crunchbase). Anduril doubled to $61bn in under a year. '
               'European rearmament and Pentagon procurement reform favour new primes, and exits are opening (Swarmer IPO, Aevex listing, D-Fend sold for $1.5bn).',
    'deploy_view': 'Early: overweight dual-use autonomy, counter-UAS, munitions supply chain and European defence. '
                   'Growth: selective. Anduril, Shield AI, Saronic and Castelion are priced for programme-of-record success, so size to contract visibility.',
    'funding': [{'period': '2026 YTD (to 2 Jun)', 'stage': 'all', 'capital_usd_bn': 14.6, 'deals': 107, 'note': 'Already above any prior full year', 'source': 'Crunchbase News', 'url': CB_DEF},
                {'period': '2025', 'stage': 'all', 'capital_usd_bn': 9.6, 'deals': 206, 'source': 'Crunchbase News', 'url': CB_DEF}],
    'valuation_notes': 'Anduril $61bn (May 2026), Shield AI $12.7bn, Saronic $9.25bn (more than double its Series C), Castelion $13bn (Aug 2026), Mach Industries $1.8bn.',
    'risks': [P('Budget and continuing-resolution timing; programme-of-record concentration', 'high'), P('Manufacturing scale-up execution', 'medium'), P('ESG and LP restrictions', 'low')],
    'catalysts': [P('NATO spending targets and European rearmament', 'high'), P('Drone and autonomy lessons from Ukraine', 'high'), P('Defense IPO window (Anduril widely expected)', 'medium')],
    'kpis': ['Programme-of-record wins', 'Backlog and production rate', 'European procurement share', 'IPO filings'],
    'segments': [
        {'name': 'New primes & autonomy', 'companies': [
            co('Anduril Industries', 'andurilindustries', 'anduril.com', desc='Autonomy, Lattice, Arsenal manufacturing'),
            co('Shield AI', 'shield', 'shield.ai', desc='Hivemind AI pilot, V-BAT', val=12.7, vdate='2026-03', rnd='$2bn Series G', inv=['Advent', 'JPMorgan']),
            co('Saronic', 'saronic', 'saronic.com', desc='Autonomous surface vessels', val=9.25, vdate='2026-03', rnd='$1.75bn Series D', inv=['Kleiner Perkins']),
            co('Helsing', 'helsing', 'helsing.ai', desc='European defence AI and strike drones')]},
        {'name': 'Munitions, hypersonics & effectors', 'companies': [
            co('Castelion', None, 'castelion.com', 'growth', 'Low-cost hypersonic strike', val=13, vdate='2026-08', rnd='$800M Series C + $250M debt', inv=['JPMorgan', 'a16z', 'Carlyle']),
            co('Mach Industries', 'machindustries', '', 'growth', 'Strike and VTOL systems', val=1.8, vdate='2026-06', rnd='$300M Series C', inv=['Infinite Capital', 'Ribbit']),
            co('Epirus', 'epirus', 'epirusinc.com', desc='High-power microwave counter-drone')]},
    ],
    'news': [{'date': '2026-08-21', 'headline': 'Castelion raises $800M Series C at $13bn', 'url': CB_WK_AUG21, 'source': 'Crunchbase News'},
             {'date': '2026-06-02', 'headline': 'Defense tech funding hits an all-time record by June', 'url': CB_DEF, 'source': 'Crunchbase News'}],
    'resources': [R('Defense startup funding hits an all-time record', CB_DEF, 'Crunchbase News', 'report', '2026-06-02'),
                  R('Anduril at $61bn and defense tech\'s 2026 reset', 'https://augment.market/pulse/anduril-at-61b-and-defense-techs-2026-reset', 'Augment Pulse', 'article', '2026')],
})

# 11 ─ Space
themes.append({
    'id': 'space', 'name': 'Space infrastructure', 'category': 'Physical', 'order': 11, 'color': '#5b4b8a',
    'signal': 'accelerating', 'heat': 83, 'conviction': 'medium', 'horizon': '1-3y', 'deploy_early': 'selective', 'deploy_growth': 'selective',
    'summary': 'Launch, satellite buses and constellations, in-space mobility and manufacturing, Earth observation, and defence space.',
    'why_now': 'SpaceX\'s June 2026 IPO ($75bn raised at about $1.77tn) re-rated the sector. Space start-ups raised a record $20.8bn in Q3 2026 across 216 deals (Seraphim), with launch and access at $16.4bn.',
    'deploy_view': 'Early: satellite buses, in-space mobility and defence-space data. Growth: selective in launch, where Stoke and Relativity compete with SpaceX\'s cost curve, so own capacity-constrained enablers.',
    'funding': [{'period': 'Q3 2026', 'stage': 'all', 'capital_usd_bn': 20.8, 'deals': 216, 'note': 'Record; launch & access $16.4bn; basis of Blue Origin\'s $10bn unclear', 'source': 'Seraphim Space Index', 'url': SPACE_Q3},
                {'period': 'Q2 2026', 'stage': 'all', 'capital_usd_bn': 7.4, 'deals': 140, 'source': 'Seraphim Space Index', 'url': SERAPHIM_Q2}],
    'risks': [P('SpaceX dominance in launch and broadband', 'high'), P('Government budget dependence', 'medium')],
    'catalysts': [P('SpaceX IPO creates public comps and liquidity', 'high'), P('Golden Dome / missile-defence constellations', 'high')],
    'kpis': ['Launch cadence and cost per kg', 'Government contract awards', 'Constellation deployment milestones'],
    'segments': [{'name': 'Launch & mobility', 'companies': [
        co('SpaceX', 'spacex', 'spacex.com', desc='Launch, Starlink; listed Jun 2026'), co('Rocket Lab', 'rocket', 'rocketlabusa.com', desc='Listed launch and spacecraft'),
        co('Stoke Space', 'stokespace', 'stokespace.com', desc='Fully reusable rocket; $1bn raise Q3 2026'),
        co('Impulse Space', 'impulsespace', 'impulsespace.com', desc='In-space transportation'), co('Relativity Space', 'relativityspace', 'relativityspace.com', desc='Terran R launch')]},
        {'name': 'Satellites, data & stations', 'companies': [
            co('K2 Space', None, 'k2space.com', 'growth', 'High-power satellite buses; $500M raise Q3 2026'),
            co('Muon Space', 'muonspace', 'muonspace.com', desc='Earth-observation constellations; $250M Series C (Eclipse)'),
            co('Varda Space', 'vardaspaceindustries', 'varda.com', desc='In-space manufacturing and re-entry'),
            co('Vast', None, 'vastspace.com', 'growth', 'Commercial space stations')]}],
    'resources': [R('Seraphim Space Index Q2 2026', SERAPHIM_Q2, 'Seraphim', 'report', '2026-07'),
                  R('Space start-ups raise a record $20.8bn in Q3', SPACE_Q3, 'Analytics Insight (Seraphim data)', 'news', '2026-10-14')],
})

# 12 ─ Quantum
themes.append({
    'id': 'quantum', 'name': 'Quantum computing', 'category': 'Frontier', 'order': 12, 'color': '#6c3483',
    'signal': 'emerging', 'heat': 70, 'conviction': 'medium', 'horizon': '3-7y', 'deploy_early': 'selective', 'deploy_growth': 'watch',
    'summary': 'Quantum hardware (photonic, trapped-ion, neutral-atom, superconducting), error correction, and quantum software and sensing.',
    'why_now': '2025 was a record $3.9bn across 125 deals (PitchBook), and growth-stage share jumped to 30% of deal value. Q1 2026 exits totalled $5.7bn and Quantinuum IPO\'d in June 2026. BlackRock ($1.7bn) and Nvidia ($1.6bn) are the largest investors.',
    'deploy_view': 'Early: selective in error-correction and enabling hardware (control systems, cryo, photonics) that wins whichever modality leads. '
                   'Growth: watch. Listed comps now exist (Quantinuum, IonQ, SPACs) and most insiders do not expect commercially useful machines before about 2030.',
    'funding': [{'period': '2025', 'stage': 'all', 'capital_usd_bn': 3.9, 'deals': 125, 'note': 'Record year', 'source': 'PitchBook via Fortune', 'url': FORTUNE_Q},
                {'period': 'Q1 2026', 'stage': 'all', 'capital_usd_bn': 1.2, 'source': 'PitchBook via Fortune', 'url': FORTUNE_Q},
                {'period': 'Q1 2026 exits', 'stage': 'all', 'capital_usd_bn': 5.7, 'note': 'Xanadu, Infleqtion, Quantum Circuits, Horizon Quantum', 'source': 'PitchBook via Fortune', 'url': FORTUNE_Q}],
    'valuation_notes': 'PsiQuantum $7bn (Series E, Sep 2025). Quantinuum $10bn pre-money (Series B), then IPO at $60/share (Jun 2026).',
    'risks': [P('Timeline to fault-tolerant advantage is uncertain (about 2030+)', 'high'), P('Modality risk: the winning qubit type is unknown', 'high'), P('SPAC-listed comps are volatile', 'medium')],
    'catalysts': [P('Logical-qubit milestones', 'high'), P('Government programmes: above $60bn committed globally; DARPA QBI', 'medium')],
    'kpis': ['Logical qubits and error rates', 'Government programme selections (DARPA QBI)', 'Listed-comp multiples'],
    'segments': [{'name': 'Hardware platforms', 'companies': [
        co('PsiQuantum', 'psiquantum', 'psiquantum.com', desc='Photonic, utility-scale quantum'), co('Quantinuum', 'quantinuum', 'quantinuum.com', desc='Trapped-ion; listed Jun 2026'),
        co('Atom Computing', 'atomcomputing', 'atom-computing.com', desc='Neutral-atom'), co('QuEra', None, 'quera.com', 'growth', 'Neutral-atom'),
        co('IQM', None, 'meetiqm.com', 'growth', 'Superconducting (Finland)'), co('Pasqal', None, 'pasqal.com', 'growth', 'Neutral-atom (France)'),
        co('Alice & Bob', None, 'alice-bob.com', 'early', 'Cat-qubit error correction (France)')]}],
    'resources': [R('BlackRock, Nvidia and Temasek are betting billions on quantum', FORTUNE_Q, 'Fortune (PitchBook data)', 'article', '2026-06-29')],
})

# 13 ─ Energy for AI
themes.append({
    'id': 'energy-for-ai', 'name': 'Power for AI: nuclear, fusion, geothermal & storage', 'category': 'Energy', 'order': 13, 'color': '#1d7a47',
    'signal': 'accelerating', 'heat': 84, 'conviction': 'high', 'horizon': '3-7y', 'deploy_early': 'overweight', 'deploy_growth': 'selective',
    'summary': 'Firm, clean power for data centres: advanced fission and SMRs, fusion, enhanced geothermal, long-duration and thermal storage, fuel supply.',
    'why_now': 'Power is the binding constraint on AI build-out. Fusion raised a record $4.48bn in the 12 months to Jul 2026 (FIA), and energy was one of five Q3 2026 sectors above $10bn (Crunchbase). Hyperscalers are signing PPAs (Microsoft–Helion, Google–CFS).',
    'deploy_view': 'Early: overweight fission micro-reactors, fuel (HALEU) and grid-edge enablers with offtake LOIs. Growth: selective. Fusion leaders are binary on science milestones; geothermal and storage have clearer near-term revenue.',
    'funding': [{'period': '12m to Jul 2026', 'stage': 'all', 'capital_usd_bn': 4.48, 'note': 'Fusion only; $14.24bn cumulative since 2021', 'source': 'Fusion Industry Association', 'url': FIA},
                {'period': 'Q3 2026', 'stage': 'all', 'capital_usd_bn': None, 'note': 'Energy one of five sectors above $10bn in Q3 venture funding', 'source': 'Crunchbase News', 'url': CB_Q3}],
    'valuation_notes': 'Oklo and Fervo trade publicly. CFS raised $1bn (Jul 2026), Helion $465M, Proxima Fusion $518M, Inertia $450M Series A, Antares $370M Series C.',
    'risks': [P('NRC licensing timelines', 'high'), P('Fusion science risk (net energy, materials)', 'high'), P('Fuel supply (HALEU)', 'medium')],
    'catalysts': [P('Hyperscaler PPAs and siting deals', 'high'), P('DOE reactor pilot programme and executive orders', 'medium')],
    'kpis': ['PPAs / offtake signed (MW)', 'Licensing milestones', 'Fusion Q>1 demonstrations', 'Cost per MWh'],
    'segments': [
        {'name': 'Advanced fission', 'companies': [
            co('Oklo', 'oklo', 'oklo.com', desc='Listed micro-reactor developer'), co('Radiant', 'radiantindustries', 'radiantnuclear.com', desc='Portable micro-reactors'),
            co('Valar Atomics', 'valaratomics', 'valaratomics.com', desc='Small modular reactors'), co('Kairos Power', 'kairospower', 'kairospower.com', desc='Molten-salt cooled reactors'),
            co('Antares', None, 'antaresindustries.com', 'growth', 'Micro-reactors; $370M Series C (Paradigm, Caffeinated)'),
            co('General Matter', 'generalmatter', 'generalmatter.com', desc='Nuclear fuel enrichment')]},
        {'name': 'Fusion', 'companies': [
            co('Commonwealth Fusion Systems', 'commonwealthfusionsystems', 'cfs.energy', desc='Tokamak; $1bn raise Jul 2026'), co('Helion', 'helionenergy', 'helionenergy.com', desc='Pulsed fusion; Microsoft PPA'),
            co('TAE Technologies', 'tae', 'tae.com', desc='Beam-driven FRC fusion'), co('Pacific Fusion', 'pacificfusion', 'pacificfusion.com', desc='Pulser-driven inertial fusion'),
            co('Proxima Fusion', None, 'proximafusion.com', 'growth', 'Stellarator (Germany); $518M, Jul 2026'), co('Inertia Enterprises', None, '', 'growth', 'Laser inertial fusion; $450M Series A')]},
        {'name': 'Geothermal & storage', 'companies': [
            co('Fervo Energy', 'fervoenergy', 'fervoenergy.com', desc='Enhanced geothermal; listed'),
            co('Antora Energy', None, 'antora.energy', 'growth', 'Thermal batteries; $550M Series C (G2VP, Eclipse)')]},
    ],
    'news': [{'date': '2026-07-31', 'headline': 'Commonwealth Fusion Systems raises $1bn; Antora $550M; Antares $370M', 'url': CB_WK_JUL31, 'source': 'Crunchbase News'}],
    'resources': [R('Record $4.48bn funding year for fusion (FIA Global Fusion Industry 2026)', FIA, 'Power Engineering', 'report', '2026-07-24'),
                  R('VC money floods into US nuclear start-ups as AI power demand explodes', 'https://oilprice.com/Energy/Energy-General/VC-Money-Floods-Into-US-Nuclear-Startups-as-AI-Power-Demand-Explodes.amp.html', 'OilPrice', 'article', '2026')],
})

# 14 ─ Reindustrialisation
themes.append({
    'id': 'advanced-manufacturing', 'name': 'Advanced manufacturing & reindustrialisation', 'category': 'Physical', 'order': 14, 'color': '#7a5a1e',
    'signal': 'accelerating', 'heat': 72, 'conviction': 'medium', 'horizon': '1-3y', 'deploy_early': 'overweight', 'deploy_growth': 'selective',
    'summary': 'AI-native factories, precision machining, additive manufacturing, inspection, and supply-chain onshoring for defence and aerospace.',
    'why_now': 'Defence demand and onshoring policy require new capacity. Hadrian raised $1.37bn in Q3 2026 (Seraphim / space data), and robotics funding (US $12.1bn YTD) increasingly targets factories.',
    'deploy_view': 'Early: overweight software-defined factories with defence and aerospace offtake. Growth: selective, as capex intensity makes these look more like PE than venture.',
    'funding': [],
    'risks': [P('Capital intensity and margins like contract manufacturing', 'high'), P('Customer concentration in defence', 'medium')],
    'catalysts': [P('Defence munitions and drone demand', 'high'), P('Tariffs and onshoring incentives', 'medium')],
    'kpis': ['Throughput per machinist', 'Contracted backlog', 'Gross margin vs legacy job shops'],
    'segments': [{'name': 'AI-native factories & tools', 'companies': [
        co('Hadrian', 'hadrian', 'hadrian.co', desc='Automated precision factories; $1.37bn raise, Q3 2026'),
        co('Lumafield', 'lumafield', 'lumafield.com', desc='CT-scan inspection'), co('Bright Machines', 'brightmachines', 'brightmachines.com', desc='Software-defined manufacturing'),
        co('Divergent', None, 'divergent3d.com', 'growth', 'AI-designed, additively manufactured structures'),
        co('Machina Labs', None, 'machinalabs.ai', 'early', 'Robotic sheet-metal forming')]}],
})

# 15 ─ Cyber
themes.append({
    'id': 'ai-security', 'name': 'AI security & cybersecurity', 'category': 'Software', 'order': 15, 'color': '#455a64',
    'signal': 'steady', 'heat': 71, 'conviction': 'medium', 'horizon': '1-3y', 'deploy_early': 'overweight', 'deploy_growth': 'selective',
    'summary': 'Securing AI agents and AI-written code, data security for AI, AI-driven SOC automation, and identity for non-human actors.',
    'why_now': 'Cyber funding was steady at $10.6bn in H1 2026 (Crunchbase), but AI-security seed is exploding: $855M across 150+ seed rounds in 2026 (Crunchbase via AI Weekly). Google\'s Wiz deal ($32bn) set the exit bar, and Cyera has raised again (about $800M, Nov 2026).',
    'deploy_view': 'Early: overweight agent security, AI-code vulnerability, and data security for LLM pipelines, where incumbents lag. Growth: selective, with consolidation via M&A as the main exit.',
    'funding': [{'period': 'H1 2026', 'stage': 'all', 'capital_usd_bn': 10.6, 'note': 'Global cyber, seed to growth', 'source': 'Crunchbase News', 'url': CB_CYBER},
                {'period': '2026 YTD', 'stage': 'early', 'capital_usd_bn': 0.855, 'deals': 150, 'note': 'AI-security seed rounds', 'source': 'AI Weekly (Crunchbase data)', 'url': 'https://aiweekly.co/alerts/ai-security-startups-pull-855m-across-150-seed-rounds-in-2026'}],
    'risks': [P('Platform bundling by CrowdStrike, Palo Alto, Microsoft', 'high'), P('Crowded seed market', 'medium')],
    'catalysts': [P('Agent adoption creates new attack surface', 'high'), P('Labs launching frontier cyber-defence (State of AI prediction)', 'medium')],
    'kpis': ['M&A multiples', 'AI-agent security budget lines', 'Time-to-detect improvements'],
    'segments': [{'name': 'Data & AI security', 'companies': [
        co('Cyera', 'cyera', 'cyera.io', desc='AI-native data security; about $800M raise, Nov 2026'), co('Wiz', 'wiz', 'wiz.io', desc='Cloud security; acquired by Google'),
        co('Chainguard', 'chainguard', 'chainguard.dev', desc='Secure software supply chain'), co('Sentra', None, 'sentra.io', 'growth', 'Data security; $150M, Nov 2026'),
        co('Abnormal Security', 'abnormalsecurity', 'abnormalsecurity.com', desc='AI email security'), co('Snyk', 'snyk', 'snyk.io', desc='Developer security')]}],
    'resources': [R('So far, 2026 is a solid year for cybersecurity startup funding', CB_CYBER, 'Crunchbase News', 'report', '2026-07')],
})

# 16 ─ Fintech & stablecoins
themes.append({
    'id': 'fintech-stablecoins', 'name': 'Fintech, stablecoins & agentic payments', 'category': 'Finance', 'order': 16, 'color': '#0e6655',
    'signal': 'steady', 'heat': 64, 'conviction': 'medium', 'horizon': '1-3y', 'deploy_early': 'selective', 'deploy_growth': 'selective',
    'summary': 'Stablecoin payment rails and treasury, AI-native finance software, neobanks, and payments for AI agents.',
    'why_now': 'Clear US stablecoin rules (GENIUS Act, 2025) brought institutional adoption. Card networks are expected to add rules for agent-initiated purchases (a State of AI 2027 prediction). Ramp $60bn and Revolut $115bn show fintech leaders compounding.',
    'deploy_view': 'Early: selective in stablecoin infrastructure for cross-border B2B and agentic payments. Growth: concentrate in proven compounders (Stripe, Ramp, Revolut) via secondaries.',
    'funding': [],
    'risks': [P('Regulatory reversals; bank partner risk', 'medium'), P('Crypto-cycle correlation', 'medium')],
    'catalysts': [P('Stablecoin B2B settlement adoption', 'high'), P('Agent commerce standards', 'medium')],
    'kpis': ['Stablecoin settlement volume', 'Take rates', 'Growth-stage secondary prices'],
    'segments': [{'name': 'Payments & finance software', 'companies': [
        co('Stripe', 'stripe', 'stripe.com', desc='Payments; owns Bridge (stablecoins)'), co('Ramp', 'ramp', 'ramp.com', desc='Spend management and AI finance'),
        co('Revolut', 'revolut', 'revolut.com', desc='Global neobank'), co('Mercury', 'mercury', 'mercury.com', desc='Business banking'), co('Plaid', 'plaid', 'plaid.com', desc='Financial data network')]},
        {'name': 'Stablecoin rails', 'companies': [co('Kast', None, '', 'early', 'Stablecoin payments', val=0.6, vdate='', rnd='$80M'),
                                                    co('Velocity', None, '', 'early', 'Stablecoin treasury for enterprises', rnd='$38M Series A (Dragonfly, FirstMark)')]}],
    'resources': [R('a16z crypto: big ideas for 2026', 'https://www.a16zcrypto.com/posts/article/big-ideas-things-excited-about-crypto-2026', 'a16z crypto', 'article', '2026'),
                  R('How VCs are backing stablecoin projects in 2026', 'https://stablecoininsider.org/how-vcs-are-backing-stablecoin-projects-in-2026/', 'Stablecoin Insider', 'article', '2026')],
})

# 17 ─ Generative media & world models
themes.append({
    'id': 'generative-media', 'name': 'Generative media & world models', 'category': 'AI', 'order': 17, 'color': '#7d3c98',
    'signal': 'accelerating', 'heat': 74, 'conviction': 'medium', 'horizon': '1-3y', 'deploy_early': 'selective', 'deploy_growth': 'watch',
    'summary': 'Video, voice and image generation, interactive world models, and AI-native creative tools.',
    'why_now': 'Higgsfield $5.4bn (Aug 2026), ElevenLabs $11bn and Kling AI\'s $3bn+ round show consumer and prosumer demand. a16z flags world models and multimodal creative tools as 2026 big ideas.',
    'deploy_view': 'Early: selective in world models for simulation, robotics data and gaming. Growth: watch, because labs ship competing video and voice models.',
    'funding': [],
    'risks': [P('Commoditisation by labs (Sora, Veo)', 'high'), P('Copyright litigation', 'medium')],
    'catalysts': [P('World models feeding robotics and simulation', 'medium'), P('Enterprise voice agents', 'medium')],
    'kpis': ['Consumer ARR and retention', 'Cost per generated minute'],
    'segments': [{'name': 'Video, voice & worlds', 'companies': [
        co('ElevenLabs', 'elevenlabs', 'elevenlabs.io', desc='Voice AI'), co('Higgsfield', 'higgsfield', 'higgsfield.ai', desc='AI video', val=5.4, vdate='2026-08', rnd='$400M Series B (DST)'),
        co('General Intuition', 'generalintuition', 'generalintuition.com', desc='World models from gameplay'),
        co('Runway', None, 'runwayml.com', 'growth', 'Video generation and world models'), co('World Labs', None, 'worldlabs.ai', 'growth', 'Spatial intelligence / 3D worlds')]}],
})

# 18 ─ Neurotech
themes.append({
    'id': 'neurotech-bci', 'name': 'Neurotech & brain-computer interfaces', 'category': 'Frontier', 'order': 18, 'color': '#a04000',
    'signal': 'emerging', 'heat': 55, 'conviction': 'low', 'horizon': '7y+', 'deploy_early': 'watch', 'deploy_growth': 'avoid',
    'summary': 'Implantable and non-invasive BCIs, neural interfaces for paralysis and communication, and neuro-modulation.',
    'why_now': 'OpenAI led a $250M seed in Merge Labs (Sam Altman co-founded; about $850M valuation, Jan 2026). Neuralink human trials are expanding.',
    'deploy_view': 'Early: watch. This is a frontier option with long regulatory paths; back only exceptional teams via specialist funds.',
    'funding': [],
    'risks': [P('Regulatory and clinical timelines', 'high'), P('Small addressable market until non-invasive breakthroughs', 'medium')],
    'catalysts': [P('FDA pivotal trials', 'medium')],
    'kpis': ['Implanted patients', 'FDA milestones', 'Bandwidth (bits per second)'],
    'segments': [{'name': 'BCI', 'companies': [
        co('Neuralink', 'neuralink', 'neuralink.com', desc='Implantable BCI'), co('Merge Labs', None, '', 'early', 'Non-invasive BCI; OpenAI-led seed', val=0.85, vdate='2026-01', rnd='$250M seed'),
        co('Synchron', None, 'synchron.com', 'early', 'Endovascular BCI'), co('Paradromics', None, 'paradromics.com', 'early', 'High-bandwidth BCI'),
        co('Science Corp', None, 'science.xyz', 'early', 'Retinal and neural interfaces')]}],
    'resources': [R('OpenAI backs Merge Labs in $250M seed', 'https://techinformed.com/openai-backs-merge-labs-in-250m-seed-round-led-by-sam-altman/', 'TechInformed', 'news', '2026-01')],
})

PROXY_AI = 'Proxy: global venture +53% YoY in Q3 2026, AI 64% of it (Crunchbase); no theme-specific comparable yet'
INPUTS = {
    'frontier-models': dict(capital_growth_x=4.0, capital_note='ESTIMATE: OpenAI + Anthropic raised $227bn in 2026 YTD (CB Insights) vs about $57bn in 2025 (OpenAI $40bn; Anthropic $3.5bn + $13bn)', exits_12m=1, mega_exit=True, exits_note='xAI merged into SpaceX (2026)'),
    'ai-infrastructure': dict(capital_growth_x=1.53, capital_note=PROXY_AI + '; data centres >$10bn in Q3', exits_12m=0, exits_note='No IPO / M&A in the mapped set in the last 12 months'),
    'ai-semiconductors': dict(capital_growth_x=1.3, capital_note='ESTIMATE: $10.7bn by 10 Jun 2026, "on track to exceed 2025" (Crunchbase); 1.3x used conservatively', exits_12m=2, exits_note='Cerebras IPO (2026); Nvidia–Groq licensing deal (Dec 2025)'),
    'ai-coding': dict(capital_growth_x=1.53, capital_note=PROXY_AI, exits_12m=1, mega_exit=True, exits_note='SpaceX to acquire Cursor for $60bn (Jun 2026)'),
    'enterprise-agents': dict(capital_growth_x=1.53, capital_note=PROXY_AI, exits_12m=0, exits_note='None in the mapped set'),
    'healthcare-ai': dict(capital_growth_x=1.53, capital_note=PROXY_AI, exits_12m=0, exits_note='None in the mapped set'),
    'ai-drug-discovery': dict(exits_12m=0, exits_note='None in the mapped set'),
    'physical-ai-robotics': dict(capital_growth_x=1.80, capital_note='H1 2026 $47.4bn vs H1 2025 $26.4bn (Crunchbase physical AI)', exits_12m=1, exits_note='Mobileye acquired Mentee Robotics (~$0.9bn)'),
    'autonomous-mobility': dict(capital_growth_x=3.6, capital_note='2026 to 15 Apr $21.4bn vs all of 2025 $5.9bn (Crunchbase; Waymo about 3/4)', exits_12m=0, exits_note='Momenta filed for a HK IPO (not yet completed)'),
    'defense-tech': dict(capital_growth_x=1.52, capital_note='2026 to 2 Jun $14.6bn vs all of 2025 $9.6bn (Crunchbase)', exits_12m=4, exits_note='Swarmer IPO; Aevex and HawkEye 360 listings; Motorola–D-Fend ($1.5bn)'),
    'space': dict(capital_growth_x=2.4, capital_note='Space investment +140% in the year to Jun 2026; record $20.8bn in Q3 (Seraphim)', exits_12m=2, mega_exit=True, exits_note='SpaceX IPO ($1.77tn, Jun 2026); HawkEye 360 listing'),
    'quantum': dict(capital_growth_x=1.23, capital_note='Q1 2026 $1.2bn vs 2025 quarterly average $0.98bn (PitchBook via Fortune)', exits_12m=5, exits_note='Xanadu, Infleqtion, Quantum Circuits, Horizon Quantum (Q1 2026, $5.7bn); Quantinuum IPO (Jun 2026)'),
    'energy-for-ai': dict(capital_growth_x=1.7, capital_note='Fusion: $4.48bn in 12m to Jul 2026 vs $2.64bn the year before (FIA)', exits_12m=2, exits_note='TAE Technologies and General Fusion Nasdaq listings (2026)'),
    'advanced-manufacturing': dict(exits_12m=0, exits_note='None in the mapped set'),
    'ai-security': dict(capital_growth_x=1.0, capital_note='H1 2026 $10.6bn, "roughly in line" with prior periods (Crunchbase)', exits_12m=2, mega_exit=True, exits_note='Google–Wiz ($32bn, closed 2026); Motorola–D-Fend ($1.5bn)'),
    'fintech-stablecoins': dict(exits_12m=0, exits_note='None in the mapped set in the last 12 months'),
    'generative-media': dict(capital_growth_x=1.53, capital_note=PROXY_AI, exits_12m=0, exits_note='None in the mapped set'),
    'neurotech-bci': dict(exits_12m=0, exits_note='None in the mapped set'),
}
for t in themes:
    t['inputs'] = INPUTS[t['id']]

GLOBAL = [
    R('Q3 2026 global venture funding: $159bn, AI 64%, record 27 billion-dollar rounds', CB_Q3, 'Crunchbase News', 'report', '2026-10',
      'Quarterly benchmark: totals by stage, sector and the largest rounds.'),
    R('PitchBook-NVCA Venture Monitor Q2 2026', 'https://pitchbook.brightspotcdn.com/3a/89/e0ff94234b8d94b7517bdcd2c331/q2-2026-pitchbook-nvca-venture-monitor.pdf', 'PitchBook / NVCA', 'report', '2026-07',
      'US deal value, valuations by stage, exits, fundraising.'),
    R('PitchBook-NVCA Venture Monitor (all editions)', 'https://nvca.org/pitchbook-nvca-venture-monitor/', 'NVCA', 'data', ''),
    R('CB Insights: State of Venture Q2 2026', 'https://www.cbinsights.com/research/report/venture-trends-q2-2026/', 'CB Insights', 'report', '2026-07'),
    R('This week in AI funding (Nov 2-6, 2026)', AIF_NOV, 'aifunding.me', 'data', '2026-11-07', '25 rounds, $9.8bn in one week.'),
    R('The week\'s biggest funding rounds (Castelion, Etched, Groq...)', CB_WK_AUG21, 'Crunchbase News', 'news', '2026-08-21'),
    R('The 20VC podcast archive', 'https://thetwentyminutevc.libsyn.com/2025', '20VC', 'podcast', '', 'Harry Stebbings interviews GPs and founders; good for real-time GP sentiment.'),
    R('Top 10 VC podcasts worth your time in 2026', 'https://valueaddvc.com/blog/top-10-vc-podcasts-actually-worth-your-time-in-2026', 'Value Add VC', 'article', '2026'),
    R('StrictlyVC newsletter', 'https://newsletter.strictlyvc.com/p/openai-has-big-hardware-ambitions', 'StrictlyVC', 'newsletter', '', 'Daily venture news digest.'),
    R('Sacra: private-company research (revenue estimates)', 'https://sacra.com/research/physical-intelligence', 'Sacra', 'data', '', 'Revenue and valuation estimates for private leaders.'),
]

PLAYBOOK = [
    {'title': 'Weekly (15 min): this tab + one deal digest', 'cadence': 'Every Monday',
     'detail': 'Read the Trends brief and heat changes here, then scan one weekly round-up (Crunchbase "week\'s biggest rounds" or aifunding.me). Flag any theme whose heat moved by 5 or more for a deeper look.',
     'links': [CB_WK_AUG21, AIF_NOV]},
    {'title': 'Quarterly benchmarks (block 2 hours when they drop)', 'cadence': 'Jan / Apr / Jul / Oct',
     'detail': 'Crunchbase quarterly global funding, PitchBook-NVCA Venture Monitor, CB Insights State of Venture; plus sector trackers: Seraphim (space), FIA (fusion, annual), Menlo enterprise AI (annual, Nov), State of AI (Oct).',
     'links': [CB_Q3, 'https://nvca.org/pitchbook-nvca-venture-monitor/', SERAPHIM_Q2, MENLO, SOAI]},
    {'title': 'GP voices: 2-3 long-form interviews a week', 'cadence': 'Commute / gym',
     'detail': '20VC, Invest Like the Best, BG2 (Gerstner/Gurley), No Priors, Dwarkesh, Acquired and the a16z podcast. Note when two or more top GPs independently name the same theme: that is the earliest consensus signal.',
     'links': ['https://thetwentyminutevc.libsyn.com/2025', 'https://valueaddvc.com/blog/top-10-vc-podcasts-actually-worth-your-time-in-2026']},
    {'title': 'Use your GPs as sensors', 'cadence': 'Each quarterly update / AGM',
     'detail': 'Ask each GP: "Which theme is your partnership most over- and under-weight, and where are you seeing the highest entry prices?" Log answers as comments on the GP in Atlas. Cross-check against their portfolio additions in the Changes tab.',
     'links': []},
    {'title': 'Specialist access for physical / frontier themes', 'cadence': 'Ongoing',
     'detail': 'Physical AI, defence, space, energy and quantum reward specialist GPs (e.g. Lux, Eclipse, DCVC, Founders Fund, 8VC, Playground) and co-invest rights. Prefer funds where you get co-invest flow in your L1 themes.',
     'links': []},
    {'title': 'Primary checks before IC', 'cadence': 'Per opportunity',
     'detail': 'Expert calls (AlphaSense / Tegus / GLG), customer references, and secondary pricing (Forge, Caplight) to test whether the theme narrative shows up in revenue. Use Shortlisted to track names you would back across rounds.',
     'links': []},
    {'title': 'Keep a thesis with kill criteria per theme', 'cadence': 'Monthly',
     'detail': 'In each theme\'s note, write the 2-3 milestones that would make you overweight, and the ones that would make you stop. Refresh the theme before an IC to check them.',
     'links': []},
]

payload = {
    'asof': ASOF,
    'brief': {
        'as_of': ASOF,
        'headline': 'AI still takes about 64% of venture dollars, but the fastest-growing new themes are physical: robotics, defence, space and power',
        'summary': 'Q3 2026 global venture reached $159bn (+53% YoY; down from Q2\'s record $212bn), with AI at $102bn (64%) and a record 27 rounds of $1bn+ (Crunchbase). '
                   'Capital is concentrating: late stage took $105bn and early stage $40.6bn. Outside software, physical AI ($47.4bn in H1), defence (a record by June), space ($20.8bn in Q3, a record) '
                   'and power for AI (fusion and fission mega-rounds) are compounding fastest. For an LP: deploy EARLY where specialists see the frontier before mega-rounds (physical AI applications, '
                   'defence autonomy, nuclear and grid, agent security, vertical agents). In GROWTH, be selective and favour category leaders bought via tenders or secondaries over primary rounds priced for perfection.',
        'highlights': [P('Q3 2026: $159bn global VC, AI $102bn (64%), 27 rounds of $1bn+ (Crunchbase)', 'high'),
                       P('Enterprise AI spend $176.8bn (5.4x); Anthropic 55% of enterprise API spend (Menlo)', 'high'),
                       P('Physical AI $47.4bn in H1 2026, almost 4x H2 2025; robotics $9.9bn in Q3 (+185% YoY)', 'high'),
                       P('Defence: record $14.6bn by June; Anduril at $61bn; Castelion at $13bn', 'medium'),
                       P('Space: record $20.8bn in Q3 after the SpaceX IPO ($1.77tn)', 'medium'),
                       P('Quantum: $5.7bn of exits in Q1 2026; Quantinuum IPO', 'medium')],
        'deploy_now': [
            {'theme': 'physical-ai-robotics', 'stage': 'early', 'why': 'Application robots with paying customers before mega-round pricing'},
            {'theme': 'defense-tech', 'stage': 'early', 'why': 'Dual-use autonomy, counter-UAS, European defence; exits now opening'},
            {'theme': 'energy-for-ai', 'stage': 'early', 'why': 'Fission, fuel and grid enablers with hyperscaler offtake'},
            {'theme': 'enterprise-agents', 'stage': 'early', 'why': 'Vertical, outcome-priced agents capturing labour budgets'},
            {'theme': 'ai-security', 'stage': 'early', 'why': 'Agent and AI-code security where incumbents lag'},
            {'theme': 'frontier-models', 'stage': 'growth', 'why': 'Leaders via tenders / primaries at sane multiples only'},
            {'theme': 'physical-ai-robotics', 'stage': 'growth', 'why': 'Robot foundation-model leaders (PI, Skild), sized carefully'},
        ],
        'watch': [{'theme': 'quantum', 'stage': 'growth', 'why': 'Listed comps volatile; 2030+ timelines'},
                  {'theme': 'ai-coding', 'stage': 'growth', 'why': 'Labs\' own agents take about 70% of coding spend'},
                  {'theme': 'neurotech-bci', 'stage': 'early', 'why': 'Frontier option; specialist funds only'}],
        'cooling': [{'theme': 'ai-infrastructure', 'stage': 'growth', 'why': 'Asset-heavy neoclouds: refinancing and depreciation risk'}],
        'market': {
            'q3_2026_global_vc_usd_bn': 159, 'q3_2026_ai_usd_bn': 102, 'q3_2026_ai_share_pct': 64, 'q3_2026_late_usd_bn': 105, 'q3_2026_early_usd_bn': 40.6,
            'q3_2026_billion_rounds': 27, 'nine_month_2026_usd_bn': 679, 'enterprise_ai_spend_2026_usd_bn': 176.8, 'hyperscaler_capex_2026_usd_bn': 733,
            'sources': [{'label': 'Crunchbase News: Q3 2026 global funding', 'url': CB_Q3}, {'label': 'Menlo Ventures: State of Enterprise AI 2026', 'url': MENLO},
                        {'label': 'State of AI Report 2026', 'url': SOAI}],
        },
        'playbook': PLAYBOOK,
    },
    'themes': themes,
    'resources': GLOBAL,
}

out = sys.argv[1]
json.dump(payload, open(out, 'w'), indent=1, ensure_ascii=False)
ids = [c['id'] for t in themes for s in t['segments'] for c in s['companies'] if c['id']]
print(len(themes), 'themes', sum(len(s['companies']) for t in themes for s in t['segments']), 'companies', len(ids), 'linked')
