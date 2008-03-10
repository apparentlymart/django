from django.conf import settings
from django.contrib.gis import geos
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

# Declaring the GoogleMapException prior to getting the 
# default `GZOOM` GoogleZoom instance.
class GoogleMapException(Exception): pass
from django.contrib.gis.maps.google.overlays import GPolygon, GPolyline
from django.contrib.gis.maps.google.zoom import GoogleZoom
GZOOM = GoogleZoom()

# The default Google Maps URL (for the API javascript)
# TODO: Internationalize for Japan, UK, etc.
GOOGLE_MAPS_URL='http://maps.google.com/maps?file=api&amp;v=%s&amp;key='

class GoogleMap(object):
    "A class for generating Google Maps JavaScript."

    # String constants
    onunload = mark_safe('onunload="GUnload()"') # Cleans up after Google Maps
    vml_css  = mark_safe('v\:* {behavior:url(#default#VML);}') # CSS for IE VML
    xmlns    = mark_safe('xmlns:v="urn:schemas-microsoft-com:vml"') # XML Namespace (for IE VML).

    def __init__(self, key=None, api_url=None, version=None,
                 center=None, center_lat=0.0, center_lon=0.0,
                 zoom=None, dom_id='map', load_func='gmap_load', 
                 kml_urls=[], polygons=[], polylines=[],
                 template='gis/google/js/google-map.js',
                 extra_context={}):

        # The Google Maps API Key defined in the settings will be used
        #  if not passed in as a parameter.  The use of an API key is
        #  _required_.
        if not key:
            try:
                self.key = settings.GOOGLE_MAPS_API_KEY
            except AttributeError:
                raise GoogleMapException('Google Maps API Key not found (try adding GOOGLE_MAPS_API_KEY to your settings).')
        else:
            self.key = key
        
        # Getting the Google Maps API version, defaults to using the latest ("2.x"),
        #  this is not necessarily the most stable.
        if not version:
            self.version = getattr(settings, 'GOOGLE_MAPS_API_VERSION', '2.x')
        else:
            self.version = version

        # Can specify the API URL in the `api_url` keyword.
        if not api_url:
            self.api_url = mark_safe(getattr(settings, 'GOOGLE_MAPS_URL', GOOGLE_MAPS_URL) % self.version)
        else:
            self.api_url = api_url

        # Setting the DOM id of the map, the load function, the JavaScript
        # template, and the KML URLs array.
        self.dom_id = dom_id
        self.load_func = load_func
        self.template = template
        self.kml_urls = kml_urls
        
        # Does the user want any GPolygon or GPolyline overlays?
        self.polygons, self.polylines = [], []
        if polygons:
            for poly in polygons:
                if isinstance(poly, GPolygon): 
                    self.polygons.append(poly)
                else:
                    self.polygons.append(GPolygon(poly))
        if polylines:
            for pline in polylines:
                if isinstance(pline, GPolyline):
                    self.polylines.append(pline)
                else:
                    self.polylines.append(GPolyline(pline))
       
        # Automatically determining the zoom level if there are
        # GPolygon and/or GPolyline overlays.
        if (self.polygons or self.polylines) and zoom is None:
            envelopes = [p.envelope for p in self.polygons]
            envelopes.extend([p.envelope for p in self.polylines])
            # Creating a MultiPolygon of all the envelopes, this will
            # be used in determining the zoom level.
            zoom = geos.MultiPolygon(envelopes)
            zoom.srid = 4326
        
        # If a GEOSGeometry object is passed in for the `zoom` keyword
        # argument, then try to automatically determine an appropriate
        # zoom level.
        if isinstance(zoom, geos.GEOSGeometry):
            self.zoom = GZOOM.get_zoom(zoom)
        else:
            self.zoom = zoom

        # The map center coordinate -- the `center_lon` and `center_lat` keyword
        # are deprecated.
        if not center:
            center = (center_lon, center_lat)
        self.center = center

        # Setting the parameters for the javascript template.
        params = {'center' : self.center,
                  'dom_id' : self.dom_id,
                  'kml_urls' : self.kml_urls,
                  'load_func' : self.load_func,
                  'zoom' : self.zoom,
                  'polygons' : self.polygons,
                  'polylines' : self.polylines,
                  }
        params.update(extra_context)
        self.js = render_to_string(self.template, params)

    @property
    def body(self):
        "Returns HTML body tag for loading and unloading Google Maps javascript."
        return mark_safe('<body %s %s>' % (self.onload, self.onunload))

    @property
    def onload(self):
        "Returns the `onload` HTML <body> attribute."
        return mark_safe('onload="%s()"' % self.load_func)

    @property
    def api_script(self):
        "Returns the <script> tag for the Google Maps API javascript."
        return mark_safe('<script src="%s%s" type="text/javascript"></script>' % (self.api_url, self.key))

    @property
    def scripts(self):
        "Returns all <script></script> tags required for Google Maps JavaScript."
        return mark_safe('%s\n  <script type="text/javascript">\n//<![CDATA[\n%s//]]>\n  </script>' % (self.api_script, self.js))

    @property
    def style(self):
        "Returns additional CSS styling needed for Google Maps on IE."
        return mark_safe('<style type="text/css">%s</style>' % self.vml_css)

    @property
    def xhtml(self):
        "Returns XHTML information needed for IE VML overlays."
        return mark_safe('<html xmlns="http://www.w3.org/1999/xhtml" %s>' % self.xmlns)
