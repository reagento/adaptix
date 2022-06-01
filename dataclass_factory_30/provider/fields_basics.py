"""This module contains essential concepts of fields.

Crown defines how external structure
should be mapped to constructor fields and vice versa
and defines the policy of extra data processing.

NoneCrown means that item of dict or list maps to nothing.

This structure is named in honor of the crown of the tree.

For example,
InpDictCrown(
    {
        'a': FieldCrown('x'),
        'b': ListCrown(
            {
                0: FieldCrown('y'),
                1: FieldCrown('z'),
                2: NoneCrown(DefaultValue(10)),
            },
            extra=ExtraForbid(),
        ),
    },
    extra=ExtraCollect(),
)
means that:
    x = data['a']
    y = data['b'][0]
    z = data['b'][1]

    List at data['b'] can have only 3 elements
    and value of element with index 2 is ignored.
    If

    Dict `data` can contain additional keys
    that will be collected and passed to constructor
    according to FigureExtra of Figure.

ListCrown (it's map field) can not contain indexes gaps.
Each field
"""

#
#
#
#
#
