import googlenlp

# Clause finder states
# State strings
_STATE_NAMES = [
    "ROOT_FIND",
    "NSUBJ_FIND",
    "ISA_FIND"
]

STATE_LIMIT = len(_STATE_NAMES)
for i in range(len(_STATE_NAMES)):
    exec('%s = googlenlp.tag.ConstantTag(%i, _STATE_NAMES[%i])' % (_STATE_NAMES[i], i, i))

