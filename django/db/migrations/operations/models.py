from django.db import models
from django.db.migrations.operations.base import Operation
from django.db.migrations.state import ModelState
from django.db.migrations.utils import field_references, resolve_relation
from django.db.models.options import normalize_together
from django.utils.functional import cached_property

from .fields import AddField, AlterField, FieldOperation, RemoveField, RenameField


# [TODO] _check_for_duplicates
def _check_for_duplicates(arg_name, objs):
    used_vals = set()
    for val in objs:
        if val in used_vals:
            raise ValueError(
                "Found duplicate value %s in CreateModel %s argument." % (val, arg_name)
            )
        used_vals.add(val)


# [TODO] ModelOperation
class ModelOperation(Operation):
    # [TODO] ModelOperation > __init__
    def __init__(self, name):
        self.name = name

    # [TODO] ModelOperation > name_lower
    @cached_property
    def name_lower(self):
        return self.name.lower()

    # [TODO] ModelOperation > references_model
    def references_model(self, name, app_label):
        return name.lower() == self.name_lower

    # [TODO] ModelOperation > reduce
    def reduce(self, operation, app_label):
        return super().reduce(operation, app_label) or self.can_reduce_through(
            operation, app_label
        )

    # [TODO] ModelOperation > can_reduce_through
    def can_reduce_through(self, operation, app_label):
        return not operation.references_model(self.name, app_label)


# [TODO] CreateModel
class CreateModel(ModelOperation):
    """Create a model's table."""

    serialization_expand_args = ["fields", "options", "managers"]

    # [TODO] CreateModel > __init__
    def __init__(self, name, fields, options=None, bases=None, managers=None):
        self.fields = fields
        self.options = options or {}
        self.bases = bases or (models.Model,)
        self.managers = managers or []
        super().__init__(name)
        # Sanity-check that there are no duplicated field names, bases, or
        # manager names
        _check_for_duplicates("fields", (name for name, _ in self.fields))
        _check_for_duplicates(
            "bases",
            (
                base._meta.label_lower
                if hasattr(base, "_meta")
                else base.lower()
                if isinstance(base, str)
                else base
                for base in self.bases
            ),
        )
        _check_for_duplicates("managers", (name for name, _ in self.managers))

    # [TODO] CreateModel > deconstruct
    def deconstruct(self):
        kwargs = {
            "name": self.name,
            "fields": self.fields,
        }
        if self.options:
            kwargs["options"] = self.options
        if self.bases and self.bases != (models.Model,):
            kwargs["bases"] = self.bases
        if self.managers and self.managers != [("objects", models.Manager())]:
            kwargs["managers"] = self.managers
        return (self.__class__.__qualname__, [], kwargs)

    # [TODO] CreateModel > state_forwards
    def state_forwards(self, app_label, state):
        state.add_model(
            ModelState(
                app_label,
                self.name,
                list(self.fields),
                dict(self.options),
                tuple(self.bases),
                list(self.managers),
            )
        )

    # [TODO] CreateModel > database_forwards
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            schema_editor.create_model(model)

    # [TODO] CreateModel > database_backwards
    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        model = from_state.apps.get_model(app_label, self.name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            schema_editor.delete_model(model)

    # [TODO] CreateModel > describe
    def describe(self):
        return "Create %smodel %s" % (
            "proxy " if self.options.get("proxy", False) else "",
            self.name,
        )

    # [TODO] CreateModel > migration_name_fragment
    @property
    def migration_name_fragment(self):
        return self.name_lower

    # [TODO] CreateModel > references_model
    def references_model(self, name, app_label):
        name_lower = name.lower()
        if name_lower == self.name_lower:
            return True

        # Check we didn't inherit from the model
        reference_model_tuple = (app_label, name_lower)
        for base in self.bases:
            if (
                base is not models.Model
                and isinstance(base, (models.base.ModelBase, str))
                and resolve_relation(base, app_label) == reference_model_tuple
            ):
                return True

        # Check we have no FKs/M2Ms with it
        for _name, field in self.fields:
            if field_references(
                (app_label, self.name_lower), field, reference_model_tuple
            ):
                return True
        return False

    # [TODO] CreateModel > reduce
    def reduce(self, operation, app_label):
        if (
            isinstance(operation, DeleteModel)
            and self.name_lower == operation.name_lower
            and not self.options.get("proxy", False)
        ):
            return []
        elif (
            isinstance(operation, RenameModel)
            and self.name_lower == operation.old_name_lower
        ):
            return [
                CreateModel(
                    operation.new_name,
                    fields=self.fields,
                    options=self.options,
                    bases=self.bases,
                    managers=self.managers,
                ),
            ]
        elif (
            isinstance(operation, AlterModelOptions)
            and self.name_lower == operation.name_lower
        ):
            options = {**self.options, **operation.options}
            for key in operation.ALTER_OPTION_KEYS:
                if key not in operation.options:
                    options.pop(key, None)
            return [
                CreateModel(
                    self.name,
                    fields=self.fields,
                    options=options,
                    bases=self.bases,
                    managers=self.managers,
                ),
            ]
        elif (
            isinstance(operation, AlterModelManagers)
            and self.name_lower == operation.name_lower
        ):
            return [
                CreateModel(
                    self.name,
                    fields=self.fields,
                    options=self.options,
                    bases=self.bases,
                    managers=operation.managers,
                ),
            ]
        elif (
            isinstance(operation, AlterTogetherOptionOperation)
            and self.name_lower == operation.name_lower
        ):
            return [
                CreateModel(
                    self.name,
                    fields=self.fields,
                    options={
                        **self.options,
                        **{operation.option_name: operation.option_value},
                    },
                    bases=self.bases,
                    managers=self.managers,
                ),
            ]
        elif (
            isinstance(operation, AlterOrderWithRespectTo)
            and self.name_lower == operation.name_lower
        ):
            return [
                CreateModel(
                    self.name,
                    fields=self.fields,
                    options={
                        **self.options,
                        "order_with_respect_to": operation.order_with_respect_to,
                    },
                    bases=self.bases,
                    managers=self.managers,
                ),
            ]
        elif (
            isinstance(operation, FieldOperation)
            and self.name_lower == operation.model_name_lower
        ):
            if isinstance(operation, AddField):
                return [
                    CreateModel(
                        self.name,
                        fields=self.fields + [(operation.name, operation.field)],
                        options=self.options,
                        bases=self.bases,
                        managers=self.managers,
                    ),
                ]
            elif isinstance(operation, AlterField):
                return [
                    CreateModel(
                        self.name,
                        fields=[
                            (n, operation.field if n == operation.name else v)
                            for n, v in self.fields
                        ],
                        options=self.options,
                        bases=self.bases,
                        managers=self.managers,
                    ),
                ]
            elif isinstance(operation, RemoveField):
                options = self.options.copy()
                for option_name in ("unique_together", "index_together"):
                    option = options.pop(option_name, None)
                    if option:
                        option = set(
                            filter(
                                bool,
                                (
                                    tuple(
                                        f for f in fields if f != operation.name_lower
                                    )
                                    for fields in option
                                ),
                            )
                        )
                        if option:
                            options[option_name] = option
                order_with_respect_to = options.get("order_with_respect_to")
                if order_with_respect_to == operation.name_lower:
                    del options["order_with_respect_to"]
                return [
                    CreateModel(
                        self.name,
                        fields=[
                            (n, v)
                            for n, v in self.fields
                            if n.lower() != operation.name_lower
                        ],
                        options=options,
                        bases=self.bases,
                        managers=self.managers,
                    ),
                ]
            elif isinstance(operation, RenameField):
                options = self.options.copy()
                for option_name in ("unique_together", "index_together"):
                    option = options.get(option_name)
                    if option:
                        options[option_name] = {
                            tuple(
                                operation.new_name if f == operation.old_name else f
                                for f in fields
                            )
                            for fields in option
                        }
                order_with_respect_to = options.get("order_with_respect_to")
                if order_with_respect_to == operation.old_name:
                    options["order_with_respect_to"] = operation.new_name
                return [
                    CreateModel(
                        self.name,
                        fields=[
                            (operation.new_name if n == operation.old_name else n, v)
                            for n, v in self.fields
                        ],
                        options=options,
                        bases=self.bases,
                        managers=self.managers,
                    ),
                ]
        elif (
            isinstance(operation, IndexOperation)
            and self.name_lower == operation.model_name_lower
        ):
            if isinstance(operation, AddIndex):
                return [
                    CreateModel(
                        self.name,
                        fields=self.fields,
                        options={
                            **self.options,
                            "indexes": [
                                *self.options.get("indexes", []),
                                operation.index,
                            ],
                        },
                        bases=self.bases,
                        managers=self.managers,
                    ),
                ]
            elif isinstance(operation, RemoveIndex):
                options_indexes = [
                    index
                    for index in self.options.get("indexes", [])
                    if index.name != operation.name
                ]
                return [
                    CreateModel(
                        self.name,
                        fields=self.fields,
                        options={
                            **self.options,
                            "indexes": options_indexes,
                        },
                        bases=self.bases,
                        managers=self.managers,
                    ),
                ]
            elif isinstance(operation, RenameIndex) and operation.old_fields:
                options_index_together = {
                    fields
                    for fields in self.options.get("index_together", [])
                    if fields != operation.old_fields
                }
                if options_index_together:
                    self.options["index_together"] = options_index_together
                else:
                    self.options.pop("index_together", None)
                return [
                    CreateModel(
                        self.name,
                        fields=self.fields,
                        options={
                            **self.options,
                            "indexes": [
                                *self.options.get("indexes", []),
                                models.Index(
                                    fields=operation.old_fields, name=operation.new_name
                                ),
                            ],
                        },
                        bases=self.bases,
                        managers=self.managers,
                    ),
                ]
        return super().reduce(operation, app_label)


# [TODO] DeleteModel
class DeleteModel(ModelOperation):
    """Drop a model's table."""

    # [TODO] DeleteModel > deconstruct
    def deconstruct(self):
        kwargs = {
            "name": self.name,
        }
        return (self.__class__.__qualname__, [], kwargs)

    # [TODO] DeleteModel > state_forwards
    def state_forwards(self, app_label, state):
        state.remove_model(app_label, self.name_lower)

    # [TODO] DeleteModel > database_forwards
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = from_state.apps.get_model(app_label, self.name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            schema_editor.delete_model(model)

    # [TODO] DeleteModel > database_backwards
    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            schema_editor.create_model(model)

    # [TODO] DeleteModel > references_model
    def references_model(self, name, app_label):
        # The deleted model could be referencing the specified model through
        # related fields.
        return True

    # [TODO] DeleteModel > describe
    def describe(self):
        return "Delete model %s" % self.name

    # [TODO] DeleteModel > migration_name_fragment
    @property
    def migration_name_fragment(self):
        return "delete_%s" % self.name_lower


# [TODO] RenameModel
class RenameModel(ModelOperation):
    """Rename a model."""

    # [TODO] RenameModel > __init__
    def __init__(self, old_name, new_name):
        self.old_name = old_name
        self.new_name = new_name
        super().__init__(old_name)

    # [TODO] RenameModel > old_name_lower
    @cached_property
    def old_name_lower(self):
        return self.old_name.lower()

    # [TODO] RenameModel > new_name_lower
    @cached_property
    def new_name_lower(self):
        return self.new_name.lower()

    # [TODO] RenameModel > deconstruct
    def deconstruct(self):
        kwargs = {
            "old_name": self.old_name,
            "new_name": self.new_name,
        }
        return (self.__class__.__qualname__, [], kwargs)

    # [TODO] RenameModel > state_forwards
    def state_forwards(self, app_label, state):
        state.rename_model(app_label, self.old_name, self.new_name)

    # [TODO] RenameModel > database_forwards
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        new_model = to_state.apps.get_model(app_label, self.new_name)
        if self.allow_migrate_model(schema_editor.connection.alias, new_model):
            old_model = from_state.apps.get_model(app_label, self.old_name)
            # Move the main table
            schema_editor.alter_db_table(
                new_model,
                old_model._meta.db_table,
                new_model._meta.db_table,
            )
            # Alter the fields pointing to us
            for related_object in old_model._meta.related_objects:
                if related_object.related_model == old_model:
                    model = new_model
                    related_key = (app_label, self.new_name_lower)
                else:
                    model = related_object.related_model
                    related_key = (
                        related_object.related_model._meta.app_label,
                        related_object.related_model._meta.model_name,
                    )
                to_field = to_state.apps.get_model(*related_key)._meta.get_field(
                    related_object.field.name
                )
                schema_editor.alter_field(
                    model,
                    related_object.field,
                    to_field,
                )
            # Rename M2M fields whose name is based on this model's name.
            fields = zip(
                old_model._meta.local_many_to_many, new_model._meta.local_many_to_many
            )
            for old_field, new_field in fields:
                # Skip self-referential fields as these are renamed above.
                if (
                    new_field.model == new_field.related_model
                    or not new_field.remote_field.through._meta.auto_created
                ):
                    continue
                # Rename columns and the M2M table.
                schema_editor._alter_many_to_many(
                    new_model,
                    old_field,
                    new_field,
                    strict=False,
                )

    # [TODO] RenameModel > database_backwards
    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        self.new_name_lower, self.old_name_lower = (
            self.old_name_lower,
            self.new_name_lower,
        )
        self.new_name, self.old_name = self.old_name, self.new_name

        self.database_forwards(app_label, schema_editor, from_state, to_state)

        self.new_name_lower, self.old_name_lower = (
            self.old_name_lower,
            self.new_name_lower,
        )
        self.new_name, self.old_name = self.old_name, self.new_name

    # [TODO] RenameModel > references_model
    def references_model(self, name, app_label):
        return (
            name.lower() == self.old_name_lower or name.lower() == self.new_name_lower
        )

    # [TODO] RenameModel > describe
    def describe(self):
        return "Rename model %s to %s" % (self.old_name, self.new_name)

    # [TODO] RenameModel > migration_name_fragment
    @property
    def migration_name_fragment(self):
        return "rename_%s_%s" % (self.old_name_lower, self.new_name_lower)

    # [TODO] RenameModel > reduce
    def reduce(self, operation, app_label):
        if (
            isinstance(operation, RenameModel)
            and self.new_name_lower == operation.old_name_lower
        ):
            return [
                RenameModel(
                    self.old_name,
                    operation.new_name,
                ),
            ]
        # Skip `ModelOperation.reduce` as we want to run `references_model`
        # against self.new_name.
        return super(ModelOperation, self).reduce(
            operation, app_label
        ) or not operation.references_model(self.new_name, app_label)


# [TODO] ModelOptionOperation
class ModelOptionOperation(ModelOperation):
    # [TODO] ModelOptionOperation > reduce
    def reduce(self, operation, app_label):
        if (
            isinstance(operation, (self.__class__, DeleteModel))
            and self.name_lower == operation.name_lower
        ):
            return [operation]
        return super().reduce(operation, app_label)


# [TODO] AlterModelTable
class AlterModelTable(ModelOptionOperation):
    """Rename a model's table."""

    # [TODO] AlterModelTable > __init__
    def __init__(self, name, table):
        self.table = table
        super().__init__(name)

    # [TODO] AlterModelTable > deconstruct
    def deconstruct(self):
        kwargs = {
            "name": self.name,
            "table": self.table,
        }
        return (self.__class__.__qualname__, [], kwargs)

    # [TODO] AlterModelTable > state_forwards
    def state_forwards(self, app_label, state):
        state.alter_model_options(app_label, self.name_lower, {"db_table": self.table})

    # [TODO] AlterModelTable > database_forwards
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        new_model = to_state.apps.get_model(app_label, self.name)
        if self.allow_migrate_model(schema_editor.connection.alias, new_model):
            old_model = from_state.apps.get_model(app_label, self.name)
            schema_editor.alter_db_table(
                new_model,
                old_model._meta.db_table,
                new_model._meta.db_table,
            )
            # Rename M2M fields whose name is based on this model's db_table
            for old_field, new_field in zip(
                old_model._meta.local_many_to_many, new_model._meta.local_many_to_many
            ):
                if new_field.remote_field.through._meta.auto_created:
                    schema_editor.alter_db_table(
                        new_field.remote_field.through,
                        old_field.remote_field.through._meta.db_table,
                        new_field.remote_field.through._meta.db_table,
                    )

    # [TODO] AlterModelTable > database_backwards
    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        return self.database_forwards(app_label, schema_editor, from_state, to_state)

    # [TODO] AlterModelTable > describe
    def describe(self):
        return "Rename table for %s to %s" % (
            self.name,
            self.table if self.table is not None else "(default)",
        )

    # [TODO] AlterModelTable > migration_name_fragment
    @property
    def migration_name_fragment(self):
        return "alter_%s_table" % self.name_lower


# [TODO] AlterModelTableComment
class AlterModelTableComment(ModelOptionOperation):
    # [TODO] AlterModelTableComment > __init__
    def __init__(self, name, table_comment):
        self.table_comment = table_comment
        super().__init__(name)

    # [TODO] AlterModelTableComment > deconstruct
    def deconstruct(self):
        kwargs = {
            "name": self.name,
            "table_comment": self.table_comment,
        }
        return (self.__class__.__qualname__, [], kwargs)

    # [TODO] AlterModelTableComment > state_forwards
    def state_forwards(self, app_label, state):
        state.alter_model_options(
            app_label, self.name_lower, {"db_table_comment": self.table_comment}
        )

    # [TODO] AlterModelTableComment > database_forwards
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        new_model = to_state.apps.get_model(app_label, self.name)
        if self.allow_migrate_model(schema_editor.connection.alias, new_model):
            old_model = from_state.apps.get_model(app_label, self.name)
            schema_editor.alter_db_table_comment(
                new_model,
                old_model._meta.db_table_comment,
                new_model._meta.db_table_comment,
            )

    # [TODO] AlterModelTableComment > database_backwards
    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        return self.database_forwards(app_label, schema_editor, from_state, to_state)

    # [TODO] AlterModelTableComment > describe
    def describe(self):
        return f"Alter {self.name} table comment"

    # [TODO] AlterModelTableComment > migration_name_fragment
    @property
    def migration_name_fragment(self):
        return f"alter_{self.name_lower}_table_comment"


# [TODO] AlterTogetherOptionOperation
class AlterTogetherOptionOperation(ModelOptionOperation):
    option_name = None

    # [TODO] AlterTogetherOptionOperation > __init__
    def __init__(self, name, option_value):
        if option_value:
            option_value = set(normalize_together(option_value))
        setattr(self, self.option_name, option_value)
        super().__init__(name)

    # [TODO] AlterTogetherOptionOperation > option_value
    @cached_property
    def option_value(self):
        return getattr(self, self.option_name)

    # [TODO] AlterTogetherOptionOperation > deconstruct
    def deconstruct(self):
        kwargs = {
            "name": self.name,
            self.option_name: self.option_value,
        }
        return (self.__class__.__qualname__, [], kwargs)

    # [TODO] AlterTogetherOptionOperation > state_forwards
    def state_forwards(self, app_label, state):
        state.alter_model_options(
            app_label,
            self.name_lower,
            {self.option_name: self.option_value},
        )

    # [TODO] AlterTogetherOptionOperation > database_forwards
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        new_model = to_state.apps.get_model(app_label, self.name)
        if self.allow_migrate_model(schema_editor.connection.alias, new_model):
            old_model = from_state.apps.get_model(app_label, self.name)
            alter_together = getattr(schema_editor, "alter_%s" % self.option_name)
            alter_together(
                new_model,
                getattr(old_model._meta, self.option_name, set()),
                getattr(new_model._meta, self.option_name, set()),
            )

    # [TODO] AlterTogetherOptionOperation > database_backwards
    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        return self.database_forwards(app_label, schema_editor, from_state, to_state)

    # [TODO] AlterTogetherOptionOperation > references_field
    def references_field(self, model_name, name, app_label):
        return self.references_model(model_name, app_label) and (
            not self.option_value
            or any((name in fields) for fields in self.option_value)
        )

    # [TODO] AlterTogetherOptionOperation > describe
    def describe(self):
        return "Alter %s for %s (%s constraint(s))" % (
            self.option_name,
            self.name,
            len(self.option_value or ""),
        )

    # [TODO] AlterTogetherOptionOperation > migration_name_fragment
    @property
    def migration_name_fragment(self):
        return "alter_%s_%s" % (self.name_lower, self.option_name)

    # [TODO] AlterTogetherOptionOperation > can_reduce_through
    def can_reduce_through(self, operation, app_label):
        return super().can_reduce_through(operation, app_label) or (
            isinstance(operation, AlterTogetherOptionOperation)
            and type(operation) is not type(self)
        )


# [TODO] AlterUniqueTogether
class AlterUniqueTogether(AlterTogetherOptionOperation):
    """
    Change the value of unique_together to the target one.
    Input value of unique_together must be a set of tuples.
    """

    option_name = "unique_together"

    # [TODO] AlterUniqueTogether > __init__
    def __init__(self, name, unique_together):
        super().__init__(name, unique_together)


# [TODO] AlterIndexTogether
class AlterIndexTogether(AlterTogetherOptionOperation):
    """
    Change the value of index_together to the target one.
    Input value of index_together must be a set of tuples.
    """

    option_name = "index_together"

    # [TODO] AlterIndexTogether > __init__
    def __init__(self, name, index_together):
        super().__init__(name, index_together)


# [TODO] AlterOrderWithRespectTo
class AlterOrderWithRespectTo(ModelOptionOperation):
    """Represent a change with the order_with_respect_to option."""

    option_name = "order_with_respect_to"

    # [TODO] AlterOrderWithRespectTo > __init__
    def __init__(self, name, order_with_respect_to):
        self.order_with_respect_to = order_with_respect_to
        super().__init__(name)

    # [TODO] AlterOrderWithRespectTo > deconstruct
    def deconstruct(self):
        kwargs = {
            "name": self.name,
            "order_with_respect_to": self.order_with_respect_to,
        }
        return (self.__class__.__qualname__, [], kwargs)

    # [TODO] AlterOrderWithRespectTo > state_forwards
    def state_forwards(self, app_label, state):
        state.alter_model_options(
            app_label,
            self.name_lower,
            {self.option_name: self.order_with_respect_to},
        )

    # [TODO] AlterOrderWithRespectTo > database_forwards
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        to_model = to_state.apps.get_model(app_label, self.name)
        if self.allow_migrate_model(schema_editor.connection.alias, to_model):
            from_model = from_state.apps.get_model(app_label, self.name)
            # Remove a field if we need to
            if (
                from_model._meta.order_with_respect_to
                and not to_model._meta.order_with_respect_to
            ):
                schema_editor.remove_field(
                    from_model, from_model._meta.get_field("_order")
                )
            # Add a field if we need to (altering the column is untouched as
            # it's likely a rename)
            elif (
                to_model._meta.order_with_respect_to
                and not from_model._meta.order_with_respect_to
            ):
                field = to_model._meta.get_field("_order")
                if not field.has_default():
                    field.default = 0
                schema_editor.add_field(
                    from_model,
                    field,
                )

    # [TODO] AlterOrderWithRespectTo > database_backwards
    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        self.database_forwards(app_label, schema_editor, from_state, to_state)

    # [TODO] AlterOrderWithRespectTo > references_field
    def references_field(self, model_name, name, app_label):
        return self.references_model(model_name, app_label) and (
            self.order_with_respect_to is None or name == self.order_with_respect_to
        )

    # [TODO] AlterOrderWithRespectTo > describe
    def describe(self):
        return "Set order_with_respect_to on %s to %s" % (
            self.name,
            self.order_with_respect_to,
        )

    # [TODO] AlterOrderWithRespectTo > migration_name_fragment
    @property
    def migration_name_fragment(self):
        return "alter_%s_order_with_respect_to" % self.name_lower


# [TODO] AlterModelOptions
class AlterModelOptions(ModelOptionOperation):
    """
    Set new model options that don't directly affect the database schema
    (like verbose_name, permissions, ordering). Python code in migrations
    may still need them.
    """

    # Model options we want to compare and preserve in an AlterModelOptions op
    ALTER_OPTION_KEYS = [
        "base_manager_name",
        "default_manager_name",
        "default_related_name",
        "get_latest_by",
        "managed",
        "ordering",
        "permissions",
        "default_permissions",
        "select_on_save",
        "verbose_name",
        "verbose_name_plural",
    ]

    # [TODO] AlterModelOptions > __init__
    def __init__(self, name, options):
        self.options = options
        super().__init__(name)

    # [TODO] AlterModelOptions > deconstruct
    def deconstruct(self):
        kwargs = {
            "name": self.name,
            "options": self.options,
        }
        return (self.__class__.__qualname__, [], kwargs)

    # [TODO] AlterModelOptions > state_forwards
    def state_forwards(self, app_label, state):
        state.alter_model_options(
            app_label,
            self.name_lower,
            self.options,
            self.ALTER_OPTION_KEYS,
        )

    # [TODO] AlterModelOptions > database_forwards
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        pass

    # [TODO] AlterModelOptions > database_backwards
    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        pass

    # [TODO] AlterModelOptions > describe
    def describe(self):
        return "Change Meta options on %s" % self.name

    # [TODO] AlterModelOptions > migration_name_fragment
    @property
    def migration_name_fragment(self):
        return "alter_%s_options" % self.name_lower


# [TODO] AlterModelManagers
class AlterModelManagers(ModelOptionOperation):
    """Alter the model's managers."""

    serialization_expand_args = ["managers"]

    # [TODO] AlterModelManagers > __init__
    def __init__(self, name, managers):
        self.managers = managers
        super().__init__(name)

    # [TODO] AlterModelManagers > deconstruct
    def deconstruct(self):
        return (self.__class__.__qualname__, [self.name, self.managers], {})

    # [TODO] AlterModelManagers > state_forwards
    def state_forwards(self, app_label, state):
        state.alter_model_managers(app_label, self.name_lower, self.managers)

    # [TODO] AlterModelManagers > database_forwards
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        pass

    # [TODO] AlterModelManagers > database_backwards
    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        pass

    # [TODO] AlterModelManagers > describe
    def describe(self):
        return "Change managers on %s" % self.name

    # [TODO] AlterModelManagers > migration_name_fragment
    @property
    def migration_name_fragment(self):
        return "alter_%s_managers" % self.name_lower


# [TODO] IndexOperation
class IndexOperation(Operation):
    option_name = "indexes"

    # [TODO] IndexOperation > model_name_lower
    @cached_property
    def model_name_lower(self):
        return self.model_name.lower()


# [TODO] AddIndex
class AddIndex(IndexOperation):
    """Add an index on a model."""

    # [TODO] AddIndex > __init__
    def __init__(self, model_name, index):
        self.model_name = model_name
        if not index.name:
            raise ValueError(
                "Indexes passed to AddIndex operations require a name "
                "argument. %r doesn't have one." % index
            )
        self.index = index

    # [TODO] AddIndex > state_forwards
    def state_forwards(self, app_label, state):
        state.add_index(app_label, self.model_name_lower, self.index)

    # [TODO] AddIndex > database_forwards
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            schema_editor.add_index(model, self.index)

    # [TODO] AddIndex > database_backwards
    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        model = from_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            schema_editor.remove_index(model, self.index)

    # [TODO] AddIndex > deconstruct
    def deconstruct(self):
        kwargs = {
            "model_name": self.model_name,
            "index": self.index,
        }
        return (
            self.__class__.__qualname__,
            [],
            kwargs,
        )

    # [TODO] AddIndex > describe
    def describe(self):
        if self.index.expressions:
            return "Create index %s on %s on model %s" % (
                self.index.name,
                ", ".join([str(expression) for expression in self.index.expressions]),
                self.model_name,
            )
        return "Create index %s on field(s) %s of model %s" % (
            self.index.name,
            ", ".join(self.index.fields),
            self.model_name,
        )

    # [TODO] AddIndex > migration_name_fragment
    @property
    def migration_name_fragment(self):
        return "%s_%s" % (self.model_name_lower, self.index.name.lower())

    # [TODO] AddIndex > reduce
    def reduce(self, operation, app_label):
        if isinstance(operation, RemoveIndex) and self.index.name == operation.name:
            return []
        if isinstance(operation, RenameIndex) and self.index.name == operation.old_name:
            self.index.name = operation.new_name
            return [AddIndex(model_name=self.model_name, index=self.index)]
        return super().reduce(operation, app_label)


# [TODO] RemoveIndex
class RemoveIndex(IndexOperation):
    """Remove an index from a model."""

    # [TODO] RemoveIndex > __init__
    def __init__(self, model_name, name):
        self.model_name = model_name
        self.name = name

    # [TODO] RemoveIndex > state_forwards
    def state_forwards(self, app_label, state):
        state.remove_index(app_label, self.model_name_lower, self.name)

    # [TODO] RemoveIndex > database_forwards
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = from_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            from_model_state = from_state.models[app_label, self.model_name_lower]
            index = from_model_state.get_index_by_name(self.name)
            schema_editor.remove_index(model, index)

    # [TODO] RemoveIndex > database_backwards
    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            to_model_state = to_state.models[app_label, self.model_name_lower]
            index = to_model_state.get_index_by_name(self.name)
            schema_editor.add_index(model, index)

    # [TODO] RemoveIndex > deconstruct
    def deconstruct(self):
        kwargs = {
            "model_name": self.model_name,
            "name": self.name,
        }
        return (
            self.__class__.__qualname__,
            [],
            kwargs,
        )

    # [TODO] RemoveIndex > describe
    def describe(self):
        return "Remove index %s from %s" % (self.name, self.model_name)

    # [TODO] RemoveIndex > migration_name_fragment
    @property
    def migration_name_fragment(self):
        return "remove_%s_%s" % (self.model_name_lower, self.name.lower())


# [TODO] RenameIndex
class RenameIndex(IndexOperation):
    """Rename an index."""

    # [TODO] RenameIndex > __init__
    def __init__(self, model_name, new_name, old_name=None, old_fields=None):
        if not old_name and not old_fields:
            raise ValueError(
                "RenameIndex requires one of old_name and old_fields arguments to be "
                "set."
            )
        if old_name and old_fields:
            raise ValueError(
                "RenameIndex.old_name and old_fields are mutually exclusive."
            )
        self.model_name = model_name
        self.new_name = new_name
        self.old_name = old_name
        self.old_fields = old_fields

    # [TODO] RenameIndex > old_name_lower
    @cached_property
    def old_name_lower(self):
        return self.old_name.lower()

    # [TODO] RenameIndex > new_name_lower
    @cached_property
    def new_name_lower(self):
        return self.new_name.lower()

    # [TODO] RenameIndex > deconstruct
    def deconstruct(self):
        kwargs = {
            "model_name": self.model_name,
            "new_name": self.new_name,
        }
        if self.old_name:
            kwargs["old_name"] = self.old_name
        if self.old_fields:
            kwargs["old_fields"] = self.old_fields
        return (self.__class__.__qualname__, [], kwargs)

    # [TODO] RenameIndex > state_forwards
    def state_forwards(self, app_label, state):
        if self.old_fields:
            state.add_index(
                app_label,
                self.model_name_lower,
                models.Index(fields=self.old_fields, name=self.new_name),
            )
            state.remove_model_options(
                app_label,
                self.model_name_lower,
                AlterIndexTogether.option_name,
                self.old_fields,
            )
        else:
            state.rename_index(
                app_label, self.model_name_lower, self.old_name, self.new_name
            )

    # [TODO] RenameIndex > database_forwards
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        if not self.allow_migrate_model(schema_editor.connection.alias, model):
            return

        if self.old_fields:
            from_model = from_state.apps.get_model(app_label, self.model_name)
            columns = [
                from_model._meta.get_field(field).column for field in self.old_fields
            ]
            matching_index_name = schema_editor._constraint_names(
                from_model, column_names=columns, index=True
            )
            if len(matching_index_name) != 1:
                raise ValueError(
                    "Found wrong number (%s) of indexes for %s(%s)."
                    % (
                        len(matching_index_name),
                        from_model._meta.db_table,
                        ", ".join(columns),
                    )
                )
            old_index = models.Index(
                fields=self.old_fields,
                name=matching_index_name[0],
            )
        else:
            from_model_state = from_state.models[app_label, self.model_name_lower]
            old_index = from_model_state.get_index_by_name(self.old_name)
        # Don't alter when the index name is not changed.
        if old_index.name == self.new_name:
            return

        to_model_state = to_state.models[app_label, self.model_name_lower]
        new_index = to_model_state.get_index_by_name(self.new_name)
        schema_editor.rename_index(model, old_index, new_index)

    # [TODO] RenameIndex > database_backwards
    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        if self.old_fields:
            # Backward operation with unnamed index is a no-op.
            return

        self.new_name_lower, self.old_name_lower = (
            self.old_name_lower,
            self.new_name_lower,
        )
        self.new_name, self.old_name = self.old_name, self.new_name

        self.database_forwards(app_label, schema_editor, from_state, to_state)

        self.new_name_lower, self.old_name_lower = (
            self.old_name_lower,
            self.new_name_lower,
        )
        self.new_name, self.old_name = self.old_name, self.new_name

    # [TODO] RenameIndex > describe
    def describe(self):
        if self.old_name:
            return (
                f"Rename index {self.old_name} on {self.model_name} to {self.new_name}"
            )
        return (
            f"Rename unnamed index for {self.old_fields} on {self.model_name} to "
            f"{self.new_name}"
        )

    # [TODO] RenameIndex > migration_name_fragment
    @property
    def migration_name_fragment(self):
        if self.old_name:
            return "rename_%s_%s" % (self.old_name_lower, self.new_name_lower)
        return "rename_%s_%s_%s" % (
            self.model_name_lower,
            "_".join(self.old_fields),
            self.new_name_lower,
        )

    # [TODO] RenameIndex > reduce
    def reduce(self, operation, app_label):
        if (
            isinstance(operation, RenameIndex)
            and self.model_name_lower == operation.model_name_lower
            and operation.old_name
            and self.new_name_lower == operation.old_name_lower
        ):
            return [
                RenameIndex(
                    self.model_name,
                    new_name=operation.new_name,
                    old_name=self.old_name,
                    old_fields=self.old_fields,
                )
            ]
        return super().reduce(operation, app_label)


# [TODO] AddConstraint
class AddConstraint(IndexOperation):
    option_name = "constraints"

    # [TODO] AddConstraint > __init__
    def __init__(self, model_name, constraint):
        self.model_name = model_name
        self.constraint = constraint

    # [TODO] AddConstraint > state_forwards
    def state_forwards(self, app_label, state):
        state.add_constraint(app_label, self.model_name_lower, self.constraint)

    # [TODO] AddConstraint > database_forwards
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            schema_editor.add_constraint(model, self.constraint)

    # [TODO] AddConstraint > database_backwards
    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            schema_editor.remove_constraint(model, self.constraint)

    # [TODO] AddConstraint > deconstruct
    def deconstruct(self):
        return (
            self.__class__.__name__,
            [],
            {
                "model_name": self.model_name,
                "constraint": self.constraint,
            },
        )

    # [TODO] AddConstraint > describe
    def describe(self):
        return "Create constraint %s on model %s" % (
            self.constraint.name,
            self.model_name,
        )

    # [TODO] AddConstraint > migration_name_fragment
    @property
    def migration_name_fragment(self):
        return "%s_%s" % (self.model_name_lower, self.constraint.name.lower())

    # [TODO] AddConstraint > reduce
    def reduce(self, operation, app_label):
        if (
            isinstance(operation, RemoveConstraint)
            and self.model_name_lower == operation.model_name_lower
            and self.constraint.name == operation.name
        ):
            return []
        return super().reduce(operation, app_label)


# [TODO] RemoveConstraint
class RemoveConstraint(IndexOperation):
    option_name = "constraints"

    # [TODO] RemoveConstraint > __init__
    def __init__(self, model_name, name):
        self.model_name = model_name
        self.name = name

    # [TODO] RemoveConstraint > state_forwards
    def state_forwards(self, app_label, state):
        state.remove_constraint(app_label, self.model_name_lower, self.name)

    # [TODO] RemoveConstraint > database_forwards
    def database_forwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            from_model_state = from_state.models[app_label, self.model_name_lower]
            constraint = from_model_state.get_constraint_by_name(self.name)
            schema_editor.remove_constraint(model, constraint)

    # [TODO] RemoveConstraint > database_backwards
    def database_backwards(self, app_label, schema_editor, from_state, to_state):
        model = to_state.apps.get_model(app_label, self.model_name)
        if self.allow_migrate_model(schema_editor.connection.alias, model):
            to_model_state = to_state.models[app_label, self.model_name_lower]
            constraint = to_model_state.get_constraint_by_name(self.name)
            schema_editor.add_constraint(model, constraint)

    # [TODO] RemoveConstraint > deconstruct
    def deconstruct(self):
        return (
            self.__class__.__name__,
            [],
            {
                "model_name": self.model_name,
                "name": self.name,
            },
        )

    # [TODO] RemoveConstraint > describe
    def describe(self):
        return "Remove constraint %s from model %s" % (self.name, self.model_name)

    # [TODO] RemoveConstraint > migration_name_fragment
    @property
    def migration_name_fragment(self):
        return "remove_%s_%s" % (self.model_name_lower, self.name.lower())