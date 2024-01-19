Due to refactoring of predicate system required for new features:

1. ``create_request_checker`` was renamed to ``create_loc_stack_checker``
2. ``LocStackPattern`` (class of ``P``) was renamed ``RequestPattern``
3. method ``RequestPattern.build_request_checker()`` was renamed to ``LocStackPattern.build_loc_stack_checker()``
