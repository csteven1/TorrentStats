//settings page

var locale = "";
var tCheckFrequency = "";
var backupFrequency = "";
var dCheckFrequency = "";
var startAtLogin = "";
var startMenuShortcut = "";
var port = ""

function initParams(param) {
	locale = param[0];
	tCheckFrequency = param[1];
	backupFrequency = param[2];
	dCheckFrequency = param[3];
	startAtLogin = parseInt(param[4]);
	startMenuShortcut = parseInt(param[5]);
	port = parseInt(param[6]);
}

$(document).ready(function() {
	const locales = {"en":"MM/DD/YYYY", "en-gb":"DD/MM/YYYY"};

	function setLocaleOption(locale) {
		var currentLocale = moment.localeData(locale).longDateFormat('L');

		for (let [key, value] of Object.entries(locales)) {
			if (currentLocale == value) {
				$('#localeSetting').val(key);
				$('#localeSetting option[value=""]').remove();
				return;
			}
		}
		$('#loadingLocale').text(currentLocale);
		$('#loadingLocale').prop('selected', true);
	}

	// fill general settings values
	setLocaleOption(locale);
	$('#port').val(port);

	function resetLocale(newLocale) {
		var longForm = moment.localeData(newLocale).longDateFormat('L');

		for (let [key, value] of Object.entries(locales)) {
			if (longForm == value) {
				$('#localeSetting').val(key);
				return;
			}
		}
		$('#localeSetting option[value=' + newLocale + ']').remove();
		$('#localeSetting').append(new Option(longForm, newLocale, true, true));
	}
	
	function verifyPort(strPort) {
		if (/^-?\d+$/.test(strPort) && (parseInt(strPort) > 1023) && (parseInt(strPort) < 49152)) {
			return true;
		}
		else {
			return false;
		}
	}

	$('#localeSetting').on('change', function() {
		$('#cancelGeneral, #saveGeneral').prop('disabled', false);
	});
	
	$('#port').on('input', function() {
		$('#cancelGeneral').prop('disabled', false);
		var port = $('#port').val();
		if (verifyPort(port)) {
			$('#port').css('border', '4px solid #808080');
			$('.portErrTooltip .portErrTTipText').css('visibility', 'hidden');
			$('.portErrTooltip .portErrTTipText').css('opacity', '0');
			$('#saveGeneral').prop('disabled', false);
			
		}
		else {
			$('#port').css('border', '4px solid red');
			$('.portErrTooltip .portErrTTipText').css('visibility', 'visible');
			$('.portErrTooltip .portErrTTipText').css('opacity', '1');
			$('#saveGeneral').prop('disabled', true);
		}
	});
	// save general settings
	$('#saveGeneral').on( 'click', function() {
		var saveLocale = $('#localeSetting option:selected').val();
		var savePort = $('#port').val();
		var settings = [saveLocale, savePort];

		$.ajax ({
			url: $SCRIPT_ROOT + '/_update_general',
			type: 'POST',
			dataType: "json",
			data: JSON.stringify({"settings": settings}),
			success: function(data) {
				$('#cancelGeneral, #saveGeneral').prop('disabled', true);
				locale = saveLocale;
				port = savePort;
				$('#notification').css("right","-20%");
				$('.notification-header > h4').text("Locale updated");
				$('.notification-body > p').hide();
				$('#notification').animate({right: 30});
				setTimeout(hideNotif, 3000);
			}
		});
	});
	$('#resetLocale').on( 'click', function() {
		$.ajax ({
			url: $SCRIPT_ROOT + '/_update_locale',
			type: 'POST',
			dataType: "json",
			data: JSON.stringify({"data": "default"}),
			success: function(data) {
				$('#cancelGeneral, #saveGeneral').prop('disabled', true);
				resetLocale(data.data);
				locale = data.data;
				$('#notification').css("right","-20%");
				$('.notification-header > h4').text("Locale updated");
				$('.notification-body > p').hide();
				$('#notification').animate({right: 30});
				setTimeout(hideNotif, 3000);
			}				
		});
	});
	// reset general settings to system defaults
	$('#resetGeneral').on( 'click', function() {
		var settings = ["default", "default"];
		
		$.ajax ({
			url: $SCRIPT_ROOT + '/_update_general',
			type: 'POST',
			dataType: "json",
			data: JSON.stringify({"settings": settings}),
			success: function(data) {
				$('#cancelGeneral, #saveGeneral').prop('disabled', true);
				resetLocale(data.data[0]);
				locale = data.data[0];
				$('#port').val(data.data[1]);
				$('#notification').css("right","-20%");
				$('.notification-header > h4').text("Locale updated");
				$('.notification-body > p').hide();
				$('#notification').animate({right: 30});
				setTimeout(hideNotif, 3000);
			}				
		});
	});
	// cancel general settings - reset to initial values
	$('#cancelGeneral').on( 'click', function() {
		setLocaleOption(locale);
		$('#port').val(port);
		$('#port').css('border', '4px solid #808080');
		$('.portErrTooltip .portErrTTipText').css('visibility', 'hidden');
		$('#cancelGeneral, #saveGeneral').prop('disabled', true);
	});
	
	function setWinOptions(startAtLogin, startMenuShortcut) {
		if (startAtLogin) {
			$('.winOptions').show();
			$('.winSetting').css('display', 'flex');
		}
		else {
			return;
		}
		if (startAtLogin == 1) {
			$('#startAtLogin').prop('checked',true);
		}
		else {
			$('#startAtLogin').prop('checked',false);
		}
		if (startMenuShortcut == 1) {
			$('#startMenu').prop('checked',true);
		}
		else {
			$('#startMenu').prop('checked',false);
		}
	}
	setWinOptions(startAtLogin, startMenuShortcut);
	
	$('#startAtLogin, #startMenu').on('change', function() {
		$('#cancelWin, #saveWin').prop('disabled', false);
	});
	
	$('#cancelWin').on( 'click', function() {
		setWinOptions(startAtLogin, startMenuShortcut);
		$('#cancelWin, #saveWin').prop('disabled', true);
	});
	
	$('#saveWin').on( 'click', function() {
		var saveStartAtLogin = $('#startAtLogin').prop('checked') ? '1' : '2';
		var saveStartMenu = $('#startMenu').prop('checked') ? '1' : '2';
		var winSettings = [saveStartAtLogin, saveStartMenu];
		
		$.ajax ({
			url: $SCRIPT_ROOT + '/_update_win',
			type: 'POST',
			dataType: "json",
			data: JSON.stringify({"settings": winSettings}),
			success: function(data) {
				$('#cancelWin, #saveWin').prop('disabled', true);
				startAtLogin = saveStartAtLogin;
				startMenuShortcut = saveStartMenu;
				$('#notification').css("right","-20%");
				$('.notification-header > h4').text("Windows Settings Updated");
				$('.notification-body > p').hide();
				$('#notification').animate({right: 30});
				setTimeout(hideNotif, 3000);
			}
		});
	});
	
	function hideNotif() {
		$('#notification').animate({right: "-20%"});
	}
	
	// fill scheduled tasks values
	$('#tCheckFrequency').val(tCheckFrequency);
	$('#backupFrequency').val(backupFrequency);
	$('#dCheckFrequency').val(dCheckFrequency);
	
	$('#saveTasks').on( 'click', function() {
		tCheckFrequency = $('#tCheckFrequency option:selected').val();
		backupFrequency = $('#backupFrequency option:selected').val();
		dCheckFrequency = $('#dCheckFrequency option:selected').val();
		var tasks = [tCheckFrequency, backupFrequency, dCheckFrequency];

		$.ajax ({
			url: $SCRIPT_ROOT + '/_update_tasks',
			type: 'POST',
			dataType: "json",
			data: JSON.stringify({"tasks": tasks}),
			success: function(data) {
				$('#cancelTasks, #saveTasks').prop('disabled', true);
				$('#notification').css("right","-20%");
				$('.notification-header > h4').text("Tasks updated");
				$('.notification-body > p').hide();
				$('#notification').animate({right: 30});
				setTimeout(hideNotif, 3000);
			}
		});
	});
	$('#cancelTasks').on( 'click', function() {
		$('#tCheckFrequency').val(tCheckFrequency);
		$('#backupFrequency').val(backupFrequency);
		$('#dCheckFrequency').val(dCheckFrequency);
		$('#cancelTasks, #saveTasks').prop('disabled', true);
	});
	
	$('#tCheckFrequency, #backupFrequency, #dCheckFrequency').on('change', function() {
		$('#cancelTasks, #saveTasks').prop('disabled', false);
	});

	var clientsTable = $('#clients_table').DataTable( {
		"ajax": $SCRIPT_ROOT + '/_clients_table',
		"ordering": false,
		"info": false,
		"paging": false,
		"searching": false,
		"autoWidth": false,
		"columns": [
			{ data: 1 },
			{ data: 2 },
			{ data: 3 },
			{ data: 6, width: "80px", render: function(data, type, row) {
					if (data == 0) {
						return "<div class='activeClient'><ul><li>Active</li></ul></div>";
					}
					else if (data == 1) {
						return "<div class='offlineClient'><ul><li>Inactive <span class='offClientTooltip'>&#9432;<span class='offClientTTipText'>Connected to qBittorrent but failed authentication. Verify your username and password are correct</span></span></li></ul></div>";
					}
					else if (data == 2) {
						return "<div class='offlineClient'><ul><li>Inactive <span class='offClientTooltip'>&#9432;<span class='offClientTTipText'>Connected to Deluge but failed authentication. Verify your username and password are correct</span></span></li></ul></div>";
					}
					else if (data == 3) {
						return "<div class='offlineClient'><ul><li style='width:75px;'>Inactive <span class='offClientTooltip'>&#9432;<span class='offClientTTipText'>No response. Verify your IP address is correct and the client is running</span></span></li></ul></div>";
					}
					else {
						return "<div class='offlineClient'><ul><li>Inactive <span class='offClientTooltip'>&#9432;<span class='offClientTTipText'>Unknown error</span></span></li></ul></div>";
					}
				}
			},
			{ data: null, defaultContent: '<button id="editClient">Edit</button>' },
			{ data: null, defaultContent: '<button id="deleteClient">Delete</button>' },
		]		
	});
	$('#refreshClients').on( 'click', function() {
		console.log("Attempting to reload table");
		clientsTable.ajax.reload();
		console.log("Table refreshed");
	});
	var editModal = $('#edit-client-modal');
	var addModal = $('#add-client-modal');

	$('.edit-client-modal-close, #cancelEdit').on('click', function() {
		editModal.hide();
		$('.editVerif').hide();
	});
	$('.add-client-modal-close, #cancelAdd').on('click', function() {
		addModal.hide();
		$('#add-ip').val('');
		$('#add-username').val('');
		$('#add-pass').val('');
		$('#add-nickname').val('');
		$('.addVerif').hide();
		$('.addVerif2').hide();
	});

	$(window).on('click', function(e) {
		if (e.target == editModal[0]) {
			editModal.hide();
			$('.editVerif').hide();
		}
		else if (e.target == addModal[0]) {
			addModal.hide();
			$('#add-ip').val('');
			$('#add-username').val('');
			$('#add-pass').val('');
			$('#add-nickname').val('');
			$('.addVerif').hide();
			$('.addVerif2').hide();
		}
	});
	var sectionName = "";
	$('#clients_table tbody').on( 'click', '#editClient', function () {
		var data = clientsTable.row( $(this).parents('tr') ).data();

		var user = data[4];
		var pass = data[5];

		if (!user) {
			user = null;
		}
		if (!pass) {
			pass = null;
		}

		$('.edit-client-modal-header > h4').html("Edit '" + data[1].replace(/\./g, ".<wbr>") + "' (" + data[2].replace(/\./g, ".<wbr>") + ")");
		$('#edit-nickname').val(data[1]);
		$('#edit-ip').val(data[3]);
		$('#edit-username').val(user);
		$('#edit-pass').val(pass);
		sectionName = data[0];

		editModal.show();
	} );

	$('#saveEdit').on('click', function() {
		var nickname = $('#edit-nickname').val();
		var ip = $('#edit-ip').val();
		var user = $('#edit-username').val();
		var pass = $('#edit-pass').val();

		var editVerify = [sectionName, nickname, ip, user, pass];

		if (!ip) {
			$('.editVerifText').text("Invalid IP address");
			$('.editVerif').css('display', 'flex');
		}
		else {
			$('.editVerifText').text("Verifying...");
			$('.editVerif').css('display', 'flex');
			$.ajax ({
				url: $SCRIPT_ROOT + '/_client_edit',
				type: 'POST',
				dataType: "json",
				data: JSON.stringify({"data": editVerify}),
				success: function(data) {
					if (Number.isInteger(data.data)) {
						if (data.data == 1) {
							$('.editVerifText').text("Connected to qBittorrent but failed authentication. Verify your username and password are correct");
						}
						else if (data.data == 2) {
							$('.editVerifText').text("Connected to Deluge but failed authentication. Verify your username and password are correct");
						}
						else if (data.data == 3) {
							$('.editVerifText').text("No response from IP address. Verify your IP address is correct and the client is running");
						}
						else if (data.data == 4) {
							$('.editVerifText').text("A client in TorrentStats is already using that IP address");
						}
						else if (data.data == 5) {
							$('.editVerifText').text("A client in TorrentStats is already using that nickname");
						}
						else {
							$('.editVerifText').text("Invalid IP address");
						}
					}
					else {
						editModal.hide()
						$('.editVerif').hide();
						clientsTable.ajax.reload();
						$('#notification').css("right","-20%");
						$('.notification-header > h4').text("Client edited successfully");
						$('.notification-body > p').text("Updating torrents");
						$('.notification-body > p').hide();
						$('#notification').animate({right: 30});
						setTimeout(hideNotif, 3000);
						$.ajax ({
							url: $SCRIPT_ROOT + '/_refresh_torrents',
							type: 'GET',
							dataType: "json",
							success: function(data) {
								$('#notification').css("right","-20%");
								$('.notification-body > p').text("All torrents updated");
								$('.notification-body > p').show();
								$('#notification').animate({right: 30});
								setTimeout(hideNotif, 3000);
							}
						});
					}
				}
			});
		}
	});

	$('#clients_table tbody').on( 'click', '#deleteClient', function () {
		var data = clientsTable.row( $(this).parents('tr') ).data();

		var confirmed = confirm("The entire history of this client will be deleted from TorrentStats. Are you sure?");
		if (confirmed == true) {
			$.ajax ({
				url: $SCRIPT_ROOT + '/_client_delete',
				type: 'POST',
				dataType: "json",
				data: JSON.stringify({"client": data[0]}),
				success: function(data) {
					clientsTable.ajax.reload();
					$('#notification').css("right","-20%");
					$('.notification-header > h4').text("Client deleted");
					$('.notification-body > p').hide();
					$('#notification').animate({right: 30});
					setTimeout(hideNotif, 3000);
				}
			});
		}
	} );
	$('#addClient').on( 'click', function() {
		$('.addPage1').show();
		$('.addPage2').hide();
		addModal.show();
	});
	var ip = $('#add-ip').val();
	var user = $('#add-username').val();
	var pass = $('#add-pass').val();
	var displayName = $('#add-nickname').val();
	var clientName = "";
	var clientType= "";

	$('#nextAdd').on('click', function() {
		ip = $('#add-ip').val();
		user = $('#add-username').val();
		pass = $('#add-pass').val();
		var addVerify = [ip, user, pass];
		
		if (!ip) {
			$('.addVerifText').text("Invalid IP address");
			$('.addVerif').css('display', 'flex');
		}
		else {
			$('.addVerifText').text("Verifying...");
			$('.addVerif').css('display', 'flex');
			$.ajax ({
				url: $SCRIPT_ROOT + '/_client_add_verify',
				type: 'POST',
				dataType: "json",
				data: JSON.stringify({"data": addVerify}),
				success: function(data) {
					if (Number.isInteger(data.data)) {
						if (data.data == 1) {
							$('.addVerifText').text("Connected to qBittorrent but failed authentication. Verify your username and password are correct");
						}
						else if (data.data == 2) {
							$('.addVerifText').text("Connected to Deluge but failed authentication. Verify your username and password are correct");
						}
						else if (data.data == 3) {
							$('.addVerifText').text("No response from IP address. Verify your IP address is correct and the client is running");
						}
						else if (data.data == 4) {
							$('.addVerifText').text("A client in TorrentStats is already connected to that IP address");
						}
						else if (data.data == 6) {
							$('.addVerifText').text("Invalid IP address");
						}
					}
					else {
						$('.addVerifText').text("Success");
						$('.addPage1').fadeOut(300, function() {
							$('#add-nickname').val(data.data[0]);
							$('#appName').text(data.data[1]);
							clientName = data.data[1];
							clientType = data.data[2];
							$('.addPage2').fadeIn(300);
							$('.addVerif').hide();
						});
					}
				}
			});
		}
	});
	$('#backAdd').on('click', function() {
		$('.addPage2').fadeOut(300, function() {
			$('.addPage1').fadeIn(300);
		});
	});
	$('#saveAdd').on('click', function() {
		displayName = $('#add-nickname').val();
		var addSave = [displayName, clientName, ip, user, pass, clientType];

		$('.addVerifText2').text("Verifying...");
		$('.addVerif2').css('display', 'flex');

		$.ajax ({
			url: $SCRIPT_ROOT + '/_client_add',
			type: 'POST',
			dataType: "json",
			data: JSON.stringify({"data": addSave}),
			success: function(data) {
				if (data.data == 5) {
					$('.addVerifText2').text("A client in TorrentStats is already using that nickname");
				}
				else {
					addModal.hide();
					$('#add-ip').val('');
					$('#add-username').val('');
					$('#add-pass').val('');
					$('#add-nickname').val('');
					$('.addVerif').hide();
					$('.addVerif2').hide();
					
					clientsTable.ajax.reload();
					$('#notification').css("right","-20%");
					$('.notification-header > h4').text("Client added successfully");
					$('.notification-body > p').text("Adding torrents...");
					$('.notification-body > p').show();
					$('#notification').animate({right: 30});
					setTimeout(hideNotif, 3000);
					$.ajax ({
						url: $SCRIPT_ROOT + '/_refresh_torrents',
						type: 'GET',
						dataType: "json",
						success: function(data) {
							$('#notification').css("right","-20%");
							$('.notification-body > p').text("All torrents addded successfully");
							$('.notification-body > p').show();
							$('#notification').animate({right: 30});
							setTimeout(hideNotif, 3000);
						}
					});
				}
			}
		});
	});
	$('#closeNotif, .notification-close').on('click', function() {
		hideNotif();
	});
});