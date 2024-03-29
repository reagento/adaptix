from adaptix import DebugTrail, Retort

external_retort = Retort(
    recipe=[
        # very complex configuration
    ],
)

# create retort to faster load data from an internal trusted source
# where it already validated
internal_retort = external_retort.replace(
    strict_coercion=False,
    debug_trail=DebugTrail.DISABLE,
)
