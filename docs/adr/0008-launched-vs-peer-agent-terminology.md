# 0008. Launched harness versus peer agent

- Status: Accepted
- Date: 2026-09-16

## Context

The tool is called peeragent and it ships a skill called
launch-peer-agent. The name states the intent: peeragent is a
building block for agents that work alongside each other across
platforms.

What the tool actually starts is narrower than the name suggests.
It is a terminal program in a pane. It has no identity, no team, no
mailbox and no registration anywhere. Calling it a peer agent in
the prose would promise infrastructure that peeragent neither
provides nor knows about, and a caller that believed the promise
would look for a channel that does not exist.

## Decision

The names stay: the tool is peeragent and the skill is
launch-peer-agent, because they say what the tool is for.

The prose is precise where the names are aspirational. The process
peeragent spawns is the launched harness. It may become a peer
agent once it registers with such an infrastructure, and that step
is outside this tool. The caller that invokes peeragent and reads
its output is the starting agent.

## Consequences

- The documentation explains the distinction once, close to where
  the name is introduced, and the glossary carries both terms.
- The message names keep their subcommand-derived prefix, while
  the prose around them says launched harness. The distinction is
  in the explanation, not in a renaming of the interface.
- Setting up a channel between the starting agent and the launched
  harness is explicitly out of scope. It is the business of the
  launch prompt, and the shipped skill makes describing it an
  obligation of the starting agent.
- A reader who arrives from a fleet-oriented vocabulary is told
  what peeragent does not do, instead of discovering it later.

## Alternatives considered

Renaming the tool to something purely descriptive. Rejected: the
name carries the intent, and the intent is worth stating.

Using peer agent throughout the documentation. Rejected: it
overclaims, and the first caller that looked for an identity or a
mailbox would be misled.
