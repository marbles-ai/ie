# -*- coding: utf-8 -*-
from __future__ import unicode_literals, print_function

## @{
## @ingroup gconst
## @defgroup reftypes DRS Referent Types

RT_PROPERNAME    = 0x0000000000000001
RT_ENTITY        = 0x0000000000000002
RT_EVENT         = 0x0000000000000004
RT_LOCATION      = 0x0000000000000008
RT_DIRECTION     = 0x0000000000000010
RT_DATE          = 0x0000000000000020
RT_WEEKDAY       = 0x0000000000000040
RT_MONTH         = 0x0000000000000080
RT_HUMAN         = 0x0000000000000100
RT_ANAPHORA      = 0x0000000000000200
RT_NUMBER        = 0x0000000000000400
RT_UNION         = 0x0000000000000800
RT_NEGATE        = 0x0000000000001000
RT_INTERSECTION  = 0x0000000000002000
# Adjunct
RT_EVENT_ATTRIB  = 0x0000000000004000
RT_EVENT_MODAL   = 0x0000000000008000
RT_ATTRIBUTE     = 0x0000000000010000
# Clausal Adjucts - adverbial phrases
RT_ADJUNCT       = 0x0000000000020000
RT_PP            = 0x0000000000040000

RT_RELATIVE      = 0x8000000000000000
RT_PLURAL        = 0x4000000000000000
RT_MALE          = 0x2000000000000000
RT_FEMALE        = 0x1000000000000000
RT_1P            = 0x0800000000000000
RT_2P            = 0x0400000000000000
RT_3P            = 0x0200000000000000
RT_ORPHANED      = 0x0100000000000000
RT_EMPTY_DRS     = 0x0080000000000000
RT_POSSESSIVE    = 0x0040000000000000
## @}


## @{
## @ingroup gconst
## @defgroup ccg2drs_const CCG to DRS Constants

## Compose option: remove propositions containing single referent in the subordinate DRS.
CO_REMOVE_UNARY_PROPS = 0x0001
## Compose option: print derivations to stdout during production
CO_PRINT_DERIVATION = 0x0002
## Compose option: verify signature during production
CO_VERIFY_SIGNATURES = 0x0004
## Build state slots
CO_BUILD_STATES = 0x0010
## Add state predicates
CO_ADD_STATE_PREDICATES = 0x0020
## Disable Verbnet
CO_NO_VERBNET = 0x0040
## Fast Renaming
CO_FAST_RENAME = 0x0080
## Disable wikipedia search for constituents
CO_NO_WIKI_SEARCH = 0x0100
## Discard constituents with adjuncts
CO_DISCARD_ADJUCT_CONSTITUENTS = 0x0400

## @}



