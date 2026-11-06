# Assignment: lifecycles and outcomes of a loan application

Exploratory analysis of the **BPI Challenge 2017** event log, from Assignment 3 of *Introduction to Business Process Automation and
Process Mining* (Tasks 8, 9 and 10). You do it in a notebook, with linear continuous process maps, and you hand in your **annotations**.

## Context

*Dhana* is a European bank. One of its core services is the **loan application process**. The event log contains all loan
applications filed with the bank in 2016: **31,509 applications and about 1.2 million events** (the full log), with 26 different
activities.

There are three kinds of events, told apart by the start of the activity name:

| Starts with | Family | What it records |
|---|---|---|
| `A_` | Application | the state of the loan application (created, submitted, accepted, pending, denied, ...) |
| `O_` | Offer | the state of an offer made to the customer (created, sent, returned, accepted, refused, cancelled) |
| `W_` | Workflow | a piece of work done by a bank employee (call after offers, validate application, ...) |

An application can have several offers, but at most one offer is accepted per application.

## The three tasks

- **Task 8.** Keep only the Loan Application lifecycle (all activities starting with `A_`) in the process map and write down at
  least three interesting observations.
- **Task 9.** Repeat Task 8 for the Offer lifecycle: keep the activities starting with `O_`, but not `O_Create Offer`.
- **Task 10.** Create a visualization of the case outcome distribution of the log. The set of outcomes must be pairwise mutually
  exclusive and complete. Briefly reflect on the result.

## How to work

1. **Work through the tutorial** (`tutorial.py`). It replays a short analysis of another part of the same log (the workflow activities) and explains the elements of a map,
   its settings, the patterns a map makes visible, and how to write intents and findings.
2. **Open the student notebook** (`student-notebook.py`) and enter your key. Your work is saved automatically; you can close the
   page and continue later with the same key.
3. **Draw maps** with the map explorer: choose the activities, the abstraction, the folds and what a path stands for, and press
   *Refresh visualization*. Every map you draw is recorded as a step of your analysis.
4. **Write your annotations** in the side panel. Press **Pick**, click the table cell, map node or map link you mean (or the map or table itself), and write an *intent* (what the map is
   for) and one or more *findings* (what it shows). Tag each annotation with its kind, `intent` or `finding`, and with its task:
   `task8`, `task9` or `task10` (tags are separated by spaces, for example `finding task8`).

## What you hand in

Your **annotations**, each attached to the map or table that supports it. Every map you drew is recorded with its settings, so your annotations
can be read together with the steps that produced them.

## After you have tried

The **model solution** (`model-solution.py`) replays an annotated analysis of the same three tasks. Open it after your own attempt.
