
# Profile Architecture

The system supports multiple operational contexts.

A human account may act as:

Primary user  
Advisor  
Nominee  

Profiles isolate these roles.

---

## Account

Represents authentication identity.

Each human has exactly one account.

---

## Profile

Represents operational context.

Types

PRIMARY
ADVISOR
NOMINEE

---

## ProfileAccess

Maps advisor or nominee profiles to primary profiles.

Example

Advisor → multiple primary profiles  
Nominee → multiple primary profiles

---

## Isolation Rules

Queries must always be scoped to active profile.

Cross profile access is prohibited.
