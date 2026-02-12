# How To: DyTopo Agent Orchestration

  - DyTopo (die-toe-po)
    - Dynamic Topology Agent Management

## Advantage of DyTopo Agent Interaction

One of the most striking advantages of the DyTopo framework is indeed how dramatically it boosts the performance of smaller or weaker LLM backbones—such as Qwen3-8B—bringing them much closer to (or even surpassing in relative gains) the results achieved by much larger models.

## These scripts work within Aider-Desk Agents

## Pre-requisites

- Ensure you have the latest version of Aider-Desk installed.
- Familiarize yourself with the basic usage of Aider-Desk Agents.
- Understand the concept of DyTopo Agents and their role in Aider-Desk.

- Redis for key-value storage for Agent Communication.
- MCP Server python-sandbox for SLUID (Short Local Unique Identifier) generation (used for Agentic Message Identification).

## The Agents

The DyTopo agents comprise of...
  - DT-Manager (The Software Manager and Agent Orchestrator)
  - DT-Architect (The Worker Agent)
  - DT-Dev (The Developer Worker Agent)
  - DT-Tester (The Testing Worker Agent)
  - DT-Reviewer (The Reviewer Worker Agent)

  1. DyTopo Agent Management works by first sending a  (Round-0) to the all of the worker agents.
  2. All of the worker agents then review the request... do research on the code base... then respond back to the DT-Manager with... 
     - what they have done so far, 
     - what else they may need to continue on with making progress on the request
     - and what additional things that they can do to move the request closer to fulfillment.
  3. The DT-Manager receives all of the responese from (Round-0)...
     - simulates semantic matching (when done properly, requires performing math operations on the vector embeddings of the worker's responses as defined in the paper). But, basically decideds the next appropriate DT-Worker to hand off any of the tasks returned from the work done in the prior round (Round-0), if more work needs to be done on that task.
     - Thus, a task returned by DT-Architect, if the work looks complete, will be handed off to DT-Reviewer to review before implementation by DT-Dev (The Programmer).
     - Now, we are at Round-1. The DT-Manager will then desice which tasks to send to which worker agents, and does so.
     - Worker agent do work based on the data they have, when they can go no-further, report back to the DT-Manager.
     - And, the cycle of rounds continues until there are no-more tasks to execute on, the request is fulfilled, to the best ability of the team of agents.
 
So far, I have found this agentic process quite workable. You can see the agents working on their tasks in parallel on Aider-Desk. And where your input-verification is required, you will be prompted.

## Differences from true DyTopo Process
  - The true DyTopo process is more complex, involving calculation on vector embeddings. The process simply replaces those calculations with the reasoning skills of LLM used by the DT-Manager.
  - So far, I hove found that the Grok's ability to simulate semantic matching is pretty good, and I am getting great results from it.

## Future improvements
  - The calculations required to perform semantic matching can be performed using an MCP Service. The endpoints for such a service are outlined in my research document [0-DyTopo_Agent_Prompts_and_Research.md](0-DyTopo_Agent_Prompts_and_Research.md) if you are interested.

## Key Agent Setting

### DT-Manger: (The Agentic Orchestrator)
  - Toole
    - todo: off
    - power: off
    - tasks: on
      - all-settings: Always
    - memory: on
    - MCP Servers
      - redis
      - python-sandbox

### DT-Architect (The Wise Architect)
  - todo: on
    - set_items: Never
    - get_items: Always
    - update_item_completion: Always
    - clear_items: Never
  - tasks
    - get-items: Always
    - get_task_message: Always
    - ..rest..: Never
  - memory: off
  - skills: off
  - power: off
    - MCP Servers
      - redis
      - probe (source code analyzer)
      - web_fetch (optional)
      - brave_search (optional)
      
### DT-Dev (Out Pro Programmer)
  - todo: on
    - set_items: Never
    - get_items: Always
    - update_item_completion: Always
    - clear_items: Never
  - tasks
    - get-items: Always
    - get_task_message: Always
    - ..rest..: Never
  - memory: off
  - skills: off
  - power: on (Calls on Aider to write code)
    - MCP Servers
      - redis
      - probe (source code analyzer)
      - web_fetch (optional)
      - brave_search (optional)

### DT-Tester (Writes and Runs Tests)
  - todo: on
    - set_items: Never
    - get_items: Always
    - update_item_completion: Always
    - clear_items: Never
  - tasks
    - get-items: Always
    - get_task_message: Always
    - ..rest..: Never
  - memory: off
  - skills: off
  - power: on (Calls on Aider to write code)
    - MCP Servers
      - redis
      - probe (source code analyzer)
      - web_fetch (optional)
      - brave_search (optional)

### DT-Reviewer (Reviews Plans/Code/Tests/Results)
  - todo: on
    - set_items: Never
    - get_items: Always
    - update_item_completion: Always
    - clear_items: Never
  - tasks
    - get-items: Always
    - get_task_message: Always
    - ..rest..: Never
  - memory: off
  - skills: off
  - power: off
    - MCP Servers
      - redis
      - probe (source code analyzer)
      - web_fetch (optional)
      - brave_search (optional)

## DyTopo Agent Orchestration in Context

Add the [DyTopo Agent Orchestration Basics](0-DyTopo-Agent-Orchestration-Basics.md) file as to Aider-Desk's Context, if you find that the Manager needs to know about DyTopo's agent orchestration principles.

## Redis and Python-Sandbox MCP Services

  - Redis an actually be replace by any other database look up system that is has an MCP service such as SQK, Neo4J, SqLite etc...
    Just change the text "redis" to the name of the MCP database service that is available to you.
  - python-sandbox can be replace with allowing bash execution, or the exection of a small script that returns LUIDs, whixh the agent can execute, given a few more instruction in the DT-Manager.md prompt file.

## Conclusion

Let me know of your experience with using using these Agent Orchestration prompts in the Discussions Thread.


