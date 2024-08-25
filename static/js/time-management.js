/**
 * Calculates time offsets based on the provided time label IDs, GMT offset labels, local offset labels, file time labels, and GMT offsets.
 * A time offset is calculated through a conversion from a given time to GMT, and then from GMT to a specific timezone
 *
 * @param {string} datetimestampInput - The ID of the input (can be hidden) with a value of the datetime to be converted.
 * @param {string} gmtLabelId - The ID of the GMT datetime label element (can be blank).
 * @param {string} localLabelId - The ID of the local datetime label element (can be blank).
 * @param {string} fileOriginalLabelId - The ID of the file time label element.
 * @param {string} fileGmtOffset - The GMT offset value for the file time (in minutes).
 * @param {string} localGmtOffset - The GMT offset value for the local time (in minutes).
 * @return {void}
 */
function calculateTimeOffsets(originalLabelId, gmtLabelId, localLabelId, fileOriginalLabelId, fileGmtOffset, localGmtOffset) {
    const timeStartInput = document.getElementById(originalLabelId);
    const gmtOffsetLabel = document.getElementById(gmtLabelId);
    const fileTimeLabel = document.getElementById(fileOriginalLabelId);
    const localOffsetLabel = document.getElementById(localLabelId);

    gmtOffsetLabel.style.display = 'none';
    fileTimeLabel.style.display = 'none';
    localOffsetLabel.style.display = 'none';

    const selectedTime = new Date(timeStartInput.value);
    const fileGmtOffsetInt = parseInt(fileGmtOffset);
    const localGmtOffsetInt = parseInt(localGmtOffset);

    const dateGmtOffsetString = "GMT" + (fileGmtOffsetInt >= 0 ? "+" : "") + fileGmtOffsetInt / 60;
    const localGmtOffsetString = "GMT" + (localGmtOffsetInt >= 0 ? "+" : "") + localGmtOffsetInt / 60;

    if (isNaN(fileGmtOffsetInt) || isNaN(localGmtOffsetInt)) {
        gmtOffsetLabel.textContent = 'Error in time conversion';
        localOffsetLabel.textContent = 'Error in time conversion';
        return;
    }

    const gmtOffset = fileGmtOffsetInt * 60 * 1000;
    const localOffset = localGmtOffsetInt * 60 * 1000;

    const fileTime = new Date(selectedTime.getTime());
    const gmtTime = new Date(selectedTime.getTime() - gmtOffset);
    const localTime = new Date(gmtTime.getTime() + localOffset);

    gmtOffsetLabel.textContent = `GMT Time (GMT+0): ${gmtTime.toLocaleString('en-GB')}`;
    localOffsetLabel.textContent = `Local Time (` + localGmtOffsetString + `): ${localTime.toLocaleString('en-GB')}`;
    fileTimeLabel.textContent = `File Time (${dateGmtOffsetString}): ${fileTime.toLocaleString('en-GB')}`;



    gmtOffsetLabel.style.display = 'block';
    fileTimeLabel.style.display = 'block';
    localOffsetLabel.style.display = 'block';
}

