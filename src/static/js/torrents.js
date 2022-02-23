//torrents page

$(document).ready(function() {
	var deleteModal = $('#delete-torrent-modal');
	$('.delete-torrent-modal-close, #cancelDeleteTorrent').on('click', function() {
		deleteModal.hide();
	});
	
	$(window).on('click', function(e) {
		if (e.target == torrentModal[0]) {
			torrentModal.hide();
		}
		else if (e.target == deleteModal[0]) {
			deleteModal.hide();
		}
	});
	
	var fullTable = $('#torrents_table').DataTable( {
		"ajax": $SCRIPT_ROOT + '/_full_table',
		"stateSave": true,
		"stateSaveParams": function (settings, data) {
			data.search.search = "";
			data.columns.search = "";
			data.columns[0].visible = false;
		},
		"stateDuration": 0,
		"deferRender": true,
		"autoWidth": false,
		"scrollX": true,
		"colReorder": false,
		"fixedHeader": false,
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
					deleteModal.show();
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
		"lengthMenu": [[25, 50, 100, -1], [25, 50, 100, "All"]],
		"pageLength": 25,
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
				return "<div class='text-wrap width-tracker'>" + data.replace(/\./g, '.<wbr>') + "</div>";
			   }	 
			},
			{ data: 9, width: "62px", render: function(data, type, row) {
					if ( type === 'display' || type === 'filter' ) {
						if (data === null) {
							return null;
						}
						else {
							return moment.unix(data).format('LL');
						}
					}
					return data;
				}
			},
			{ data: 10, width: "62px", render: function(data, type, row) {
					if ( type === 'display' || type === 'filter' ) {
						if (data === null) {
							return null;
						}
						else {
							return moment.unix(data).format('LL');
						}
					}
					return data;
				}
			},
			{ data: 11, render: function(data, type, row) {
				return "<div class='text-wrap width-client'>" + data.replace(/\./g, '.<wbr>') + "</div>";
			   }	 
			},
			{ data: 12, width: "66px" },
			{ data: 13, render: function(data, type, row) {
				if (( row[1] === 0 ) && (( type === 'display') || (type === 'filter'))) {
					return null;
				}
				else if (data == null) {
					return "N/A";
				}
				return "<div class='text-wrap width-directory'>" + data.replace(/\./g, '.<wbr>') + "</div>";
			   }	
			}
		]
	});
	
	$('#deleteConfirmTorrent').on( 'click', function() {
		var selected = fullTable.rows( { selected: true } ).data();
		var list = [];
		for (var i = 0; i < selected.length; i++) {
			list.push(selected[i][0]);
		}
		$.ajax ({
			url: $SCRIPT_ROOT + '/_delete_torrents',
			type: 'POST',
			dataType: "json",
			data: JSON.stringify({"list": list}),
			success: function(data) {
				deleteModal.hide();
				fullTable.ajax.reload();
			}
		});
	});
	
	$('#updateButton').on('click', function() {
		$('.icn-spin').addClass('icn-spinner');
		$.ajax ({
			url: $SCRIPT_ROOT + '/_refresh_torrents',
			type: 'GET',
			dataType: "json",
			success: function(data) {
				fullTable.ajax.reload();
				$('.icn-spin').removeClass('icn-spinner');
			}
		});
	});
	
	function showActive(checked) {
		if (checked) {
			$('#showActive').prop('checked', true);
			fullTable.column(11).search('^(?!Deleted).*$',true, false).draw();
		} 
		else {
			$('#showActive').prop('checked', false);
			fullTable.column(11).search('').draw();
		}
	}
	
	var showActiveChecked = false;
	if (localStorage.getItem('showActiveOption') != null) {
		showActiveChecked = $.parseJSON(localStorage.getItem('showActiveOption').toLowerCase());
		$('#showActive').prop('checked', showActiveChecked);
	};
	
	showActive(showActiveChecked);
	
	$('#showActive').on('change', function () {
		localStorage.setItem('showActiveOption', this.checked);
		showActive(this.checked);
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