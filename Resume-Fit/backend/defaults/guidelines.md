# Resume Writing Rulebook

This rulebook governs how resumes are written and scored.

It supports:
1. Fulltime resumes
2. Contract resumes

It also supports these main role types:
1. AI Engineer
2. Data Scientist
3. Software Engineer

The system must optimize for:
- ATS match
- recruiter readability
- realism and credibility
- role alignment
- job type alignment

If a change improves ATS but makes the resume sound fake, inflated, or obviously AI-generated, do not follow it blindly. Preserve realism first, then maximize ATS within that boundary.

--------------------------------------------------
SECTION 1. GLOBAL WRITING RULES
--------------------------------------------------

1.1 Natural engineering writing

Prefer direct, grounded wording.

Prefer:
- built
- designed
- implemented
- developed
- deployed
- integrated
- monitored
- optimized
- evaluated
- reviewed
- guided
- automated

Avoid generic claims such as:
- proven track record
- demonstrated ability
- deep expertise
- strong experience
- hands-on experience
- cutting-edge
- best-in-class
- world-class
- delivering business value

1.2 Bullet quality rule

A strong bullet usually shows:
object or data + action + system or tool + result

Examples:
- Built a RAG workflow that retrieved policy content from a vector index and injected grounded context into GPT responses, reducing repetitive support queries.
- Implemented monitoring for prediction drift and response quality, then triggered retraining jobs when service thresholds were breached.

Weak bullets:
- Worked on AI solutions using Python and AWS.
- Responsible for model monitoring.
- Strong experience with large language models.

1.3 Communication and grammar rules

- Keep language simple, direct, and readable
- Use only periods and commas
- Do not use semicolons
- Do not use a comma before "and"
- Avoid stacked noun phrases
- Avoid whitepaper-like wording
- Do not sound overly literary or robotic
- In most bullets, keep one main action
- In most bullets, keep one clear result
- Avoid repeating the same phrase root inside one section unless clearly necessary

1.4 Metrics rule

Metrics should appear naturally.

Useful metrics include:
- latency
- throughput
- accuracy
- user volume
- request volume
- cost reduction
- automation %
- processing time
- manual effort reduction

Do not force numbers into every bullet.

1.5 Replaceable skills rule

Not every listed skill must be equally emphasized in work bullets.

It is acceptable to:
- keep some tools only in Skills
- emphasize only the strongest or most relevant substitute in experience
- avoid forcing weak or replaceable tools into bullets

Examples:
- Python may carry the main programming emphasis without forcing Java
- LangChain may carry the agentic workflow emphasis without forcing CrewAI everywhere
- LoRA or QLoRA can support LLM optimization language without forcing every adjacent fine-tuning term

--------------------------------------------------
SECTION 2. ROLE TYPE RULES
--------------------------------------------------

2.1 AI Engineer

Focus on:
- LLM systems
- RAG
- agentic workflows
- orchestration
- APIs
- model deployment
- monitoring
- vector retrieval
- evaluation frameworks
- cloud deployment
- platform components
- secure production systems

2.2 Data Scientist

Focus on:
- experimentation
- feature engineering
- model training
- model evaluation
- statistical rigor
- business translation
- predictive modeling
- data quality
- analysis
- stakeholder reporting

2.3 Software Engineer

Focus on:
- backend systems
- APIs
- microservices
- event-driven systems
- integration layers
- platform engineering
- reliability
- scalability
- automation
- production architecture
- cloud-native services

2.4 Unknown role type fallback

If role type is not one of the supported types:
- do not force AI-specific language
- infer emphasis from the JD
- stay closer to general software, data, or AI systems wording
- avoid role-specific jargon unless the JD clearly supports it

--------------------------------------------------
SECTION 3. JOB TYPE RULES
--------------------------------------------------

3.1 Fulltime mode

Goals:
- focused
- recruiter-friendly
- concise
- selective
- realistic
- approximately 2 pages

Experience positioning:
- 5+ years

Date rules:
- Cognizant: Jun 2020 - Oct 2021
- Amrita University: Jun 2016 - May 2020

Bullet count guidance:
- Summary: 3 to 4 bullets
- Experience 1: 7 bullets
- Experience 2: 5 to 6 bullets
- Experience 3: 5 to 6 bullets
- Experience 4: use only when relevant and usually concise

Fulltime writing rules:
- Do not force every optional or replaceable JD item into bullets
- Prefer realism over maximum keyword density
- Skills can carry some adjacent or replaceable tools
- Minimize repetition
- Summary should feel selective and mature
- Do not overstate technical authority unless clearly supported
- Do not force defense, clearance, or enterprise authority language unless strongly proven

3.2 Contract mode

Goals:
- vendor-friendly
- keyword-dense
- more explicit
- more detailed
- broader in technical coverage
- usually 3 to 4 pages, and sometimes 4 to 5 if vendor submission needs that depth

Experience positioning:
- 7+ years

Date rules:
- Cognizant: Jun 2018 - Oct 2021
- Amrita University: Jun 2014 - May 2018

Bullet count guidance:
- Summary: 6 to 10 bullets
- Experience 1: 12 to 18 bullets
- Experience 2: 10 to 14 bullets
- Experience 3: 8 to 12 bullets
- Experience 4: 6 to 10 bullets

Contract writing rules:
- More repeated reinforcement of core technical skills is acceptable
- More in-depth architecture, platform, deployment, observability, and framework details are acceptable
- More direct JD mirroring is acceptable if still believable
- Resume can include more specific tools and cloud sub-services
- Long bullets are acceptable when still readable
- Strategic repetition is acceptable if it increases keyword coverage and still sounds plausible
- More low-level system details are acceptable
- More platform-specific language is acceptable
- Vendor recruiter preferences matter more than recruiter concision

3.3 Scoring tolerance by job type

Fulltime scoring should be stricter on:
- realism
- inflated wording
- over-broad claims
- tool stuffing

Contract scoring should be more tolerant of:
- longer bullets
- repeated skills
- deeper technical detail
- broader keyword coverage
- mild JD mirroring
- more explicit technology mentions
- more specific vendor-style skill density

The scorer must not penalize years-of-experience differences when they are consistent with the chosen job type.

--------------------------------------------------
SECTION 4. RESUME EXPANSION ALGORITHM
--------------------------------------------------

This algorithm is for Contract resumes and vendor-friendly submissions.

Goal:
Expand a concise resume into a denser 3 to 4 page resume without hallucinating fake experience.

Step 1. Identify core ownership areas
Extract 5 to 8 ownership areas from the JD.

Examples:
- orchestration design
- model deployment
- API integration
- vector retrieval
- CI/CD
- observability
- governance
- platform design

Step 2. Expand each ownership area into multiple bullet angles

For each ownership area, generate bullets from different angles:
- architecture decision
- implementation detail
- platform or runtime behavior
- monitoring and operations
- integration pattern
- stakeholder or delivery impact

Step 3. Split compressed bullets

If one bullet contains too many ideas, split it into 2 to 3 bullets.

Example:

Original:
- Built LangGraph multi-agent workflow deployed on AWS.

Expanded:
- Designed LangGraph-based multi-agent orchestration workflow coordinating task-specific agents for document retrieval and response generation.
- Integrated the workflow with AWS-hosted inference services and runtime controls to support scalable production execution.
- Added operational monitoring and quality checks to track agent latency, response consistency, and failure patterns.

Step 4. Expand tools into workflows

Do not list tools only.
Explain what each tool did in the system.

Bad:
- Used Bedrock, Lambda, CloudWatch, and EKS.

Better:
- Deployed runtime components on Lambda for low-latency agent execution and used CloudWatch dashboards to track invocation behavior and response latency.
- Managed EKS-based inference services for workloads requiring containerized scaling and controlled rollout behavior.

Step 5. Expand data and object detail

Name the real objects and data that flowed through the system:
- documents
- transcripts
- policies
- feature tables
- model artifacts
- vector indexes
- request payloads
- connectors
- APIs
- extracted fields

Step 6. Expand operational detail

For contract mode, add:
- latency handling
- scaling
- retries
- monitoring
- logging
- deployment flows
- model versioning
- evaluation checkpoints
- security controls
when these are believable.

Step 7. Allow controlled repetition

In Contract mode, repeating core terms is acceptable when useful for ATS.

Examples:
- RAG
- embeddings
- vector database
- orchestration
- AWS
- Azure
- CI/CD
- monitoring
- APIs

Step 8. Cap hallucination risk

Do not invent new domains, titles, or responsibilities.
Expand only what is consistent with:
- JD
- known experience
- resume_details input
- plausible system behavior

--------------------------------------------------
SECTION 5. SUMMARY RULES
--------------------------------------------------

The Summary should describe:
- expertise
- scope
- technical domain
- type of systems worked on
- level of ownership

Do not include quantified achievements in Summary.

Summary balance:
- about 60% target role or JD alignment
- about 40% systems, production actions, or business-operational context

Avoid in Summary unless extensively proven:
- national security
- defense domain
- clearance
- public trust
- fedramp
- enterprise AI authority claims
- technical thought leader claims

--------------------------------------------------
SECTION 6. SCORING EXCLUSIONS
--------------------------------------------------

The scorer must not penalize the resume for:
- summary length differences that follow the chosen job type
- experience year differences that follow the chosen job type
- date differences that follow the chosen job type
- selective emphasis of replaceable skills
- keeping granular tools mainly in Skills
- vendor-style longer bullets in Contract mode
- moderate repetition in Contract mode when it improves ATS and remains believable

--------------------------------------------------
SECTION 7. FINAL CHECK
--------------------------------------------------

Before finalizing:
1. Does it sound like a real engineer and not an AI keyword sheet
2. Does the chosen job type clearly shape depth and density
3. Does the chosen role type clearly shape emphasis
4. Are optional and replaceable skills handled naturally
5. Are the bullets readable and grounded
6. For Contract mode, does the resume show enough vendor-level technical density
7. For Fulltime mode, does the resume stay focused and selective