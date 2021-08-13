//index/torrents crossover js
var torrent_id = 0;
var torrentModal = '';
var singleHistoryTable = '';

$(document).ready(function() {
	torrentModal = $('#torrent-modal');
	$('.torrent-modal-close').on('click', function() {
		torrentModal.hide();
	});
	
	function getID() {
		return torrent_id;
	}

	singleHistoryTable = $('#single_history_table').DataTable( {
		"ajax": {
			"url": $SCRIPT_ROOT + '/_single_history_table',
			"contentType": "application/json",
			"type": 'POST',
			"data": function(d) {
				return JSON.stringify(d.id = getID());
			}
		},
		"stateSave": true,	
		"deferRender": true,
		"scrollX": true,
		"order": [[0, 'desc']],
		"pageLength": 25,
		"select": false,
		"dom": 'Blrtip',
		"buttons": [
			{
				extend: 'colvis'
			}
		],
		"pagingType": "full_numbers",
		"autoWidth": false,
		"columns": [
			{ data: 0, width: "62px", render: function(data, type, row) {
					if ( type === 'display' || type === 'filter' ) {
						if (data === null) {
							return "N/A";
						}
						else {
							return moment.unix(data).format('L');
						}
					}
					return data;
				}
			},
			{ data: 1, render: $.fn.dataTable.render.percentBar('round', '#ffffff', '#00b300', '#00b300', '#006600', 1, 'solid') },
			{ data: 2, width: "73px", render: function(data, type, row) {
					if ( type === 'display' || type === 'filter' ) {
						if (data > 0) {
							return "<div class='downloaded'>" + formatBytes(data) + "</div>";
						}
						else {	
							return formatBytes(data);
						}
					}
					return data;
				}
			},
			{ data: 3, width: "56px", render: function(data, type, row) {
					if ( type === 'display' || type === 'filter' ) {
						if (data > 0) {
							return "<div class='uploaded'>" + formatBytes(data) + "</div>";
						}
						else {	
							return formatBytes(data);
						}
					}
					return data;
				}
			},
			{ data: 4, width: "66px", render: function(data, type, row) {
					if ( type === 'display' || type === 'filter' ) {
						if (row[2] > 0) {
							return "<div class='downloaded'>" + formatBytes(data) + "</div>";
						}
						else {	
							return formatBytes(data);
						}
					}
					return data;
				}
			},
			{ data: 5, width: "50px", render: function(data, type, row) {
					if ( type === 'display' || type === 'filter' ) {
						if (row[3] > 0) {
							return "<div class='uploaded'>" + formatBytes(data) + "</div>";
						}
						else {	
							return formatBytes(data);
						}
					}
					return data;
				}
			},
			{ data: 6, width: "45px", render: function(data, type, row) {
					return data.toFixed(3);
				}
			}
		]
	});
});