# Project Proposal: Secure .env Credential Sharing Tool

## The Problem
The problem that will be addressed by this project is the need of developers working in teams to share secret credentials, such as API keys, that are stored typically in `.env` files. Because these files are confidential, they cannot be added to a remote repository. There needs to be a way for team members to access such credentials securely, without having others share them via third party communication.

## Target Audience
The target audience of this project is anyone working in teams to develop software.
* **Development Teams:** This largely consists of software development teams.
* **Students:** Could also include students working on projects.
* **Individual Developers:** In some cases, it would also be targeted at individual developers working on a project across multiple machines.

## Context
The problem occurs largely when a new member joins a team or project and needs to be onboarded. When new features are added, new API keys are added to the `.env` file but cannot be pushed to a remote repository. Currently, third party communication services that are not secure are often utilized to share information.

## Significance
Using a messaging service to send credentials without any kind of encryption poses quite a risk to security. If an account was breached containing messages related to the contents of a `.env` file, someone with malicious intent could suddenly have access to all API keys, to databases, etc.

Developers know that sensitive information should not be shared through messaging applications, but do it anyway due to convenience. Students are even less likely to take proper precautions. There should be a way to access said information that is just as convenient and still secure.

> **Scenario:** A possible scenario involves a tech startup sharing code via a discord server. Someone sends the `.env` file in a chat to a new member so they can access all of the environment variables. One of them later clicks on a phishing link by mistake, and their discord account becomes compromised. The attacker could then gain access to the startups database, customer information, all third party services, etc.

## Existing Solutions

### Password Managers
Password managers can be used to save credentials, but they typically are not designed to save keys integrated directly into the workflow of a developer. They often result in copy and paste, which is clunky and adds unnecessary steps.

### Commercial Tools
There are commercial tools that have been released to solve this issue for teams of developers. These are polished solutions that do work and do combat this issue. However:
* **Cost:** They can be expensive for small companies and student teams. They seem to often charge a nominal amount “per secret” that can add up quickly if working on a larger project.
* **Complexity:** They can also be complex to configure and then host.

## Proposed Solution
I aim to create a tool with an easy to use **command line interface**. It will fall into a nice middle ground of being much more secure than a simple chat in a messaging app, but not as complex and expensive as a deployed service from a giant corporation.

