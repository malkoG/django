from django.db import DatabaseError


# [TODO] AmbiguityError
class AmbiguityError(Exception):
    """More than one migration matches a name prefix."""

    pass


# [TODO] BadMigrationError
class BadMigrationError(Exception):
    """There's a bad migration (unreadable/bad format/etc.)."""

    pass


# [TODO] CircularDependencyError
class CircularDependencyError(Exception):
    """There's an impossible-to-resolve circular dependency."""

    pass


# [TODO] InconsistentMigrationHistory
class InconsistentMigrationHistory(Exception):
    """An applied migration has some of its dependencies not applied."""

    pass


# [TODO] InvalidBasesError
class InvalidBasesError(ValueError):
    """A model's base classes can't be resolved."""

    pass


# [TODO] IrreversibleError
class IrreversibleError(RuntimeError):
    """An irreversible migration is about to be reversed."""

    pass


# [TODO] NodeNotFoundError
class NodeNotFoundError(LookupError):
    """An attempt on a node is made that is not available in the graph."""

    # [TODO] NodeNotFoundError > __init__
    def __init__(self, message, node, origin=None):
        self.message = message
        self.origin = origin
        self.node = node

    # [TODO] NodeNotFoundError > __str__
    def __str__(self):
        return self.message

    # [TODO] NodeNotFoundError > __repr__
    def __repr__(self):
        return "NodeNotFoundError(%r)" % (self.node,)


# [TODO] MigrationSchemaMissing
class MigrationSchemaMissing(DatabaseError):
    pass


# [TODO] InvalidMigrationPlan
class InvalidMigrationPlan(ValueError):
    pass