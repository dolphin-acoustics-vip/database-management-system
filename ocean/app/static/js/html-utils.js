/**
 * Adds shift-click and select-all functionality to a list of checkboxes.
 * @param {NodeList} checkboxes - A NodeList of HTML checkboxes.
 * @example
 * const checkboxes = document.querySelectorAll('input[name="selections-checkboxes"]');
 * addShiftClickFunctionality(checkboxes);
 */
function addShiftClickFunctionality(checkboxes) {
    let lastChecked;
  
    checkboxes.forEach(function (checkbox) {
      checkbox.addEventListener('click', function (event) {
        // Shift-click functionality
        if (event.shiftKey && lastChecked) {
          const start = Array.prototype.indexOf.call(checkboxes, lastChecked);
          const end = Array.prototype.indexOf.call(checkboxes, checkbox);
          const checkboxesToCheck = Array.prototype.slice.call(checkboxes, Math.min(start, end), Math.max(start, end) + 1);
  
          checkboxesToCheck.forEach((checkbox) => {
            checkbox.checked = true;
          });
        }
  
        // Select-all functionality
        if (checkbox.classList.contains('select-all')) {
          checkboxes.forEach((checkbox) => {
            checkbox.checked = checkbox === event.target ? event.target.checked : event.target.checked;
          });
        }
  
        lastChecked = event.target;
      });
    });
  }

  /**
   * Add event listener to a delete button. When clicked, it gets the values of all
   * checked checkboxes, sets the values of all selected checkboxes in a hidden input 
   * field, and submits a form.
   * @param {NodeList} checkboxes - The checkboxes
   * @param {HTMLElement} button - The button that will trigger the submission
   * @param {HTMLElement} input - The hidden input field that will store the values of selected checkboxes
   * @param {HTMLFormElement} form - The form that will be submitted
   */
  function addCheckboxFormSubmission(checkboxes, button, input, form) {
    // Add event listener to the delete button
    button.addEventListener('click', () => {
        // Get the checked checkboxes
        const checkedCheckboxes = Array.from(checkboxes).filter(checkbox => checkbox.checked);
        
        // Get the file IDs of the checked checkboxes
        const selectedValues = checkedCheckboxes.map(checkbox => checkbox.value);

        // Set the file IDs in the hidden input field
        input.value = selectedValues.join(',');

        // Submit the form
        form.submit();
    });
  }

/**
 * Handles file upload by dividing the file into 20MB chunks and uploading each chunk sequentially.
 * 
 * @param {HTMLInputElement} fileInput - The file input element used for selecting the file to upload.
 * @param {HTMLElement} progressBar - The progress bar element to display upload progress.
 * @param {HTMLInputElement} fileIdStore - An input element to store the file ID received from the server.
 * @param {HTMLButtonElement} submissionButton - The button element that triggers form submission, which gets disabled during upload.
 * 
 * The function listens for changes on the file input and, upon file selection, it disables the submission button 
 * and uploads the file in chunks. It updates the progress bar as each chunk is uploaded. Once the upload is complete,
 * it displays the uploaded filename and provides a reset button to clear the upload state, re-enabling the file input 
 * and submission button.
 * 
 * 
 */
function fileUploadHandler(fileInput, progressBar, fileIdStore, fileNameStore, submissionButton) {
  // const fileInput = document.getElementById('file-input');
  // const progressBar = document.getElementById('progress-bar-inner');
  // const form = document.getElementById('file-upload-form');

  fileInput.addEventListener('change', async () => {
    submissionButton.disabled = true;
      const file = fileInput.files[0];
      const fileSize = file.size;
      const chunkSize = 1024 * 1024 * 20; // 20MB chunks
      const numChunks = Math.ceil(fileSize / chunkSize);

      progressBar.style="display: block";
    

      let chunkIndex = 0;

      const uploadFile = (overrideFileId = null) => {
          const chunk = file.slice(chunkIndex * chunkSize, (chunkIndex + 1) * chunkSize);
          const formData = new FormData();
          formData.append('filename', file.name);
          formData.append('chunk', chunk);
          formData.append('chunk_index', chunkIndex);
          formData.append('num_chunks', numChunks);
          if (overrideFileId) {
              formData.append('file_id', overrideFileId);
          }

          fetch('/ocean/upload_chunk', {
              method: 'POST',
              body: formData,
          })
          .then((response) => response.json())
          .then((data) => {
              const progress = (chunkIndex + 1) / numChunks * 100;
              // progressBar.style.width = `${progress}%`;
              progressBar.value = progress;
              chunkIndex++;

              if (chunkIndex < numChunks) {
                  uploadFile(data.file_id);
              } else {
                // Update the input field to show the filename and store file_id
                const textField = document.createElement('input');
                textField.type = 'text';
                textField.value = `Uploaded: ${file.name}`;
                textField.readOnly = true;
                
                fileIdStore.value = data.file_id;
                fileNameStore.value = data.filename;
                fileInput.value = '';
                // Create a reset button
                const resetButton = document.createElement('button');
                resetButton.type = 'button';
                resetButton.textContent = 'Clear Upload';
                resetButton.addEventListener('click', () => {
                    // Reset the file input
                    
                    textField.remove();
                    resetButton.remove();
                    fileIdStore.value = '';
                    fileNameStore.value = '';
                    fileInput.style.display = 'block';
                });

                // Hide the original file input and show the text field and reset button
                fileInput.style.display = 'none';
                fileInput.parentNode.insertBefore(textField, fileInput);
                fileInput.parentNode.insertBefore(resetButton, fileInput.nextSibling);
                submissionButton.disabled = false;
                progressBar.style="display: none";

              }
          })
          .catch((error) => console.error(error));
      };

      uploadFile();
  });

}


/**
 * Handles form submission with a progress bar and periodic server pings.
 * 
 * @param {string} formId - The ID of the form element to be submitted.
 * @param {string} progressBarId - The ID of the progress bar element to display upload progress.
 * @param {string} progressTextId - The ID of the text element to display upload percentage.
 * 
 * This function adds an event listener to the specified form, preventing its default submission behavior.
 * It displays the progress bar and text during the file upload, updating them with the current upload percentage.
 * Periodic pings are sent to the server every 2 seconds to keep the connection alive. Once the upload is complete,
 * the ping interval is cleared. If the server responds with a redirect URL upon successful upload, the page is redirected.
 */
  function uploadFormWithProgress(formId, progressBarId, progressTextId) {

    const form = document.getElementById(formId);
    const progressBar = document.getElementById(progressBarId);
    const progressText = document.getElementById(progressTextId);
  
    form.addEventListener('submit', (e) => {  
      e.preventDefault();

      progressBar.style="display: block";
      progressText.style="display: block";
      const xhr = new XMLHttpRequest();
      xhr.upload.addEventListener('progress', (e) => {
        const percent = Math.round((e.loaded / e.total) * 100);
        progressBar.value = percent;
        progressText.textContent = `${percent}%`;
      });
      
      // Start periodic pings to keep the connection alive
      var pingInterval = setInterval(function() {
        var pingXhr = new XMLHttpRequest();
        pingXhr.open('GET', '/ocean/ping', true);
        pingXhr.send();
      }, 2000); // Send a ping every 2 seconds


      const formData = new FormData(form);
      xhr.open(form.method, form.action, true);
      xhr.onreadystatechange = () => {
        if (xhr.readyState === XMLHttpRequest.DONE) {
          if (xhr.status === 200) {
            
            const redirectUrl = xhr.responseURL;
            if (redirectUrl) {
              window.location.href = redirectUrl;
            }
          }
        }
      };
      // Clear the ping interval when the upload is done
      xhr.onloadend = function() {
        clearInterval(pingInterval);
    };
      xhr.send(formData);
    });
  }
  




  // function uploadFormWithProgress(formId, progressBarId, progressTextId, url) {
  //   const form = document.getElementById(formId);
  //   const progressBar = document.getElementById(progressBarId);
  //   const progressText = document.getElementById(progressTextId);
  //   const submitButton = form.querySelector('button[type="submit"]');
  
  //   submitButton.addEventListener('click', (e) => {
  //     e.preventDefault();
  //     const xhr = new XMLHttpRequest();
  //     xhr.upload.addEventListener('progress', (e) => {
  //       const percent = Math.round((e.loaded / e.total) * 100);
  //       progressBar.value = percent;
  //       progressText.textContent = `${percent}%`;
  //     });
  
  //     const formData = new FormData(form);
  //     xhr.open('POST', url, true);
  //     xhr.onreadystatechange = () => {
  //       if (xhr.readyState === XMLHttpRequest.DONE) {
  //         if (xhr.status === 200) {
  //           const redirectUrl = xhr.responseURL;
  //           if (redirectUrl) {
  //             window.location.href = redirectUrl;
  //           }
  //         }
  //       }
  //     };
  //     xhr.send(formData);
  //   });
  // }

/**
 * Handles form submission with a progress bar and periodic server pings.
 * 
 * @param {string} formId - The ID of the form element to be submitted.
 * @param {string} progressBarId - The ID of the progress bar element to display upload progress.
 * @param {string} progressTextId - The ID of the text element to display upload percentage.
 * 
 * This function adds an event listener to the specified form, preventing its default submission behavior.
 * It displays the progress bar and text during the file upload, updating them with the current upload percentage.
 * Periodic pings are sent to the server every 2 seconds to keep the connection alive. Once the upload is complete,
 * the ping interval is cleared. If the server responds with a redirect URL upon successful upload, the page is redirected.
 */
  function uploadFormWithProgress(formId, progressBarId, progressTextId) {

    const form = document.getElementById(formId);
    const progressBar = document.getElementById(progressBarId);
    const progressText = document.getElementById(progressTextId);
  
    form.addEventListener('submit', (e) => {  
      e.preventDefault();

      progressBar.style="display: block";
      progressText.style="display: block";
      const xhr = new XMLHttpRequest();
      xhr.upload.addEventListener('progress', (e) => {
        const percent = Math.round((e.loaded / e.total) * 100);
        progressBar.value = percent;
        progressText.textContent = `${percent}%`;
      });
      
      // Start periodic pings to keep the connection alive
      var pingInterval = setInterval(function() {
        var pingXhr = new XMLHttpRequest();
        pingXhr.open('GET', '/ocean/ping', true);
        pingXhr.send();
      }, 2000); // Send a ping every 2 seconds


      const formData = new FormData(form);
      xhr.open(form.method, form.action, true);
      xhr.onreadystatechange = () => {
        if (xhr.readyState === XMLHttpRequest.DONE) {
          if (xhr.status === 200) {
            
            const redirectUrl = xhr.responseURL;
            if (redirectUrl) {
              window.location.href = redirectUrl;
            }
          }
        }
      };
      // Clear the ping interval when the upload is done
      xhr.onloadend = function() {
        clearInterval(pingInterval);
    };
      xhr.send(formData);
    });
  }
  




  // function uploadFormWithProgress(formId, progressBarId, progressTextId, url) {
  //   const form = document.getElementById(formId);
  //   const progressBar = document.getElementById(progressBarId);
  //   const progressText = document.getElementById(progressTextId);
  //   const submitButton = form.querySelector('button[type="submit"]');
  
  //   submitButton.addEventListener('click', (e) => {
  //     e.preventDefault();
  //     const xhr = new XMLHttpRequest();
  //     xhr.upload.addEventListener('progress', (e) => {
  //       const percent = Math.round((e.loaded / e.total) * 100);
  //       progressBar.value = percent;
  //       progressText.textContent = `${percent}%`;
  //     });
  
  //     const formData = new FormData(form);
  //     xhr.open('POST', url, true);
  //     xhr.onreadystatechange = () => {
  //       if (xhr.readyState === XMLHttpRequest.DONE) {
  //         if (xhr.status === 200) {
  //           const redirectUrl = xhr.responseURL;
  //           if (redirectUrl) {
  //             window.location.href = redirectUrl;
  //           }
  //         }
  //       }
  //     };
  //     xhr.send(formData);
  //   });
  // }