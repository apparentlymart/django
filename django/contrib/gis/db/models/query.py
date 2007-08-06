import operator
from django.core.exceptions import ImproperlyConfigured
from django.db import backend
from django.db.models.query import Q, QuerySet
from django.db.models.fields import FieldDoesNotExist
from django.contrib.gis.db.models.fields import GeometryField
from django.contrib.gis.db.backend import parse_lookup # parse_lookup depends on the spatial database backend.

class GeoQ(Q):
    "Geographical query encapsulation object."

    def get_sql(self, opts):
        "Overloaded to use our own parse_lookup() function."
        return parse_lookup(self.kwargs.items(), opts)

class GeoQuerySet(QuerySet):
    "Geographical-enabled QuerySet object."

    def __init__(self, model=None):
        super(GeoQuerySet, self).__init__(model=model)

        # We only want to use the GeoQ object for our queries
        self._filters = GeoQ()

    def _filter_or_exclude(self, mapper, *args, **kwargs):
        # mapper is a callable used to transform Q objects,
        # or None for identity transform
        if mapper is None:
            mapper = lambda x: x
        if len(args) > 0 or len(kwargs) > 0:
            assert self._limit is None and self._offset is None, \
                "Cannot filter a query once a slice has been taken."

        clone = self._clone()
        if len(kwargs) > 0:
            clone._filters = clone._filters & mapper(GeoQ(**kwargs)) # Using the GeoQ object for our filters instead
        if len(args) > 0:
            clone._filters = clone._filters & reduce(operator.and_, map(mapper, args))
        return clone

    def kml(self, field_name, precision=8):
        """Returns KML representation of the given field name in a `kml` 
        attribute on each element of the QuerySet."""
        # Is KML output supported?
        try:
            from django.contrib.gis.db.backend.postgis import ASKML
        except ImportError:
            raise ImproperlyConfigured, 'AsKML() only available in PostGIS versions 1.2.1 and greater.'

        # Is the given field name a geographic field?
        field = self.model._meta.get_field(field_name)
        if not isinstance(field, GeometryField):
            raise TypeError, 'KML output only available on GeometryField fields.'
        field_col = "%s.%s" % (backend.quote_name(self.model._meta.db_table),
                               backend.quote_name(field.column))
        
        # Adding the AsKML function call to the SELECT part of the SQL.
        return self.extra(select={'kml':'%s(%s,%s)' % (ASKML, field_col, precision)})
