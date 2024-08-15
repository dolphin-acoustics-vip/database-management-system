/**
 * Calculates time offsets based on the provided time label IDs, GMT offset labels, location offset labels, data time labels, and GMT offsets.
 * A time offset is calculated through a conversion from a given time to GMT, and then from GMT to a specific timezone
 *
 * @param {string} datetimestampInput - The ID of the input (can be hidden) with a value of the datetime to be converted.
 * @param {string} gmtLabelId - The ID of the GMT datetime label element (can be blank).
 * @param {string} locationLabelId - The ID of the location datetime label element (can be blank).
 * @param {string} dataOriginalLabelId - The ID of the data time label element.
 * @param {string} dataGmtOffset - The GMT offset value for the data time (in minutes).
 * @param {string} locationGmtOffset - The GMT offset value for the location time (in minutes).
 * @return {void}
 */
function calculateTimeOffsets(originalLabelId, gmtLabelId, locationLabelId, dataOriginalLabelId, dataGmtOffset, locationGmtOffset) {
    const timeStartInput = document.getElementById(originalLabelId);
    const gmtOffsetLabel = document.getElementById(gmtLabelId);
    const dataTimeLabel = document.getElementById(dataOriginalLabelId);
    const locationOffsetLabel = document.getElementById(locationLabelId);

    gmtOffsetLabel.style.display = 'none';
    dataTimeLabel.style.display = 'none';
    locationOffsetLabel.style.display = 'none';

    const selectedTime = new Date(timeStartInput.value);
    const dataGmtOffsetInt = parseInt(dataGmtOffset);
    const locationGmtOffsetInt = parseInt(locationGmtOffset);

    const dateGmtOffsetString = "GMT" + (dataGmtOffsetInt >= 0 ? "+" : "") + dataGmtOffsetInt / 60;
    const locationGmtOffsetString = "GMT" + (locationGmtOffsetInt >= 0 ? "+" : "") + locationGmtOffsetInt / 60;

    if (isNaN(dataGmtOffsetInt) || isNaN(locationGmtOffsetInt)) {
        gmtOffsetLabel.textContent = 'Error in time conversion';
        locationOffsetLabel.textContent = 'Error in time conversion';
        return;
    }

    const gmtOffset = dataGmtOffsetInt * 60 * 1000;
    const locationOffset = locationGmtOffsetInt * 60 * 1000;

    const dataTime = new Date(selectedTime.getTime());
    const gmtTime = new Date(selectedTime.getTime() - gmtOffset);
    const locationTime = new Date(gmtTime.getTime() + locationOffset);

    gmtOffsetLabel.textContent = `GMT Time (GMT+0): ${gmtTime.toLocaleString('en-GB')}`;
    locationOffsetLabel.textContent = `Location Time (` + locationGmtOffsetString + `): ${locationTime.toLocaleString('en-GB')}`;
    dataTimeLabel.textContent = `Data Time (${dateGmtOffsetString}): ${dataTime.toLocaleString('en-GB')}`;



    gmtOffsetLabel.style.display = 'block';
    dataTimeLabel.style.display = 'block';
    locationOffsetLabel.style.display = 'block';
}

