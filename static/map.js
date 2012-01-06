$(document).ready(function() {

    $('.search-results .map').each(function() {

        var map = new L.Map(this, {
            center: new L.LatLng(46, 25.0),
            zoom: 6
        });

        var osm_url = 'http://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png'
        var osm = new L.TileLayer(osm_url, {maxZoom: 18});
        map.addLayer(osm);

        var shapes = new L.GeoJSON();
        map.addLayer(shapes);

        var sitecode_hash = {};
        $('.search-results .sitecode').each(function() {
            var code = $(this).text();
            sitecode_hash[code] = true;
        });
        var keep = function(code) { return sitecode_hash[code]; };

        $.getJSON(R.assets + 'sci-wgs84.geojson', function(data) {
            data['features'] = filter_features(data['features'], keep);
            shapes.addGeoJSON(data);
        });

        $.getJSON(R.assets + 'spa-wgs84.geojson', function(data) {
            data['features'] = filter_features(data['features'], keep);
            shapes.addGeoJSON(data);
        });

        function filter_features(features, keep) {
            return $.map(features, function(feature) {
                var sitecode = feature['properties']['SITECODE'];
                if(keep(sitecode)) {
                    return feature;
                }
            });
        }

    });

});
