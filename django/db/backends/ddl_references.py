"""
Helpers to manipulate deferred DDL statements that might need to be adjusted or
discarded within when executing a migration.
"""
from copy import deepcopy


# [TODO] Reference
class Reference:
    """Base class that defines the reference interface."""

    # [TODO] Reference > references_table
    def references_table(self, table):
        """
        Return whether or not this instance references the specified table.
        """
        return False

    # [TODO] Reference > references_column
    def references_column(self, table, column):
        """
        Return whether or not this instance references the specified column.
        """
        return False

    # [TODO] Reference > rename_table_references
    def rename_table_references(self, old_table, new_table):
        """
        Rename all references to the old_name to the new_table.
        """
        pass

    # [TODO] Reference > rename_column_references
    def rename_column_references(self, table, old_column, new_column):
        """
        Rename all references to the old_column to the new_column.
        """
        pass

    # [TODO] Reference > __repr__
    def __repr__(self):
        return "<%s %r>" % (self.__class__.__name__, str(self))

    # [TODO] Reference > __str__
    def __str__(self):
        raise NotImplementedError(
            "Subclasses must define how they should be converted to string."
        )


# [TODO] Table
class Table(Reference):
    """Hold a reference to a table."""

    # [TODO] Table > __init__
    def __init__(self, table, quote_name):
        self.table = table
        self.quote_name = quote_name

    # [TODO] Table > references_table
    def references_table(self, table):
        return self.table == table

    # [TODO] Table > rename_table_references
    def rename_table_references(self, old_table, new_table):
        if self.table == old_table:
            self.table = new_table

    # [TODO] Table > __str__
    def __str__(self):
        return self.quote_name(self.table)


# [TODO] TableColumns
class TableColumns(Table):
    """Base class for references to multiple columns of a table."""

    # [TODO] TableColumns > __init__
    def __init__(self, table, columns):
        self.table = table
        self.columns = columns

    # [TODO] TableColumns > references_column
    def references_column(self, table, column):
        return self.table == table and column in self.columns

    # [TODO] TableColumns > rename_column_references
    def rename_column_references(self, table, old_column, new_column):
        if self.table == table:
            for index, column in enumerate(self.columns):
                if column == old_column:
                    self.columns[index] = new_column


# [TODO] Columns
class Columns(TableColumns):
    """Hold a reference to one or many columns."""

    # [TODO] Columns > __init__
    def __init__(self, table, columns, quote_name, col_suffixes=()):
        self.quote_name = quote_name
        self.col_suffixes = col_suffixes
        super().__init__(table, columns)

    # [TODO] Columns > __str__
    def __str__(self):
        def col_str(column, idx):
            col = self.quote_name(column)
            try:
                suffix = self.col_suffixes[idx]
                if suffix:
                    col = "{} {}".format(col, suffix)
            except IndexError:
                pass
            return col

        return ", ".join(
            col_str(column, idx) for idx, column in enumerate(self.columns)
        )


# [TODO] IndexName
class IndexName(TableColumns):
    """Hold a reference to an index name."""

    # [TODO] IndexName > __init__
    def __init__(self, table, columns, suffix, create_index_name):
        self.suffix = suffix
        self.create_index_name = create_index_name
        super().__init__(table, columns)

    # [TODO] IndexName > __str__
    def __str__(self):
        return self.create_index_name(self.table, self.columns, self.suffix)


# [TODO] IndexColumns
class IndexColumns(Columns):
    # [TODO] IndexColumns > __init__
    def __init__(self, table, columns, quote_name, col_suffixes=(), opclasses=()):
        self.opclasses = opclasses
        super().__init__(table, columns, quote_name, col_suffixes)

    # [TODO] IndexColumns > __str__
    def __str__(self):
        def col_str(column, idx):
            # Index.__init__() guarantees that self.opclasses is the same
            # length as self.columns.
            col = "{} {}".format(self.quote_name(column), self.opclasses[idx])
            try:
                suffix = self.col_suffixes[idx]
                if suffix:
                    col = "{} {}".format(col, suffix)
            except IndexError:
                pass
            return col

        return ", ".join(
            col_str(column, idx) for idx, column in enumerate(self.columns)
        )


# [TODO] ForeignKeyName
class ForeignKeyName(TableColumns):
    """Hold a reference to a foreign key name."""

    # [TODO] ForeignKeyName > __init__
    def __init__(
        self,
        from_table,
        from_columns,
        to_table,
        to_columns,
        suffix_template,
        create_fk_name,
    ):
        self.to_reference = TableColumns(to_table, to_columns)
        self.suffix_template = suffix_template
        self.create_fk_name = create_fk_name
        super().__init__(
            from_table,
            from_columns,
        )

    # [TODO] ForeignKeyName > references_table
    def references_table(self, table):
        return super().references_table(table) or self.to_reference.references_table(
            table
        )

    # [TODO] ForeignKeyName > references_column
    def references_column(self, table, column):
        return super().references_column(
            table, column
        ) or self.to_reference.references_column(table, column)

    # [TODO] ForeignKeyName > rename_table_references
    def rename_table_references(self, old_table, new_table):
        super().rename_table_references(old_table, new_table)
        self.to_reference.rename_table_references(old_table, new_table)

    # [TODO] ForeignKeyName > rename_column_references
    def rename_column_references(self, table, old_column, new_column):
        super().rename_column_references(table, old_column, new_column)
        self.to_reference.rename_column_references(table, old_column, new_column)

    # [TODO] ForeignKeyName > __str__
    def __str__(self):
        suffix = self.suffix_template % {
            "to_table": self.to_reference.table,
            "to_column": self.to_reference.columns[0],
        }
        return self.create_fk_name(self.table, self.columns, suffix)


# [TODO] Statement
class Statement(Reference):
    """
    Statement template and formatting parameters container.

    Allows keeping a reference to a statement without interpolating identifiers
    that might have to be adjusted if they're referencing a table or column
    that is removed
    """

    # [TODO] Statement > __init__
    def __init__(self, template, **parts):
        self.template = template
        self.parts = parts

    # [TODO] Statement > references_table
    def references_table(self, table):
        return any(
            hasattr(part, "references_table") and part.references_table(table)
            for part in self.parts.values()
        )

    # [TODO] Statement > references_column
    def references_column(self, table, column):
        return any(
            hasattr(part, "references_column") and part.references_column(table, column)
            for part in self.parts.values()
        )

    # [TODO] Statement > rename_table_references
    def rename_table_references(self, old_table, new_table):
        for part in self.parts.values():
            if hasattr(part, "rename_table_references"):
                part.rename_table_references(old_table, new_table)

    # [TODO] Statement > rename_column_references
    def rename_column_references(self, table, old_column, new_column):
        for part in self.parts.values():
            if hasattr(part, "rename_column_references"):
                part.rename_column_references(table, old_column, new_column)

    # [TODO] Statement > __str__
    def __str__(self):
        return self.template % self.parts


# [TODO] Expressions
class Expressions(TableColumns):
    # [TODO] Expressions > __init__
    def __init__(self, table, expressions, compiler, quote_value):
        self.compiler = compiler
        self.expressions = expressions
        self.quote_value = quote_value
        columns = [
            col.target.column
            for col in self.compiler.query._gen_cols([self.expressions])
        ]
        super().__init__(table, columns)

    # [TODO] Expressions > rename_table_references
    def rename_table_references(self, old_table, new_table):
        if self.table != old_table:
            return
        self.expressions = self.expressions.relabeled_clone({old_table: new_table})
        super().rename_table_references(old_table, new_table)

    # [TODO] Expressions > rename_column_references
    def rename_column_references(self, table, old_column, new_column):
        if self.table != table:
            return
        expressions = deepcopy(self.expressions)
        self.columns = []
        for col in self.compiler.query._gen_cols([expressions]):
            if col.target.column == old_column:
                col.target.column = new_column
            self.columns.append(col.target.column)
        self.expressions = expressions

    # [TODO] Expressions > __str__
    def __str__(self):
        sql, params = self.compiler.compile(self.expressions)
        params = map(self.quote_value, params)
        return sql % tuple(params)