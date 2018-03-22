define(['jquery', '//s7.addthis.com/js/300/addthis_widget.js'], function($) {
	function ShareBar(element) {
		if (window.addthis_config) {
			return;
		}
		window.addthis_config = {
		  pubid: "prestosports",
		  username: "prestosports",
		  services_exclude: 'facebook, twitter, google_plusone_share, email, printfriendly, print',
		  services_compact: 'favorites, myspace, stumbleupon, reddit, digg, pinterest, delicious, linkedin, pdfmyurl',
		  data_track_clickback: false
		}
		addthis.init();
		
		$(window).on('historychanged', function(e, data) {
			var config = $.extend(true, {}, window.addthis_config),
	        	share = $.extend(true, {}, window.addthis_share);
	        
	        if (data.title) {
		        share.title = data.title;
	        }
	        if (data.url) {
	        	share.url = data.url;
	        }
	        $('[data-module="share-buttons"]').each(function() {
	        	addthis.toolbox(this, config, share);
	        });
		});
	};
	return ShareBar;
});