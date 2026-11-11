# AGENTS.md - Winny

Working title: Winny
Status: pre-build, hackathon submission due 12 November 2026
Owner: solo build
Last updated: 11 November 2026

This is the project brief. Read it before doing anything in this repository. It is written as a product document, not a technical one, so anyone can understand what Winny is, who it is for, what it must do, and what it must never do. No technical background needed.

If you are an agent working here, the rules in section 19 apply to you. The rest explains the product so your work stays on brief.

---

## 1. Summary

Winny is the family consent layer for money.

An AI agent can now spend a person's money. Winny makes sure a person they trust sees the payment first. The agent proposes a payment, PayPal reserves the amount, a family member approves or stops it, and only then does the money move.

Winny does not hold money. It does not open accounts. It does not pool funds. It asks a specific person a specific question about a specific payment, with the evidence attached.

Hackathon context: judging is equally weighted across implementation, PayPal depth, AI depth, and demo. The demo is 25 percent of the score.

---

## 2. The problem

Every tool that guards AI spending builds a wall: a separate wallet, a scoped card, a spending limit, a policy engine. All of them are designed for one power user with one credit card.

Real family money does not work like that. It is shared, supervised, and negotiated:

- A parent funding a rent deposit for an adult child studying abroad cannot check the landlord from another continent.
- An adult child watching a parent get talked into a gift card scam by a voice that sounds like a grandchild.
- Siblings splitting the cost of a parent's care, with no shared record of who paid what.

The people who most need a second pair of eyes are the ones nobody builds for. Existing tools either block the payment and start a fight, or say nothing and let the money go.

---

## 3. The idea in one sentence

The agent proposes, PayPal authorises, a person you trust co-signs, and only then does it capture.

Or, for a demo: "The money is on hold, not gone. That distinction is the whole product."

---

## 4. Who it is for

**The sponsor.** A parent funding an adult child abroad. Pays deposits, rent, tuition. Wants control without surveillance, and wants to stop a scam before the money is gone.

**The supervised.** An older parent. Keeps independence. Most payments pass without anyone being asked. Only the odd ones get a check. The product must never feel like a cage.

**The co-signer.** A sibling or relative. Gets a clear notification with evidence, not a vague alert. Taps once. Nobody has to trust anybody's memory because the record is shared.

Minors are out of scope. Everyone in the product is an adult. "Child" means an adult child, typically a student abroad.

---

## 5. The three scenarios that define the product

These are the three stories the product is designed around. If a feature does not help one of them, it is probably not needed.

### 5.1 The rent deposit

A student abroad is about to send a large sum to a landlord she found online. The photos look real, the price is good, and he says he is overseas and will courier the keys. Winny holds the payment, checks the listing, the ownership record, and whether he agreed to a video tour. Two checks fail. Her brother gets one notification with the reasons and taps stop. The hold releases, nothing is charged, and she gets a note on what to ask next time.

### 5.2 The gift card scam

A parent gets a call that sounds like a grandchild in trouble, asking for gift cards, urgently, and asking her not to tell anyone. Winny sees a new payee, a gift card category, and urgency plus secrecy in the message. It asks the family co-signer before anything moves. The co-signer calls instead of approving.

### 5.3 The monthly allowance

A parent sends a fixed amount to an adult child on the same day every month. It is a known payee, a known amount, and a known schedule. Winny captures it automatically and notifies nobody. This case exists to prove the product stays quiet. If it asked every time, people would delete it in a week.

---

## 6. How it works, in plain language

1. A payment is started with the amount, the recipient, and the purpose.
2. Instead of sending the money immediately, Winny asks PayPal to reserve the amount. The money is on hold, not gone.
3. Winny checks the payment against the family's rules and a short list of warning signs, and writes one clear sentence explaining what it found.
4. If nothing looks wrong, the payment completes automatically and nobody is disturbed.
5. If something looks wrong, a named family member is asked to approve or stop it. They see the one sentence and the evidence behind it.
6. Approve means the money moves. Stop means the money is released back to the payer. Either way a receipt is written and the family sees the same record.
7. If nobody answers, the request moves to the next person, then expires and releases the money. Nothing is left hanging.

The gap between "money reserved" and "money moved" is the whole product. It is a short, visible window where a person can decide.

---

## 7. What the user sees

- A family circle with clear roles.
- A payment screen with amount, recipient, and purpose.
- A held state with a countdown, so it is obvious nothing has moved yet.
- A plain-English reason if the payment needs a co-signer.
- One notification with: who is paying and how much, the strongest reason in one sentence, approve or stop or call, and what happens if they do nothing.
- A receipt for every outcome.
- A shared history, so the family has one record instead of three memories.

Anything longer than that notification is ignored. Anything vaguer turns into a phone call instead of a decision.

---

## 8. Product requirements

### Must have

- A family circle with roles: sponsor, member, supervised, co-signer.
- The ability to start a payment and have the amount reserved rather than sent.
- A risk check that returns a plain-English reason.
- Automatic completion for low-risk payments, with no notification.
- A co-signer request for high-risk payments, with evidence attached.
- Approve completes the payment. Stop releases the money.
- A receipt and a shared record for every outcome.
- A timer that escalates or releases when nobody answers.
- A payment cannot be approved by the person who created it.

### Should have

- Rules a family can read and understand: thresholds, trusted payees, quiet hours.
- Evidence checks for the rent case: listing photos, ownership record, video tour agreement.
- Evidence checks for the scam case: new payee, gift card or crypto category, urgency and secrecy language.
- A scheduled payment that completes silently, to prove the product stays quiet.

### Will not have

- Multi-currency conversion.
- A mobile app.
- Chat.
- Identity verification flows.
- A second payment provider.
- An admin panel.
- Dark mode.
- Crypto.
- Lending, credit, or investing.

Each of those is a day that does not exist. Build only what the three scenarios need.

---

## 9. How the risk decision is made

The decision is a short, readable checklist, not a hidden model. A family should be able to read the rules and predict what will happen. That is what makes it trustworthy.

The checks are grouped by how much they matter:

- **Strong warning signs.** A brand new payee. A payee tied to a known scam pattern. Gift cards, crypto, or wire transfers. An amount far above the person's normal spending. Messages that combine urgency and secrecy.
- **Medium warning signs.** Listing or document details that do not match. A new country for this payer. An unusual time of day.
- **Weak warning signs.** A payee who has been quiet for a long time. An amount close to the family limit. Two payments to the same payee within an hour.
- **Reassuring signs.** A payee who has been paid successfully several times. A payment that matches an existing schedule. A payee the co-signer has approved before.

Most payments fall in the "nothing to worry about" band and pass silently. Some fall in the "ask someone" band. A few strong cases always ask, plus a deliberate wait for first-time payees.

### What the AI does, and does not do

The AI has exactly three jobs:

1. Read messy text, like chats, notes, and receipts, and pull out the warning signs.
2. Write the one sentence a person can act on.
3. Draft the follow-up message after a payment is stopped.

The AI never decides whether money moves. The rules decide. The AI explains. That distinction matters to users, judges, and regulators.

---

## 10. The rules that must never be broken

**Winny never holds, pools, or stores customer money.**

The moment money sits in an account the product controls, it becomes a licensed financial activity. There is no family exemption in the US, the UK, the EU, or India. The money always moves directly from one person's own PayPal to the recipient.

### Never build

1. A balance. No family wallet, no top up, no stored value.
2. A pool. No collecting money from three siblings into one place.
3. Custody. No holding a deposit in an escrow account the product controls.
4. A transfer between two Winny users that bypasses PayPal.
5. A promise of protection the product cannot keep. Winny is not an insurer.

### The family pot, done legally

The instinct is right, the implementation is not. It is a plan, not a balance. "This month the family needs $2,400 for Meera." Each member pays their share directly to the final recipient. Winny shows progress: $900 of $2,400 funded, by whom. The money never passes through Winny.

### Words to use and avoid

Say: "We never hold your money." "PayPal authorises, a person you trust co-signs, then it captures." "We are a second opinion, not insurance." "Most payments pass silently."

Never say: bank, wallet, deposit, pot, balance, custody, escrow account, "we protect you from all scams", "we hold the money until it is safe", "our AI decides".

One wrong word in a demo turns a good project into a compliance question.

### Honest limits

Person-to-person payments generally carry no buyer protection. Winny deals with exactly the kind of payments that protection excludes. Never suggest otherwise.

On the approval screen, say once: "Winny is a second opinion, not insurance. If you approve a payment, it goes through."

On a stopped payment receipt, say: "We stopped this because of the reasons above. We cannot guarantee every scam will be caught."

---

## 11. Principles

1. Never hold money. The product records decisions, it never becomes the middleman for funds.
2. Ask, do not block. A blocked payment starts a fight. A question starts a decision.
3. Evidence with the ask. Send the reason, not just the alert.
4. Silence is the default. Most payments pass. The product earns its place by speaking rarely.
5. The record is shared. Everyone sees the same history.
6. Reversible beats fast. A hold that costs thirty seconds is cheaper than a scam that costs a month.

---

## 12. Success measures

- Share of payments that pass without a co-sign: above 85 percent. Below that, the product is annoying.
- Time from hold to co-signer decision: under 10 minutes.
- Value of stopped payments per family per year.
- False positives, meaning good payments that were held: under 10 percent.
- Co-signer approval rate. If it goes above 95 percent, the risk check is miscalibrated or the evidence is too weak.

---

## 13. What done looks like

The product is done when this is true:

A stranger can open the app, start a payment, see it held, read a plain-English reason, approve or stop it from a second account, and see the correct outcome in the shared history, live, without anyone touching the database.

Everything else is decoration.

### Never cut

- The hold. Without it there is no product.
- The stop path. A demo where nothing gets stopped is a demo of a payment button.
- The automatic case. Without it the product looks annoying.
- The plain-English reason. Without it the co-signer is guessing.

---

## 14. Current status

### Ready

- Product definition, positioning, principles, and the three scenarios.
- A 10-slide pitch deck covering the shift, the gap, the product, the demo, the wedge, the business model, competition, timing, and the ask.
- The core payment idea has been written down and tested in theory.

### Not ready yet

- The core money flow has not been proven end to end yet. Until it is, no copy or slide may claim a working demo.
- There is no visible product screen yet. The biggest open decision is whether the demo is a plain terminal record or a single simple screen showing hold, co-sign request, stop, and receipt.
- The submission materials are not planned yet: demo video script, recording, repository link, deck link, and submission form copy.

### Next decisions, in order

1. Prove the core flow works before building any screen.
2. Choose the demo surface: plain record or one simple screen.
3. Plan the submission materials and the recording schedule.
4. Rehearse the three scenarios until the demo is boring.
5. Only then polish anything.

---

## 15. Risks to watch

| Risk | Why it matters | What to do |
|---|---|---|
| Described as a bank or wallet | Turns a product into a compliance question | Fixed vocabulary, reviewed before every recording |
| Core money flow does not behave as expected | The whole demo depends on it | Prove it first, have an honest fallback |
| Co-signer approves a scam | Product trust breaks | Show evidence, use the liability line, keep the shared record |
| Consent fatigue | People delete the product | Default to silence, use limits and quiet hours |
| The demo looks scripted | Judges stop believing it | One live approval, one live stop, one honest limitation |
| Running out of time | No submission | Cut from the bottom of the requirement list, never the four essentials |

---

## 16. Demo plan

**Framing.** "We are not a wallet and we do not hold funds. Every payment goes directly between two people. What we own is the decision in the middle."

**The mechanic.** A normal checkout sends money immediately. Winny reserves it first, then asks a person. That gap is the product.

**The live story.** Run the rent scenario: hold, reason, evidence, co-signer, stop, receipt. Then show the monthly allowance completing silently, so nobody thinks the product asks every time. Then the honest close.

**The honest close.** "We are a second opinion, not insurance. Sometimes we will be wrong. But the record shows exactly what the family saw when they decided, and that is more than any bank statement gives you."

**Show live:** the hold being created, the reason, the co-signer decision, the released money.
**Pre-record as backup:** the full walkthrough, the notification arriving, the gift card scenario, the automatic allowance.

---

## 17. Questions the judges will ask

**Why not just call your kid?** Because people do not call. The call is awkward, and the awkwardness is exactly why scams work. Winny removes the call for the boring cases and makes the dangerous cases automatic.

**Isn't this just a spending limit?** A limit says no at the register and embarrasses the person. Winny asks a specific person a specific question with evidence, and lets the payment through when it is fine.

**What stops the co-signer from rubber-stamping?** One line of evidence and one tap, kept cheap on purpose. If approvals pass 95 percent, the checks are miscalibrated, and that is a number to watch.

**Why PayPal?** Because the hold, the payment network, and the payout rails already exist, and money can move person to person without Winny becoming a financial institution.

**What if the co-signer approves a scam?** The record shows what they saw and when they approved. Winny never claims to be insurance. A later version would add a mandatory wait for first-time payees.

**Is this legal?** Yes, because Winny never holds or moves money itself. Every payment is a direct PayPal transaction between two people. Winny stores decisions, not funds.

---

## 18. Business thinking, short version

The product is infrastructure, not a consumer app. The consumer family circle proves the idea. The business is a consent layer that other products license: banks, marketplaces, agent platforms, and payment companies that need a human approval step before an agent spends.

The wedge is the authorization hold plus the co-sign decision. Allowance apps and scheduled transfers already exist and are commoditised. A scheduled transfer cannot ask a person mid-payment, because the money has already left. Winny can, because the money is only reserved.

Revenue thinking, in order of preference: a platform fee to businesses that embed the consent layer, a per-active-family subscription, or a small fee per held payment. Never a take rate on the money itself.

---

## 19. Working agreements

1. Product language only in user-facing copy. No technical jargon, no endpoint names, no database talk.
2. Never describe Winny as a wallet, bank, escrow, or balance product.
3. Never claim a working demo until the core flow has been proven.
4. Small, focused changes. New files rather than rewrites.
5. Cut scope before cutting quality on the four essentials.
6. Rehearse the demo until it is boring.
7. No em dashes in any copy.
