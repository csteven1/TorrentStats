//base js
const sizes = ['b', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];

function formatBytes(bytes, decimals = 2) {
	if (bytes === 0) return '0 b';

	const k = 1024;
	const dm = decimals < 0 ? 0 : decimals;

	const i = Math.floor(Math.log(bytes) / Math.log(k));

	return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

$(document).ready(function() {
	moment.updateLocale('en', {
		longDateFormat : {
			LT: "h:mm A",
			LTS: "h:mm:ss A",
			L: "MM/DD/YYYY",
			l: "M/D/YYYY",
			LL: "MM/DD/YYYY HH:mm:ss",
			ll: "MMM D YYYY",
			LLL: "MMMM Do YYYY LT",
			lll: "MMM D YYYY LT",
			LLLL: "dddd, MMMM Do YYYY LT",
			llll: "ddd, MMM D YYYY LT"
		}
	});
	moment.updateLocale('en-gb', {
		longDateFormat : {
			LT: "h:mm A",
			LTS: "h:mm:ss A",
			L: "DD/MM/YYYY",
			l: "M/D/YYYY",
			LL: "DD/MM/YYYY HH:mm:ss",
			ll: "MMM D YYYY",
			LLL: "MMMM Do YYYY LT",
			lll: "MMM D YYYY LT",
			LLLL: "dddd, MMMM Do YYYY LT",
			llll: "ddd, MMM D YYYY LT"
		}
	});
});