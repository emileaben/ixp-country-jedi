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

// requires files in the right place
// requires jquery to have been loaded
// args:
//   d: d3 data elt
//   jquery_elt: a jquery_elt to put the resulting html at
function jedi_cell_detail_to_jquery_elt( proto, src_id , dst_id , jquery_elt ) {
   json_file = "../common/details/{0}/{1}/{2}/latest.json".format( proto, src_id, dst_id );
   $.ajax({url: json_file, 
      async: true
   }).done(function( data ) {
      var txt = '<pre>{0}</pre>'.format(data['tracetxt']);
      if (typeof(data['traixroute']) !== 'undefined') { 

        txt += '<pre>Name of IXP: <b>{0}</b></br>'.format(data['traixroute'][0]['name']);
        txt += 'IXP on hop: <b>{0}</b></br>'.format(data['traixroute'][0]['hop']); 
        txt += 'IXP on the same country? <b>{0}</b> </pre>'.format(data['traixroute'][0]['in_country']); 

      }
      jquery_elt.html( txt );
   });
}
