# Assignment: what does a loan application carry?

Exploratory analysis of the **BPI Challenge 2017** event log, from Assignment 3 of *Introduction to Business Process Automation and
Process Mining* (Task 1, Schemas). You do it in a notebook, with process maps, and you hand in your **notes**.

## Context

*Dhana* is a European bank. One of its core services is the **loan application process**. The event log contains all loan
applications filed with the bank in 2016: **31,509 applications and about 1.2 million events** (the full log, not the smaller one),
with 26 different activities and 19 columns.

There are three kinds of events, told apart by the start of the activity name:

| Starts with | Family | What it records |
|---|---|---|
| `A_` | Application | the state of the loan application (created, submitted, accepted, pending, denied, ...) |
| `O_` | Offer | the state of an offer made to the customer (created, sent, returned, accepted, refused, cancelled) |
| `W_` | Workflow | a piece of work done by a bank employee (call after offers, validate application, ...) |

An application can have several offers, but at most one offer is accepted per application.

An **event log** is a table with one row per event. Each event belongs to a **case** (here, one loan application), has an
**activity** and a **timestamp**, and may carry further **attributes** (the requested amount, the offer id, the credit score, ...).
The *schema* of an activity is the set of attributes that take a value on its events.

## The three questions

1. Which data (attributes) does the first activity, **`A_Create Application`**, carry? (Which schema is associated with it?)
2. Which of those attributes have **missing values**?
3. Is there any attribute that is **re-used across different activities**?

## How to work

You work in the **student notebook** (`student-notebook.py`). You do not change any code: you open it, enter your key and use
the tools on the page.

1. **Enter your key.** It identifies your work. If you worked before, your earlier steps and notes come back by themselves. Your work
   is saved automatically; you can close the page and continue later with the same key.
2. **Take a first look at the event log** (section 1): the activities, the attributes of every column, a sample of events, and the
   attributes of any one activity.
3. **Explore with process maps** (section 2). A map draws every case as a path from left to right; the width of a band is the number
   of cases that follow it. Choose the activities to draw and press *Refresh visualization*. A map shows the order of activities, not
   attributes: to ask an attribute question, draw only the events that have a value for that attribute, and the activities in the map
   are exactly the ones that carry it.
4. **Write your notes** in the side panel. Press **Pick**, click the table or the map you mean (or a part of it), write what it shows
   and why it answers the question, and press **Add**. Use tags to group notes, for example one tag per question.

## What you hand in

Your **notes**, each attached to the table or the map that supports it. For each of the three questions, say what the answer is and
point at the evidence. Every table and map you used is recorded as a step of your analysis, so your notes can be read together with
the steps that produced them.

## After you have tried

The **model solution** (`model-solution.py`) is a tutorial: a recorded, annotated analysis of the same three questions, with the
reasoning behind each step and the maps that support the findings. Open it after your own attempt.
