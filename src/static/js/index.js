//index js
var monthDData = [];
var monthUData = [];
var monthSizeFormat = 0

function getSizeFormat(bytes) {
	if (bytes === 0) return 0;

	const k = 1024;

	const i = Math.floor(Math.log(bytes) / Math.log(k));

	return i;
}
function formatBytesHighchart(bytes, size) {
	var formattedByte = (bytes / Math.pow(1024, size));
	var roundedByte = Math.round((formattedByte + Number.EPSILON) * 100) / 100;

	return roundedByte;
}
function monthChartData(data) {
	var monthlyMax = 0;
	$.each(data, function() {
		if (monthlyMax < this[1]) {
			monthlyMax = this[1];
		}
		if (monthlyMax < this[2]) {
			monthlyMax = this[2];
		}
	});
	monthSizeFormat = getSizeFormat(monthlyMax);

	$.each(data, function(index, row) {
		var date = Date.parse(row[0]);
		monthDData.push([ date, formatBytesHighchart(parseInt(row[1]),monthSizeFormat) ]);
		monthUData.push([ date, formatBytesHighchart(parseInt(row[2]),monthSizeFormat) ]);
	});
}

$(document).ready(function() {
	var dateModal = $('#date-modal');
	$('.date-modal-close').on('click', function() {
		dateModal.hide();
	});
	
	$(window).on('click', function(e) {
		if (e.target == dateModal[0]) {
			dateModal.hide();
		}
		else if (e.target == torrentModal[0]) {
			torrentModal.hide();
		}
	});
	
	//variables for highcharts
	var selectedSeries = 0;
	var clickedDate = 0;
	var tracker = null;
	var client = null;
	
	function dailyModalParams() {
		return [selectedSeries,tracker,client,clickedDate];
	}
	
	var dateTable = $('#date_table').DataTable( {
		"ajax": {
			"url": $SCRIPT_ROOT + '/_date_table',
			"contentType": "application/json",
			"type": 'POST',
			"data": function(d) {
				return JSON.stringify(d.date = dailyModalParams());
			}
		},
		"stateSave": true,	
		"deferRender": true,
		"scrollX": true,
		"order": [[1, 'desc']], 
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
			//name
			{ data: 2, render: function(data, type, row) {
				if (( row[1] === 0 ) && (( type === 'display') || (type === 'filter'))) {
					return null;
				}
				return "<div class='text-wrap width-filename'><button type='button' id='openButton'>" + data.replace(/\./g, '.<wbr>') + "</button></div>";
			   }
			},
			//downloaded
			{ data: 3, width: "73px", render: function(data, type, row) {
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
			//uploaded
			{ data: 4, width: "56px", render: function(data, type, row) {
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
			//total down
			{ data: 5, width: "66px", render: function(data, type, row) {
					if ( type === 'display' || type === 'filter' ) {
						if (row[3] > 0) {
							return "<div class='downloaded'>" + formatBytes(data) + "</div>";
						}
						else {	
							return formatBytes(data);
						}
					}
					return data;
				}
			},
			//total up
			{ data: 6, width: "50px", render: function(data, type, row) {
					if ( type === 'display' || type === 'filter' ) {
						if (row[4] > 0) {
							return "<div class='uploaded'>" + formatBytes(data) + "</div>";
						}
						else {	
							return formatBytes(data);
						}
					}
					return data;
				}
			},
			//ratio
			{ data: 7, width: "45px", render: function(data, type, row) {
					return data.toFixed(3);
				}
			},
			//size
			{ data: 8, width: "49px", render: function(data, type, row) {
					if ( type === 'display' || type === 'filter' ) {
						return formatBytes(data);
					}
					return data;
				}
			},
			//progress
			{ data: 9, render: $.fn.dataTable.render.percentBar('round', '#ffffff', '#00b300', '#00b300', '#006600', 1, 'solid') },
			//tracker
			{ data: 10, render: function(data, type, row) {
				if (( row[1] === 0 ) && (( type === 'display') || (type === 'filter'))) {
					return null;
				}
				return "<div class='text-wrap width-tracker'>" + data.replace(/\./g, '.<wbr>') + "</div>";
			   }	 
			},
			//client
			{ data: 11, render: function(data, type, row) {
				return "<div class='text-wrap width-client'>" + data.replace(/\./g, '.<wbr>') + "</div>";
			   }	 
			},
			//status
			{ data: 12, width: "66px" },
			//torrent name
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
	
	var dData = [];
	var uData = [];

	var dailyMax = 0;
	var dailySizeFormat = getSizeFormat(dailyMax);

	Highcharts.setOptions({
		time: {
			timezone: moment.tz.guess()
		}
	});
	$('#dailyChartContainer').highcharts({
		title: {
			text: null
		},
		chart: {
			backgroundColor: '#404040'
		},
		credits: {
			enabled: false
		},
		tooltip: {
			backgroundColor: 'rgba(89, 89, 89, .92)',
			borderWidth: 2,
			borderColor: '#efef43',
			style: {
				color: 'white',
				lineHeight: '16px'
			},
			formatter: function() {
				var s = '<span style="font-size:10px;font-weight:600;">' + Highcharts.dateFormat('%A, %b %e, %Y', this.x) + '</span>';
				var total = 0;
				$.each(this.points, function(i, point) {
					s += '<br/><span style="color:' + point.series.color + '">● </span>' + point.series.name + ': ' + point.y + ' ' + sizes[dailySizeFormat];
					total += point.y;
				});
				s += '<br/>● <span style="font-size:13px;font-weight:700;">Total: ' + parseFloat(total.toFixed(2)) + sizes[dailySizeFormat] + "</span>";
				return s;
			},
			shared: true
		},
		xAxis: {
			type: 'datetime',
			tickWidth: 1,
			minTickInterval: 24 * 3600 * 1000,
			crosshair: true,
			labels: {
				style: {
					color: 'white'
				}
			}
		},
		yAxis: {
			title: {
				text: null
			},
			gridLineColor: '#cccccc',
			labels: {
				style: {
					color: 'white'
				},
				format: '{value} ' + sizes[dailySizeFormat]
			}
		},
		legend: {
			itemStyle: {
				color: 'white',
				fontWeight: '600'
			},
			itemHoverStyle: {
				color: '#e6e6e6'
			}
		},
		plotOptions: {
			series: {
				marker: {
					lineWidth: 2,
					symbol: 'circle',
					lineColor: null
				},
				cursor: 'pointer',
				point: {
					events: {
						click: function () {
							clickedDate = this.category/1000;
							var displayDate = moment.unix(clickedDate).format("dddd, Do MMMM YYYY");
							if (this.series.options.id == 0) {
								$('.date-modal-header > h4').html("Downloaded on " + displayDate + " <span class='downloaded'>&#9660;" + this.y + " " + sizes[dailySizeFormat] + "</span>");
								if (this.series.options.id != selectedSeries) {
									dateTable.order( [[1, 'desc']] ).draw();
								}
								selectedSeries = 0;
								dateTable.ajax.reload();
								dateModal.show();
							}
							else {
								$('.date-modal-header > h4').html("Uploaded on " + displayDate + " <span class='uploaded'>&#9650;" + this.y + " " + sizes[dailySizeFormat] + "</span>");
								if (this.series.options.id != selectedSeries) {
									dateTable.order( [[2, 'desc']] ).draw();
								}
								selectedSeries = 1;
								dateTable.ajax.reload();
								dateModal.show();
							}
						}
					}
				}
			}
		},
		series: [{
			id: 0,
			name: 'Download',
			data: dData,
			color: '#fa3838',
			lineWidth: 3
		}, {
			id: 1,
			name: 'Upload',
			data: uData,
			color: '#1aff66',
			lineWidth: 3
		}]
	});	
	var dailyChart = $('#dailyChartContainer').highcharts();
	
	var topTrackers = [];
	var trackerDData = [];
	var trackerUData = [];
	var trackerMax = 0;
	var trackerSizeFormat = getSizeFormat(trackerMax);
	
	$('#trackerChartContainer').highcharts({
		title: {
			text: null
		},
		chart: {
			type: 'bar',
			backgroundColor: '#404040'
		},
		credits: {
			enabled: false
		},
		xAxis: {
			type: 'category',
			labels: {
				style: {
					color: 'white'
				}
			}
		},
		yAxis: {
			title: {
				text: null
			},
			gridLineColor: '#cccccc',
			labels: {
				style: {
					color: 'white'
				},
				format: '{value} ' + sizes[trackerSizeFormat]
			},
			min: 0,
			stackLabels: {
				enabled: true,
				style: {
					color: 'white',
					fontSize: '12px',
					fontWeight: '600'
				},
				formatter: function() {
					return Math.round(this.total) + " " + sizes[trackerSizeFormat]
				}
			}
		},
		legend: {
			reversed: true,
			itemStyle: {
				color: 'white',
				fontWeight: '600'
			},
			itemHoverStyle: {
				color: '#e6e6e6'
			}
		},
		tooltip: {
			backgroundColor: '#595959',
			borderWidth: 2,
			style: {
				color: 'white',
			},
			pointFormatter: function() {
				return '<span style="color:' + this.series.color + '";>●</span> ' + this.series.name + ': ' + this.y + ' ' + sizes[trackerSizeFormat] + '<br/><span style="font-weight:700;">● Total: ' + this.stackTotal + ' ' + sizes[trackerSizeFormat] + '</span>'
			}
		},	
		plotOptions: {
			bar: {
				stacking: 'normal',
				dataLabels: {
					enabled: true,
					style: {
						color: 'black',
						fontWeight: '600',
						textOutline: null
					},
					formatter: function() {
						return Math.round(this.y) + " " + sizes[trackerSizeFormat]
					}
				}
			},
			series: {
				borderColor: '#262626'
			}
		},
		series: [{
			id: 0,
			name: 'Download',
			data: trackerDData,
			color: '#fa3838',
			lineWidth: 3
		}, {
			id: 1,
			name: 'Upload',
			data: trackerUData,
			color: '#1aff66',
			lineWidth: 3
		}]
	});
	var trackerChart = $('#trackerChartContainer').highcharts();
	
	var numDays = 30;
	if (localStorage.getItem('numDays') != null) {
		numDays = localStorage.getItem('numDays');
	};
	if (localStorage.getItem('tracker') != null) {
		tracker = localStorage.getItem('tracker');
	};
	if (localStorage.getItem('client') != null) {
		client = localStorage.getItem('client');
	};
	$('#days').val(numDays);
	$('.numDaysTitle').text("Last " + numDays + " Days");

	function chartParams() {
		return [numDays, tracker, client];
	}
	
	function refreshCharts() {
		$.ajax({
			url: $SCRIPT_ROOT + '/_get_chart_data',
			contentType: 'application/json; charset=utf-8',
			type: 'POST',
			datatype: 'json',
			data: JSON.stringify({data:chartParams()}),
			success: function(data) {
				if (typeof(data) != 'string') {	
					dailyMax = data.data[1];
					dailySizeFormat = getSizeFormat(dailyMax);
					trackerMax = data.data[3];
					trackerSizeFormat = getSizeFormat(trackerMax);

					$.each(data.data[0], function(index, row) {
						var currentDate = Date.parse(row[0]);
						dData.push([ currentDate, formatBytesHighchart(parseInt(row[1]),dailySizeFormat) ]);
						uData.push([ currentDate, formatBytesHighchart(parseInt(row[2]),dailySizeFormat) ]);
					});
				
					$.each(data.data[2], function(index, row) {
						topTrackers.push(row[0]);
						trackerDData.push([ row[0], formatBytesHighchart(parseInt(row[1]),trackerSizeFormat) ]);
						trackerUData.push([ row[0], formatBytesHighchart(parseInt(row[2]),trackerSizeFormat) ]);
					});
				}

				dailyChart.series[0].setData(dData, false);
				dailyChart.series[1].setData(uData, false);
				dailyChart.yAxis[0].options.labels.format = '{value} ' + sizes[dailySizeFormat];
				dailyChart.series[0].update({tooltip:{valueSuffix:' ' + sizes[dailySizeFormat]}}, false);
				dailyChart.series[1].update({tooltip:{valueSuffix:' ' + sizes[dailySizeFormat]}}, false);
				
				trackerChart.series[0].setData(trackerDData, false);
				trackerChart.series[1].setData(trackerUData, false);
				trackerChart.yAxis[0].options.labels.format = '{value} ' + sizes[trackerSizeFormat];
				trackerChart.series[0].update({tooltip:{valueSuffix:' ' + sizes[trackerSizeFormat]}}, false);
				trackerChart.series[1].update({tooltip:{valueSuffix:' ' + sizes[trackerSizeFormat]}}, false);

				dailyChart.redraw();
				trackerChart.redraw();
				
				dData = [];
				uData = [];
				dailyMax = 0;
				
				topTrackers = [];
				trackerDData = [];
				trackerUData = [];
				trackerMax = 0;
			}
		});
	}
	refreshCharts();
	$('#refreshHighchart').on('click', function() {
		localStorage.clear();
	});
		
	$('#monthlyChartContainer').highcharts({
		chart: {
			type: 'column',
			backgroundColor: '#404040'
		},
		title: {
			text: null
		},
		credits: {
			enabled: false
		},
		xAxis: {
			type: 'datetime',
			tickWidth: 1,
			minTickInterval: 24 * 3600 * 1000,
			labels: {
				style: {
					color: 'white'
				}
			}
		},
		yAxis: {
			title: {
				text: null
			},
			gridLineColor: '#cccccc',
			labels: {
				style: {
					color: 'white'
				},
				format: '{value} ' + sizes[monthSizeFormat]
			},
			stackLabels: {
				enabled: true,
				style: {
					color: 'white',
					fontSize: '12px',
					fontWeight: '600'
				},
				formatter: function() {
					return Math.round(this.total) + " " + sizes[monthSizeFormat]
				}
			}
		},
		legend: {
			itemStyle: {
				color: 'white',
				fontWeight: '600'
			},
			itemHoverStyle: {
				color: '#e6e6e6'
			}
		},
		tooltip: {
			backgroundColor: '#595959',
			borderWidth: 2,
			style: {
				color: 'white',
			},
			pointFormatter: function() {
				return '<span style="color:' + this.series.color + '";>●</span> ' + this.series.name + ': ' + this.y + ' ' + sizes[monthSizeFormat] + '<br/><span style="font-weight:700;">● Total: ' + this.stackTotal + ' ' + sizes[monthSizeFormat] + '</span>'
			}
		},	
		plotOptions: {
			column: {
				stacking: 'normal',
				dataLabels: {
					enabled: true,
					style: {
						color: 'black',
						fontWeight: '600',
						textOutline: null
					},
					formatter: function() {
						return Math.round(this.y) + " " + sizes[monthSizeFormat]
					}
				}
			},
			series: {
				borderColor: '#262626'
			}
		},
		series: [{
			id: 0,
			name: 'Download',
			data: monthDData,
			color: '#fa3838',
			lineWidth: 3
		}, {
			id: 1,
			name: 'Upload',
			data: monthUData,
			color: '#1aff66',
			lineWidth: 3
		}]
	});
	//fill tracker and client dropdowns
	$.getJSON($SCRIPT_ROOT + '/_trackers_clients', function(data) {
		var trackers = $('#tracker');
		var clients = $('#client');
		
		if (tracker != null) {
			$.each(data.data[0], function() {
				if (tracker == this[0]) {
					trackers.append(new Option(this[1], this[0], true, true));
				}
				else {
					trackers.append(new Option(this[1], this[0]));
				}
			});
		}
		else {
			$.each(data.data[0], function() {
				trackers.append(new Option(this[1], this[0]));
			});
		}
		
		if (client != null) {
			$.each(data.data[1], function() {
				if (client == this[0]) {
					clients.append(new Option(this[1], this[0], true, true));
				}
				else {
					clients.append(new Option(this[1], this[0]));
				}
			});
		}
		else {
			$.each(data.data[1], function() {
				clients.append(new Option(this[1], this[0]));
			});
		}
		
		$('#loadingTrackers').text('All Trackers');
		$('#loadingClients').text('All Clients');
	});

	$('#tracker, #client, #days').on('change', function() {
		tracker = $('#tracker option:selected').val();
		client = $('#client option:selected').val();
		var tempDays = $('#days').val();
		if ((/^-?\d+$/.test(tempDays)) && (parseInt(tempDays) > 0)) {
			numDays = tempDays;
			localStorage.setItem('numDays', numDays);
			localStorage.setItem('tracker', tracker);
			localStorage.setItem('client', client);
			$('.numDaysTitle').text("Last " + numDays + " Days");

			refreshCharts();
		}
		else {
			$('#days').val(numDays);
		}
		
	});
	
	var allTimeSelection = 24;
	var allTimeRow = "";
	
	var allTimeTable = $('#all_time_table').DataTable( {
		"ajax": {
			"url": $SCRIPT_ROOT + '/_all_time_table',
			"contentType": "application/json",
			"type": 'POST',
			"data": function(d) {
				return JSON.stringify(d.date = allTimeSelection);
			}
		},
		"ordering": false,
		"info": false,
		"paging": false,
		"searching": false,
		"autoWidth": false,
		"columns": [
			{ data: 0, width: "73px", render: function(data, type, row) {
					allTimeRow = data;
					if (allTimeRow == "Downloaded") {
						return "<span style='color:#ff6666;'>" + data + "</span>";
					}
					else if (allTimeRow == "Uploaded") {
						return "<span style='color:#71da71;'>" + data + "</span>";
					}
					else if (allTimeRow == "Total") {
						return "<span style='color:#66ccff;'>" + data + "</span>";
					}
				}
			},
			{ data: 1, render: function(data, type, row) {
					if (allTimeSelection == 24) {
						return moment(data, 'YYYY/MM/DD').format('dddd, MMM Do YYYY');
					}
					else if (allTimeSelection == 30) {
						return moment(data, 'YYYY/MM').format('MMMM YYYY');
					}
				}
			},
			{ data: 2, width: "73px", render: function(data, type, row) {
					if (allTimeRow == "Downloaded") {
						return "<span style='color:#ff6666;'>" + formatBytes(data) + "</span>";
					}
					else {
						return formatBytes(data);
					}
				}
			},
			{ data: 3, width: "56px", render: function(data, type, row) {
					if (allTimeRow == "Uploaded") {
						return "<span style='color:#71da71;'>" + formatBytes(data) + "</span>";
					}
					else {
						return formatBytes(data);
					}
				}
			},
			{ data: 4, width: "56px", render: function(data, type, row) {
					if (allTimeRow == "Total") {
						return "<span style='color:#66ccff;'>" + formatBytes(data) + "</span>";
					}
					else {
						return formatBytes(data);
					}
				}
			},
		]
	});
	
	$('#all_time_24_btn').on( 'click', function () {
		$('#all_time_24_btn').prop('disabled', true);
		$('#all_time_month_btn').prop('disabled', false);
		allTimeSelection = 24;
		allTimeTable.ajax.reload();
	});
	$('#all_time_month_btn').on( 'click', function () {
		$('#all_time_month_btn').prop('disabled', true);
		$('#all_time_24_btn').prop('disabled', false);
		allTimeSelection = 30;
		allTimeTable.ajax.reload();
	});
	
	$('#date_table tbody').on( 'click', 'button', function () {
		var data = dateTable.row( $(this).parents('tr') ).data();
		torrent_id = data[0];
		singleHistoryTable.ajax.reload();
		$('.torrent-modal-header > h4').html("History for '" + data[2].replace(/\./g, ".<wbr>") + "'");
		torrentModal.show();
	});
});