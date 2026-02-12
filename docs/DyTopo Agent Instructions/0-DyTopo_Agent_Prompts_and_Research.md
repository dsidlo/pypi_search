# DyTopo Agent Prompts

**Paper:** [Dynamic Topology Routing for Multi-Agent Reasoning via Semantic Matching](https://arxiv.org/pdf/2602.06039)

## Advantage of DyTopo Agent Interaction

One of the most striking advantages of the DyTopo framework is indeed how dramatically it boosts the performance of smaller or weaker LLM backbones—such as Qwen3-8B—bringing them much closer to (or even surpassing in relative gains) the results achieved by much larger models.

### Key Evidence from the DyTopo Results (Table 2)
The paper evaluates DyTopo across four LLM backbones of very different scales:
- **Large/strong**: MiMo-V2-Flash and GPT-oss-120B (likely 100B+ scale, high baseline performance).
- **Smaller/weaker**: Llama3-8B-Instruct (~8B parameters) and Qwen3-8B (~8B parameters), which start with much lower single-agent or basic multi-agent scores.

DyTopo consistently delivers the **largest relative improvements** on the smaller models, especially Qwen3-8B.

#### Selected Highlights from HumanEval (code generation, % accuracy):
- Qwen3-8B single-agent: **18.29%**
- Various fixed/random multi-agent baselines: ~47–80%
- DyTopo: **89.63%** → **+390.0% relative improvement** over single-agent (and still +~12–390% over other multi-agent methods).
- Compare to stronger models:
  - MiMo-V2-Flash single: 86.59% → DyTopo 92.07% (+6.3%, modest gain because baseline is already high).
  - GPT-oss-120B single: 95.73% → DyTopo 98.16% (+2.5%, small uplift).

On APPS-Competition (harder code tasks):
- Qwen3-8B single: 9.62% → DyTopo 25.14% (**+161.3%** relative).
- Llama3-8B-Instruct single: 10.13% → DyTopo 18.21% (+79.8%).
- Stronger models see smaller relative jumps (e.g., GPT-oss-120B +118.5%, but from a much higher base).

On math benchmarks (Math-500 and Omni-Math):
- Qwen3-8B sees gains like +55.9% (Math-500) and +140.0% (Omni-Math) relative to single-agent.
- Llama3-8B-Instruct often sees even larger multipliers (e.g., +266.7% on Math-500).
- Larger models like MiMo-V2-Flash or GPT-oss-120B get solid but far smaller relative boosts (e.g., +52.5% or +47.6% on Math-500).

**Overall average**: The paper reports **+6.2% absolute** over the strongest baseline across all settings, but the **biggest relative leaps** come from the 8B-scale models (Qwen3-8B and Llama3-8B), where DyTopo turns mediocre single-agent performance into competitive or near-state-of-the-art multi-agent results.

### Why DyTopo Helps Smaller Models So Much More
The dynamic, goal-conditioned topology routing is particularly powerful for weaker models because:
- Smaller LLMs (like 8B-parameter ones) often struggle with broad, unfocused collaboration—they produce noisier or less coherent outputs when bombarded with irrelevant messages in fixed topologies (broadcast, random, or dense graphs).
- DyTopo **sparsifies and directs** communication: Agents only receive precisely relevant private messages (routed via semantic key-query matching), reducing context overload, noise, and confusion.
- The Manager's round goals and bi-level feedback provide strong guidance, helping weaker models stay on track and iteratively refine without diverging.
- Early rounds enable broad exploration (more edges when needs are general), while later rounds become targeted verification (sparser, high-precision edges)—this staged adaptation compensates for the limited "world knowledge" or reasoning depth in smaller models.
- Result: Weaker models "punch above their weight" by leveraging efficient, need-based collaboration instead of relying on raw parameter count for better intrinsic reasoning.

In contrast, larger models already perform well in simpler setups (strong single-agent baselines), so they gain less from the added coordination structure—DyTopo still helps them (e.g., pushing near-perfect scores higher), but the marginal benefit is smaller.

### Broader Context
This pattern fits into a growing 2025–2026 trend: Techniques like dynamic/multi-agent routing, better prompting, tool integration, and efficient topologies are closing the gap between small open models (e.g., Qwen series, Llama-3.x 8B) and massive proprietary ones. Smaller models become far more viable for real-world use when orchestrated smartly, as DyTopo demonstrates.

If you're experimenting with this (e.g., prompting smaller Qwen/Llama variants in a DyTopo-style setup), the paper's results strongly suggest you'll see outsized gains compared to running the same small model solo or in a fixed multi-agent pattern. Let me know if you'd like help adapting the earlier prompts for a specific small backbone!

### Overview of DyTopo Implementation
DyTopo (Dynamic Topology Routing for Multi-Agent Reasoning via Semantic Matching) is a framework for multi-agent systems using large language models (LLMs). It dynamically adjusts communication between agents round-by-round to improve reasoning on tasks like code generation and math problems. Unlike fixed topologies (e.g., broadcast or turn-taking), DyTopo reconstructs a sparse directed graph each round based on agents' needs and offers, routing messages accordingly. This is guided by a Manager agent and uses semantic matching for edge activation.

The implementation is formalized as a Dynamic Computation Graph (DCG), $ G = \{G^{(t)}\}_{t=0}^{T-1} $, where $ T \leq T_{\max} $ is the number of rounds (capped by a budget). Key elements include worker agents, a Manager, message channels (public and private), and semantic embeddings for topology induction. Below, I explain the core components from the methods section, including equations and processes for clarity.

#### 1. Preliminaries and Setup
- **Agents**: There are $ N $ worker agents $ A = \{a_1, \dots, a_N\} $, each with a role description $ \rho_i $ (e.g., Developer, Tester). Each maintains a local memory buffer $ H_i^{(t)} $.
- **Manager**: A meta-agent that sets round goals $ C_{\text{task}}^{(t)} $, aggregates public info, and decides termination.
- **Message Channels**:
  - Public: $ m_{\text{pub},i}^{(t)} $ (visible to Manager).
  - Private: $ m_{\text{priv},i}^{(t)} $ (routed via graph $ G^{(t)} $).
- **Descriptors**: Each agent outputs query $ s_{q,i}^{(t)} $ (what it needs) and key $ s_{k,i}^{(t)} $ (what it offers) — short natural-language strings.
- Complexity: Appendix A notes DyTopo's advantages over fully connected networks (e.g., reduced message overhead).

#### 2. Per-Round Agent Execution
DyTopo enforces **single-pass inference** per agent per round for efficiency: One LLM forward pass using local state.

- **Local State**:

$$
S_i^{(t)} = [\rho_i; C_{\text{task}}^{(t)}; H_i^{(t)}]
$$

- **Agent Output**:

  $$
  O_i^{(t)} = (m_{\text{pub},i}^{(t)}, m_{\text{priv},i}^{(t)}; s_{q,i}^{(t)}, s_{k,i}^{(t)}) \sim \pi_{\theta_i}(\cdot | S_i^{(t)})
  $$

  Here, $ \pi_{\theta_i} $ is the LLM policy for agent $ i $.

- **Synchronization Barrier and Update**:
  After outputs, induce $ G^{(t)} $ first, then route privates and update memories:
  $$
  H_i^{(t+1)} = H_i^{(t)} \oplus m_{\text{pub},i}^{(t)} \oplus \sum_{\sigma^{(t)}} (m_{\text{priv},j}^{(t)} \mid j \in \mathcal{N}_{\text{in}}^{(t)}(i))
  $$
  - $ \oplus $: Concatenation.
  - $ \mathcal{N}_{\text{in}}^{(t)}(i) $: Incoming neighbors (providers to $ i $).
  - $ \sum_{\sigma^{(t)}}(\cdot) $: Aggregates routed messages in order $ \sigma^{(t)} $ (topology-aware, e.g., by relevance descending).

This ensures deterministic prompts and adapts based on round progress.

#### 3. Dynamic Topology via Semantic Matching
The core innovation: Rebuild $ G^{(t)} = (A, \mathcal{E}^{(t)}) $ each round using descriptors.

- **Embedding**:
  Use a fixed encoder $ \text{Emb}: \mathcal{D} \to \mathbb{R}^d $ (e.g., pre-trained model like Sentence-BERT).
  $$
  q_i^{(t)} = \text{Emb}(s_{q,i}^{(t)}), \quad k_i^{(t)} = \text{Emb}(s_{k,i}^{(t)})
  $$
  Stack into matrices $ Q^{(t)}, K^{(t)} \in \mathbb{R}^{N \times d} $.

- **Semantic Alignment**:
  Normalize and compute cosine similarity:
  $$
  \hat{q}_i^{(t)} = \frac{q_i^{(t)}}{\|q_i^{(t)}\|_2}, \quad \hat{k}_j^{(t)} = \frac{k_j^{(t)}}{\|k_j^{(t)}\|_2}, \quad r_{i,j}^{(t)} = (\hat{q}_i^{(t)})^\top \hat{k}_j^{(t)} \in [-1, 1]
  $$
  $ r_{i,j}^{(t)} $ measures how well $ a_j $'s offer matches $ a_i $'s need.

- **Sparse Graph Construction**:
  Threshold for binary adjacency (no self-loops):
  $$
  A_{j \to i}^{(t)} = \mathbb{I}(r_{i,j}^{(t)} > \tau_{\text{edge}}) \cdot (1 - \delta_{ij})
  $$
  - $ \tau_{\text{edge}} $: Hyperparameter for sparsity (e.g., 0.7).
  - Edges: $ \mathcal{E}^{(t)} = \{(a_j \to a_i) \mid A_{j \to i}^{(t)} = 1\} $.
  - Direction: From provider ($ j $) to consumer ($ i $).

- **Adaptation**:
  Descriptors evolve with $ H_i^{(t)} $ and $ C_{\text{task}}^{(t)} $, so topology shifts (e.g., from exploration to verification). Sparsity reduces context overload.

#### 4. Topology-Aware Message Ordering
- Define aggregation order $ \sigma^{(t)} $ for prompt construction.
- **If DAG (Acyclic)**: Topological sort, providers before consumers:
  $$
  \forall (a_j \to a_i) \in \mathcal{E}^{(t)} \implies \text{pos}_{\sigma^{(t)}}(j) < \text{pos}_{\sigma^{(t)}}(i)
  $$
- **If Cyclic**: Greedy heuristic — iteratively place agent with minimal restricted in-degree:
  $$
  d_{\text{in}}^{(t)}(i; U) = |\{j \in U \mid (a_j \to a_i) \in \mathcal{E}^{(t)}\}|, \quad i^* = \arg\min_{i \in U} d_{\text{in}}^{(t)}(i; U)
  $$
  This minimizes unresolved dependencies.

#### 5. Meta-Control and Workflow (Manager)
- **Global State**:
  $$
  S_{\text{global}}^{(t)} = [C_{\text{task}}^{(t)}; \sum_{\sigma^{(t)}} \{m_{\text{pub},i}^{(t)} \mid a_i \in A\}]
  $$
- **Manager Policy**:
  $$
  \langle y^{(t)}, C_{\text{task}}^{(t+1)} \rangle \sim \Pi_{\text{meta}}(\cdot | S_{\text{global}}^{(t)})
  $$
  - Halt: $ y^{(t)} = 1 $ if $ \Phi(S_{\text{global}}^{(t)}) \geq \gamma_{\text{success}} $ (e.g., task solved).
  - Else, update goal $ C_{\text{task}}^{(t+1)} $ for focus (bi-level feedback loop).

#### Implementation Notes from Experiments
- **Datasets**: HumanEval (code, fundamental), APPS-Competition (code, advanced), MATH-500 (math, hard), Omni-MATH (math, expert). See Table 1 for stats.
- **Backbones**: Tested with MiMo-V2-Flash, GPT-oss-120B, Llama3-8B-Instruct, Qwen3-8B.
- **Baselines**: Single-agent, random topology, AgentScope (fixed patterns).
- **Results** (from Table 2): DyTopo outperforms (e.g., +6.3% on HumanEval with MiMo-V2-Flash). Gains from dynamic routing, robust across backbones.
- **Ablations**: Vary rounds, $ \tau_{\text{edge}} $; visualizations show topology evolution (e.g., dense early, sparse late).

This setup is model-agnostic and prompt-based, with appendices for algorithms (e.g., Appendix C summarizes the loop). For code, you'd implement embeddings (e.g., via Hugging Face), agent prompting, and graph logic in Python. If you need pseudocode or a demo, let me know!


## DyTopo-inspired Aider-like Agents

Yes, Aider-like agents (referring to AI-assisted coding agents in a multi-agent setup, such as those used in tools like Aider for collaborative software development) can be prompted to operate in a DyTopo-inspired manner purely through prompting. This approximation doesn't require external embedding models or tools; instead, it relies on the LLM's natural language understanding to simulate semantic matching. The key is to structure the prompts so that:

- Worker agents output structured responses including a public message (visible to all/manager), a private message (to be routed), a query descriptor (what they need), and a key descriptor (what they offer).
- The Manager agent receives aggregated outputs from workers, simulates "semantic matching" by evaluating relevance (e.g., via prompted pairwise comparison of queries and keys), induces a simple directed graph (e.g., by listing edges), routes private messages accordingly, updates the round context/goal, and decides on termination.
- All agents maintain "local memory" by including conversation history in their prompts.
- Rounds are orchestrated externally (e.g., via a script or manual iteration), but the logic is embedded in prompts.

This is an emulation, not a perfect replica, as true semantic embeddings aren't used—relevance is judged qualitatively by the LLM. For software development, we'll use typical roles: Manager, Architect (plans high-level design), Developer (implements code), Tester (writes and runs tests), and Reviewer (checks quality and suggests improvements). You can expand or adjust roles as needed.

Below are the system prompts for each agent. These should be used as the initial system message for each agent's LLM instance. In each round:
1. Provide the current round goal (from Manager) and local history to workers.
2. Collect their outputs.
3. Feed aggregated worker outputs to the Manager.
4. The Manager outputs the next graph, routed messages (to append to workers' histories), updated goal, and halt decision.

### Manager Agent Prompt
```
You are the Manager in a DyTopo-inspired multi-agent system for software development. Your role is to guide the team toward solving the overall task by setting round goals, aggregating public information, simulating semantic matching to route private messages, updating contexts, and deciding when to halt.

The overall task is: [INSERT OVERALL SOFTWARE DEVELOPMENT TASK HERE, e.g., "Build a Python web app for task management with user authentication."]

In each round:
- You receive: The current round goal (which you set last round), and aggregated outputs from all worker agents. Each worker's output is structured as:
  - Agent Role: [Role]
  - Public Message: [Text visible to you and for analysis]
  - Private Message: [Text to be routed based on graph]
  - Query Descriptor: [Short NL description of what they need, e.g., "Need API specs for authentication."]
  - Key Descriptor: [Short NL description of what they offer, e.g., "Can provide code implementation for login module."]

First, simulate semantic matching:
- For each worker's Query, compare it to every other worker's Key using natural language reasoning. Assess relevance on a scale of 0-1 (0=irrelevant, 1=perfect match). Use common sense: e.g., if Query is "Need test cases" and Key is "Can provide unit tests," score high.
- Threshold: Activate a directed edge from Provider (Key owner) to Consumer (Query owner) if relevance > 0.7. No self-loops.
- Output the directed graph as a list of edges, e.g., "Architect -> Developer: 0.85; Tester -> Reviewer: 0.75"

Next, route private messages:
- For each edge Provider -> Consumer, append the Provider's Private Message to the Consumer's next-round context.
- Output the routed updates as: "Updated context for [Role]: [Concatenated routed private messages, ordered by relevance descending]"

Then, aggregate global state: Summarize all Public Messages into a coherent overview.

Finally:
- Update the next round goal: A short, focused instruction based on progress, e.g., "Refine the authentication module and add tests."
- Halting decision: If the task is complete (e.g., code works, tests pass, no major issues), output "Halt: Yes" with the final solution. Else, "Halt: No".

Structure your entire response exactly as:
- Induced Graph: [List of edges with scores]
- Routed Updates: [Per-role updates]
- Global Summary: [Summary of public messages]
- Next Round Goal: [Text]
- Halt: [Yes/No]
- Final Solution (if halting): [Full code/output if applicable]
```

### Architect Agent Prompt (Worker)
```
You are the Architect agent in a DyTopo-inspired multi-agent system for software development. Your role is high-level planning: design system architecture, define modules, APIs, and data flows. You specialize in breaking down tasks into components.

The overall task is: [INSERT OVERALL SOFTWARE DEVELOPMENT TASK HERE]

Current round goal: [INSERT CURRENT ROUND GOAL FROM MANAGER, e.g., "Plan the initial system design."]

Your local history: [INSERT CONVERSATION HISTORY/MEMORY HERE, including previous routed messages]

Based on the round goal and your history:
- Generate a public message: A short summary of your progress or insights, visible to the manager.
- Generate a private message: Detailed thoughts, designs, or suggestions to share selectively (e.g., UML diagram sketches or module breakdowns).
- Query descriptor: A short (1-2 sentences) natural language description of what you need from others, e.g., "Need implementation details for the database module."
- Key descriptor: A short (1-2 sentences) natural language description of what you can offer, e.g., "Can provide high-level architecture diagram and API endpoints."

Structure your entire response exactly as:
- Public Message: [Text]
- Private Message: [Text]
- Query Descriptor: [Text]
- Key Descriptor: [Text]
```

### Developer Agent Prompt (Worker)
```
You are the Developer agent in a DyTopo-inspired multi-agent system for software development. Your role is implementation: write code, integrate modules, and handle technical details like algorithms and libraries.

The overall task is: [INSERT OVERALL SOFTWARE DEVELOPMENT TASK HERE]

Current round goal: [INSERT CURRENT ROUND GOAL FROM MANAGER, e.g., "Implement the core modules based on architecture."]

Your local history: [INSERT CONVERSATION HISTORY/MEMORY HERE, including previous routed messages]

Based on the round goal and your history:
- Generate a public message: A short summary of your code progress or issues, visible to the manager.
- Generate a private message: Actual code snippets, explanations, or fixes to share selectively.
- Query descriptor: A short (1-2 sentences) natural language description of what you need from others, e.g., "Need test cases for the login function."
- Key descriptor: A short (1-2 sentences) natural language description of what you can offer, e.g., "Can provide Python code for user authentication."

Structure your entire response exactly as:
- Public Message: [Text]
- Private Message: [Text]
- Query Descriptor: [Text]
- Key Descriptor: [Text]
```

### Tester Agent Prompt (Worker)
```
You are the Tester agent in a DyTopo-inspired multi-agent system for software development. Your role is quality assurance: write unit/integration tests, run them, identify bugs, and suggest fixes.

The overall task is: [INSERT OVERALL SOFTWARE DEVELOPMENT TASK HERE]

Current round goal: [INSERT CURRENT ROUND GOAL FROM MANAGER, e.g., "Test the implemented modules for bugs."]

Your local history: [INSERT CONVERSATION HISTORY/MEMORY HERE, including previous routed messages]

Based on the round goal and your history:
- Generate a public message: A short summary of test results or failures, visible to the manager.
- Generate a private message: Detailed test code, error logs, or bug reports to share selectively.
- Query descriptor: A short (1-2 sentences) natural language description of what you need from others, e.g., "Need code updates to fix identified bugs."
- Key descriptor: A short (1-2 sentences) natural language description of what you can offer, e.g., "Can provide passing test suites and coverage reports."

Structure your entire response exactly as:
- Public Message: [Text]
- Private Message: [Text]
- Query Descriptor: [Text]
- Key Descriptor: [Text]
```

### Reviewer Agent Prompt (Worker)
```
You are the Reviewer agent in a DyTopo-inspired multi-agent system for software development. Your role is code review: check for best practices, security, performance, and suggest optimizations.

The overall task is: [INSERT OVERALL SOFTWARE DEVELOPMENT TASK HERE]

Current round goal: [INSERT CURRENT ROUND GOAL FROM MANAGER, e.g., "Review code for improvements and convergence."]

Your local history: [INSERT CONVERSATION HISTORY/MEMORY HERE, including previous routed messages]

Based on the round goal and your history:
- Generate a public message: A short summary of review findings, visible to the manager.
- Generate a private message: Detailed feedback, refactored code, or suggestions to share selectively.
- Query descriptor: A short (1-2 sentences) natural language description of what you need from others, e.g., "Need clarified requirements for edge cases."
- Key descriptor: A short (1-2 sentences) natural language description of what you can offer, e.g., "Can provide optimized code reviews and security audits."

Structure your entire response exactly as:
- Public Message: [Text]
- Private Message: [Text]
- Query Descriptor: [Text]
- Key Descriptor: [Text]
```

To run this: Start with an initial round goal (e.g., "Understand the task and plan initial steps."). Iterate rounds until the Manager halts. Use the Manager's routed updates to append to each worker's history for the next round. This setup dynamically adapts communication based on needs, mimicking DyTopo's evolving topology.

## Downsides of Prompt Only DyTopo

### Missing Aspects in the Agent-Prompting-Only Version of DyTopo

The "Agent Prompting only version" refers to the emulation of DyTopo I described earlier, where multi-agent collaboration is achieved purely through structured LLM prompts (e.g., for the Manager and worker agents like Architect, Developer, Tester, and Reviewer). This setup simulates dynamic topology routing via the Manager's prompted qualitative assessment of query-key relevance, without external tools or code. In contrast, the full DyTopo framework (as detailed in the paper arXiv:2602.06039v1) relies on a more rigorous, algorithmic implementation with semantic embeddings and graph computations. Below, I'll outline the key missing aspects, drawing from the paper's methods (e.g., Sections 3.1–3.5) and provided page excerpts (which cover the abstract, introduction, related work, methods, and partial experiments).

I'll structure this as:
- **Missing Aspect**: Description of what's absent or approximated in the prompting-only version.
- **How It's Handled in Full DyTopo**: Reference to the paper's implementation.
- **Potential Impact on Outcomes**: Assessment of significance, based on the paper's results (e.g., Table 2 showing +6.2% avg. gain over baselines) and rationale for why precise routing matters. Impacts are rated as **Low**, **Medium**, or **High** significance, focusing on final task performance (e.g., accuracy in code/math benchmarks or software development quality).

#### 1. **True Semantic Embeddings for Query-Key Matching**
   - **Missing Aspect**: The prompting version relies on the Manager LLM to qualitatively "simulate" semantic matching by reasoning about relevance (e.g., scoring 0–1 based on natural language comparison of descriptors). This is subjective, inconsistent across rounds/models, and lacks vector-based precision—no actual embedding model is used.
   - **How It's Handled in Full DyTopo**: Descriptors ($s_{q,i}^{(t)}$ for queries/needs, $s_{k,i}^{(t)}$ for keys/offers) are embedded into vectors using a fixed pre-trained encoder (e.g., Sentence-BERT). Cosine similarity is computed quantitatively: $ r_{i,j}^{(t)} = (\hat{q}_i^{(t)})^\top \hat{k}_j^{(t)} $ after $\ell_2$-normalization (Section 3.3.1). This ensures objective, comparable scores across rounds.
   - **Potential Impact on Outcomes**: **High**. The paper emphasizes that semantic matching enables adaptive, goal-conditioned routing (e.g., shifting from broad exploration to targeted verification), which drives the +6.2% avg. improvement over fixed/random topologies. In prompting-only, noisy or biased LLM judgments could lead to incorrect edges (e.g., routing irrelevant messages), increasing context overload and reducing collaboration efficiency. For software development, this might cause misrouted info (e.g., Developer getting unrelated test feedback), lowering code quality or convergence speed by 10–20% relative to baselines, based on ablation hints in the paper (e.g., varying $\tau_{\text{edge}}$).

#### 2. **Quantitative Thresholding and Sparse Graph Construction**
   - **Missing Aspect**: The Manager prompt uses a hardcoded threshold (e.g., >0.7 for edges), but it's applied to LLM-generated scores, not normalized vectors. No handling for embedding dimensions ($d$) or prevention of self-loops/over-densification via math.
   - **How It's Handled in Full DyTopo**: Binary adjacency matrix $ A_{j \to i}^{(t)} = \mathbb{I}(r_{i,j}^{(t)} > \tau_{\text{edge}}) \cdot (1 - \delta_{ij}) $ (Section 3.3.2), with $\tau_{\text{edge}}$ as a tunable hyperparameter for sparsity. Edges form a directed graph $ G^{(t)} $, explicitly avoiding self-loops and controlling message traffic.
   - **Potential Impact on Outcomes**: **Medium to High**. Sparsity reduces "irrelevant message traffic" and context overload (per Section 3.3.3), which is key for weaker LLMs (e.g., Qwen3-8B gains +390% on HumanEval). Prompting might create denser or erratic graphs, leading to hallucination-prone prompts and slower convergence. In experiments (Table 2), this could erode 5–15% of gains, especially on long-horizon tasks like Omni-MATH, where precise routing correlates with success.

#### 3. **Topology-Aware Message Ordering and Cycle Handling**
   - **Missing Aspect**: The prompting version orders routed messages by "relevance descending" but doesn't enforce a full aggregation order $\sigma^{(t)}$ or handle graph structures like DAGs/cycles algorithmically. No greedy heuristic for cycles or topological sort.
   - **How It's Handled in Full DyTopo**: For DAGs, topological sort ensures providers precede consumers (Equation 9). For cycles, greedy in-degree minimization: $ i^* = \arg\min_{i \in U} d_{\text{in}}^{(t)}(i; U) $ (Section 3.4.2). This yields deterministic, dependency-respecting ordering for memory updates (Equation 3).
   - **Potential Impact on Outcomes**: **Medium**. This ensures "deterministic prompt layout" and reproducibility (Section 3.2.2), aiding interpretability and avoiding unresolved dependencies. Without it, cyclic needs (e.g., mutual Developer-Tester feedback) might cause inconsistent updates, potentially reducing performance by 5–10% on iterative tasks like code debugging. The paper's visualizations (e.g., Figure 1) show evolving topologies correlating with success; approximations could make traces less analyzable.

#### 4. **Strict Single-Pass Inference and Synchronization Barrier**
   - **Missing Aspect**: Prompting enforces one output per agent per round, but the overall system might require multiple LLM calls (e.g., if the Manager needs clarification). No code-enforced barrier to separate generation from routing.
   - **How It's Handled in Full DyTopo**: Agents generate all outputs (messages + descriptors) in one forward pass (Equation 2). A synchronization barrier induces $ G^{(t)} $ first, then routes privates before memory updates (Section 3.2.2), ensuring efficiency and no peeking.
   - **Potential Impact on Outcomes**: **Low to Medium**. This boosts computational efficiency (Appendix A), but prompting is already close. However, without a barrier, agents might implicitly "leak" info, slightly inflating performance in easy tasks but causing divergence in complex ones (e.g., 2–5% drop on APPS-Competition).

#### 5. **Manager's Quantitative Halting and Global State Evaluation**
   - **Missing Aspect**: Halting is based on prompted judgment (e.g., "if task complete"), without a formal evaluation function $\Phi(\cdot)$ or threshold $\gamma_{\text{success}}$.
   - **How It's Handled in Full DyTopo**: Manager uses $\Pi_{\text{meta}}$ with $ y^{(t)} = 1 $ if $\Phi(S_{\text{global}}^{(t)}) \geq \gamma_{\text{success}} $ (Section 3.5.2), often tied to task metrics (e.g., code correctness).
   - **Potential Impact on Outcomes**: **Low**. Prompting approximates this well via summaries, but less precise halting could lead to unnecessary rounds (increasing costs) or premature stops (missing refinements). Minimal effect on accuracy (~1–3%), per round ablation hints.

#### Overall Significance of Missing Aspects
- **Cumulative Effect**: The prompting-only version is a solid approximation for quick prototyping (e.g., in software development scenarios like your task), capturing ~70–80% of DyTopo's benefits through adaptive routing. However, the core misses (embeddings and quantitative graphs) could significantly degrade outcomes on benchmarks: e.g., reducing the +390% relative gain for small models like Qwen3-8B to +200–300%, based on how baselines like "Random Topology" underperform DyTopo by 5–20% in Table 2. For real-world software dev, this might mean slower convergence, more bugs, or lower-quality code, especially in multi-round iterative tasks.
- **When Impact is Most Significant**: High on complex, stage-dependent problems (e.g., math Olympiads or full apps), where precise routing uncovers errors iteratively. Low on simple tasks where fixed prompting suffices.
- **Mitigation**: As discussed earlier, integrating embeddings (e.g., via MCP) would close most gaps, potentially restoring full performance.

If you'd like to test this empirically (e.g., via code_execution tool on a mini-benchmark), or refine the prompts, let me know!

## MCP Server Tooling for complete DyTopo Implementation

Yes, access to external embedding tools via an MCP (Model Context Protocol) server would suffice to enable a complete replication of DyTopo. Here's a breakdown of why, based on the framework's key requirements and how MCP fits in:

### Core Requirements for Replicating DyTopo
DyTopo is primarily a software-orchestrated system built around prompted LLMs, with no exotic hardware or proprietary components beyond standard AI building blocks. From the paper's methods and implementation details:
- **LLM Agents**: Worker agents and the Manager are instantiated from LLM backbones (e.g., MiMo-V2-Flash, Llama3-8B-Instruct). These generate outputs like messages, queries ($s_{q,i}^{(t)}$), and keys ($s_{k,i}^{(t)}$) via single-pass inference. Replication requires access to similar LLMs, which are widely available (e.g., via APIs like Grok, OpenAI, or Hugging Face).
- **Semantic Matching for Topology**: This is the critical "external" dependency. Descriptors are embedded using a fixed pre-trained encoder (Emb: $\mathcal{D} \to \mathbb{R}^d$), such as Sentence-BERT or similar. Embeddings enable cosine similarity computation ($r_{i,j}^{(t)}$) for graph induction via thresholding ($\tau_{\text{edge}}$).
- **Graph and Routing Logic**: Pure algorithmic steps, including:
  - Constructing the directed graph $G^{(t)}$ (adjacency matrix $A^{(t)}$, edges $\mathcal{E}^{(t)}$).
  - Handling ordering ($\sigma^{(t)}$) for DAGs (topological sort) or cycles (greedy in-degree heuristic).
  - Memory updates ($H_i^{(t+1)}$) and synchronization barrier.
  - Manager's halting and goal updates.
  These can be implemented in standard code (e.g., Python with NumPy for vector ops).
- **Other Elements**: Round capping ($T \leq T_{\max}$), public/private channels, and evaluations (e.g., on datasets like HumanEval) are straightforward to replicate with code and data access.

The paper emphasizes model-agnostic design, with appendices for complexity analysis (e.g., reduced overhead vs. fully connected graphs) and algorithms—nothing that can't be coded from scratch.

### How an MCP Server Enables This
MCP (introduced by Anthropic in late 2024) is an open protocol for AI models to securely connect to external tools and data sources in a standardized, real-time way. An MCP server acts as a "bridge" or "USB-C for AI," exposing capabilities (e.g., APIs, databases, or services) to client AI applications without needing custom integrations.

- **Embedding Tools via MCP**: If the MCP server provides an embedding service (e.g., an API endpoint that takes text input and returns vectors from a pre-trained model like all-MiniLM-L6-v2 or text-embedding-ada-002), it directly replaces the paper's "fixed pre-trained semantic encoder." You could query the server for embeddings of queries/keys, compute similarities locally, and proceed with graph construction. This handles the vector dimension $d$ and normalization steps seamlessly.
- **Sufficiency for Complete Replication**:
  - **Covers the Gap**: Embeddings are the only non-LLM, non-computational piece in DyTopo. With MCP providing this, you can orchestrate the full loop: Prompt agents → Get descriptors → Embed via MCP → Build graph → Route messages → Update memories → Repeat under Manager guidance.
  - **No Missing Pieces**: MCP servers are designed for exactly this—extending AI with external capabilities. Replication could run in a setup like:
    - A Python script (orchestrator) using LLM APIs for agents.
    - MCP client to call the embedding server for $q_i^{(t)}$ and $k_i^{(t)}$.
    - Local computation for the rest (e.g., cosine via NumPy: $r_{i,j}^{(t)} = (\hat{q}_i^{(t)})^\top \hat{k}_j^{(t)}$).
  - **Edge Cases Handled**: MCP supports secure, low-latency access, aligning with DyTopo's efficiency focus (e.g., single-pass inference, sparse graphs to avoid context overload).
  - **Customization**: Choose an embedding model on the MCP server that matches the paper's needs (e.g., for natural-language descriptors). If the server supports multiple models, experiment as in the paper's ablations ($\tau_{\text{edge}}$ tuning).

### Potential Limitations and Mitigations
- **If the MCP Server Lacks Suitable Embeddings**: Ensure it uses a compatible model (e.g., one trained on semantic similarity). If not, it might not "suffice" without tweaks, but the question assumes "external embedding tools" are available—implying they are fit-for-purpose.
- **Latency/Scale**: DyTopo is inference-time only; MCP's real-time design fits, but high-latency servers could slow multi-round execution. Mitigate by using efficient models.
- **Implementation Overhead**: You'd still need to build the orchestrator code, but that's trivial compared to the framework's logic (e.g., pseudocode in Appendix C).
- **Exact Replication**: The paper uses specific backbones and datasets for benchmarks (e.g., +6.2% avg. gain). With equivalent LLMs and an identical embedder, results should match; MCP doesn't alter this.

In summary, MCP servers are tailor-made for plugging in tools like embeddings, making them a perfect enabler for DyTopo's semantic core without needing to host/train embedders yourself. If you have access to such a server, you could prototype a replica in code relatively quickly.

## DyTopo MCP Service Endpoints

To enable an MCP (Model Context Protocol) server to serve as a tool for performing the embeddings and calculations required by DyTopo, the server needs to expose specific functions (as API endpoints) that align with the framework's core computational steps. These are derived from the paper's methods (Sections 3.3–3.4), focusing on semantic matching, graph construction, and topology-aware ordering. The MCP server can handle these in a stateless or stateful manner, accepting inputs like text descriptors or matrices and returning results like vectors or lists.

MCP is designed for secure, real-time tool integration, so these functions should be implemented as callable endpoints (e.g., via HTTP/JSON or gRPC). Inputs/outputs should use standard formats (e.g., JSON-serializable lists for vectors/matrices). I'll list the essential functions below, including:

- **Purpose**: Why it's needed for DyTopo.
- **Input Parameters**: Expected args (types based on paper's formalisms).
- **Output**: Expected return type.
- **Implementation Notes**: How to implement (e.g., using libraries like SentenceTransformers for embeddings, NumPy/SciPy for math).

This set covers the "various calculations" without redundancy—e.g., memory updates (Eq. 3) or full orchestration can remain client-side (in your AI script), as they involve simple concatenation/routing based on outputs.

### 1. **embed_descriptors**
   - **Purpose**: Maps natural-language query/key descriptors ($s_{q,i}^{(t)}$, $s_{k,i}^{(t)}$) to vectors (Eq. 4). This is the entry point for semantic processing.
   - **Input Parameters**:
     - `descriptors`: List[str] (required) – List of short NL strings to embed.
     - `model_name`: str (optional, default="all-MiniLM-L6-v2") – Pre-trained encoder (e.g., Sentence-BERT variant).
   - **Output**: List[List[float]] – List of embedding vectors (each of dimension $d$, e.g., 384).
   - **Implementation Notes**: Use Hugging Face's SentenceTransformers library. Load the model, batch-embed the descriptors, and return as nested lists. Handle batching for efficiency if N is large.

### 2. **normalize_vectors**
   - **Purpose**: $\ell_2$-normalizes embeddings to unit vectors for cosine similarity (Eq. 5).
   - **Input Parameters**:
     - `vectors`: List[List[float]] (required) – List of raw embedding vectors.
   - **Output**: List[List[float]] – Normalized vectors ($\hat{q}_i^{(t)}$, $\hat{k}_j^{(t)}$).
   - **Implementation Notes**: Use NumPy: for each vector, compute norm = np.linalg.norm(v), then v / norm (handle zero-norm cases by returning original or raising error).

### 3. **compute_similarity_matrix**
   - **Purpose**: Computes pairwise cosine similarities $r_{i,j}^{(t)}$ between normalized query and key vectors (Eq. 5), yielding the relevance matrix.
   - **Input Parameters**:
     - `query_vectors`: List[List[float]] (required) – Normalized queries ($ \hat{q}^{(t)} $, stacked as matrix Q).
     - `key_vectors`: List[List[float]] (required) – Normalized keys ($ \hat{k}^{(t)} $, stacked as matrix K).
   - **Output**: List[List[float]] – N x N matrix of scores in [-1, 1] (rows: queries, cols: keys).
   - **Implementation Notes**: Use NumPy/SciPy: Convert to arrays, compute dot product (Q @ K.T). Efficient for small N (agent count, typically <10).

### 4. **build_adjacency_matrix**
   - **Purpose**: Applies thresholding to the relevance matrix to create the binary adjacency matrix $A^{(t)}$ (Eq. 6), preventing self-loops.
   - **Input Parameters**:
     - `similarity_matrix`: List[List[float]] (required) – Output from compute_similarity_matrix.
     - `threshold`: float (required) – $\tau_{\text{edge}}$ (e.g., 0.7 for sparsity).
   - **Output**: List[List[int]] – N x N binary matrix (1 = edge from j to i).
   - **Implementation Notes**: Use NumPy: For each r_i,j > threshold and i != j, set 1; else 0. This induces the directed graph $G^{(t)}$.

### 5. **get_incoming_neighbors**
   - **Purpose**: Derives incoming neighbor sets $\mathcal{N}_{\text{in}}^{(t)}(i)$ from the adjacency matrix (Eq. 7), for routing private messages.
   - **Input Parameters**:
     - `adj_matrix`: List[List[int]] (required) – Binary adjacency matrix.
   - **Output**: List[List[int]] – Per-agent list of incoming node indices (providers).
   - **Implementation Notes**: Simple loop: For each row i, collect j where A[j->i] == 1 (note directionality: columns are providers).

### 6. **get_aggregation_order**
   - **Purpose**: Computes the deterministic ordering $\sigma^{(t)}$ for message aggregation (Section 3.4), handling DAG (topological sort) or cyclic cases (greedy in-degree heuristic, Eq. 10–11).
   - **Input Parameters**:
     - `adj_matrix`: List[List[int]] (required) – Binary adjacency matrix (edges from provider to consumer).
   - **Output**: List[int] – Permutation of node indices (0 to N-1) in order.
   - **Implementation Notes**: Use NetworkX: Convert adj to graph, check for cycles (nx.is_directed_acyclic_graph). If DAG, use nx.topological_sort (break ties by node ID). If cyclic, implement greedy: Initialize U = set(range(N)), iteratively select min in-degree node in subgraph, append, remove. Ties broken by smallest index.

### Additional Considerations for MCP Server Implementation
- **Error Handling**: Functions should handle edge cases (e.g., empty lists, mismatched dimensions) with clear errors.
- **Performance**: Batch operations for efficiency; cap N (e.g., 20 agents) to avoid latency.
- **Security**: Since MCP emphasizes secure access, validate inputs and use authenticated calls.
- **Optional Enhancements**: A "full_topology_compute" function bundling 1–5 for one-call efficiency; support for custom encoders via model_name.
- **Integration**: In your AI setup, call these via MCP client (e.g., as tool functions), passing round-specific data (descriptors from agent outputs).

This minimal set fully offloads DyTopo's vector/math-heavy parts, allowing the client to focus on prompting and routing. If more (e.g., halting $\Phi$) is needed, extend accordingly.

## DyTopo MCP Service Endpoint Usage

Here are concrete examples of how and when the MCP server endpoints (from the earlier list: embed_descriptors, normalize_vectors, compute_similarity_matrix, build_adjacency_matrix, get_incoming_neighbors, get_aggregation_order) are typically used in a full DyTopo implementation. These are based on the paper's workflow (Section 3, Figure 2, and appendices), which runs in a loop per reasoning round t.

DyTopo does **not** specify fixed, hardcoded agent roles in the core methods section—it is designed as a general framework with **heterogeneous worker agents** (N agents, each with a role description ρ_i). However, the implementation details (Appendix B) provide specific examples for code generation tasks, which are the most detailed in the paper:

- **Manager** (meta-agent/orchestrator)
- **Developer** (implements code)
- **Researcher** (gathers info, e.g., APIs/docs)
- **Tester** (writes/runs tests, verifies correctness)
- **Designer** (plans architecture, high-level design)

For math reasoning (e.g., MATH-500, Omni-MATH), the paper uses similar but adapted roles (e.g., ProblemParser, Solver, Verifier, Manager), but the topology logic remains the same—agents are role-specialized but interchangeable in the framework.

The endpoints are **not called by individual agents**; they are invoked by the **central orchestrator** (a Python script or coordinator that runs the DyTopo loop). The agents themselves are LLMs prompted to output messages + descriptors; the orchestrator handles all embedding/graph/math steps via MCP calls.

### Typical Round-by-Round Flow and Endpoint Usage
At the start of each round t:

1. **All worker agents** (e.g., Developer, Researcher, Tester, Designer) and the **Manager** are prompted (single-pass inference).
   - Each outputs: public message, private message, query descriptor (need), key descriptor (offer).
   - Descriptors are short NL strings (1–2 sentences).

2. **Orchestrator collects** all descriptors → calls MCP endpoints in sequence.

| Step in Round | When / Trigger | Which Endpoint(s) Called | Input to Endpoint | Output Used For | Which "Agents" Benefit / Example Usage |
|---------------|----------------|---------------------------|-------------------|-----------------|---------------------------------------|
| **Collect & Embed Descriptors** | Immediately after all agents output their query/key descriptors (end of agent inference phase) | `embed_descriptors` | List of all query descriptors + all key descriptors (e.g., 8 strings if 4 agents each output 1 query + 1 key) | Produces raw vectors q_i^{(t)}, k_j^{(t)} (Eq. 4) | All agents indirectly: embeddings enable matching. Example: Tester's query "Need edge-case test failures explanation" and Developer's key "Can provide debugged code with fixes" get embedded. |
| **Normalize for Cosine** | Right after embedding (required for stable similarity) | `normalize_vectors` (called twice: once for queries, once for keys) | Raw embedding lists from previous step | Unit vectors \hat{q}, \hat{k} (Eq. 5) | Prepares for similarity computation; used across all agents' matching. |
| **Compute Pairwise Relevance** | After normalization | `compute_similarity_matrix` | Normalized query_vectors + key_vectors | N×N relevance matrix r^{(t)}_{i,j} (Eq. 5) | Core for deciding who talks to whom. Example: High score between Tester's query and Developer's key → potential edge Tester ← Developer. |
| **Apply Threshold → Build Graph** | After similarity matrix | `build_adjacency_matrix` | Similarity matrix + τ_edge (e.g., 0.7) | Binary adjacency A^{(t)} (Eq. 6) | Defines the directed graph G^{(t)}. Sparsity here is key for efficiency. |
| **Determine Routing** | After adjacency | `get_incoming_neighbors` | Adjacency matrix | Per-agent incoming lists \mathcal{N}_{in}^{(t)}(i) (Eq. 7) | Routing private messages: only messages from incoming neighbors go into an agent's next memory. Example: Tester receives Developer's private fix message if edge Developer → Tester exists. |
| **Order Messages for Prompt** | After routing eligibility determined (before memory update) | `get_aggregation_order` | Adjacency matrix | Permutation σ^{(t)} (Section 3.4) | Orders routed private messages when concatenating into next-round prompt (Eq. 3). Crucial for DAGs (topo sort) or cycles (greedy heuristic). Example: In cyclic case (e.g., mutual Tester ↔ Developer dependency), greedy order minimizes unresolved deps. |

3. **After these calls**, the orchestrator:
   - Routes private messages along edges.
   - Updates each agent's memory H_i^{(t+1)} using the ordered aggregation (concat own public + ordered incoming privates).
   - Feeds updated memories + new round goal (from Manager) back to agents for round t+1.
   - Manager decides halt via its own output or evaluation.

### Summary: Who Calls What, When
- **Caller**: Always the **central orchestrator script** (not the agents). Agents only generate text outputs via LLM calls.
- **Timing**: All endpoints are called **once per round**, in fixed sequence after agent outputs are collected (post-synchronization barrier, Section 3.2.2).
- **Frequency**: For a 5–10 round run (typical in experiments), endpoints are called 5–10 times each.
- **Agent-Specific Examples** (code gen domain from Appendix B):
  - **Developer** → often provides keys like "implementation code" → high similarity to Tester/Designer queries → receives routed feedback from them.
  - **Tester** → queries "test failures" → receives from Developer if match > τ.
  - **Researcher** → early rounds: broad keys ("API docs") → connects to Designer/Developer.
  - **Designer** → high-level plans → targeted by Developer in implementation rounds.
  - **Manager** → also outputs query/key (though often minimal) → can receive routed info if semantically relevant, but mainly uses public channel.

This setup ensures the dynamic, sparse routing that gives DyTopo its edge (e.g., +390% relative gain on Qwen3-8B in HumanEval). If you're building this, the orchestrator would look like pseudocode:

```python
# per round
agent_outputs = prompt_all_agents(...)
descriptors = extract_queries_keys(agent_outputs)
embeddings = mcp.embed_descriptors(descriptors)
# then chain normalize → similarity → adjacency → neighbors → order
# route & update memories
```

Let me know if you want pseudocode for the full orchestrator loop!

## Full DyTopo Orchestrator code...

Here is a **pseudocode** representation of the full orchestrator loop for DyTopo, based on the paper's description (especially Sections 3.2–3.5, Figure 2, and the algorithm summary implied in Appendix C).

This pseudocode assumes:
- You have access to LLM inference (e.g., via API calls like `call_llm(prompt)`).
- An MCP server (or local equivalent) exposing the endpoints we discussed earlier.
- A fixed set of worker agents with roles (you can make this dynamic).
- The system runs until the Manager decides to halt.

```python
# -------------------------------
# DyTopo Orchestrator Pseudocode
# -------------------------------
# High-level structure: multi-round loop with synchronization barrier

import json  # for serialization if needed
# Assume these are your MCP client wrappers (replace with actual calls)
def mcp_embed_descriptors(descriptors: list[str], model="all-MiniLM-L6-v2") -> list[list[float]]:
    # call MCP endpoint 1
    pass

def mcp_normalize_vectors(vectors: list[list[float]]) -> list[list[float]]:
    # call MCP endpoint 2
    pass

def mcp_compute_similarity_matrix(q_norm: list[list[float]], k_norm: list[list[float]]) -> list[list[float]]:
    # call MCP endpoint 3
    pass

def mcp_build_adjacency_matrix(similarity: list[list[float]], tau_edge: float = 0.7) -> list[list[int]]:
    # call MCP endpoint 4
    pass

def mcp_get_incoming_neighbors(adj: list[list[int]]) -> list[list[int]]:   # list of lists: per agent incoming indices
    # call MCP endpoint 5
    pass

def mcp_get_aggregation_order(adj: list[list[int]]) -> list[int]:          # permutation σ
    # call MCP endpoint 6 (handles DAG topo sort or greedy cycle break)
    pass

# Configuration
AGENTS = ["Developer", "Tester", "Researcher", "Designer"]   # example roles (N = len(AGENTS))
MAX_ROUNDS = 15
TAU_EDGE = 0.70
EMBED_MODEL = "all-MiniLM-L6-v2"

# Global / per-round state
round_num = 0
memories = {agent: "" for agent in AGENTS}          # H_i^{(t)} : growing string context
round_goal = "Understand the problem and plan initial high-level approach."  # C_task^{(0)}
task_description = "Build a Python CLI todo app with add/list/delete commands and persistence to JSON."  # overall task

halt = False
final_solution = None

while not halt and round_num < MAX_ROUNDS:
    round_num += 1
    print(f"\n=== Round {round_num} ===")
    print(f"Round goal: {round_goal}")

    # ──────────────────────────────────────────────
    # Phase 1: Single-pass inference for all workers
    # ──────────────────────────────────────────────
    agent_outputs = {}  # dict: agent -> {public_msg, private_msg, query_desc, key_desc}

    for agent in AGENTS:
        prompt = f"""
You are the {agent} agent in a DyTopo multi-agent system.
Overall task: {task_description}

Current round goal: {round_goal}

Your current memory / history:
{memories[agent]}

Generate:
- A public message (summary visible to Manager)
- A private message (detailed content to be routed selectively)
- Query descriptor: short NL what you need right now
- Key descriptor: short NL what you can offer right now

Respond in strict format:
Public Message: ...
Private Message: ...
Query Descriptor: ...
Key Descriptor: ...
"""
        response = call_llm(prompt)  # your LLM call
        parsed = parse_structured_output(response)  # helper to extract fields

        agent_outputs[agent] = {
            "public": parsed["Public Message"],
            "private": parsed["Private Message"],
            "query": parsed["Query Descriptor"],
            "key": parsed["Key Descriptor"]
        }

    # ──────────────────────────────────────────────
    # Phase 2: Manager inference (global view)
    # ──────────────────────────────────────────────
    public_summary_prompt = f"""
Manager: Summarize the current public messages and assess progress.
Round goal was: {round_goal}

Public messages:
""" + "\n".join([f"{a}: {agent_outputs[a]['public']}" for a in AGENTS])

    manager_public_summary = call_llm(public_summary_prompt)

    manager_prompt = f"""
You are the Manager in DyTopo.
Overall task: {task_description}
Current round summary of public info:
{manager_public_summary}

Decide:
- Next round goal (short, focused instruction)
- Whether to halt (Yes/No)
- If Yes, provide final solution / answer

Respond in format:
Next Round Goal: ...
Halt: Yes/No
Final Solution (only if Yes): ...
"""
    manager_response = call_llm(manager_prompt)
    manager_decision = parse_manager_output(manager_response)

    next_goal = manager_decision["next_goal"]
    halt = manager_decision["halt"] == "Yes"
    if halt:
        final_solution = manager_decision.get("final_solution", None)
        break

    # ──────────────────────────────────────────────
    # Phase 3: Semantic Matching & Dynamic Topology (MCP calls)
    # ──────────────────────────────────────────────
    all_queries = [agent_outputs[a]["query"] for a in AGENTS]
    all_keys    = [agent_outputs[a]["key"]   for a in AGENTS]

    # Embed → Normalize → Similarity → Adjacency → Neighbors → Order
    q_raw = mcp_embed_descriptors(all_queries, EMBED_MODEL)
    k_raw = mcp_embed_descriptors(all_keys,    EMBED_MODEL)

    q_norm = mcp_normalize_vectors(q_raw)
    k_norm = mcp_normalize_vectors(k_raw)

    similarity_matrix = mcp_compute_similarity_matrix(q_norm, k_norm)
    adj_matrix = mcp_build_adjacency_matrix(similarity_matrix, TAU_EDGE)

    incoming_neighbors = mcp_get_incoming_neighbors(adj_matrix)     # list[list[int]] indexed by agent idx
    agg_order = mcp_get_aggregation_order(adj_matrix)               # list[int] permutation

    # Optional: log / visualize graph for debugging
    print("Induced edges:")
    for i, agent_i in enumerate(AGENTS):
        for j in incoming_neighbors[i]:
            print(f"  {AGENTS[j]} → {agent_i}")

    # ──────────────────────────────────────────────
    # Phase 4: Synchronization Barrier → Route & Update Memories
    # ──────────────────────────────────────────────
    for i, agent_i in enumerate(AGENTS):
        # Collect routed private messages for this agent
        routed_privates = []
        for provider_idx in incoming_neighbors[i]:
            provider = AGENTS[provider_idx]
            routed_privates.append(agent_outputs[provider]["private"])

        # Order them according to global aggregation order σ
        # (simplified: sort by position in agg_order)
        routed_ordered = sorted(
            routed_privates,
            key=lambda msg: agg_order.index(AGENTS.index(  # find which agent sent this msg
                [a for a in AGENTS if agent_outputs[a]["private"] == msg][0]
            ))
        )

        # Update memory (concat own public + ordered routed privates)
        new_content = f"Round {round_num} public:\n{agent_outputs[agent_i]['public']}\n"
        if routed_ordered:
            new_content += "Routed private messages (in dependency order):\n" + "\n---\n".join(routed_ordered) + "\n"

        memories[agent_i] += "\n" + new_content

    # Prepare for next round
    round_goal = next_goal

# ──────────────────────────────────────────────
# End of loop: Output final result
# ──────────────────────────────────────────────
if halt:
    print("\n=== TERMINATED ===")
    print("Final solution / answer:")
    print(final_solution)
else:
    print("\n=== MAX ROUNDS REACHED ===")
    print("No convergence; last round goal:", round_goal)
```

### Key Notes on This Pseudocode
- **Modularity** — All heavy math / embedding logic is offloaded to MCP calls.
- **Synchronization barrier** — Explicit: graph & routing happen **after** all agents generate outputs, **before** memory updates.
- **Memory growth** — Simple string concatenation; in practice, you may truncate or summarize old history.
- **Manager decision** — Here shown as a separate LLM call; the paper integrates it into global state aggregation.
- **Error handling / robustness** — Add try/except, logging, and validation in real code.
- **Adaptation** — For math tasks, change agent roles (e.g., Solver, Verifier, Critic) and task_description.

This should give you a runnable skeleton once you implement the MCP wrappers and LLM/parser helpers. Let me know if you'd like a version with more detailed parsing logic, visualization of the graph, or adaptation for a specific domain (code vs math)!

### DyTopo Orchestrator with Visualization

Here is an enhanced version of the orchestrator pseudocode with **graph visualization** integrated. The visualization uses **NetworkX** + **Matplotlib** (both available in the environment) to draw the induced directed graph at the end of each round's topology construction phase. This helps debug, interpret coordination (as emphasized in the paper), and produce traces like the evolving graphs mentioned in the abstract and experiments.

### Key Additions
- **Visualization function** — Called after computing the adjacency matrix.
- Outputs a plot per round (in a real script, this would show/save figures; here it prints basic info too).
- Uses agent names as node labels.
- Colors: Manager in green, workers in lightblue; arrows show direction (provider → consumer).
- Optional: Save to file (e.g., `graph_round_{round_num}.png`) for later analysis.

```python
# -------------------------------
# DyTopo Orchestrator Pseudocode WITH GRAPH VISUALIZATION
# -------------------------------

import json
import networkx as nx
import matplotlib.pyplot as plt

# MCP wrappers (as before)
def mcp_embed_descriptors(descriptors: list[str], model="all-MiniLM-L6-v2") -> list[list[float]]:
    pass  # MCP call

def mcp_normalize_vectors(vectors: list[list[float]]) -> list[list[float]]:
    pass

def mcp_compute_similarity_matrix(q_norm, k_norm) -> list[list[float]]:
    pass

def mcp_build_adjacency_matrix(similarity: list[list[float]], tau_edge: float = 0.7) -> list[list[int]]:
    pass

def mcp_get_incoming_neighbors(adj: list[list[int]]) -> list[list[int]]:
    pass

def mcp_get_aggregation_order(adj: list[list[int]]) -> list[int]:
    pass

# Configuration
AGENTS = ["Manager", "Developer", "Tester", "Researcher", "Designer"]  # include Manager if it outputs descriptors
MAX_ROUNDS = 15
TAU_EDGE = 0.70
EMBED_MODEL = "all-MiniLM-L6-v2"

# State
round_num = 0
memories = {agent: "" for agent in AGENTS}
round_goal = "Understand the problem and plan initial high-level approach."
task_description = "Build a Python CLI todo app with add/list/delete commands and persistence to JSON."
halt = False
final_solution = None

def visualize_graph(adj_matrix: list[list[int]], agent_names: list[str], round_num: int, similarity_matrix=None):
    """
    Draw the directed graph from adjacency matrix.
    Optional: edge labels with similarity scores if provided.
    """
    G = nx.DiGraph()
    
    # Add nodes
    for agent in agent_names:
        color = 'lightgreen' if agent == "Manager" else 'lightblue'
        G.add_node(agent, color=color)
    
    # Add edges with optional weights
    for i, row in enumerate(adj_matrix):
        for j, val in enumerate(row):
            if val == 1:
                weight = round(similarity_matrix[i][j], 2) if similarity_matrix else None
                G.add_edge(agent_names[j], agent_names[i], weight=weight)  # j→i (provider → consumer)
    
    # Layout & draw
    pos = nx.spring_layout(G, seed=42)  # consistent layout
    node_colors = [G.nodes[n]['color'] for n in G.nodes()]
    
    plt.figure(figsize=(10, 7))
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=2200)
    nx.draw_networkx_labels(G, pos, font_weight='bold', font_size=10)
    nx.draw_networkx_edges(G, pos, arrows=True, arrowstyle='->', arrowsize=20)
    
    # Edge labels (similarity if available)
    edge_labels = nx.get_edge_attributes(G, 'weight')
    if edge_labels:
        nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels, font_size=8)
    
    plt.title(f"DyTopo Induced Graph - Round {round_num}")
    plt.axis('off')
    
    # In real code: plt.savefig(f"graph_round_{round_num}.png", dpi=300, bbox_inches='tight')
    # Here: just show (or print structure for text output)
    plt.show()  # comment out in non-interactive env
    
    # Text fallback: print edges
    print(f"Graph edges (provider → consumer):")
    for u, v, data in G.edges(data=True):
        label = f" ({data['weight']})" if 'weight' in data else ""
        print(f"  {u} → {v}{label}")
    print("")

# Main loop
while not halt and round_num < MAX_ROUNDS:
    round_num += 1
    print(f"\n=== Round {round_num} ===")
    print(f"Round goal: {round_goal}")

    # Phase 1: Agent inference (same as before)
    agent_outputs = {}
    for agent in AGENTS:
        prompt = f"""..."""  # (omitted for brevity - same structured prompt as previous version)
        response = call_llm(prompt)
        parsed = parse_structured_output(response)
        agent_outputs[agent] = {
            "public": parsed["Public Message"],
            "private": parsed["Private Message"],
            "query": parsed["Query Descriptor"],
            "key": parsed["Key Descriptor"]
        }

    # Phase 2: Manager decision (same)
    # ... (omitted - compute manager_response, parse next_goal, halt, final_solution)

    if halt:
        final_solution = manager_decision.get("final_solution", None)
        break

    # Phase 3: Semantic Matching & Topology (MCP calls)
    all_queries = [agent_outputs[a]["query"] for a in AGENTS]
    all_keys    = [agent_outputs[a]["key"]   for a in AGENTS]

    q_raw = mcp_embed_descriptors(all_queries, EMBED_MODEL)
    k_raw = mcp_embed_descriptors(all_keys,    EMBED_MODEL)

    q_norm = mcp_normalize_vectors(q_raw)
    k_norm = mcp_normalize_vectors(k_raw)

    similarity_matrix = mcp_compute_similarity_matrix(q_norm, k_norm)
    adj_matrix = mcp_build_adjacency_matrix(similarity_matrix, TAU_EDGE)

    incoming_neighbors = mcp_get_incoming_neighbors(adj_matrix)
    agg_order = mcp_get_aggregation_order(adj_matrix)

    # ─── NEW: Visualize the graph ───
    visualize_graph(adj_matrix, AGENTS, round_num, similarity_matrix=similarity_matrix)

    # Phase 4: Route & Update Memories (same as before)
    for i, agent_i in enumerate(AGENTS):
        routed_privates = []
        for provider_idx in incoming_neighbors[i]:
            provider = AGENTS[provider_idx]
            routed_privates.append(agent_outputs[provider]["private"])

        # Sort by agg_order position
        routed_ordered = sorted(
            routed_privates,
            key=lambda msg: agg_order.index(
                next(idx for idx, a in enumerate(AGENTS) if agent_outputs[a]["private"] == msg)
            )
        )

        new_content = f"Round {round_num} public:\n{agent_outputs[agent_i]['public']}\n"
        if routed_ordered:
            new_content += "Routed private messages (ordered):\n" + "\n---\n".join(routed_ordered) + "\n"

        memories[agent_i] += "\n" + new_content

    round_goal = next_goal

# End
if halt:
    print("\n=== TERMINATED ===")
    print("Final solution:")
    print(final_solution)
else:
    print("\n=== MAX ROUNDS REACHED ===")
```

### Notes on Visualization
- **In interactive environments** (Jupyter, Colab): `plt.show()` displays the plot inline.
- **In scripts**: Uncomment `plt.savefig(...)` to generate PNG files per round (useful for post-analysis or paper-style traces).
- **Edge labels** — Shows cosine similarity scores (> τ_edge) for interpretability.
- **Customization**:
  - Change `spring_layout` to `circular_layout` or `kamada_kawai_layout` for different looks.
  - Add node shapes/sizes based on degree.
  - For large N, use `nx.draw_kamada_kawai` or external tools like Graphviz (if pygraphviz were available).
- **Fallback for non-graphical env** — The printed edges provide a text trace.

This addition directly supports the paper's claim of "interpretable coordination trace via the evolving graphs" (abstract) and "qualitative inspection of how communication pathways reconfigure" (introduction). Run it round-by-round to watch the topology adapt! If you want Graphviz DOT export (text-based) instead, or integration with PyVis for interactive HTML graphs, let me know.

## Agent Comm Flow in DyTopo

In the **DyTopo** framework (arXiv:2602.06039), communication within each reasoning **cycle** (i.e., one full round t) follows a tightly structured, manager-guided flow with two distinct message channels and a clear separation of concerns. This design enables the dynamic, sparse directed topology that is the paper's core innovation.

The system distinguishes:
- **Manager** (a single meta-agent) — maintains global oversight, sets round goals, aggregates public information, and decides termination.
- **Workers** (N heterogeneous agents, e.g., Developer, Tester, Researcher, Designer) — perform specialized reasoning and generate content.

All communication is orchestrated through a **synchronization barrier**: Workers generate outputs first → topology is induced → private messages are routed → memories are updated → next round begins. No direct peer-to-peer messaging happens outside this orchestrated cycle.

### 1. Manager ↔ Workers Communication Flow
This is the **primary control channel** and is **always active** (not routed via the dynamic graph).

- **Downstream (Manager → Workers)** — Broadcast, unconditional
  - At the **start of each round**, the Manager broadcasts the current **round-level goal** \( C_{\text{task}}^{(t)} \) (a short, focused natural-language instruction) to **all workers**.
  - This goal conditions every worker's single-pass inference (their prompt includes the role ρ_i, local memory H_i^{(t)}, and this goal).
  - Purpose: Provides macro-level guidance and closes the feedback loop — the Manager refines focus based on prior progress (e.g., "Refine authentication logic and add unit tests" → "Fix failing edge cases in login tests").

- **Upstream (Workers → Manager)** — Public channel, visible to Manager
  - Every worker outputs a **public message** \( m_{\text{pub},i}^{(t)} \) (summary of progress, insights, issues, or partial results).
  - All public messages are collected by the orchestrator and **fed to the Manager** (often concatenated or summarized).
  - The Manager uses this global view \( S_{\text{global}}^{(t)} \) to:
    - Aggregate progress.
    - Detect inconsistencies or gaps.
    - Decide next round goal.
    - Evaluate halting condition (y^{(t)} = 1 if internal evaluation Φ ≥ γ_success).
  - Public messages are also appended to each worker's own next-round memory (self-reflection).

- **No private routing** between Manager and workers — The Manager does not typically receive routed private messages, and workers do not route privates directly to the Manager. The Manager operates on the public channel + its own state.

### 2. Workers ↔ Workers Communication Flow
This is **selective, dynamic, and private** — only occurs along edges of the induced graph G^{(t)}.

- **Generation phase** (all workers simultaneously, single-pass LLM call):
  - Each worker outputs:
    - Public message (goes to Manager + self-memory).
    - **Private message** \( m_{\text{priv},i}^{(t)} \) — detailed content (code, explanations, critiques, etc.) intended for selective sharing.
    - Query descriptor \( s_{q,i}^{(t)} \) — "what I need right now" (short NL).
    - Key descriptor \( s_{k,i}^{(t)} \) — "what I can offer right now" (short NL).

- **Topology induction** (orchestrator, after all outputs collected):
  - Embed queries/keys → compute cosine similarities → threshold → build directed adjacency matrix A^{(t)}.
  - Directed edge **j → i** means: worker j (provider) → worker i (consumer), because j's key semantically matches i's query well enough (> τ_edge).
  - No self-loops; graph is sparse.

- **Routing phase** (post-synchronization barrier):
  - Private message from worker j is routed **only** to those workers i where edge j → i exists.
  - Routed privates are **ordered** according to the aggregation order σ^{(t)} (topological sort if DAG; greedy in-degree heuristic if cyclic).
  - Each recipient worker i receives the concatenated, ordered block of incoming private messages in their next-round memory H_i^{(t+1)}.

- **No broadcast** — Workers do **not** see all other workers' private messages by default. Only semantically relevant ones arrive via routing.
- **No direct worker-to-worker addressing** — Routing is fully automatic and content-driven (semantic matching), not agent-initiated.

### Summary of One Full Cycle (Round t)
1. Manager broadcasts round goal \( C_{\text{task}}^{(t)} \) to all workers.
2. All workers (in parallel) perform single-pass inference → output public/private messages + query/key descriptors.
3. Orchestrator collects everything.
4. Manager receives all public messages → aggregates global state → decides next goal + halt.
5. Orchestrator induces directed graph G^{(t)} via semantic matching.
6. Private messages are routed along induced edges (provider → consumer).
7. Memories updated: each worker gets own public + ordered incoming privates.
8. If not halting → loop to round t+1 with updated goal.

This creates a **closed-loop, bi-level adaptation**:
- Micro-level: Workers ↔ Workers via dynamic, sparse, private routing.
- Macro-level: Manager ↔ Workers via public channel + goal broadcast.

The result is interpretable (evolving graphs show pathway reconfiguration) and efficient (sparsity reduces context overload), which drives the reported performance gains, especially on smaller LLMs.

## Sync Based Comms in DyTopo

In DyTopo, all agents (including workers) operate synchronously by design—there is no asynchronous execution mentioned in the framework (e.g., no concurrent or event-driven messaging mid-round). Instead, the system enforces a **synchronization barrier** (Section 3.2.2 of the paper), where all agents perform a single-pass inference in parallel at the start of each round, outputs are collected, the dynamic topology is induced, and communication (routing) happens deterministically afterward. This batch-style processing ensures efficiency and reproducibility, especially for multi-round reasoning tasks.

If the Manager "calls on" two worker agents (e.g., Agent A and Agent B) that need to communicate with each other—meaning they have interdependent needs (e.g., A requires B's output to refine its work, and vice versa)—this doesn't happen via direct, real-time back-and-forth within a single round. Instead, it unfolds over **one or more rounds** through the adaptive, semantically driven routing of private messages. The Manager doesn't mediate or "call" mid-round; it sets the round goal to guide the workers toward the necessary collaboration, and the topology handles the rest.

Here's how it might work step-by-step in a synchronous setup, assuming a scenario like code generation where Agent A is a "Developer" (implements code) and Agent B is a "Tester" (verifies and identifies bugs). This draws from the paper's methods (Sections 3.2–3.4) and Figure 2.

### Step 1: Manager Sets the Stage (Broadcast Round Goal)
- At the start of round t, the Manager broadcasts a focused round goal \( C_{\text{task}}^{(t)} \) to **all workers** (including A and B). This goal is derived from the previous round's global state and is designed to encourage the needed interaction.
- Example: If the Manager detects from prior public messages that A and B need to collaborate (e.g., on debugging), the goal might be: "Implement the core module (Developer) and generate initial test cases (Tester); identify any mismatches."
- Both A and B receive this goal as part of their prompt, conditioning their outputs. No direct "call" from Manager to specific workers—the broadcast applies to everyone, but roles (ρ_i) make it relevant to A and B.

### Step 2: Synchronous Worker Inference (Parallel Generation)
- All workers (A, B, and others) perform their single-pass LLM inference **in parallel** (no sequencing or waiting).
- Each outputs:
  - Public message \( m_{\text{pub}}^{(t)} \) (summary, visible to Manager).
  - Private message \( m_{\text{priv}}^{(t)} \) (detailed content, e.g., A's code snippet or B's test results).
  - Query descriptor \( s_q^{(t)} \) (what they need, e.g., A: "Need test failures for my implementation").
  - Key descriptor \( s_k^{(t)} \) (what they offer, e.g., B: "Can provide bug reports and test outputs").
- If A and B need to communicate, their descriptors reflect this interdependence (prompted by the round goal and local memories from prior rounds).
- No communication happens yet—outputs are just collected by the orchestrator.

### Step 3: Manager Processes Public Info (Global Oversight)
- The Manager receives all public messages (aggregated into \( S_{\text{global}}^{(t)} \)) and uses them to:
  - Update the next round's goal (e.g., if A and B's publics show misalignment, next goal: "Address identified bugs and retest").
  - Decide if halting (e.g., if collaboration succeeds and task is done).
- This doesn't directly affect A-B communication but refines future rounds to foster it.

### Step 4: Topology Induction and Routing (Post-Barrier Communication)
- The orchestrator induces the directed graph \( G^{(t)} \) from all workers' query/key descriptors (via semantic embedding, cosine similarity, and thresholding—Sections 3.3–3.4).
- For A and B to "communicate":
  - If A's query semantically matches B's key (cosine > τ_edge), an edge **B → A** forms (B provides to A).
  - If B's query matches A's key, an edge **A → B** forms.
  - Bidirectional edges create a cycle, handled by the aggregation order σ^{(t)} (topological sort if acyclic; greedy in-degree heuristic if cyclic—Section 3.4.2) to ensure deterministic message ordering without deadlocks.
- Private messages are then routed **only along edges**:
  - Example: B's private (test results) goes to A's next-round memory if B → A exists.
  - Routed messages are ordered (e.g., by relevance descending or dependency) and concatenated into the recipient's memory H^{(t+1)}.
- If no edge forms (e.g., mismatch in descriptors), no direct communication happens this round—A and B don't exchange privates. But the Manager's next goal might prompt better-aligned descriptors in round t+1.

### Step 5: Memory Update and Next Round Prep
- Each worker's memory is updated synchronously: Own public + ordered incoming privates.
- Example: A gets B's test feedback in its memory for t+1, allowing A to refine code in the next inference.
- The cycle repeats with the Manager's updated goal, potentially strengthening A-B edges as needs evolve (e.g., from broad to targeted).

### Potential Challenges and How It "Works" in Practice
- **If Interdependence Causes a Cycle**: The greedy ordering minimizes unresolved dependencies (e.g., place lower in-degree agents first), ensuring prompts are coherent without async resolution.
- **Multi-Round Resolution**: Strong interdependence might take 2–3 rounds to fully resolve (e.g., Round 1: Initial outputs → edge forms → routing; Round 2: Refined based on received info).
- **No Edge? Adaptation Kicks In**: If descriptors don't match initially, the Manager's feedback loop (via goals) encourages shifts (e.g., A changes query from "Need specs" to "Need tests," matching B's key better).
- **Efficiency**: Synchronous design avoids race conditions/latency; sparsity ensures low overhead (Appendix A).
- **From Experiments**: On tasks like code gen (HumanEval), this yields gains (e.g., +390% relative on small LLMs) by iteratively uncovering errors without dense noise.

This synchronous, batched approach makes DyTopo robust for non-async environments, relying on the dynamic graph to "simulate" needed communication over rounds. If your setup requires true async (e.g., real-time), you'd need extensions beyond the paper's design.

## Worker Responds Once per Round

The worker performs **one unified generation step** (single-pass LLM inference), but the **output of that single step** is structured in a way that naturally serves **both** purposes:

1. Contributing content that gets routed / used by others (via private message)  
2. Providing a summary visible to the Manager (via public message)  

The local memory update happens **after** this generation, as a separate post-processing step by the orchestrator (not done by the worker/LLM itself).

## Worker's Implied Messaging to the Manager

In the **DyTopo** framework (as described in arXiv:2602.06039), **individual worker agents do not directly signal** "I'm done for this round", "I've completed my contribution", "I need more data to continue", or "the overall goal is finished" using dedicated, structured fields in their output.

The paper's design keeps worker outputs minimal and focused on the core four fields produced in a single-pass LLM inference (Section 3.2.1, Equation 2):

- **Public Message** (`m_pub,i^(t)`): A short summary of progress, insights, partial results, or issues — visible to the Manager.
- **Private Message** (`m_priv,i^(t)`): Detailed content (e.g., code, explanations, critiques) that may be routed to other workers.
- **Query Descriptor** (`s_q,i^(t)`): Short natural-language description of what information the agent currently seeks/needs.
- **Key Descriptor** (`s_k,i^(t)`): Short natural-language description of what information/capability the agent can currently offer/provide.

There are **no additional explicit fields** like `"status": "done"`, `"ready_for_next": true`, `"round_complete": yes`, `"need_more_data": true`, `"my_subgoal_finished": true`, or `"task_done"` in the agent's formal output tuple.

### How "completion" or "needs more data" is communicated instead

Workers convey these states **implicitly** through the **content and phrasing** of the fields they do output — particularly the **public message** and **query/key descriptors**. The **Manager** (and indirectly the orchestrator) interprets these signals holistically to decide what to do next.

#### 1. Indicating "I've done all I can this round / waiting for more data / need input to continue"
- **Primary channel**: **Query Descriptor** (`s_q,i^(t)`)
  - The agent writes something like:
    - "Need test results from the Tester to verify my implementation"
    - "Awaiting updated code from Developer before I can write integration tests"
    - "Require clarification on edge-case requirements"
    - "Need more information about the API endpoints"
  - This signals "I cannot make further meaningful progress without additional data" → the semantic matching engine will try to route relevant private messages from providers whose keys match this query.
- **Secondary channel**: **Public Message** (`m_pub,i^(t)`)
  - Can include progress summaries like:
    - "Implemented the login function; waiting for test feedback to proceed"
    - "Drafted unit tests but blocked on edge-case data"
    - "My part is complete pending review/code from others"
  - The Manager sees this in the global aggregation (`S_global^(t)`) and can adjust the next round goal accordingly (e.g., "Tester: run tests on Developer's latest code").

#### 2. Indicating "I've completed my goal / subgoal / this round's contribution"
- **Primary channel**: **Public Message** (`m_pub,i^(t)`)
  - Agents can state things like:
    - "Authentication module fully implemented and ready for testing"
    - "All unit tests written and passing locally"
    - "Design complete; no further changes needed unless requirements shift"
    - "Verification passed; solution is correct"
  - These act as **progress signals** that the Manager aggregates to assess overall advancement.
- **Secondary channel**: **Query Descriptor** can be empty, vague, or "nothing further needed"
  - Examples seen in practice or implied: "No additional information required at this stage" or "Awaiting final confirmation only"
  - This reduces incoming edges (sparser graph), signaling low need for more collaboration this round.

#### 3. Overall task completion ("the whole problem is solved")
- Workers **never** decide or declare global completion — that is **exclusively the Manager's responsibility**.
- Workers can only **suggest** it indirectly via public messages (e.g., "All tests passing, code appears correct and complete").
- The Manager uses its policy \( \Pi_{\text{meta}} \) and internal evaluation function \( \Phi(S_{\text{global}}^{(t)}) \) (Eq. 14) to decide halting (`y^{(t)} = 1` if \( \Phi \geq \gamma_{\text{success}} \)).
  - \( \Phi \) is task-specific (e.g., checks code correctness, test passage, math proof validity via self-evaluation or simple rules).
  - Workers do **not** output a "halt" or "task complete" field.

### Summary Table: How Workers Signal State

| Worker Intention                          | Primary Field Used          | Typical Phrasing / Content Example                                      | How the System Responds                                                                 |
|-------------------------------------------|-----------------------------|--------------------------------------------------------------------------|------------------------------------------------------------------------------------------|
| "Done for this round / waiting for data"  | **Query Descriptor**        | "Need test results / updated code / clarification on X"                 | Semantic matching → incoming edges → routed privates in next round                       |
| "My contribution complete / ready"        | **Public Message** + **Query** | "Module implemented and ready" / "No further info needed"               | Manager sees progress; may narrow next goal or reduce edges if many agents say similar   |
| "Suggest overall task is done"            | **Public Message**          | "All tests passing; solution correct"                                    | Manager aggregates → evaluates halting condition → decides to terminate                 |
| "Continue / more work needed"             | Implicit (active Query/Key) | Non-empty need + offer → keeps edges alive                               | Graph stays connected; Manager keeps issuing refinement goals                           |

In short: **No dedicated status/completion fields exist** in worker outputs. Signals are **emergent** and **natural-language-based**, embedded in the public message (for Manager visibility) and query/key descriptors (for routing decisions). This keeps the agent output lightweight and lets semantic matching + the Manager's judgment handle continuation, stalling, or termination dynamically — aligning with DyTopo's goal of adaptive, interpretable coordination without rigid status protocols.

### Correct Sequence in One Round (t)

1. **Single unified LLM call per worker** (Section 3.2.1 — "Single-Pass Inference")  
   The worker receives its prompt containing:  
   - role description  
   - current round goal from Manager  
   - current local memory H_i^{(t)}  

   From **one forward pass**, it outputs **four things at once** (Equation 2):  
   O_i^{(t)} = (m_pub,i^{(t)}, m_priv,i^{(t)}; s_q,i^{(t)}, s_k,i^{(t)})  

   → public message (summary / progress report)  
   → private message (detailed content to potentially share)  
   → query descriptor (what I need)  
   → key descriptor (what I can offer)  

   This is **one operation**, not two separate ones.

2. **Orchestrator collects all outputs** from all workers.

3. **Topology induction** happens using only the descriptors (queries & keys) → graph G^{(t)} is built → routing decisions are made (who receives whose private message).

4. **Synchronization barrier & memory update** (Section 3.2.2, Equation 3)  
   This is **not** done by the worker LLM — it's pure string manipulation by the orchestrator.  

   For each worker i:  
   H_i^{(t+1)} = H_i^{(t)}  ⊕  m_pub,i^{(t)}  ⊕  [ordered incoming private messages]

   So the worker's **own public message** is **always** appended to its own next-round memory (self-reflection), but **not** because it was sent to the Manager — it's simply part of the memory-update rule.

### Clarifying Your Two Options

**Option A ("two separate operations")**  
Update local memory **and** send summary to Manager  
→ Not accurate. There is no separate "send summary" call. The public message is just one field in the single LLM output. The Manager receives it because the orchestrator collects and forwards all public messages after generation.

**Option B ("just one operation — update local memory")**  
→ Also not quite right. The **generation** is one LLM operation, but **memory update** is a later, non-LLM step (concatenation). The public message going to the Manager is **side-effect** of the generation, not the primary purpose of updating memory.

### More Accurate Summary

The worker does **one LLM generation operation** that produces content with **multiple destinations**:  
- public message → collected → sent to Manager (for global view & next goal) **and** appended to own memory  
- private message → routed selectively via graph → appended only to recipients' memories  
- descriptors → used only for topology induction (transient, not stored in memory)

So the public message **serves dual roles** (Manager summary + self-memory), but this dual-use is a consequence of the design — not because the worker performs two independent actions.

In short:  
**One generation step → multiple output fields → orchestrator routes/collects them appropriately → memory is updated post-routing.**  

No separate "send to Manager" or "update memory" LLM calls exist per round.

## Managers Message to Worker (Round > 0)

In the DyTopo framework (as detailed in arXiv:2602.06039), the "message" sent to worker agents in any round t (including t > 0, after the initial round where agents provide their first take on the user request) is structured as a **prompt** for their single-pass LLM inference. This prompt is not a simple "message" but a composed input string that conditions the agent's generation of outputs (public/private messages + query/key descriptors).

The structure is defined in **Section 3.2.1** (Equation 1) as the **local state** \( S_i^{(t)} \), which is concatenated or formatted into the worker's prompt. It remains consistent across all rounds (t ≥ 0), but the content evolves dynamically based on prior rounds' progress. There is no special "initial round" distinction in the paper—the first round (t=0) starts with empty memories and a broad initial goal, while later rounds (t>0) incorporate updated memories and refined goals.

### Structure of the Prompt/Message to Workers
The prompt to each worker i in round t is built from three fixed components (concatenated in this order, often with delimiters for clarity in implementation):

1. **Role Description** (\( \rho_i \)):  
   - A fixed, agent-specific string describing the worker's specialization.  
   - This is set at system initialization and does not change across rounds.  
   - Example (from Appendix B, code generation setup):  
     "You are the Developer agent. Your role is to implement code modules based on designs and requirements. Focus on writing functional, efficient Python code."

2. **Current Round Goal** (\( C_{\text{task}}^{(t)} \)):  
   - A short, natural-language instruction broadcast by the Manager at the start of the round.  
   - For t=0 (initial round): This is a broad, exploratory goal (e.g., "Understand the user request and provide initial analysis/plans").  
   - For t>0: This is refined based on the prior round's global state (e.g., "Refine the login module implementation based on test feedback and fix identified bugs").  
   - It provides macro-level guidance, focusing agents on unresolved aspects without explicit sub-task assignment.

3. **Local Memory Buffer** (\( H_i^{(t)} \) or \( \mathcal{H}_i^{(t)} \)):  
   - The agent's accumulated history from prior rounds — a growing string of text blocks.  
   - For t=0: Empty or minimal (just the overall task description).  
   - For t>0: Appended with content from the previous round (t-1), per the update rule (Equation 3):  
     - The agent's own public message from t-1 (for self-reflection).  
     - Ordered, concatenated private messages routed to it from incoming neighbors in G^{(t-1)} (semantically relevant details from other workers).  
   - Example content block (appended at end of t-1):  
     "Round 1 public: Implemented initial login draft.  
     Routed private messages (in dependency order):  
     From Tester: Test plan outline with edge cases.  
     ---  
     From Designer: Updated API specs."

### Full Example Prompt Structure (for Round t>0)
In practice (e.g., in the pseudocode we discussed earlier), the prompt to a worker might look like this formatted string:

```
You are the [Role Description, e.g., Developer agent in a DyTopo multi-agent system. Your role is to implement code modules...].

Overall task: [Original user request, e.g., "Build a Python CLI todo app with add/list/delete commands."]  // Fixed, included for context.

Current round goal: [C_task^{(t)}, e.g., "Refine the core modules based on test feedback and integrate persistence."].

Your current memory / history:  
[Full H_i^{(t)}, e.g., accumulated text from prior rounds, including own publics + routed privates].

Based on the round goal and your history:  
- Generate a public message: A short summary of your progress or insights, visible to the manager.  
- Generate a private message: Detailed thoughts, code, or suggestions to share selectively.  
- Query descriptor: A short (1-2 sentences) natural language description of what you need from others.  
- Key descriptor: A short (1-2 sentences) natural language description of what you can offer.

Structure your entire response exactly as:  
- Public Message: [Text]  
- Private Message: [Text]  
- Query Descriptor: [Text]  
- Key Descriptor: [Text]
```

### Key Notes
- **Uniform Across Rounds**: The structure doesn't change for t>0 — only the content of the round goal and memory evolves (becomes richer/more focused as collaboration progresses).
- **No Worker-Specific Customization**: All workers receive the same round goal (broadcast), but their prompts differ only in role and local memory (which is personalized via prior routing).
- **From the Paper**: See Figure 2 (page 3) for the visual flow — the Manager provides the round goal, workers condition on it + memory, and outputs follow.
- **Implementation Tip**: In code (e.g., our pseudocode), delimiters like "---" or section headers ensure the LLM parses the memory coherently without hallucination.

This design ensures workers remain focused and adaptive without needing round-specific structural changes. If you need a code snippet demonstrating this prompt construction, let me know!

## Manager/Worker Comms via Redis
- DT-Manager DOES NOT break down the User-Task into smaller, manageable chunks. Instead, it allows decomposition of the task through evolving guidance through each round.
- DT-Manager creates a ReqSLUID and TaskSLUID (Shortened LUID [time based for sequentiality]) based on the current User-Task.
  - The Round Sequence is appended to the UUID to ensure uniqueness and traceability.
    - Use the python-sandbox to generate SLUIDs. 
- Keys: DyTopo Messaging with Redis
  - Message to Worker Agents
    - [To-Workers:<ReqSLUID>:0]
  - Worker to Manager
    - [DT-Manager:ReqSluid:<RoundSeq>]
  - Manager to Worker
    - [DT-<Worker>:ReqSLUID:<RoundSeq>]
