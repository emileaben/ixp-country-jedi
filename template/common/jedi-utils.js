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
      var txt = '<pre>{0}</pre>'.format( data['tracetxt'] );
      jquery_elt.html( txt );
   });
}


// Display the source and destination ASN of each cell
function jedi_cell_show_source_dest_asn( proto, src_as , dst_as , source_asn, dest_asn, pageX, pageY) {


        source_asn.style("display", "block");  //The tooltip appears
        dest_asn.style("display", "block");  //The tooltip appears
        
        source_asn.html( "Source ASN: <b>" + src_as +"</b>"  )
        .style("left", pageX - 220 + "px") 
        .style("top", pageY - 15 + "px");

        dest_asn.html( "Dest ASN: <b>" + dst_as +"</b>"  )
        .style("left", pageX - 110 + "px") 
        .style("top", pageY - 70 + "px");
              
}

// Display the traceroute information
function jedi_cell_show_traceroute_on_click( proto, src_id , dst_id , traceroute_detail, pageX, pageY) {


  json_file = "../common/details/{0}/{1}/{2}/latest.json".format( proto, src_id, dst_id );
  $.ajax({url: json_file, 
    async: true
  }).done(function( data ) {
    var txt = '<button style="text-align:center" type="button" onclick="close_details(0)">Close</button> <pre>{0}</pre>'.format( data['tracetxt'] );
    traceroute_detail.style("display", "block"); 

    traceroute_detail.html( txt )
      .style("left", (pageX + 20) + "px") 
      .style("top", pageY + "px")
  });
              
}