//torrents page

$(document).ready(function() {
	$(window).on('click', function(e) {
		if (e.target == torrentModal[0]) {
			torrentModal.hide();
		}
	});
	
	var fullTable = $('#torrents_table').DataTable( {
		"ajax": $SCRIPT_ROOT + '/_full_table',
		"stateSave": true,
		"stateSaveParams": function (settings, data) {
			data.search.search = "";
			data.columns[0].visible = false;
		},			
		"deferRender": true,
		"scrollX": true,
		"colReorder": {
			fixedColumnsLeft: 1
		},
		"order": [[1, 'asc']], 
		"select": {
			style: 'api',
			selector: 'td:first-child'
		},
		"language": {
			"search": "Search: "
		},
		"dom": 'Blfrtip',
		"buttons": [ 
			{
				extend: 'selected',
				text: 'Hide/Show Selected',
				className: 'hideSelected',
				visible: false,
				action: function (e, dt, button, config ) {
					var selected = dt.rows( { selected: true } ).data();
					var list = [];
					for (var i = 0; i < selected.length; i++) {
						list.push(selected[i][0]);
					}
					$.ajax ({
						url: $SCRIPT_ROOT + '/_hide_torrents',
						type: 'POST',
						dataType: "json",
						data: JSON.stringify({"list": list}),
						success: function(msg) {
							console.log(msg);
						}
					});			
					dt.ajax.reload(null, false);								
				}
			},
			{
				extend: 'selected',
				text: 'Delete Selected',
				className: 'deleteSelected',
				visible: false,
				action: function (e, dt, button, config ) {
					var confirmed = confirm("These torrents will be deleted from the database. Bandwidth statistics will no longer be accurate. Are you sure?");
					if (confirmed == true) {
						var selected = dt.rows( { selected: true } ).data();
						var list = [];
						for (var i = 0; i < selected.length; i++) {
							list.push(selected[i][0]);
						}
						$.ajax ({
							url: $SCRIPT_ROOT + '/_delete_torrents',
							type: 'POST',
							dataType: "json",
							data: JSON.stringify({"list": list}),
							success: function(msg) {
								console.log(msg);
							}
						});			
						dt.ajax.reload(null, false);
					}
				}
			},
			{
				extend: 'columnToggle',
				text: 'Hide/Delete Mode',
				columns: '.hideMode',
				className: 'hideButton'
			},
			{
				extend: 'colvis',
				columns: ':gt(0)'
			}
		],
		"pagingType": "full_numbers",
		"autoWidth": false,
		"columns": [
			{
				"orderable": false,
				"targets": 0,
				defaultContent: '',
				className: 'select-checkbox',
				"data": null,
				"visible": false
			},
			{ data: 2, render: function(data, type, row) {
				if (( row[1] === 0 ) && (( type === 'display') || (type === 'filter'))) {
					return null;
				}
				return "<div class='text-wrap width-filename'><button type='button' id='openButton'>" + data.replace(/\./g, '.<wbr>') + "</button></div>";
			   }
			},
			{ data: 3, width: "49px", render: function(data, type, row) {
					if ( type === 'display' || type === 'filter' ) {
						return formatBytes(data);
					}
					return data;
				}
			},
			{ data: 4, render: $.fn.dataTable.render.percentBar('round', '#ffffff', '#00b300', '#00b300', '#006600', 1, 'solid') },
			{ data: 5, width: "73px", render: function(data, type, row) {
					if ( type === 'display' || type === 'filter' ) {
						return formatBytes(data);
					}
					return data;
				}
			},
			{ data: 6, width: "56px", render: function(data, type, row) {
					if ( type === 'display' || type === 'filter' ) {
						return formatBytes(data);
					}
					return data;
				}
			},
			{ data: 7, width: "45px", render: function(data, type, row) {
					return data.toFixed(3);
				}
			},
			{ data: 8, render: function(data, type, row) {
				if (( row[1] === 0 ) && (( type === 'display') || (type === 'filter'))) {
					return null;
				}
				return "<div class='text-wrap width-tracker-client'>" + data.replace(/\./g, '.<wbr>') + "</div>";
			   }	 
			},
			{ data: 9, width: "62px", render: function(data, type, row) {
					if ( type === 'display' || type === 'filter' ) {
						if (data === null) {
							return null;
						}
						else {
							return moment.unix(data).format('L');
						}
					}
					return data;
				}
			},
			{ data: 10, render: function(data, type, row) {
				return "<div class='text-wrap width-tracker-client'>" + data.replace(/\./g, '.<wbr>') + "</div>";
			   }	 
			},
			{ data: 11, width: "66px" },
			{ data: 12, render: function(data, type, row) {
				if (( row[1] === 0 ) && (( type === 'display') || (type === 'filter'))) {
					return null;
				}
				else if (data == null) {
					return "N/A";
				}
				return "<div class='text-wrap width-filename'>" + data.replace(/\./g, '.<wbr>') + "</div>";
			   }	
			}
		]
	});
	
	$('#torrents_table_wrapper .dt-buttons').detach().prependTo('div.dt-button-header');
	$('.buttons-selected').hide();
	$('.buttons-columnVisibility').click(function() {
		if (fullTable.select.style() == 'multi') {
			fullTable.select.style('api');
		}
		else {
			fullTable.select.style('multi');
		}
		$('.buttons-selected').toggle();
		$('.hideDeleteText').toggle();
		fullTable.rows().deselect();
	});
	$('#torrents_table tbody').on( 'click', 'button', function () {
		var data = fullTable.row( $(this).parents('tr') ).data();
		torrent_id = data[0];
		singleHistoryTable.ajax.reload();
		$('.torrent-modal-header > h4').html("History for '" + data[2].replace(/\./g, ".<wbr>") + "'");
		torrentModal.show();
	});
});