// .format() for strings
// First, checks if it isn't implemented yet.
if (!String.prototype.format) {
  String.prototype.format = function() {
    var args = arguments;
    return this.replace(/{(\d+)}/g, function(match, number) { 
      return typeof args[number] != 'undefined'
        ? args[number]
        : match
      ;
    });
  };
}

var maps = {
   'v4': undefined,
   'v6': undefined,
};

var center = new L.LatLng(52,4);

var myStyle = {
   'className': '.animatedpath',
   'weight': 2
};

function initmap() {
   // set up the map
   var osmAttrib='Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors';
   var mapqUrl='http://otile1.mqcdn.com/tiles/1.0.0/map/{z}/{x}/{y}.jpg';

   var map_v4 = new L.Map('map_v4');
   map_v4.setView([20, 0], 12);
   var osm4 = new L.TileLayer(mapqUrl, {attribution: osmAttrib});
   map_v4.addLayer(osm4);

   var map_v6 = new L.Map('map_v6');
   map_v6.setView([20, 0], 12);
   var osm6 = new L.TileLayer(mapqUrl, {attribution: osmAttrib});
   map_v6.addLayer(osm6);
   maps = {
      'v4': map_v4,
      'v6': map_v6,
   };
   map_v4.sync( map_v6 );
   map_v6.sync( map_v4 );

/*var osmUrl='http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
   var osmAttrib='Map data &copy; <a href="http://openstreetmap.org">OpenStreetMap</a> contributors';
   var osm = new L.TileLayer(osmUrl, {attribution: osmAttrib});      
   map.addLayer(osm);
   */

   /*var blackmarble = L.tileLayer('http://{s}.tiles.earthatlas.info/black-marble/{z}/{x}/{y}.png', {
      attribution: 'Map imagery by <a href="http://www.nasa.gov/mission_pages/NPP/news/earth-at-night.html">NASA Earth Observatory/NOAA NGDC</a>',
      maxZoom: 6
   });
   map.addLayer(blackmarble);
   */

   var svg = d3.select(maps['v4'].getPanes().overlayPane).append("svg"),
   g = svg.append("g").attr("class", "leaflet-zoom-hide");

   function onEachFeature(feature, layer) {
      //console.log( feature, layer );
   }
   function doStyle( feature ) {
      var locStyle = myStyle;
      if ( feature.properties.is_direct == false ) {
         locStyle.dashArray = '2,10,2,10';
         locStyle['opacity'] = 0.25;
      } else {
         locStyle.dashArray = '10,10,3,10';
         locStyle['opacity'] = 0.70;
      }
      /* if ( feature.properties.sasn == 1299 || feature.properties.dasn == 1299) {
         locStyle['color'] = "#ff7800";
         locStyle['opacity'] = 0.80;
      } else { */
      //locStyle['color'] = "#1f78b4";
      locStyle['color'] = "#191970"
      return locStyle;
   }
   ['v4','v6'].map( function( proto ) {
      $.getJSON( "geopath.{0}.json".format( proto ), function( geodata ) {
         gjlayer = L.geoJson(geodata,{
            style: doStyle,
            onEachFeature: onEachFeature
         }).addTo(maps[ proto ]);
         // fit map to features
         if ( maps[ proto ].getZoom() > maps[proto].getBoundsZoom( gjlayer.getBounds() ) ) {
            maps[ proto ].fitBounds( gjlayer.getBounds() );
         }
      });
   });

}
